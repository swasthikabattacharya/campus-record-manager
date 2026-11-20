"""
Custom Binary Search Tree (BST) Implementation for Campus Record Manager.
Keeps student names in alphabetical order for sorted listings and prefix searches.
Each node stores the student name and Student ID.
"""

class BSTNode:
    # Initialize a tree node holding student name and student ID
    def __init__(self, name, student_id):
        self.name = name.strip()
        self.student_id = student_id.strip().upper()
        self.left = None
        self.right = None


class BST:
    # Initialize an empty Binary Search Tree
    def __init__(self):
        self.root = None

    # Insert a new student name and student ID into the tree
    def insert(self, name, student_id):
        clean_name = name.strip()
        clean_id = student_id.strip().upper()
        self.root = self._insert_node(self.root, clean_name, clean_id)

    # Helper function to recursively insert a node at the correct position
    def _insert_node(self, node, name, student_id):
        if node is None:
            return BSTNode(name, student_id)
        
        # Compare names case-insensitively
        if name.lower() < node.name.lower():
            node.left = self._insert_node(node.left, name, student_id)
        else:
            node.right = self._insert_node(node.right, name, student_id)
        return node

    # Delete a student record by name and student ID from the tree
    def delete(self, name, student_id):
        clean_name = name.strip()
        clean_id = student_id.strip().upper()
        self.root = self._delete_node(self.root, clean_name, clean_id)

    # Helper function to find the node with minimum value in a subtree
    def _find_min(self, node):
        curr = node
        while curr.left is not None:
            curr = curr.left
        return curr

    # Helper function to recursively delete a specific student node
    def _delete_node(self, node, name, student_id):
        if node is None:
            return None

        target = name.lower()
        curr = node.name.lower()

        if target < curr:
            node.left = self._delete_node(node.left, name, student_id)
        elif target > curr:
            node.right = self._delete_node(node.right, name, student_id)
        else:
            # Name matches; check if student_id matches as well
            if node.student_id == student_id:
                # Case 1: Node has no left child
                if node.left is None:
                    return node.right
                # Case 2: Node has no right child
                if node.right is None:
                    return node.left
                # Case 3: Node has two children - replace with in-order successor
                successor = self._find_min(node.right)
                node.name = successor.name
                node.student_id = successor.student_id
                node.right = self._delete_node(node.right, successor.name, successor.student_id)
            else:
                # Same name but different ID, continues in right subtree where duplicates are inserted
                node.right = self._delete_node(node.right, name, student_id)
        return node

    # Perform in-order traversal to retrieve all students sorted alphabetically
    def inorder(self):
        result = []
        
        def walk(node):
            if node is not None:
                walk(node.left)
                result.append((node.name, node.student_id))
                walk(node.right)

        walk(self.root)
        return result

    # Find all students whose name begins with the given prefix
    def search_prefix(self, prefix):
        pref = prefix.strip().lower()
        if not pref:
            return self.inorder()

        result = []

        def walk(node):
            if node is None:
                return

            curr_name = node.name.lower()

            # If current name starts with prefix, check both subtrees to collect all matches
            if curr_name.startswith(pref):
                walk(node.left)
                result.append((node.name, node.student_id))
                walk(node.right)
            elif curr_name < pref:
                # Current name comes before prefix in alphabet, target can only be in right subtree
                walk(node.right)
            else:
                # Current name comes after prefix in alphabet, target can only be in left subtree
                walk(node.left)

        walk(self.root)
        return result

    # Clear all nodes from the tree
    def clear(self):
        self.root = None

    # Return total count of nodes in the tree
    def count(self):
        def _count(node):
            if node is None:
                return 0
            return 1 + _count(node.left) + _count(node.right)
        return _count(self.root)
