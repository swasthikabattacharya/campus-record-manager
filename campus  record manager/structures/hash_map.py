"""
Custom Chained Hash Map Implementation for Campus Record Manager.
Uses separate chaining for collision resolution and dynamic resizing at 0.75 load factor.
Keys are normalized using strip().upper().
No built-in Python dictionary is used as the hash map storage.
"""

class HashNode:
    # Initialize a key-value node stored inside a bucket chain
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.next = None


class CustomHashMap:
    # Initialize the hash map with a default capacity and 0.75 load factor threshold
    def __init__(self, initial_capacity=16, load_factor_threshold=0.75):
        self.capacity = initial_capacity
        self.load_factor_threshold = load_factor_threshold
        self.size = 0
        # Buckets array containing heads of linked lists (chaining)
        self.buckets = [None] * self.capacity

    # Normalize key to uppercase and stripped string
    def _normalize_key(self, key):
        if key is None:
            return ""
        return str(key).strip().upper()

    # Calculate bucket index using a polynomial rolling hash function
    def _hash(self, key):
        normalized = self._normalize_key(key)
        hash_val = 0
        for char in normalized:
            hash_val = (hash_val * 31 + ord(char)) & 0xFFFFFFFF
        return hash_val % self.capacity

    # Double the capacity and rehash all existing elements into new buckets
    def _resize(self):
        old_buckets = self.buckets
        self.capacity *= 2
        self.buckets = [None] * self.capacity
        self.size = 0

        for head in old_buckets:
            curr = head
            while curr is not None:
                self.put(curr.key, curr.value)
                curr = curr.next

    # Insert or update a key-value pair in the hash map
    def put(self, key, value):
        norm_key = self._normalize_key(key)
        if not norm_key:
            raise ValueError("Key cannot be empty.")

        # Check if resize is needed before adding new element
        if (self.size + 1) / self.capacity >= self.load_factor_threshold:
            self._resize()

        idx = self._hash(norm_key)
        curr = self.buckets[idx]

        # Check if key already exists in this chain
        while curr is not None:
            if curr.key == norm_key:
                curr.value = value
                return False  # Updated existing
            curr = curr.next

        # Key does not exist, prepend new node to the chain (O(1) insert)
        new_node = HashNode(norm_key, value)
        new_node.next = self.buckets[idx]
        self.buckets[idx] = new_node
        self.size += 1
        return True  # Added new

    # Retrieve value associated with key, or None if not found
    def get(self, key):
        norm_key = self._normalize_key(key)
        if not norm_key:
            return None
        idx = self._hash(norm_key)
        curr = self.buckets[idx]
        while curr is not None:
            if curr.key == norm_key:
                return curr.value
            curr = curr.next
        return None

    # Check whether a key exists in the hash map
    def contains(self, key):
        return self.get(key) is not None

    # Remove a key-value pair from the hash map, returning True if deleted
    def remove(self, key):
        norm_key = self._normalize_key(key)
        if not norm_key:
            return False

        idx = self._hash(norm_key)
        curr = self.buckets[idx]
        prev = None

        while curr is not None:
            if curr.key == norm_key:
                if prev is None:
                    self.buckets[idx] = curr.next
                else:
                    prev.next = curr.next
                self.size -= 1
                return True
            prev = curr
            curr = curr.next
        return False

    # Return a list of all stored values
    def values(self):
        result = []
        for head in self.buckets:
            curr = head
            while curr is not None:
                result.append(curr.value)
                curr = curr.next
        return result

    # Return a list of all stored keys
    def keys(self):
        result = []
        for head in self.buckets:
            curr = head
            while curr is not None:
                result.append(curr.key)
                curr = curr.next
        return result

    # Return a list of all stored (key, value) pairs
    def items(self):
        result = []
        for head in self.buckets:
            curr = head
            while curr is not None:
                result.append((curr.key, curr.value))
                curr = curr.next
        return result

    # Clear all entries from the hash map and reset capacity
    def clear(self):
        self.capacity = 16
        self.size = 0
        self.buckets = [None] * self.capacity

    # Return the total number of items stored in the hash map
    def __len__(self):
        return self.size
