"""Tests for CRDT registers: LWWRegister and MVRegister.

Registers are implemented as Operation-based CRDTs (CmRDT).
Instead of merge(), they use:
- write(): Execute a local write operation
- apply_operation(): Apply an operation from another replica
- get_operations(): Get unsync'd operations to send to other replicas
"""

from src import LWWRegister, MVRegister


class TestLWWRegister:
    """Tests for Last-Writer-Wins Register (Operation-based)."""

    def test_single_write_read(self):
        """Test basic write and read operation."""
        r = LWWRegister()
        r.write(value=42, timestamp=1.0, replica_id='A')
        assert r.read() == 42

    def test_overwrite_with_higher_timestamp(self):
        """Test that higher timestamp wins."""
        r = LWWRegister()
        r.write(value=10, timestamp=1.0, replica_id='A')
        r.write(value=20, timestamp=2.0, replica_id='B')
        assert r.read() == 20

    def test_lower_timestamp_write_ignored(self):
        """Test that lower timestamp write is ignored."""
        r = LWWRegister()
        r.write(value=20, timestamp=2.0, replica_id='A')
        r.write(value=10, timestamp=1.0, replica_id='B')
        assert r.read() == 20

    def test_equal_timestamp_tiebreaker(self):
        """Test tiebreaker when timestamps are equal."""
        r = LWWRegister()
        r.write(value=10, timestamp=1.0, replica_id='A')
        r.write(value=20, timestamp=1.0, replica_id='B')
        # Should use replica_id lexicographically
        result = r.read()
        assert result in [10, 20]  # Implementation dependent on tiebreaker
        
    def test_operation_replication(self):
        """Test that operations can be replicated between replicas."""
        r1 = LWWRegister()
        r2 = LWWRegister()
        
        r1.write(value=100, timestamp=5.0, replica_id='A')
        
        # Get operations from r1 and apply to r2
        ops = r1.get_operations()
        for op, metadata in ops:
            r2.apply_operation(op, metadata)
        
        assert r2.read() == 100

    def test_replicas_converge_with_concurrent_writes(self):
        """Test that replicas converge after exchanging concurrent writes."""
        r1 = LWWRegister()
        r2 = LWWRegister()
        
        # Concurrent writes from different replicas
        r1.write(value=10, timestamp=1.0, replica_id='A')
        r2.write(value=20, timestamp=2.0, replica_id='B')
        
        # Exchange operations
        ops1 = r1.get_operations()
        ops2 = r2.get_operations()
        
        for op, metadata in ops1:
            r2.apply_operation(op, metadata)
        for op, metadata in ops2:
            r1.apply_operation(op, metadata)
        
        # Both should have the same result (higher timestamp wins)
        assert r1.read() == r2.read() == 20

    def test_operations_are_commutative(self):
        """Test that operations can be applied in any order with same result."""
        r1 = LWWRegister()
        r2 = LWWRegister()
        
        r1.write(value=10, timestamp=1.0, replica_id='A')
        r1.write(value=30, timestamp=3.0, replica_id='C')
        
        r2.write(value=20, timestamp=2.0, replica_id='B')
        
        # Apply operations from r1 to a test replica in one order
        test1 = LWWRegister()
        ops = r1.get_operations() + r2.get_operations()
        for op, metadata in ops:
            test1.apply_operation(op, metadata)
        
        # Apply operations in reverse order to another test replica
        test2 = LWWRegister()
        for op, metadata in reversed(ops):
            test2.apply_operation(op, metadata)
        
        # Both should reach the same result
        assert test1.read() == test2.read()

    def test_empty_register_read_none(self):
        """Test that reading from empty register returns None."""
        r = LWWRegister()
        assert r.read() is None

    def test_multiple_writes_same_replica(self):
        """Test multiple writes from same replica."""
        r = LWWRegister()
        r.write(value=1, timestamp=1.0, replica_id='A')
        assert r.read() == 1
        r.write(value=2, timestamp=2.0, replica_id='A')
        assert r.read() == 2

    def test_get_operations_returns_unsync_ops(self):
        """Test that get_operations returns operations to sync."""
        r = LWWRegister()
        
        # No operations yet
        assert r.get_operations() == []
        
        # After write, should have operations
        r.write(value=42, timestamp=1.0, replica_id='A')
        ops = r.get_operations()
        assert len(ops) > 0


class TestMVRegister:
    """Tests for Multi-Value Register (Operation-based)."""

    def test_single_write_read(self):
        """Test basic write and read."""
        r = MVRegister('replica_1')
        r.write(10)
        assert 10 in r.read()

    def test_causally_related_writes_single_value(self):
        """Test that causally related writes result in single value."""
        r = MVRegister('replica_1')
        r.write(10)
        r.write(20)
        # The second write is causally after the first
        values = r.read()
        assert len(values) == 1
        assert 20 in values

    def test_concurrent_writes_multiple_values(self):
        """Test that concurrent writes from different replicas are both kept."""
        r1 = MVRegister('replica_1')
        r2 = MVRegister('replica_2')
        
        r1.write(10)
        r2.write(20)
        
        # Exchange operations
        ops1 = r1.get_operations()
        ops2 = r2.get_operations()
        
        for op, metadata in ops1:
            r2.apply_operation(op, metadata)
        for op, metadata in ops2:
            r1.apply_operation(op, metadata)
        
        # Both should have both values
        assert 10 in r1.read()
        assert 20 in r1.read()
        assert 10 in r2.read()
        assert 20 in r2.read()

    def test_concurrent_writes_and_replicate(self):
        """Test replicating concurrent values."""
        r1 = MVRegister('A')
        r2 = MVRegister('B')
        
        r1.write(100)
        r2.write(200)
        
        ops1 = r1.get_operations()
        ops2 = r2.get_operations()
        
        for op, metadata in ops1:
            r2.apply_operation(op, metadata)
        for op, metadata in ops2:
            r1.apply_operation(op, metadata)
        
        assert r1.read() == {100, 200}
        assert r2.read() == {100, 200}

    def test_causal_write_resolution(self):
        """Test that causally later writes subsume earlier ones."""
        r = MVRegister('r1')
        
        r.write('value_a')
        ops_a = r.get_operations()
        
        r.write('value_b')
        ops_b = r.get_operations()
        
        # Apply both operations from same replica
        # value_b should subsume value_a
        result = r.read()
        assert 'value_b' in result

    def test_empty_register_read_empty_set(self):
        """Test that reading from empty register returns empty set."""
        r = MVRegister('r1')
        assert r.read() == set()

    def test_three_way_convergence(self):
        """Test convergence of three replicas."""
        r1 = MVRegister('r1')
        r2 = MVRegister('r2')
        r3 = MVRegister('r3')
        
        r1.write(1)
        r2.write(2)
        r3.write(3)
        
        # Collect all operations
        all_ops = r1.get_operations() + r2.get_operations() + r3.get_operations()
        
        # Apply all operations to each replica
        for r in [r1, r2, r3]:
            for op, metadata in all_ops:
                r.apply_operation(op, metadata)
        
        # All should have converged
        expected = {1, 2, 3}
        assert r1.read() == expected
        assert r2.read() == expected
        assert r3.read() == expected

    def test_operations_commutative(self):
        """Test that operations are commutative."""
        r1 = MVRegister('r1')
        r2 = MVRegister('r2')
        r3 = MVRegister('r3')
        
        r1.write('A')
        r2.write('B')
        r3.write('C')
        
        ops = r1.get_operations() + r2.get_operations() + r3.get_operations()
        
        # Apply in order to test_a
        test_a = MVRegister('test_a')
        for op, metadata in ops:
            test_a.apply_operation(op, metadata)
        
        # Apply in reverse order to test_b
        test_b = MVRegister('test_b')
        for op, metadata in reversed(ops):
            test_b.apply_operation(op, metadata)
        
        # Both should reach the same result
        assert test_a.read() == test_b.read()
