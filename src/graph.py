"""CRDT Implementations - Graph module.

Graph is implemented as a State-based CvRDT.
"""

from collections.abc import Hashable
from typing import Any, Dict, List, Tuple, Set
from .crdt_base import CvRDT

Edge = Tuple[Hashable, Hashable]


def _successors(edges: Set[Edge]) -> Dict[Hashable, List[Hashable]]:
    """Список смежности: вершина -> вершины, в которые из неё идут рёбра."""
    graph: Dict[Hashable, List[Hashable]] = {}
    for u, v in edges:
        graph.setdefault(u, []).append(v)
    return graph


def _reachable(edges: Set[Edge], start: Hashable, target: Hashable) -> bool:
    """Есть ли путь start ->* target (DFS по стеку)."""
    graph = _successors(edges)
    stack, visited = [start], {start}
    while stack:
        node = stack.pop()
        if node == target:
            return True
        for nxt in graph.get(node, []):
            if nxt not in visited:
                visited.add(nxt)
                stack.append(nxt)
    return False


def _has_cycle(edges: Set[Edge]) -> bool:
    """Есть ли цикл: ребро u->v лежит на цикле, если из v достижима u."""
    return any(_reachable(edges, v, u) for u, v in edges)


class AddOnlyDAG(CvRDT):
    """Add-only Monotonic Directed Acyclic Graph (DAG, State-based CvRDT).
    
    A graph where nodes and edges can only be added, never removed.
    The graph must remain acyclic (no cycles allowed).
    
    When attempting to add an edge that would create a cycle, the operation
    is rejected (returns False).
    
    Merge operation combines all nodes and edges from both graphs,
    checking acyclicity.
    
    Example:
        >>> g1 = AddOnlyDAG()
        >>> g2 = AddOnlyDAG()
        >>> g1.add_node('A')
        >>> g1.add_node('B')
        >>> g1.add_edge('A', 'B')  # True, no cycle
        True
        >>> g1.add_edge('B', 'A')  # False, would create cycle
        False
        >>> g2.add_node('C')
        >>> g2.add_edge('B', 'C')
        >>> g1.merge(g2)
        >>> g1.nodes()
        {'A', 'B', 'C'}
        >>> g1.edges()
        {('A', 'B'), ('B', 'C')}
    """

    def __init__(self) -> None:
        """Initialize an empty DAG."""
        self._nodes: Set[Hashable] = set()
        self._edges: Set[Tuple[Hashable, Hashable]] = set()

    def add_node(self, node: Any) -> None:
        """Add a node to the graph.
        
        Args:
            node: The node to add (can be any hashable type)
        """
        self._nodes.add(node)

    def add_edge(self, from_node: Any, to_node: Any) -> bool:
        """Add a directed edge from from_node to to_node.
        
        Args:
            from_node: The source node
            to_node: The destination node
        
        Returns:
            True if edge was added successfully
            False if adding the edge would create a cycle
        
        Note:
            If nodes don't exist, they are added automatically.
        """
        # Ребро u->v замыкает цикл, если из v уже можно дойти до u (или это петля u->u)
        if from_node == to_node or _reachable(self._edges, to_node, from_node):
            return False
        self._nodes.update((from_node, to_node))
        self._edges.add((from_node, to_node))
        return True

    def has_edge(self, from_node: Any, to_node: Any) -> bool:
        """Check if a directed edge exists.
        
        Args:
            from_node: The source node
            to_node: The destination node
        
        Returns:
            True if edge from_node -> to_node exists
        """
        return (from_node, to_node) in self._edges

    def nodes(self) -> Set[Any]:
        """Return all nodes in the graph."""
        return set(self._nodes)

    def edges(self) -> Set[Tuple[Any, Any]]:
        """Return all edges in the graph.
        
        Returns:
            A set of tuples (from_node, to_node)
        """
        return set(self._edges)

    def merge(self, other: "AddOnlyDAG") -> None:
        """Merge another DAG into this one.
        
        Combines all nodes and edges. If the merge would create a cycle,
        raises an exception (as both DAGs should be acyclic already,
        this indicates a logical error).
        
        Args:
            other: Another DAG to merge
        
        Raises:
            ValueError: If merging would create a cycle (shouldn't happen
                       if both DAGs are valid)
        """
        if not isinstance(other, AddOnlyDAG):
            raise TypeError("can merge only AddOnlyDAG")
        edges = self._edges | other._edges
        # Каждый граф ацикличен сам по себе, но конкурентные A->B и B->A вместе дают цикл.
        # Проверяем до изменения состояния, чтобы при ошибке реплика осталась прежней.
        if _has_cycle(edges):
            raise ValueError("merge would create a cycle")
        self._nodes |= other._nodes
        self._edges = edges

    def __eq__(self, other: Any) -> bool:
        """Check if two DAGs have the same nodes and edges."""
        return isinstance(other, AddOnlyDAG) and self._nodes == other._nodes and self._edges == other._edges

    def __repr__(self) -> str:
        """Return string representation of the DAG."""
        return f"AddOnlyDAG(nodes={self._nodes}, edges={self._edges})"