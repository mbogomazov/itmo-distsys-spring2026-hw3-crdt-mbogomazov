"""CRDT Implementations - Registers module.

Registers are implemented as Operation-based CRDTs (CmRDT).
Each write operation is tracked and replicated across all replicas.
"""

from typing import Any, Dict, Optional, List, Tuple, TypedDict
from .crdt_base import CmRDT


class LWWMeta(TypedDict):
    """Метаданные операции записи LWW-регистра."""

    timestamp: float
    replica_id: str


class MVMeta(TypedDict):
    """Метаданные операции записи MV-регистра."""

    replica_id: str
    vv: Dict[str, int]


VersionVector = Dict[str, int]


def vv_leq(a: VersionVector, b: VersionVector) -> bool:
    """a <= b покомпонентно: всё, что видел a, видел и b (a в причинном прошлом b)."""
    return all(count <= b.get(replica_id, 0) for replica_id, count in a.items())


class LWWRegister(CmRDT):
    """Last-Writer-Wins Register (Operation-based CmRDT).

    An operation-based register that stores the last written value, resolved by timestamp.
    When multiple writes occur, the one with the highest timestamp wins.

    If timestamps are equal, a tiebreaker (replica_id) is used.

    How it works (Operation-based):
    - Each write(value, timestamp, replica_id) is an operation
    - Operations are replicated to all replicas
    - Each replica applies all operations and keeps only the one with highest timestamp
    - Commutativity: operations can be applied in any order, result is the same

    Example:
        >>> r = LWWRegister()
        >>> r.write(value=42, timestamp=1.0, replica_id='A')
        >>> r.read()
        42
        >>> r.write(value=99, timestamp=2.0, replica_id='B')
        >>> r.read()
        99
    """

    def __init__(self) -> None:
        """Initialize an empty LWW register."""
        self._value: Any = None
        # Ключ победителя (timestamp, replica_id); None — записей ещё не было
        self._stamp: Optional[Tuple[float, str]] = None
        # Локальные записи, ещё не отданные через get_operations()
        self._outbox: List[Tuple[Any, LWWMeta]] = []

    def read(self) -> Optional[Any]:
        """Read the current value from the register.

        Returns:
            The current value or None if register is empty
        """
        return self._value

    def write(self, value: Any, timestamp: float, replica_id: str) -> None:
        """Execute a write operation.

        Args:
            value: The value to write
            timestamp: The timestamp of this write
            replica_id: The ID of the replica performing the write
        """
        metadata: LWWMeta = {"timestamp": timestamp, "replica_id": replica_id}
        self.apply_operation(value, metadata)
        self._outbox.append((value, metadata))

    def apply_operation(self, operation: Any, metadata: Any = None) -> None:
        """Apply a write operation from another replica.

        Args:
            operation: The value that was written
            metadata: Dict with 'timestamp' and 'replica_id'
        """
        stamp = (metadata["timestamp"], metadata["replica_id"])
        # Побеждает больший (timestamp, replica_id): при равных метках — больший replica_id.
        # Строгое ">" делает повторное применение той же операции no-op (идемпотентность).
        if self._stamp is None or stamp > self._stamp:
            self._value = operation
            self._stamp = stamp

    def get_operations(self) -> List[tuple]:
        """Get all unsync'd operations.

        Returns:
            List of (value, metadata) tuples where metadata has 'timestamp' and 'replica_id'
        """
        # Отдаём накопленные операции и очищаем буфер: они считаются отправленными
        ops, self._outbox = self._outbox, []
        return ops

    def __eq__(self, other: Any) -> bool:
        """Check if two LWW registers have the same state."""
        return (
            isinstance(other, LWWRegister)
            and self._value == other._value
            and self._stamp == other._stamp
        )

    def __repr__(self) -> str:
        """Return string representation of the register state."""
        return f"LWWRegister(value={self._value!r}, stamp={self._stamp})"


class MVRegister(CmRDT):
    """Multi-Value Register (Operation-based CmRDT).

    An operation-based register that can hold multiple values in case of concurrent writes.
    Uses version vectors to track causal history.

    When writes are causally related (one happens-after another), only the newer value is kept.
    When writes are concurrent (incomparable in the causal order), both values are stored.

    How it works (Operation-based):
    - Each write(value) is an operation
    - Each operation has metadata: (replica_id, version_vector)
    - Operations are replicated to all replicas
    - Each replica applies operations atomically
    - Version vectors determine causal relationships

    Example:
        >>> r1 = MVRegister('replica_1')
        >>> r2 = MVRegister('replica_2')
        >>> r1.write(10)
        >>> r2.write(20)
        >>> # Sync: r1 and r2 exchange operations
        >>> r1.get_operations()  # r1 sends its write(10) to r2
        >>> r2.apply_operation(10, metadata={'replica_id': 'replica_1', 'vv': {...}})
        >>> r1.apply_operation(20, metadata={'replica_id': 'replica_2', 'vv': {...}})
        >>> r1.read()
        {10, 20}  # Both values since they were concurrent
    """

    def __init__(self, replica_id: str = "A") -> None:
        """Initialize an empty MV register.

        Args:
            replica_id: The ID of this replica
        """
        self._replica_id = replica_id
        # Всё, что эта реплика видела: покомпонентный max по всем применённым записям
        self._vv: VersionVector = {}
        # Текущие попарно конкурентные записи: (значение, version vector записи)
        self._entries: List[Tuple[Any, VersionVector]] = []
        self._outbox: List[Tuple[Any, MVMeta]] = []

    def write(self, value: Any) -> None:
        """Execute a write operation from this replica.

        This increments the version vector for this replica and records the write operation.

        Args:
            value: The value to write
        """
        # Новая запись "видит" всё, что видела реплика, плюс одно своё событие,
        # поэтому она доминирует над всеми текущими значениями.
        vv = dict(self._vv)
        vv[self._replica_id] = vv.get(self._replica_id, 0) + 1
        metadata: MVMeta = {"replica_id": self._replica_id, "vv": vv}
        self.apply_operation(value, metadata)
        self._outbox.append((value, metadata))

    def read(self) -> set:
        """Read all current values.

        Returns:
            A set of all causally incomparable values
        """
        return {value for value, _ in self._entries}

    def apply_operation(self, operation: Any, metadata: Any = None) -> None:
        """Apply a write operation to this replica.

        Args:
            operation: The value that was written
            metadata: Dict with 'replica_id' and 'vv' (version vector)
        """
        op_vv: VersionVector = dict(metadata["vv"])
        # Уже видели эту запись (или что-то после неё) — дубликат или устаревшая запись
        if vv_leq(op_vv, self._vv):
            return
        # Выкидываем значения из причинного прошлого новой записи, конкурентные оставляем
        self._entries = [(v, vv) for v, vv in self._entries if not vv_leq(vv, op_vv)]
        self._entries.append((operation, op_vv))
        for replica_id, count in op_vv.items():
            self._vv[replica_id] = max(self._vv.get(replica_id, 0), count)

    def get_operations(self) -> List[tuple]:
        """Get all unsync'd operations.

        Returns:
            List of (operation, metadata) tuples
        """
        ops, self._outbox = self._outbox, []
        return ops

    def _state(self) -> set:
        """Множество записей (значение, VV) без учёта порядка — для сравнения реплик."""
        return {(value, frozenset(vv.items())) for value, vv in self._entries}

    def __eq__(self, other: Any) -> bool:
        """Check if two MV registers have the same values."""
        return isinstance(other, MVRegister) and self._state() == other._state()

    def __repr__(self) -> str:
        """Return string representation of the register state."""
        return f"MVRegister({self._replica_id!r}, entries={self._entries})"
