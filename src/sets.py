"""CRDT Implementations - Sets module.

All sets are implemented as State-based CvRDTs.
"""

from collections.abc import Hashable
from typing import Any, Dict, Optional, Set, Tuple
from uuid import uuid4
from .crdt_base import CvRDT


class GrowOnlySet(CvRDT):
    """Grow-only Set (Add-only Set, State-based CvRDT).

    A set that can only grow - adding elements is allowed, but removing is not.
    This is the simplest CRDT.

    The merge operation is simply set union.

    Example:
        >>> s1 = GrowOnlySet()
        >>> s2 = GrowOnlySet()
        >>> s1.add(1)
        >>> s1.add(2)
        >>> s2.add(2)
        >>> s2.add(3)
        >>> s1.merge(s2)
        >>> s1.elements()
        {1, 2, 3}
    """

    def __init__(self) -> None:
        """Initialize an empty grow-only set."""
        self._items: Set[Hashable] = set()

    def add(self, element: Any) -> None:
        """Add an element to the set.

        This operation is idempotent - adding the same element twice
        has the same effect as adding it once.
        """
        self._items.add(element)

    def contains(self, element: Any) -> bool:
        """Check if an element is in the set."""
        return element in self._items

    def elements(self) -> Set[Any]:
        """Return all elements in the set."""
        return set(self._items)

    def merge(self, other: "GrowOnlySet") -> None:
        """Merge another grow-only set into this one.

        The result contains all elements from both sets (set union).
        """
        if not isinstance(other, GrowOnlySet):
            raise TypeError("can merge only GrowOnlySet")
        self._items |= other._items

    def __eq__(self, other: Any) -> bool:
        """Check if two grow-only sets have the same elements."""
        return isinstance(other, GrowOnlySet) and self._items == other._items

    def __repr__(self) -> str:
        """Return string representation of the set."""
        return f"GrowOnlySet({self._items})"


class PNSet(CvRDT):
    """Positive-Negative Set (State-based CvRDT).

    A set that supports both add and remove operations. Uses unique IDs (uid)
    to track which specific instance of an element was added/removed.

    An element is in the set if:
    - It exists in the "add set" (for some uid)
    - AND it does not exist in the "remove set" (for that same uid)

    Problem: If an element is added, then removed, then the add operation
    is replayed from another branch, the element will reappear.
    This is a known limitation of PN-Sets.

    Example:
        >>> s = PNSet()
        >>> uid1 = 'add1'
        >>> s.add(1, uid1)
        >>> s.contains(1)
        True
        >>> s.remove(1, uid1)
        >>> s.contains(1)
        False
    """

    def __init__(self) -> None:
        """Initialize an empty PN-Set."""
        self._p: Set[Tuple[Hashable, str]] = set()  # добавления (element, uid)
        self._n: Set[Tuple[Hashable, str]] = set()  # удаления (element, uid) — tombstones

    def add(self, element: Any, uid: str) -> None:
        """Add an element with a unique ID.

        Args:
            element: The element to add
            uid: A unique identifier for this add operation
        """
        self._p.add((element, uid))

    def remove(self, element: Any, uid: str) -> None:
        """Remove an element by removing a specific uid.

        Args:
            element: The element to remove
            uid: The uid of the add operation to remove
        """
        # Удалять можно только то, что реплика видела в P (иначе удалять нечего).
        # Пару не стираем из P (merge вернул бы её обратно), а кладём в N навсегда.
        if (element, uid) in self._p:
            self._n.add((element, uid))

    def contains(self, element: Any) -> bool:
        """Check if an element is in the set.

        An element is in the set if there exists at least one uid for which
        (element, uid) is in P but not in N.
        """
        return any(e == element for e, _ in self._p - self._n)

    def elements(self) -> Set[Any]:
        """Return all elements currently in the set."""
        return {e for e, _ in self._p - self._n}

    def merge(self, other: "PNSet") -> None:
        """Merge another PN-Set into this one.

        The merged set contains:
        - Union of add sets: P_merged = P1 ∪ P2
        - Union of remove sets: N_merged = N1 ∪ N2
        """
        if not isinstance(other, PNSet):
            raise TypeError("can merge only PNSet")
        self._p |= other._p
        self._n |= other._n

    def __eq__(self, other: Any) -> bool:
        """Check if two PN-Sets have the same state."""
        return isinstance(other, PNSet) and self._p == other._p and self._n == other._n

    def __repr__(self) -> str:
        """Return string representation of the set."""
        return f"PNSet(P={self._p}, N={self._n})"


class UniqueSet(CvRDT):
    """Unique-Set (Observed-Remove Set simplified, State-based CvRDT).

    A set where each add operation generates a unique tag (like a UUID).
    Elements can be removed by removing their specific tag.

    This avoids the "tombstone" problem of PN-Sets: if you remove a tagged
    add, it won't reappear with the same tag.

    Example:
        >>> s = UniqueSet()
        >>> uid1 = s.add(1)  # Returns unique tag
        >>> s.contains(1)
        True
        >>> s.remove(1, uid1)
        >>> s.contains(1)
        False
    """

    def __init__(self) -> None:
        """Initialize an empty Unique-Set."""
        self._tags: Dict[str, Hashable] = {}  # tag -> element (все когда-либо добавленные)
        self._removed: Set[str] = set()  # удалённые теги (tombstones)

    def add(self, element: Any) -> str:
        """Add an element and return its unique tag.

        Args:
            element: The element to add

        Returns:
            A unique tag (string) for this add operation
        """
        # UUID глобально уникален, поэтому каждое add — отдельный "экземпляр" элемента
        tag = str(uuid4())
        self._tags[tag] = element
        return tag

    def remove(self, element: Any, uid: str) -> None:
        """Remove a specific instance of an element.

        Args:
            element: The element to remove
            uid: The unique tag of the add operation to remove
        """
        # Тег уникален, значит однозначно указывает на одно add; element нужен только для API.
        # Тег может быть ещё не виден локально — tombstone сработает, когда add придёт через merge.
        self._removed.add(uid)

    def _alive(self) -> Dict[str, Hashable]:
        """Теги, которые добавлены и ещё не удалены."""
        return {tag: e for tag, e in self._tags.items() if tag not in self._removed}

    def contains(self, element: Any) -> bool:
        """Check if an element is in the set.

        An element is in the set if there exists at least one tag for it
        in the set.
        """
        return element in self._alive().values()

    def elements(self) -> Set[Any]:
        """Return all elements currently in the set."""
        return set(self._alive().values())

    def merge(self, other: "UniqueSet") -> None:
        """Merge another Unique-Set into this one.

        The merged set is the union of all (element, tag) pairs from both sets.
        """
        if not isinstance(other, UniqueSet):
            raise TypeError("can merge only UniqueSet")
        self._tags.update(other._tags)  # у одного тега всегда один и тот же элемент
        self._removed |= other._removed

    def __eq__(self, other: Any) -> bool:
        """Check if two Unique-Sets have the same state."""
        return (
            isinstance(other, UniqueSet)
            and self._tags == other._tags
            and self._removed == other._removed
        )

    def __repr__(self) -> str:
        """Return string representation of the set."""
        return f"UniqueSet(tags={self._tags}, removed={self._removed})"


class ORSet(CvRDT):
    """Observed-Remove Set (OR-Set, State-based CvRDT).

    A fully featured set that supports both add and remove without anomalies.
    Uses causal metadata to ensure that removes only remove observed adds.

    Unlike PN-Set, OR-Set solves the problem where a removed element could
    be re-added by a concurrent add operation. In OR-Set, this is allowed
    but only if the add truly happened after the remove in causal order.

    Example:
        >>> s1 = ORSet('replica_1')
        >>> s2 = ORSet('replica_2')
        >>> uid1 = s1.add(1)
        >>> s1.merge(s2)  # s2 now knows about the add
        >>> s2.remove(1, uid1)
        >>> s2.merge(s1)  # s1 doesn't know about the remove yet
        >>> s1.merge(s2)  # Now both have converged
        >>> s1.elements()
        set()  # 1 was removed
    """

    def __init__(self, replica_id: str = "A") -> None:
        """Initialize an empty OR-Set.

        Args:
            replica_id: The ID of this replica (for causal tracking)
        """
        self._replica_id = replica_id
        # Как в PN-Set, но элементы — пары (element, uid):
        # P — все добавления, N — «корзина» удалённых пар (tombstones)
        self._p: Set[Tuple[Hashable, str]] = set()
        self._n: Set[Tuple[Hashable, str]] = set()

    def add(self, element: Any) -> str:
        """Add an element and return its unique tag.

        Args:
            element: The element to add

        Returns:
            A unique tag identifying this add operation
        """
        # Каждое add получает новый уникальный uid, поэтому новое add не «съедается»
        # старым удалением: удаляются только пары, которые реплика уже видела (add-wins)
        uid = f"{self._replica_id}:{uuid4()}"
        self._p.add((element, uid))
        return uid

    def remove(self, element: Any, uid: Optional[str] = None) -> None:
        """Remove a specific instance of an element.

        Args:
            element: The element to remove
            uid: The tag of the add operation to remove
        """
        # Observed remove: переносим в N только пары, которые реплика наблюдает в P.
        # uid задан — одну пару; uid=None — все видимые пары этого элемента.
        for e, tag in self._p - self._n:
            if e == element and (uid is None or tag == uid):
                self._n.add((e, tag))

    def contains(self, element: Any) -> bool:
        """Check if an element is in the set."""
        return element in self.elements()

    def elements(self) -> Set[Any]:
        """Return all elements currently in the set."""
        return {e for e, _ in self._p - self._n}

    def merge(self, other: "ORSet") -> None:
        """Merge another OR-Set into this one.

        After merge, all (element, tag) pairs from both sets are preserved,
        and all removals are respected (if both have seen an add and a remove,
        it's removed).
        """
        if not isinstance(other, ORSet):
            raise TypeError("can merge only ORSet")
        # Объединение по отдельности: коммутативно, ассоциативно, идемпотентно
        self._p |= other._p
        self._n |= other._n

    def __eq__(self, other: Any) -> bool:
        """Check if two OR-Sets have the same state."""
        return isinstance(other, ORSet) and self._p == other._p and self._n == other._n

    def __repr__(self) -> str:
        """Return string representation of the set."""
        return f"ORSet({self._replica_id!r}, P={self._p}, N={self._n})"
