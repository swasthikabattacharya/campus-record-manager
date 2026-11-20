"""Unit test to verify CustomHashMap and BST functionality."""
import random
from structures.hash_map import CustomHashMap
from structures.bst import BST

def test_hash_map():
    hm = CustomHashMap(initial_capacity=4, load_factor_threshold=0.75)
    records = [
        ("25RBAID0001", "Saritha"),
        ("25RBAID0002", "Swasthika"),
        ("25RBAID0017", "Abdur"),
        ("25RBAIM0065", "Srujana"),
        ("25RBAID0009", "Divya"),
        ("25RBAID0040", "Rahul"),
        ("25RBAID0080", "Ananya"),
        ("25RBAID0033", "Vikram"),
        ("25RBAID0050", "Pooja"),
    ]

    for student_id, name in records:
        hm.put(student_id, {"id": student_id, "name": name})

    assert len(hm) == 9
    assert hm.capacity > 4, f"Capacity should have resized from 4, got {hm.capacity}"

    # Verify retrieval with lowercase and spaces
    assert hm.get(" 25rbaid0002 ")["name"] == "Swasthika"
    assert hm.contains("25RBAID0017")
    assert not hm.contains("UNKNOWN_ID")

    # Test remove
    assert hm.remove("25rbaid0001") is True
    assert len(hm) == 8
    assert not hm.contains("25RBAID0001")
    assert hm.remove("25RBAID0001") is False

    print("CustomHashMap test passed successfully!")

def test_bst():
    bst = BST()
    names = [
        ("Meera", "ID_1"),
        ("Arjun", "ID_2"),
        ("Sneha", "ID_3"),
        ("Divya", "ID_4"),
        ("Saritha", "ID_5"),
        ("Swasthika", "ID_6"),
        ("Abdur", "ID_7"),
        ("Srujana", "ID_8"),
        ("Arjun", "ID_9"),  # Duplicate name
    ]

    for name, sid in names:
        bst.insert(name, sid)

    inorder = bst.inorder()
    extracted_names = [n for n, sid in inorder]
    expected_sorted = sorted([n for n, sid in names], key=lambda x: x.lower())
    assert extracted_names == expected_sorted, f"In-order mismatch: {extracted_names} vs {expected_sorted}"

    # Test prefix search
    s_prefix = bst.search_prefix("S")
    s_names = [n for n, sid in s_prefix]
    for n in s_names:
        assert n.lower().startswith("s"), f"{n} does not start with S"
    assert len(s_names) == 4  # Saritha, Sneha, Srujana, Swasthika

    # Test delete duplicate name node specifically
    bst.delete("Arjun", "ID_2")
    remaining_names = [n for n, sid in bst.inorder()]
    assert remaining_names.count("Arjun") == 1
    # ID_9 should still be there
    assert ("Arjun", "ID_9") in bst.inorder()

    # Test delete two-children root node
    bst.delete("Meera", "ID_1")
    assert ("Meera", "ID_1") not in bst.inorder()

    print("BST test passed successfully!")

if __name__ == "__main__":
    test_hash_map()
    test_bst()
    print("All core data structure tests passed!")
