"""Tests for CRDT graph: Add-only Monotonic DAG."""

from copy import deepcopy
from src import AddOnlyDAG


class TestAddOnlyDAG:
    """Tests for Add-only Directed Acyclic Graph (DAG)."""

    def test_add_single_node(self):
        """Test adding a single node."""
        g = AddOnlyDAG()
        g.add_node('A')
        assert 'A' in g.nodes()

    def test_add_multiple_nodes(self):
        """Test adding multiple nodes."""
        g = AddOnlyDAG()
        g.add_node('A')
        g.add_node('B')
        g.add_node('C')
        assert g.nodes() == {'A', 'B', 'C'}

    def test_add_edge_between_nodes(self):
        """Test adding edge between nodes."""
        g = AddOnlyDAG()
        g.add_node('A')
        g.add_node('B')
        result = g.add_edge('A', 'B')
        
        assert result is True
        assert g.has_edge('A', 'B')
        assert ('A', 'B') in g.edges()

    def test_add_edge_creates_nodes(self):
        """Test that adding edge creates nodes automatically."""
        g = AddOnlyDAG()
        result = g.add_edge('A', 'B')
        
        assert result is True
        assert 'A' in g.nodes()
        assert 'B' in g.nodes()

    def test_reject_cycle_simple(self):
        """Test that simple cycle (A->B->A) is rejected."""
        g = AddOnlyDAG()
        g.add_edge('A', 'B')
        result = g.add_edge('B', 'A')
        
        assert result is False

    def test_reject_cycle_self_loop(self):
        """Test that self-loop is rejected."""
        g = AddOnlyDAG()
        result = g.add_edge('A', 'A')
        
        assert result is False

    def test_reject_cycle_complex(self):
        """Test that complex cycle is rejected."""
        g = AddOnlyDAG()
        g.add_edge('A', 'B')
        g.add_edge('B', 'C')
        g.add_edge('C', 'D')
        
        # Trying to create cycle A->B->C->D->A
        result = g.add_edge('D', 'A')
        assert result is False

    def test_linear_path(self):
        """Test creating a linear path."""
        g = AddOnlyDAG()
        assert g.add_edge('A', 'B') is True
        assert g.add_edge('B', 'C') is True
        assert g.add_edge('C', 'D') is True
        
        edges = g.edges()
        assert ('A', 'B') in edges
        assert ('B', 'C') in edges
        assert ('C', 'D') in edges

    def test_tree_structure(self):
        """Test creating a tree structure (no cycles)."""
        g = AddOnlyDAG()
        # Create a tree:
        #     A
        #    / \
        #   B   C
        #   |
        #   D
        
        g.add_edge('A', 'B')
        g.add_edge('A', 'C')
        g.add_edge('B', 'D')
        
        assert len(g.nodes()) == 4
        assert len(g.edges()) == 3

    def test_diamond_structure(self):
        """Test creating a diamond structure (no cycles)."""
        g = AddOnlyDAG()
        # Create diamond:
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        
        g.add_edge('A', 'B')
        g.add_edge('A', 'C')
        g.add_edge('B', 'D')
        g.add_edge('C', 'D')
        
        assert len(g.nodes()) == 4
        assert len(g.edges()) == 4

    def test_reject_back_edge(self):
        """Test that back edges creating cycles are rejected."""
        g = AddOnlyDAG()
        g.add_edge('A', 'B')
        g.add_edge('A', 'C')
        g.add_edge('B', 'D')
        g.add_edge('C', 'D')
        
        # Try to add back edge D->A
        result = g.add_edge('D', 'A')
        assert result is False

    def test_merge_combines_nodes(self):
        """Test that merge combines nodes from both graphs."""
        g1 = AddOnlyDAG()
        g2 = AddOnlyDAG()
        
        g1.add_node('A')
        g1.add_node('B')
        g2.add_node('C')
        g2.add_node('D')
        
        g1.merge(g2)
        
        assert g1.nodes() == {'A', 'B', 'C', 'D'}

    def test_merge_combines_edges(self):
        """Test that merge combines edges from both graphs."""
        g1 = AddOnlyDAG()
        g2 = AddOnlyDAG()
        
        g1.add_edge('A', 'B')
        g2.add_edge('B', 'C')
        
        g1.merge(g2)
        
        edges = g1.edges()
        assert ('A', 'B') in edges
        assert ('B', 'C') in edges

    def test_merge_preserves_acyclicity(self):
        """Test that merge preserves acyclicity."""
        g1 = AddOnlyDAG()
        g2 = AddOnlyDAG()
        
        g1.add_edge('A', 'B')
        g1.add_edge('B', 'C')
        g2.add_edge('C', 'D')
        
        g1.merge(g2)
        
        # Try to add back edge - should still be rejected
        result = g1.add_edge('D', 'A')
        assert result is False

    def test_has_edge_false_for_nonexistent(self):
        """Test that has_edge returns False for nonexistent edges."""
        g = AddOnlyDAG()
        g.add_edge('A', 'B')
        
        assert g.has_edge('B', 'A') is False
        assert g.has_edge('A', 'C') is False

    def test_empty_graph(self):
        """Test empty graph."""
        g = AddOnlyDAG()
        assert g.nodes() == set()
        assert g.edges() == set()

    def test_nodes_different_types(self):
        """Test nodes can be different types."""
        g = AddOnlyDAG()
        g.add_edge(1, 2)
        g.add_edge(2, 'C')
        g.add_edge('C', (4, 5))
        
        nodes = g.nodes()
        assert 1 in nodes
        assert 2 in nodes
        assert 'C' in nodes
        assert (4, 5) in nodes

    def test_merge_two_independents_graphs(self):
        """Test merging two independent (non-overlapping) graphs."""
        g1 = AddOnlyDAG()
        g2 = AddOnlyDAG()
        
        # Graph 1: A->B
        g1.add_edge('A', 'B')
        
        # Graph 2: C->D
        g2.add_edge('C', 'D')
        
        g1.merge(g2)
        
        assert g1.nodes() == {'A', 'B', 'C', 'D'}
        assert ('A', 'B') in g1.edges()
        assert ('C', 'D') in g1.edges()

    def test_cannot_remove_node_or_edge(self):
        """Test that add-only graph doesn't have remove operations."""
        g = AddOnlyDAG()
        g.add_edge('A', 'B')
        
        # Should not have remove methods
        assert not hasattr(g, 'remove_node')
        assert not hasattr(g, 'remove_edge')

    def test_complex_dag_scenario(self):
        """Test a complex DAG with multiple paths."""
        g = AddOnlyDAG()
        
        # Create complex DAG:
        #     A
        #    / \
        #   B   C
        #  / \ /
        # D   E
        #  \ /
        #   F
        
        edges = [
            ('A', 'B'), ('A', 'C'),
            ('B', 'D'), ('B', 'E'), ('C', 'E'),
            ('D', 'F'), ('E', 'F')
        ]
        
        for src, dst in edges:
            result = g.add_edge(src, dst)
            assert result is True, f"Should be able to add edge {src}->{dst}"
        
        # Verify structure
        assert len(g.nodes()) == 6
        assert len(g.edges()) == 7
        
        # Try to add edge that would create cycle
        result = g.add_edge('F', 'A')
        assert result is False

    def test_merge_conflict_free(self):
        """Test that merge of two DAGs is conflict-free."""
        g1 = AddOnlyDAG()
        g2 = AddOnlyDAG()
        
        g1.add_edge('A', 'B')
        g2.add_edge('B', 'C')
        
        # Merge both ways should give same result
        merged1 = AddOnlyDAG()
        merged1.merge(g1)
        merged1.merge(g2)
        
        merged2 = AddOnlyDAG()
        merged2.merge(g2)
        merged2.merge(g1)
        
        assert merged1.nodes() == merged2.nodes()
        assert merged1.edges() == merged2.edges()

def test_add_only_dag_merge_commutativity():
    """Test that AddOnlyDAG merge is commutative."""
    g1 = AddOnlyDAG()
    g2 = AddOnlyDAG()
    
    g1.add_node('A')
    g1.add_node('B')
    g1.add_edge('A', 'B')
    
    g2.add_node('C')
    g2.add_edge('B', 'C')
    
    result_1 = deepcopy(g1)
    result_1.merge(g2)
    
    result_2 = deepcopy(g2)
    result_2.merge(g1)
    
    assert result_1 == result_2, "DAG merge should be commutative"


def test_add_only_dag_merge_associativity():
    """Test that AddOnlyDAG merge is associative."""
    g1 = AddOnlyDAG()
    g2 = AddOnlyDAG()
    g3 = AddOnlyDAG()
    
    g1.add_node('A')
    g1.add_node('B')
    g1.add_edge('A', 'B')
    
    g2.add_node('C')
    g2.add_edge('B', 'C')
    
    g3.add_node('D')
    g3.add_edge('C', 'D')
    
    result_1 = deepcopy(g1)
    result_1.merge(g2)
    result_1.merge(g3)
    
    result_2 = deepcopy(g1)
    temp = deepcopy(g2)
    temp.merge(g3)
    result_2.merge(temp)
    
    assert result_1 == result_2, "DAG merge should be associative"