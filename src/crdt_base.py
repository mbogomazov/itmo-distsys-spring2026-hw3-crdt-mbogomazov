"""Base classes for CRDT implementations."""

from abc import ABC, abstractmethod
from typing import Any, List

class CvRDT(ABC):
    """Abstract base class for State-based CRDTs (Convergent Replicated Data Type).
    
    State-based CRDTs (CvRDT) synchronize by exchanging full states.
    
    Key properties:
    - Synchronization: full state is sent between replicas
    - merge() operation must be: commutative, associative, and idempotent
    - All replicas converge by merging states
    
    Example:
        Replica A executes operations independently, creating state S_A.
        Replica B executes operations independently, creating state S_B.
        When they synchronize:
            merge(S_A, S_B) = merge(S_B, S_A)  (commutative)
            All replicas converge to the same state.
    """

    @abstractmethod
    def merge(self, other: "CvRDT") -> None:
        """Merge another CvRDT state into this one.
        
        The merge operation must satisfy:
        1. Commutativity: merge(A, B) == merge(B, A)
        2. Associativity: merge(merge(A, B), C) == merge(A, merge(B, C))
        3. Idempotence: merge(A, A) == A
        
        Args:
            other: Another CvRDT instance of the same type to merge with this one
        
        Raises:
            TypeError: If other is not the same CvRDT type
        """
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        """Check if two CvRDT instances have the same state.
        
        This is essential for testing merge properties.
        """
        raise NotImplementedError

    @abstractmethod
    def __repr__(self) -> str:
        """Return a string representation of the CvRDT state."""
        raise NotImplementedError


class CmRDT(ABC):
    """Abstract base class for Operation-based CRDTs (Commutative Replicated Data Type).
    
    Operation-based CRDTs (CmRDT) synchronize by exchanging operations.
    
    Key properties:
    - Synchronization: only operations are sent between replicas
    - All operations must be commutative (order doesn't matter)
    - Each replica applies operations atomically
    - Causal ordering is preserved through metadata (e.g., vector clocks)
    
    Example:
        Replica A: executes write(10, ts=1)
        Replica B: executes write(20, ts=2)
        Each replica applies both operations. Result is deterministic regardless of order.
    """

    @abstractmethod
    def apply_operation(self, operation: Any, metadata: Any = None) -> None:
        """Apply an operation to this replica.
        
        The operation must be deterministic - applying the same operation
        twice should result in the same state as applying it once.
        
        Args:
            operation: The operation to apply
            metadata: Optional metadata (e.g., timestamp, version vector, replica_id)
        """
        raise NotImplementedError

    @abstractmethod
    def get_operations(self) -> List[tuple]:
        """Get the list of operations to sync with other replicas.
        
        Returns:
            List of (operation, metadata) tuples that haven't been synced yet
        """
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        """Check if two CmRDT instances have the same state."""
        raise NotImplementedError

    @abstractmethod
    def __repr__(self) -> str:
        """Return a string representation of the CmRDT state."""
        raise NotImplementedError
