import unittest
import tempfile
import os
from src.objects.blob import Blob
from src.objects.commit import Commit

class TestBlob(unittest.TestCase):
    def test_blob_creation(self):
        data = b"Hello, World!"
        blob = Blob(data)
        
        self.assertEqual(blob.data, data)
        
        serialized = blob.serialize()
        self.assertTrue(serialized.startswith(b'blob 13\0'))
        
        new_blob = Blob()
        new_blob.deserialize(serialized)
        self.assertEqual(new_blob.data, data)
    
    def test_blob_hash(self):
        blob = Blob(b"test content")
        hash_val = blob.get_hash()
        self.assertEqual(len(hash_val), 40)  # SHA-1 is 40 chars

# SPACE FOR IMPROVEMENT:
# - Add more test cases
# - Integration tests
# - Performance tests
# - Fuzz testing