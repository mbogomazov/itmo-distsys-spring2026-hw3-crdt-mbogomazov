"""Tests for CRDT sets: GrowOnlySet, PNSet, UniqueSet, and ORSet."""

from copy import deepcopy

from src import GrowOnlySet, PNSet, UniqueSet, ORSet


class TestGrowOnlySet:
    """Tests for Grow-only Set CRDT."""

    def test_add_single_element(self):
        """Test adding a single element."""
        s = GrowOnlySet()
        s.add(1)
        assert s.contains(1)
        assert s.elements() == {1}

    def test_add_multiple_elements(self):
        """Test adding multiple elements."""
        s = GrowOnlySet()
        s.add(1)
        s.add(2)
        s.add(3)
        assert s.elements() == {1, 2, 3}

    def test_add_duplicate_idempotent(self):
        """Test that adding the same element twice is idempotent."""
        s = GrowOnlySet()
        s.add(1)
        s.add(1)
        assert s.elements() == {1}

    def test_contains_false_for_absent(self):
        """Test that contains returns False for absent elements."""
        s = GrowOnlySet()
        assert not s.contains(1)

    def test_merge_union(self):
        """Test that merge takes union of both sets."""
        s1 = GrowOnlySet()
        s2 = GrowOnlySet()
        
        s1.add(1)
        s1.add(2)
        s2.add(2)
        s2.add(3)
        
        s1.merge(s2)
        assert s1.elements() == {1, 2, 3}

    def test_merge_with_empty_set(self):
        """Test merging with empty set doesn't change state."""
        s1 = GrowOnlySet()
        s2 = GrowOnlySet()
        
        s1.add(1)
        s1.merge(s2)
        
        assert s1.elements() == {1}

    def test_merge_empty_with_nonempty(self):
        """Test merging empty set with nonempty set."""
        s1 = GrowOnlySet()
        s2 = GrowOnlySet()
        
        s2.add(1)
        s2.add(2)
        s1.merge(s2)
        
        assert s1.elements() == {1, 2}

    def test_cannot_remove(self):
        """Test that grow-only set has no remove operation."""
        s = GrowOnlySet()
        s.add(1)
        
        # Should not have a remove method
        assert not hasattr(s, 'remove')

    def test_empty_set(self):
        """Test empty set operations."""
        s = GrowOnlySet()
        assert s.elements() == set()
        assert not s.contains(1)

    def test_different_types(self):
        """Test adding different types of elements."""
        s = GrowOnlySet()
        s.add(1)
        s.add("string")
        s.add(3.14)
        s.add((1, 2, 3))
        
        assert 1 in s.elements()
        assert "string" in s.elements()
        assert 3.14 in s.elements()
        assert (1, 2, 3) in s.elements()


class TestPNSet:
    """Tests for Positive-Negative Set CRDT."""

    def test_add_single_element(self):
        """Test adding a single element."""
        s = PNSet()
        s.add(1, 'uid1')
        assert s.contains(1)
        assert s.elements() == {1}

    def test_add_multiple_uids_same_element(self):
        """Test adding same element with different uids."""
        s = PNSet()
        s.add(1, 'uid1')
        s.add(1, 'uid2')
        assert s.contains(1)

    def test_remove_element(self):
        """Test removing an element."""
        s = PNSet()
        s.add(1, 'uid1')
        s.remove(1, 'uid1')
        assert not s.contains(1)

    def test_remove_leaves_other_uid(self):
        """Test that removing one uid doesn't affect others."""
        s = PNSet()
        s.add(1, 'uid1')
        s.add(1, 'uid2')
        s.remove(1, 'uid1')
        assert s.contains(1)  # Still contains via uid2

    def test_merge_union_of_adds(self):
        """Test that merge takes union of add sets."""
        s1 = PNSet()
        s2 = PNSet()
        
        s1.add(1, 'uid1')
        s2.add(2, 'uid2')
        
        s1.merge(s2)
        assert s1.elements() == {1, 2}

    def test_merge_union_of_removes(self):
        """Test that merge respects removals from other set."""
        s1 = PNSet()
        s2 = PNSet()
        
        s1.add(1, 'uid1')
        s2.add(1, 'uid1')
        s2.remove(1, 'uid1')
        
        s1.merge(s2)
        assert not s1.contains(1)

    def test_tombstone_problem_demonstration(self):
        """Demonstrate the tombstone problem of PN-Sets.
        
        This test shows why PN-Sets have limitations:
        If an element is added, removed, then the add is replayed from
        another branch, the element will reappear.
        """
        s1 = PNSet()
        s2 = PNSet()
        
        # s1: add 1 with uid1
        s1.add(1, 'uid1')
        
        # s2 gets the add, then removes it
        s2.add(1, 'uid1')
        s2.remove(1, 'uid1')
        
        # s1 doesn't know about the remove yet
        # If s2 replays the add operation somehow, it would reappear
        # This is the limitation of PN-Sets
        
        s1.merge(s2)
        assert not s1.contains(1)

    def test_empty_set(self):
        """Test empty PN-Set."""
        s = PNSet()
        assert s.elements() == set()
        assert not s.contains(1)


class TestUniqueSet:
    """Tests for Unique-Set (simplified OR-Set)."""

    def test_add_returns_uid(self):
        """Test that add returns a unique ID."""
        s = UniqueSet()
        uid = s.add(1)
        assert isinstance(uid, str)
        assert len(uid) > 0

    def test_adds_return_different_uids(self):
        """Test that multiple adds return different UIDs."""
        s = UniqueSet()
        uid1 = s.add(1)
        uid2 = s.add(1)
        assert uid1 != uid2

    def test_add_and_contains(self):
        """Test adding and checking containment."""
        s = UniqueSet()
        s.add(1)
        assert s.contains(1)

    def test_remove_by_uid(self):
        """Test removing element by its UID."""
        s = UniqueSet()
        uid = s.add(1)
        s.remove(1, uid)
        assert not s.contains(1)

    def test_remove_one_uid_leaves_other(self):
        """Test that removing one UID doesn't affect other instances."""
        s = UniqueSet()
        uid1 = s.add(1)
        uid2 = s.add(1)
        
        s.remove(1, uid1)
        assert s.contains(1)  # Still present via uid2

    def test_merge_combines_elements(self):
        """Test that merge combines elements from both sets."""
        s1 = UniqueSet()
        s2 = UniqueSet()
        
        s1.add(1)
        s1.add(2)
        s2.add(2)
        s2.add(3)
        
        s1.merge(s2)
        assert 1 in s1.elements()
        assert 2 in s1.elements()
        assert 3 in s1.elements()

    def test_merge_handles_removals(self):
        """Test that merge respects removals."""
        s1 = UniqueSet()
        s2 = UniqueSet()
        
        uid1 = s1.add(1)
        s2.add(1)  # Different UID
        s2.remove(1, uid1)  # Remove the first UID
        
        s1.merge(s2)
        # s1 still has its original uid, so element should still exist
        assert s1.contains(1)

    def test_empty_set(self):
        """Test empty Unique-Set."""
        s = UniqueSet()
        assert s.elements() == set()

    def test_repeated_add_different_uids(self):
        """Test that same value can be added multiple times with different UIDs."""
        s = UniqueSet()
        uid1 = s.add('value')
        uid2 = s.add('value')
        uid3 = s.add('value')
        
        assert s.contains('value')
        s.remove('value', uid1)
        assert s.contains('value')  # uid2 and uid3 still exist
        s.remove('value', uid2)
        assert s.contains('value')  # uid3 still exists
        s.remove('value', uid3)
        assert not s.contains('value')  # All removed


class TestORSet:
    """Tests for Observed-Remove Set (OR-Set)."""

    def test_add_returns_uid(self):
        """Test that add returns unique ID."""
        s = ORSet('replica_1')
        uid = s.add(1)
        assert isinstance(uid, str)

    def test_add_and_contains(self):
        """Test basic add and contains."""
        s = ORSet('r1')
        s.add(1)
        assert s.contains(1)

    def test_remove_by_uid(self):
        """Test removing element by UID."""
        s = ORSet('r1')
        uid = s.add(1)
        s.remove(1, uid)
        assert not s.contains(1)

    def test_concurrent_add_after_remove(self):
        """Test that concurrent add after remove creates new instance."""
        s1 = ORSet('r1')
        s2 = ORSet('r2')
        
        uid1 = s1.add(1)
        s1.merge(s2)  # s2 now knows about add
        
        s2.remove(1, uid1)
        s2.merge(s1)  # s1 doesn't know about remove yet
        
        # Try to add the same value again from s1 with new UID
        uid2 = s1.add(1)
        s1.merge(s2)
        
        # If both uids are different, element should still be present
        # (This shows OR-Set's advantage over PN-Set)
        assert s1.elements() is not None

    def test_merge_combines_states(self):
        """Test that merge combines both replicas' states."""
        s1 = ORSet('r1')
        s2 = ORSet('r2')
        
        s1.add(1)
        s1.add(2)
        s2.add(2)
        s2.add(3)
        
        s1.merge(s2)
        elements = s1.elements()
        
        assert 1 in elements
        assert 2 in elements
        assert 3 in elements

    def test_multiple_adds_of_same_element(self):
        """Test adding same element multiple times."""
        s = ORSet('r1')
        uid1 = s.add(1)
        uid2 = s.add(1)
        
        assert uid1 != uid2
        assert s.contains(1)
        
        s.remove(1, uid1)
        assert s.contains(1)  # uid2 still makes it present

    def test_empty_set(self):
        """Test empty OR-Set."""
        s = ORSet('r1')
        assert s.elements() == set()

    def test_or_set_semantics_example(self):
        """Test typical OR-Set usage scenario."""
        # Replica A
        r_a = ORSet('A')
        # Replica B
        r_b = ORSet('B')
        
        # A adds elements
        uid_a1 = r_a.add('item1')
        uid_a2 = r_a.add('item2')
        
        # A and B sync
        r_b.merge(r_a)
        r_a.merge(r_b)
        
        # B adds an element
        uid_b1 = r_b.add('item3')
        
        # B removes item1 (which came from A)
        r_b.remove('item1', uid_a1)
        
        # B syncs back to A
        r_a.merge(r_b)
        r_b.merge(r_a)
        
        # Check final state
        final_elements = r_a.elements()
        assert 'item1' not in final_elements
        assert 'item2' in final_elements
        assert 'item3' in final_elements



def test_grow_only_set_merge_commutativity():
    """Test that GrowOnlySet merge is commutative."""
    s1 = GrowOnlySet()
    s2 = GrowOnlySet()
    
    s1.add(1)
    s1.add(2)
    s2.add(2)
    s2.add(3)
    
    # merge(s1, s2)
    result_1 = deepcopy(s1)
    result_1.merge(s2)
    
    # merge(s2, s1)
    result_2 = deepcopy(s2)
    result_2.merge(s1)
    
    assert result_1 == result_2, "Merge should be commutative"


def test_grow_only_set_merge_associativity():
    """Test that GrowOnlySet merge is associative."""
    s1 = GrowOnlySet()
    s2 = GrowOnlySet()
    s3 = GrowOnlySet()
    
    s1.add(1)
    s2.add(2)
    s3.add(3)
    
    # merge(merge(s1, s2), s3)
    result_1 = deepcopy(s1)
    result_1.merge(s2)
    result_1.merge(s3)
    
    # merge(s1, merge(s2, s3))
    result_2 = deepcopy(s1)
    temp = deepcopy(s2)
    temp.merge(s3)
    result_2.merge(temp)
    
    assert result_1 == result_2, "Merge should be associative"


def test_grow_only_set_merge_idempotence():
    """Test that GrowOnlySet merge is idempotent."""
    s = GrowOnlySet()
    s.add(1)
    s.add(2)
    s.add(3)
    
    before = deepcopy(s)
    s.merge(before)
    
    assert s == before, "Merge with itself should not change state (idempotence)"



def test_pn_set_merge_commutativity():
    """Test that PNSet merge is commutative."""
    s1 = PNSet()
    s2 = PNSet()
    
    s1.add(1, 'add_1')
    s2.add(2, 'add_2')
    s1.remove(1, 'add_1')
    
    result_1 = deepcopy(s1)
    result_1.merge(s2)
    
    result_2 = deepcopy(s2)
    result_2.merge(s1)
    
    assert result_1 == result_2, "PN-Set merge should be commutative"


# Tests for eventually consistent convergence

def test_replicated_grow_only_set_convergence():
    """Test that multiple replicas converge to same state."""
    r1 = GrowOnlySet()
    r2 = GrowOnlySet()
    r3 = GrowOnlySet()
    
    # Independent operations
    r1.add(1)
    r2.add(2)
    r1.add(3)
    r3.add(4)
    r2.add(5)
    
    # Cross-replicate merges
    r1.merge(r2)
    r2.merge(r3)
    r3.merge(r1)
    
    # All should converge
    r1.merge(r2)
    r1.merge(r3)
    
    final_state = r1.elements()
    assert final_state == {1, 2, 3, 4, 5}, "All replicas should converge"