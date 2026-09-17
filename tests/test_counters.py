"""Tests for CRDT counters: GrowOnlyCounter and PNCounter."""

from copy import deepcopy
from src import GrowOnlyCounter, PNCounter


class TestGrowOnlyCounter:
    """Tests for Grow-only Counter CRDT."""

    def test_initial_value_zero(self):
        """Test that initial counter value is 0."""
        c = GrowOnlyCounter()
        assert c.value() == 0

    def test_single_increment(self):
        """Test incrementing counter by 1."""
        c = GrowOnlyCounter()
        c.increment('replica_1', 1)
        assert c.value() == 1

    def test_multiple_increments_same_replica(self):
        """Test multiple increments from same replica."""
        c = GrowOnlyCounter()
        c.increment('replica_1', 5)
        c.increment('replica_1', 3)
        assert c.value() == 8

    def test_increments_from_different_replicas(self):
        """Test increments from different replicas sum up."""
        c = GrowOnlyCounter()
        c.increment('replica_1', 5)
        c.increment('replica_2', 3)
        c.increment('replica_1', 2)
        assert c.value() == 10

    def test_merge_takes_max_per_replica(self):
        """Test that merge takes maximum value for each replica."""
        c1 = GrowOnlyCounter()
        c2 = GrowOnlyCounter()
        
        c1.increment('replica_1', 5)
        c2.increment('replica_1', 3)
        
        c1.merge(c2)
        # Should have max(5, 3) = 5 for replica_1
        assert c1.value() == 5

    def test_merge_combines_different_replicas(self):
        """Test that merge combines updates from different replicas."""
        c1 = GrowOnlyCounter()
        c2 = GrowOnlyCounter()
        
        c1.increment('replica_1', 5)
        c2.increment('replica_2', 3)
        
        c1.merge(c2)
        # Should sum both replicas: 5 + 3 = 8
        assert c1.value() == 8

    def test_merge_complex_scenario(self):
        """Test merge with complex scenario of multiple replicas."""
        c1 = GrowOnlyCounter()
        c2 = GrowOnlyCounter()
        c3 = GrowOnlyCounter()
        
        c1.increment('r1', 1)
        c1.increment('r2', 1)
        
        c2.increment('r1', 2)
        c2.increment('r3', 1)
        
        c3.increment('r2', 2)
        c3.increment('r3', 1)
        
        c1.merge(c2)
        # c1 now has: r1=max(1,2)=2, r2=1, r3=1 -> total=4
        assert c1.value() == 4
        
        c1.merge(c3)
        # c1 now has: r1=2, r2=max(1,2)=2, r3=max(1,1)=1 -> total=5
        assert c1.value() == 5

    def test_cannot_decrement(self):
        """Test that grow-only counter doesn't have decrement."""
        c = GrowOnlyCounter()
        assert not hasattr(c, 'decrement')

    def test_large_increment(self):
        """Test incrementing by large values."""
        c = GrowOnlyCounter()
        c.increment('r1', 1000000)
        assert c.value() == 1000000

    def test_merge_with_empty_counter(self):
        """Test merging with empty counter."""
        c1 = GrowOnlyCounter()
        c2 = GrowOnlyCounter()
        
        c1.increment('r1', 5)
        c1.merge(c2)  # Merge with 0
        
        assert c1.value() == 5

    def test_default_increment_value_one(self):
        """Test that increment without value defaults to 1."""
        c = GrowOnlyCounter()
        c.increment('r1')  # No value specified
        assert c.value() == 1


class TestPNCounter:
    """Tests for Positive-Negative Counter CRDT."""

    def test_initial_value_zero(self):
        """Test that initial counter value is 0."""
        c = PNCounter()
        assert c.value() == 0

    def test_single_increment(self):
        """Test incrementing counter."""
        c = PNCounter()
        c.increment('r1', 5)
        assert c.value() == 5

    def test_single_decrement(self):
        """Test decrementing counter."""
        c = PNCounter()
        c.decrement('r1', 3)
        assert c.value() == -3

    def test_increment_and_decrement(self):
        """Test increment and decrement operations."""
        c = PNCounter()
        c.increment('r1', 10)
        c.decrement('r1', 3)
        assert c.value() == 7

    def test_multiple_replicas_increment(self):
        """Test increments from multiple replicas."""
        c = PNCounter()
        c.increment('r1', 5)
        c.increment('r2', 3)
        assert c.value() == 8

    def test_multiple_replicas_decrement(self):
        """Test decrements from multiple replicas."""
        c = PNCounter()
        c.decrement('r1', 5)
        c.decrement('r2', 3)
        assert c.value() == -8

    def test_mixed_operations(self):
        """Test mixed increment and decrement operations."""
        c = PNCounter()
        c.increment('r1', 100)
        c.decrement('r1', 30)
        c.increment('r2', 20)
        c.decrement('r2', 5)
        # (100 + 20) - (30 + 5) = 120 - 35 = 85
        assert c.value() == 85

    def test_merge_increments(self):
        """Test merging counters with increments."""
        c1 = PNCounter()
        c2 = PNCounter()
        
        c1.increment('r1', 5)
        c2.increment('r1', 3)
        
        c1.merge(c2)
        # merge takes max for each replica: max(5, 3) = 5
        assert c1.value() == 5

    def test_merge_decrements(self):
        """Test merging counters with decrements."""
        c1 = PNCounter()
        c2 = PNCounter()
        
        c1.decrement('r1', 5)
        c2.decrement('r1', 3)
        
        c1.merge(c2)
        # merge takes max for each replica: max(5, 3) = 5
        assert c1.value() == -5

    def test_merge_mixed_operations(self):
        """Test merging with mixed increment/decrement operations."""
        c1 = PNCounter()
        c2 = PNCounter()
        
        c1.increment('r1', 10)
        c1.decrement('r2', 5)
        
        c2.increment('r1', 3)
        c2.increment('r2', 2)
        
        c1.merge(c2)
        # After merge: increments = max(10, 3) + max(0, 2) = 10 + 2 = 12
        #              decrements = max(0, 0) + max(5, 0) = 0 + 5 = 5
        # value = 12 - 5 = 7
        assert c1.value() == 7

    def test_concurrent_increments_and_decrements(self):
        """Test scenario with concurrent operations from multiple replicas."""
        c1 = PNCounter()
        c2 = PNCounter()
        c3 = PNCounter()
        
        # Replica 1
        c1.increment('r1', 100)
        
        # Replica 2
        c2.increment('r2', 50)
        
        # Replica 3
        c3.decrement('r3', 30)
        
        # Cross merges
        c1.merge(c2)
        c1.merge(c3)
        
        # Total: 100 + 50 - 30 = 120
        assert c1.value() == 120

    def test_negative_result(self):
        """Test that counter can be negative."""
        c = PNCounter()
        c.decrement('r1', 50)
        c.increment('r1', 30)
        assert c.value() == -20

    def test_merge_convergence(self):
        """Test that all replicas converge to same value after merges."""
        c1 = PNCounter()
        c2 = PNCounter()
        c3 = PNCounter()
        
        c1.increment('r1', 10)
        c2.decrement('r2', 5)
        c3.increment('r3', 3)
        
        # All merge with each other
        c1.merge(c2)
        c1.merge(c3)
        c2.merge(c1)
        c3.merge(c1)
        
        # All should have same final value
        expected_value = 10 - 5 + 3
        assert c1.value() == expected_value
        assert c2.value() == expected_value
        assert c3.value() == expected_value

    def test_default_operations(self):
        """Test default increment/decrement values."""
        c = PNCounter()
        c.increment('r1')  # Default 1
        c.decrement('r2')  # Default 1
        assert c.value() == 0

    def test_replica_independence(self):
        """Test that operations from different replicas are independent."""
        c = PNCounter()
        c.increment('r1', 100)
        c.decrement('r1', 50)
        c.increment('r2', 25)
        c.decrement('r2', 10)
        
        # r1: 100 - 50 = 50
        # r2: 25 - 10 = 15
        # Total: 50 + 15 = 65
        assert c.value() == 65


def test_grow_only_counter_merge_commutativity():
    """Test that GrowOnlyCounter merge is commutative."""
    c1 = GrowOnlyCounter()
    c2 = GrowOnlyCounter()
    
    c1.increment('replica_1', 5)
    c1.increment('replica_2', 2)
    c2.increment('replica_1', 3)
    c2.increment('replica_3', 4)
    
    result_1 = deepcopy(c1)
    result_1.merge(c2)
    
    result_2 = deepcopy(c2)
    result_2.merge(c1)
    
    assert result_1 == result_2, "Counter merge should be commutative"


def test_grow_only_counter_merge_associativity():
    """Test that GrowOnlyCounter merge is associative."""
    c1 = GrowOnlyCounter()
    c2 = GrowOnlyCounter()
    c3 = GrowOnlyCounter()
    
    c1.increment('r1', 1)
    c2.increment('r1', 2)
    c3.increment('r1', 3)
    
    result_1 = deepcopy(c1)
    result_1.merge(c2)
    result_1.merge(c3)
    
    result_2 = deepcopy(c1)
    temp = deepcopy(c2)
    temp.merge(c3)
    result_2.merge(temp)
    
    assert result_1 == result_2, "Counter merge should be associative"


def test_grow_only_counter_merge_idempotence():
    """Test that GrowOnlyCounter merge is idempotent."""
    c = GrowOnlyCounter()
    c.increment('replica_1', 10)
    
    before = deepcopy(c)
    c.merge(before)
    
    assert c == before, "Counter merge should be idempotent"


def test_pn_counter_merge_commutativity():
    """Test that PNCounter merge is commutative."""
    c1 = PNCounter()
    c2 = PNCounter()
    
    c1.increment('r1', 5)
    c1.decrement('r1', 2)
    c2.increment('r2', 3)
    c2.decrement('r2', 1)
    
    result_1 = deepcopy(c1)
    result_1.merge(c2)
    
    result_2 = deepcopy(c2)
    result_2.merge(c1)
    
    assert result_1 == result_2, "PN-Counter merge should be commutative"


def test_pn_counter_merge_associativity():
    """Test that PNCounter merge is associative."""
    c1 = PNCounter()
    c2 = PNCounter()
    c3 = PNCounter()
    
    c1.increment('r1', 1)
    c2.decrement('r1', 1)
    c3.increment('r1', 1)
    
    result_1 = deepcopy(c1)
    result_1.merge(c2)
    result_1.merge(c3)
    
    result_2 = deepcopy(c1)
    temp = deepcopy(c2)
    temp.merge(c3)
    result_2.merge(temp)
    
    assert result_1 == result_2, "PN-Counter merge should be associative"

def test_replicated_grow_only_counter_convergence():
    """Test counter convergence across replicas."""
    c1 = GrowOnlyCounter()
    c2 = GrowOnlyCounter()
    
    # Operations
    c1.increment('r1', 10)
    c2.increment('r2', 5)
    
    # Merge
    c1.merge(c2)
    c2.merge(c1)
    
    assert c1.value() == c2.value() == 15, "Counters should converge"
