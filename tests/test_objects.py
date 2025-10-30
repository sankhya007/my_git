import unittest
import tempfile
import os
import time
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
from io import StringIO

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.objects.blob import Blob
from src.objects.commit import Commit
from src.objects.tree import Tree, TreeEntry
from src.objects.factory import ObjectFactory
from src.objects.base import GitObject, ObjectValidationError
from src.repository import Repository

class TestBlob(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.test_data = b"Hello, World!"
        self.test_text = "Hello, World!"
        self.large_data = b"x" * 1024 * 1024  # 1MB of data

    def test_blob_creation(self):
        """Test basic blob creation and serialization"""
        blob = Blob(self.test_data)
        
        self.assertEqual(blob.data, self.test_data)
        
        serialized = blob.serialize()
        self.assertTrue(serialized.startswith(b'blob 13\0'))
        
        # Test deserialization
        new_blob = Blob()
        new_blob.deserialize(serialized)
        self.assertEqual(new_blob.data, self.test_data)

    def test_blob_hash(self):
        """Test blob hash calculation"""
        blob = Blob(b"test content")
        hash_val = blob.get_hash()
        self.assertEqual(len(hash_val), 40)  # SHA-1 is 40 chars
        
        # Verify hash consistency
        hash_val2 = blob.get_hash()
        self.assertEqual(hash_val, hash_val2)

    def test_blob_from_file(self):
        """Test creating blob from file"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(self.test_data)
            temp_path = f.name
        
        try:
            blob = Blob.from_file(temp_path)
            self.assertEqual(blob.data, self.test_data)
            self.assertEqual(blob.filepath, temp_path)
        finally:
            os.unlink(temp_path)

    def test_blob_from_text(self):
        """Test creating blob from text"""
        blob = Blob.from_text(self.test_text)
        self.assertEqual(blob.data, self.test_text.encode('utf-8'))
        self.assertFalse(blob.is_binary())

    def test_blob_validation(self):
        """Test blob validation"""
        blob = Blob(self.test_data)
        self.assertTrue(blob.validate())
        
        # Test invalid blob
        invalid_blob = Blob()
        with self.assertRaises(ObjectValidationError):
            invalid_blob.deserialize(b"invalid data")

    def test_blob_binary_detection(self):
        """Test binary vs text detection"""
        # Text blob
        text_blob = Blob(b"Hello, World!")
        self.assertFalse(text_blob.is_binary())
        
        # Binary blob (with null bytes)
        binary_blob = Blob(b"Hello\x00World")
        self.assertTrue(binary_blob.is_binary())
        
        # Empty blob
        empty_blob = Blob(b"")
        self.assertFalse(empty_blob.is_binary())

    def test_blob_text_operations(self):
        """Test text-based operations"""
        blob = Blob.from_text(self.test_text)
        
        # Test get_text
        text = blob.get_text()
        self.assertEqual(text, self.test_text)
        
        # Test set_text
        new_text = "New content"
        blob.set_text(new_text)
        self.assertEqual(blob.data, new_text.encode('utf-8'))
        self.assertEqual(blob.get_text(), new_text)

    def test_blob_statistics(self):
        """Test blob statistics"""
        blob = Blob(self.test_data)
        stats = blob.get_statistics()
        
        self.assertEqual(stats['type'], 'blob')
        self.assertEqual(stats['uncompressed_size'], len(self.test_data))
        self.assertIn('compression_ratio', stats)
        self.assertIn('hash_sha1', stats)
        self.assertIn('hash_sha256', stats)

    def test_blob_delta_compression(self):
        """Test delta compression between similar blobs"""
        base_data = b"Hello, World! This is some text."
        modified_data = b"Hello, World! This is modified text."
        
        base_blob = Blob(base_data)
        modified_blob = Blob(modified_data)
        
        # Create delta
        delta = base_blob.create_delta(modified_blob)
        self.assertIsNotNone(delta)
        
        # Apply delta and verify
        reconstructed_blob = base_blob.apply_delta(delta)
        self.assertEqual(reconstructed_blob.data, modified_data)

    def test_blob_streaming(self):
        """Test streaming operations for large blobs"""
        blob = Blob(self.large_data)
        
        # Test streaming serialization
        chunks = list(blob.stream_serialize(chunk_size=1024))
        reconstructed = b''.join(chunks)
        self.assertEqual(reconstructed, blob.serialize())
        
        # Test streaming compression
        compressed_chunks = list(blob.stream_compress(chunk_size=1024))
        self.assertTrue(len(compressed_chunks) > 0)

    def test_blob_edge_cases(self):
        """Test edge cases"""
        # Empty blob
        empty_blob = Blob(b"")
        self.assertEqual(empty_blob.get_hash(), hashlib.sha1(b"blob 0\0").hexdigest())
        
        # Very large blob (test memory efficiency)
        large_blob = Blob(b"x" * (1024 * 1024 * 10))  # 10MB
        self.assertEqual(len(large_blob.data), 1024 * 1024 * 10)

    def test_blob_performance(self):
        """Test blob performance with large data"""
        start_time = time.time()
        
        # Create and process large blob
        blob = Blob(self.large_data)
        blob.serialize()
        blob.get_hash()
        blob.compress()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should process 1MB in reasonable time
        self.assertLess(execution_time, 1.0, "Blob operations too slow")

class TestCommit(unittest.TestCase):
    def setUp(self):
        self.tree_sha = "a" * 40
        self.author = "Test User <test@example.com>"
        self.committer = "Test Committer <committer@example.com>"
        self.message = "Test commit message"

    def test_commit_creation(self):
        """Test basic commit creation"""
        commit = Commit()
        commit.tree = self.tree_sha
        commit.author = self.author
        commit.committer = self.committer
        commit.message = self.message
        
        serialized = commit.serialize()
        self.assertTrue(serialized.startswith(b'commit '))
        
        # Test deserialization
        new_commit = Commit()
        new_commit.deserialize(serialized)
        
        self.assertEqual(new_commit.tree, self.tree_sha)
        self.assertEqual(new_commit.author, self.author)
        self.assertEqual(new_commit.message, self.message)

    def test_commit_with_parents(self):
        """Test commit with parent commits"""
        commit = Commit()
        commit.tree = self.tree_sha
        commit.author = self.author
        commit.message = self.message
        commit.add_parent("b" * 40)
        commit.add_parent("c" * 40)
        
        self.assertEqual(len(commit.parents), 2)
        
        serialized = commit.serialize()
        self.assertIn(b"parent", serialized)

    def test_commit_validation(self):
        """Test commit validation"""
        commit = Commit()
        commit.tree = self.tree_sha
        commit.author = self.author
        commit.committer = self.committer
        commit.message = self.message
        
        self.assertTrue(commit.validate())
        
        # Test invalid commit (missing tree)
        invalid_commit = Commit()
        invalid_commit.author = self.author
        invalid_commit.message = self.message
        self.assertFalse(invalid_commit.validate())

    def test_commit_gpg_signing(self):
        """Test GPG signature support"""
        commit = Commit()
        commit.tree = self.tree_sha
        commit.author = self.author
        commit.message = self.message
        commit.set_gpgsig("-----BEGIN PGP SIGNATURE-----\nfake-signature\n-----END PGP SIGNATURE-----")
        
        serialized = commit.serialize()
        self.assertIn(b"gpgsig", serialized)
        
        # Test signature verification (placeholder)
        self.assertFalse(commit.verify_signature())  # Should be False for fake signature

    def test_commit_notes(self):
        """Test commit notes"""
        commit = Commit()
        commit.tree = self.tree_sha
        commit.author = self.author
        commit.message = self.message
        commit.add_note("This is a note")
        commit.add_note("Another note")
        
        self.assertEqual(len(commit.notes), 2)
        
        serialized = commit.serialize()
        self.assertIn(b"note", serialized)

    def test_commit_analysis(self):
        """Test commit analysis methods"""
        commit = Commit()
        commit.tree = self.tree_sha
        commit.author = self.author
        commit.message = "feat: add new feature\n\nThis is a detailed description."
        
        self.assertEqual(commit.get_summary(), "feat: add new feature")
        self.assertEqual(commit.get_body(), "This is a detailed description.")
        self.assertFalse(commit.is_merge_commit())
        self.assertTrue(commit.is_root_commit())

    def test_commit_merge_detection(self):
        """Test merge commit detection"""
        commit = Commit()
        commit.tree = self.tree_sha
        commit.author = self.author
        commit.message = "Merge branch 'feature'"
        commit.add_parent("b" * 40)
        commit.add_parent("c" * 40)
        
        self.assertTrue(commit.is_merge_commit())

class TestTree(unittest.TestCase):
    def setUp(self):
        self.file_mode = '100644'
        self.dir_mode = '40000'
        self.file_sha = "a" * 40
        self.tree_sha = "b" * 40

    def test_tree_entry_creation(self):
        """Test tree entry creation"""
        entry = TreeEntry(self.file_mode, "test.txt", self.file_sha)
        
        self.assertEqual(entry.mode, self.file_mode)
        self.assertEqual(entry.name, "test.txt")
        self.assertEqual(entry.sha, self.file_sha)
        self.assertTrue(entry.is_file())
        self.assertFalse(entry.is_directory())

    def test_tree_creation(self):
        """Test tree creation and management"""
        tree = Tree()
        tree.add_entry(self.file_mode, "file1.txt", self.file_sha)
        tree.add_entry(self.dir_mode, "subdir", self.tree_sha)
        
        self.assertEqual(len(tree.entries), 2)
        self.assertTrue(tree.has_entry("file1.txt"))
        self.assertTrue(tree.has_entry("subdir"))
        
        # Test serialization
        serialized = tree.serialize()
        self.assertTrue(serialized.startswith(b'tree '))
        
        # Test deserialization
        new_tree = Tree()
        new_tree.deserialize(serialized)
        self.assertEqual(len(new_tree.entries), 2)

    def test_tree_validation(self):
        """Test tree validation"""
        tree = Tree()
        tree.add_entry(self.file_mode, "valid.txt", self.file_sha)
        
        self.assertTrue(tree.validate())
        
        # Test invalid tree entry
        with self.assertRaises(ValueError):
            tree.add_entry("invalid_mode", "test.txt", self.file_sha)

    def test_tree_merging(self):
        """Test tree merging"""
        tree1 = Tree()
        tree1.add_entry(self.file_mode, "file1.txt", self.file_sha)
        
        tree2 = Tree()
        tree2.add_entry(self.file_mode, "file2.txt", "c" * 40)
        
        # Merge trees
        merged = tree1.merge(tree2, strategy='union')
        self.assertEqual(len(merged.entries), 2)

    def test_tree_diff(self):
        """Test tree diffing"""
        tree1 = Tree()
        tree1.add_entry(self.file_mode, "file1.txt", self.file_sha)
        
        tree2 = Tree()
        tree2.add_entry(self.file_mode, "file1.txt", "c" * 40)  # Different SHA
        tree2.add_entry(self.file_mode, "file2.txt", "d" * 40)  # New file
        
        diff = tree1.diff(tree2)
        self.assertEqual(len(diff.modified), 1)
        self.assertEqual(len(diff.added), 1)

class TestObjectIntegration(unittest.TestCase):
    """Integration tests for object interactions"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mygit_integration_")
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create a test repository
        self.repo = Repository()
        self.repo.create()

    def tearDown(self):
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_object_factory(self):
        """Test object creation and retrieval via factory"""
        # Create a blob
        blob_data = b"Test content"
        blob = Blob(blob_data)
        
        # Store via factory
        factory = ObjectFactory.get_instance()
        blob_sha = factory.write_object(self.repo, blob)
        
        # Retrieve via factory
        retrieved_blob = factory.read_object(self.repo, blob_sha)
        self.assertIsInstance(retrieved_blob, Blob)
        self.assertEqual(retrieved_blob.data, blob_data)

    def test_commit_tree_relationship(self):
        """Test commit-tree relationship"""
        # Create a tree with a blob
        blob = Blob(b"File content")
        blob_sha = ObjectFactory.get_instance().write_object(self.repo, blob)
        
        tree = Tree()
        tree.add_entry('100644', 'test.txt', blob_sha)
        tree_sha = ObjectFactory.get_instance().write_object(self.repo, tree)
        
        # Create a commit pointing to the tree
        commit = Commit()
        commit.tree = tree_sha
        commit.author = "Test <test@example.com>"
        commit.message = "Add test file"
        commit_sha = ObjectFactory.get_instance().write_object(self.repo, commit)
        
        # Verify the relationship
        retrieved_commit = ObjectFactory.get_instance().read_object(self.repo, commit_sha)
        self.assertEqual(retrieved_commit.tree, tree_sha)
        
        retrieved_tree = ObjectFactory.get_instance().read_object(self.repo, tree_sha)
        self.assertEqual(len(retrieved_tree.entries), 1)

class TestObjectPerformance(unittest.TestCase):
    """Performance tests for object operations"""
    
    def test_blob_serialization_performance(self):
        """Test blob serialization performance"""
        large_data = b"x" * (1024 * 1024)  # 1MB
        
        start_time = time.time()
        blob = Blob(large_data)
        blob.serialize()
        blob.get_hash()
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, 0.5, "Blob operations too slow")

    def test_commit_creation_performance(self):
        """Test commit creation performance with many parents"""
        commit = Commit()
        commit.tree = "a" * 40
        commit.author = "Test <test@example.com>"
        commit.message = "Performance test"
        
        # Add many parents
        for i in range(100):
            commit.add_parent("b" * 40)
        
        start_time = time.time()
        serialized = commit.serialize()
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, 0.1, "Commit serialization too slow")

    def test_tree_operations_performance(self):
        """Test tree operations performance with many entries"""
        tree = Tree()
        
        # Add many entries
        for i in range(1000):
            tree.add_entry('100644', f'file_{i}.txt', "a" * 40)
        
        start_time = time.time()
        serialized = tree.serialize()
        tree.deserialize(serialized)
        end_time = time.time()
        
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0, "Tree operations too slow")

class TestObjectFuzz(unittest.TestCase):
    """Fuzz testing for object robustness"""
    
    def test_blob_fuzz_deserialization(self):
        """Test blob deserialization with random data"""
        import random
        
        for _ in range(100):  # Test with 100 random inputs
            # Generate random data
            length = random.randint(0, 1000)
            random_data = bytes(random.randint(0, 255) for _ in range(length))
            
            blob = Blob()
            try:
                blob.deserialize(random_data)
                # If deserialization succeeds, verify we can serialize back
                blob.serialize()
            except (ObjectValidationError, ValueError):
                # Expected for invalid data
                pass

    def test_commit_fuzz_deserialization(self):
        """Test commit deserialization with random data"""
        import random
        
        for _ in range(100):
            length = random.randint(0, 1000)
            random_data = bytes(random.randint(0, 255) for _ in range(length))
            
            commit = Commit()
            try:
                commit.deserialize(random_data)
                commit.serialize()
            except (ObjectValidationError, ValueError):
                pass

    def test_tree_fuzz_deserialization(self):
        """Test tree deserialization with random data"""
        import random
        
        for _ in range(100):
            length = random.randint(0, 1000)
            random_data = bytes(random.randint(0, 255) for _ in range(length))
            
            tree = Tree()
            try:
                tree.deserialize(random_data)
                tree.serialize()
            except (ObjectValidationError, ValueError):
                pass

class TestObjectEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_blob_special_characters(self):
        """Test blob with special characters"""
        special_data = b"\x00\x01\x02\xff\xfe\xfd"  # Various byte values
        blob = Blob(special_data)
        self.assertEqual(blob.data, special_data)
        
        # Should be detected as binary
        self.assertTrue(blob.is_binary())

    def test_commit_special_messages(self):
        """Test commit with special message formats"""
        test_cases = [
            "",  # Empty message
            "a" * 1000,  # Very long message
            "Message with\nmultiple\nlines",
            "Message with trailing space ",
            " Message with leading space",
        ]
        
        for message in test_cases:
            with self.subTest(message=message[:50]):
                commit = Commit()
                commit.tree = "a" * 40
                commit.author = "Test <test@example.com>"
                commit.message = message
                
                # Should serialize and deserialize successfully
                serialized = commit.serialize()
                new_commit = Commit()
                new_commit.deserialize(serialized)
                self.assertEqual(new_commit.message, message)

    def test_tree_special_filenames(self):
        """Test tree with special filenames"""
        special_names = [
            ".hidden",
            "file with spaces",
            "file\twith\ttabs",
            "file\nwith\nnewlines",
            "café",  # Unicode
            "file/with/slashes",  # Should be rejected
        ]
        
        tree = Tree()
        for name in special_names:
            if '/' in name:
                # Should reject names with slashes
                with self.assertRaises(ValueError):
                    tree.add_entry('100644', name, "a" * 40)
            else:
                tree.add_entry('100644', name, "a" * 40)
        
        self.assertTrue(len(tree.entries) > 0)

    def test_object_equality(self):
        """Test object equality based on content"""
        blob1 = Blob(b"same content")
        blob2 = Blob(b"same content")
        blob3 = Blob(b"different content")
        
        self.assertEqual(blob1, blob2)
        self.assertNotEqual(blob1, blob3)
        
        # Test with different types
        commit = Commit()
        self.assertNotEqual(blob1, commit)

if __name__ == "__main__":
    # Run tests with increased verbosity
    unittest.main(verbosity=2)
    
    # Optionally run specific test categories
    if "--performance" in sys.argv:
        # Run only performance tests
        suite = unittest.TestSuite()
        suite.addTest(TestBlob('test_blob_performance'))
        suite.addTest(TestCommit('test_commit_creation_performance'))
        suite.addTest(TestTree('test_tree_operations_performance'))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    
    if "--fuzz" in sys.argv:
        # Run only fuzz tests
        suite = unittest.TestSuite()
        suite.addTest(TestObjectFuzz('test_blob_fuzz_deserialization'))
        suite.addTest(TestObjectFuzz('test_commit_fuzz_deserialization'))
        suite.addTest(TestObjectFuzz('test_tree_fuzz_deserialization'))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)