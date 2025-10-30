import unittest
import tempfile
import os
import time
import threading
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock
import configparser
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.repository import Repository, RepositoryError, RepositoryType, ObjectFormat
from src.objects.blob import Blob
from src.objects.factory import ObjectFactory

class TestRepository(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="repo_test_")
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """Clean up after tests"""
        os.chdir(self.original_cwd)
        import shutil
        try:
            shutil.rmtree(self.test_dir)
        except OSError:
            pass  # Directory might already be removed

    def test_repository_creation_basic(self):
        """Test basic repository creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            self.assertTrue(repo.create())
            self.assertTrue(repo.exists())
            
            # Verify directory structure
            self.assertTrue((Path(temp_dir) / ".mygit" / "objects").exists())
            self.assertTrue((Path(temp_dir) / ".mygit" / "refs" / "heads").exists())
            self.assertTrue((Path(temp_dir) / ".mygit" / "HEAD").exists())
            self.assertTrue((Path(temp_dir) / ".mygit" / "config").exists())

    def test_repository_creation_bare(self):
        """Test bare repository creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "bare_repo"
            repo = Repository(str(repo_path), bare=True)
            self.assertTrue(repo.create(bare=True))
            self.assertTrue(repo.exists())
            self.assertEqual(repo.get_type(), RepositoryType.BARE)
            self.assertIsNone(repo.worktree)

    def test_repository_creation_shared(self):
        """Test shared repository creation"""
        if os.name == 'nt':
            self.skipTest("Shared repository permissions not fully supported on Windows")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            self.assertTrue(repo.create(shared=True))
            self.assertTrue(repo.exists())
            
            # Verify shared configuration
            self.assertEqual(repo.config.get('core', 'sharedrepository'), 'true')

    def test_repository_detection(self):
        """Test repository detection logic"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create repository
            repo = Repository(temp_dir)
            repo.create()
            
            # Test detection from subdirectory
            subdir = Path(temp_dir) / "sub" / "directory"
            subdir.mkdir(parents=True)
            os.chdir(subdir)
            
            from src.repository import find_repository
            detected_repo = find_repository()
            self.assertIsNotNone(detected_repo)
            self.assertEqual(detected_repo.worktree, Path(temp_dir).resolve())

    def test_repository_detection_none(self):
        """Test repository detection when no repository exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            from src.repository import find_repository
            detected_repo = find_repository()
            self.assertIsNone(detected_repo)

    def test_repository_config_management(self):
        """Test repository configuration management"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Test configuration get/set
            repo.config.set('user', 'name', 'Test User')
            repo.config.set('user', 'email', 'test@example.com')
            
            self.assertEqual(repo.config.get('user', 'name'), 'Test User')
            self.assertEqual(repo.config.get('user', 'email'), 'test@example.com')
            
            # Test boolean and integer values
            repo.config.set('core', 'bare', 'true')
            self.assertTrue(repo.config.get_boolean('core', 'bare'))
            
            repo.config.set('core', 'bigFileThreshold', '100')
            self.assertEqual(repo.config.get_int('core', 'bigFileThreshold'), 100)

    def test_repository_validation(self):
        """Test repository validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Test validation
            validation_results = repo.validate()
            self.assertTrue(validation_results['structure_valid'])
            self.assertTrue(validation_results['config_valid'])
            self.assertTrue(validation_results['overall_valid'])
            
            # Test object stats
            self.assertIn('object_stats', validation_results)
            self.assertIn('ref_stats', validation_results)

    def test_repository_branch_management(self):
        """Test branch management"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Test initial branch
            self.assertEqual(repo.get_current_branch(), 'main')
            
            # Test branch switching
            repo.set_current_branch('develop')
            self.assertEqual(repo.get_current_branch(), 'develop')
            
            # Test branches listing
            branches = repo.get_branches()
            self.assertIn('develop', branches)

    def test_repository_HEAD_management(self):
        """Test HEAD management"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Test initial HEAD
            head_sha = repo.get_HEAD()
            self.assertIsNone(head_sha)  # No commits yet
            
            # Test detached HEAD
            test_sha = "a" * 40
            (repo.gitdir / "HEAD").write_text(test_sha)
            self.assertEqual(repo.get_HEAD(), test_sha)
            self.assertTrue(repo.is_detached_head())

    def test_repository_statistics(self):
        """Test repository statistics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            stats = repo.get_statistics()
            
            self.assertEqual(stats['type'], 'regular')
            self.assertEqual(stats['object_format'], 'sha1')
            self.assertEqual(stats['current_branch'], 'main')
            self.assertEqual(stats['branch_count'], 0)
            self.assertIn('validation', stats)
            self.assertIn('config_sections', stats)

    def test_repository_remote_management(self):
        """Test remote URL management"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Test remote URL setting
            repo.set_remote_url('origin', 'https://github.com/user/repo.git')
            url = repo.get_remote_url('origin')
            self.assertEqual(url, 'https://github.com/user/repo.git')
            
            # Test non-existent remote
            url = repo.get_remote_url('nonexistent')
            self.assertIsNone(url)

class TestRepositoryEdgeCases(unittest.TestCase):
    """Test repository edge cases and error conditions"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="repo_edge_")

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree(self.test_dir)
        except OSError:
            pass

    def test_repository_creation_existing(self):
        """Test repository creation when already exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Try to create again
            with self.assertRaises(RepositoryError):
                repo.create()

    def test_repository_creation_permission_denied(self):
        """Test repository creation with permission issues"""
        if os.name == 'nt':
            self.skipTest("Permission testing not reliable on Windows")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Make directory read-only
            os.chmod(temp_dir, 0o444)
            
            try:
                repo = Repository(temp_dir)
                with self.assertRaises(RepositoryError):
                    repo.create()
            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)

    def test_repository_creation_invalid_path(self):
        """Test repository creation with invalid path"""
        # Test with file instead of directory
        with tempfile.NamedTemporaryFile() as temp_file:
            repo = Repository(temp_file.name)
            with self.assertRaises(RepositoryError):
                repo.create()

    def test_repository_corrupted_structure(self):
        """Test repository with corrupted structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Corrupt the repository by removing essential files
            (repo.gitdir / "HEAD").unlink()
            
            validation_results = repo.validate()
            self.assertFalse(validation_results['structure_valid'])
            self.assertFalse(validation_results['overall_valid'])

    def test_repository_corrupted_config(self):
        """Test repository with corrupted config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Write invalid config
            (repo.gitdir / "config").write_text("invalid config content")
            
            validation_results = repo.validate()
            self.assertFalse(validation_results['config_valid'])

    def test_repository_nonexistent_path(self):
        """Test repository operations on non-existent path"""
        repo = Repository("/nonexistent/path/repo")
        self.assertFalse(repo.exists())

    def test_repository_empty_directory(self):
        """Test repository operations on empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            self.assertFalse(repo.exists())

    def test_repository_malformed_HEAD(self):
        """Test repository with malformed HEAD"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(temp_dir)
            repo.create()
            
            # Write malformed HEAD
            (repo.gitdir / "HEAD").write_text("invalid content")
            
            with self.assertRaises(RepositoryError):
                repo.get_HEAD()

    def test_repository_symlink_handling(self):
        """Test repository with symbolic links"""
        if os.name == 'nt':
            self.skipTest("Symbolic links not fully supported on Windows")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create repository
            repo_dir = Path(temp_dir) / "repo"
            repo = Repository(str(repo_dir))
            repo.create()
            
            # Create symlink to repository
            link_dir = Path(temp_dir) / "link"
            link_dir.symlink_to(repo_dir)
            
            # Test accessing through symlink
            linked_repo = Repository(str(link_dir))
            self.assertTrue(linked_repo.exists())

class TestRepositoryConcurrentAccess(unittest.TestCase):
    """Test repository concurrent access scenarios"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="repo_concurrent_")
        self.repo = Repository(self.test_dir)
        self.repo.create()
        self.lock_timeout = 5.0  # seconds

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree(self.test_dir)
        except OSError:
            pass

    def test_concurrent_repository_creation(self):
        """Test concurrent repository creation attempts"""
        results = []
        errors = []
        
        def create_repo():
            try:
                repo = Repository(self.test_dir)
                result = repo.create()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads trying to create repository
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_repo)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=self.lock_timeout)
        
        # Only one should succeed, others should fail
        self.assertEqual(results.count(True), 1)
        self.assertEqual(len(errors), 4)

    def test_concurrent_branch_operations(self):
        """Test concurrent branch operations"""
        branch_operations = []
        lock = threading.Lock()
        
        def switch_branches(thread_id):
            try:
                # Each thread tries to switch to different branches
                branch_name = f"branch_{thread_id}"
                self.repo.set_current_branch(branch_name)
                
                with lock:
                    branch_operations.append((thread_id, branch_name))
            except Exception as e:
                with lock:
                    branch_operations.append((thread_id, f"error: {e}"))
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=switch_branches, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=self.lock_timeout)
        
        # All operations should complete
        self.assertEqual(len(branch_operations), 10)
        
        # Final branch should be one of them
        final_branch = self.repo.get_current_branch()
        self.assertTrue(any(branch_name == final_branch for _, branch_name in branch_operations))

    def test_concurrent_config_updates(self):
        """Test concurrent configuration updates"""
        config_updates = []
        lock = threading.Lock()
        
        def update_config(thread_id):
            try:
                key = f"test_key_{thread_id}"
                value = f"value_{thread_id}"
                
                self.repo.config.set('concurrent', key, value)
                
                with lock:
                    config_updates.append((thread_id, key, value))
            except Exception as e:
                with lock:
                    config_updates.append((thread_id, f"error: {e}", ""))
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_config, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=self.lock_timeout)
        
        # All updates should complete
        self.assertEqual(len(config_updates), 10)
        
        # Verify all values were set
        for thread_id, key, value in config_updates:
            if not key.startswith("error"):
                self.assertEqual(self.repo.config.get('concurrent', key), value)

    def test_concurrent_object_creation(self):
        """Test concurrent object creation"""
        created_objects = []
        lock = threading.Lock()
        
        def create_object(thread_id):
            try:
                # Each thread creates a blob
                blob_data = f"Content from thread {thread_id}".encode()
                blob = Blob(blob_data)
                
                factory = ObjectFactory.get_instance()
                blob_sha = factory.write_object(self.repo, blob)
                
                with lock:
                    created_objects.append((thread_id, blob_sha))
            except Exception as e:
                with lock:
                    created_objects.append((thread_id, f"error: {e}"))
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_object, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=self.lock_timeout)
        
        # All objects should be created
        self.assertEqual(len(created_objects), 5)
        
        # Verify objects can be retrieved
        for thread_id, blob_sha in created_objects:
            if not blob_sha.startswith("error"):
                factory = ObjectFactory.get_instance()
                retrieved_blob = factory.read_object(self.repo, blob_sha)
                self.assertIsInstance(retrieved_blob, Blob)

    def test_file_locking_contention(self):
        """Test file locking under contention"""
        if os.name == 'nt':
            self.skipTest("File locking behavior differs on Windows")
        
        lock_attempts = []
        lock = threading.Lock()
        
        def attempt_lock(file_id):
            try:
                test_file = self.repo.gitdir / f"lock_test_{file_id}.txt"
                test_file.write_text("test content")
                
                # Try to acquire exclusive lock
                from src.utils.file_utils import FileLock, FileLockType
                
                file_lock = FileLock(test_file, FileLockType.EXCLUSIVE)
                acquired = file_lock.acquire(timeout=1.0)
                
                with lock:
                    lock_attempts.append((file_id, acquired))
                
                if acquired:
                    time.sleep(0.1)  # Hold lock briefly
                    file_lock.release()
            except Exception as e:
                with lock:
                    lock_attempts.append((file_id, f"error: {e}"))
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=attempt_lock, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=self.lock_timeout)
        
        # Most lock attempts should succeed (some might fail due to contention)
        success_count = sum(1 for _, result in lock_attempts if result is True)
        self.assertGreater(success_count, 0)

class TestRepositoryPerformance(unittest.TestCase):
    """Test repository performance under various conditions"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="repo_perf_")

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree(self.test_dir)
        except OSError:
            pass

    def test_repository_creation_performance(self):
        """Test repository creation performance"""
        start_time = time.time()
        
        repo = Repository(self.test_dir)
        repo.create()
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create repository quickly
        self.assertLess(creation_time, 1.0, "Repository creation too slow")

    def test_repository_validation_performance(self):
        """Test repository validation performance"""
        repo = Repository(self.test_dir)
        repo.create()
        
        # Create some objects to make validation more realistic
        factory = ObjectFactory.get_instance()
        for i in range(100):
            blob = Blob(f"Content {i}".encode())
            factory.write_object(repo, blob)
        
        start_time = time.time()
        validation_results = repo.validate()
        end_time = time.time()
        validation_time = end_time - start_time
        
        self.assertTrue(validation_results['overall_valid'])
        self.assertLess(validation_time, 2.0, "Repository validation too slow")

    def test_repository_config_performance(self):
        """Test configuration operations performance"""
        repo = Repository(self.test_dir)
        repo.create()
        
        start_time = time.time()
        
        # Perform many configuration operations
        for i in range(1000):
            repo.config.set('performance', f'key_{i}', f'value_{i}')
        
        end_time = time.time()
        config_time = end_time - start_time
        
        self.assertLess(config_time, 1.0, "Configuration operations too slow")

    def test_repository_branch_operations_performance(self):
        """Test branch operations performance"""
        repo = Repository(self.test_dir)
        repo.create()
        
        start_time = time.time()
        
        # Perform many branch operations
        for i in range(100):
            branch_name = f"branch_{i}"
            repo.set_current_branch(branch_name)
        
        end_time = time.time()
        branch_time = end_time - start_time
        
        self.assertLess(branch_time, 1.0, "Branch operations too slow")

class TestRepositoryRecovery(unittest.TestCase):
    """Test repository recovery from various failure states"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="repo_recovery_")

    def tearDown(self):
        import shutil
        try:
            shutil.rmtree(self.test_dir)
        except OSError:
            pass

    def test_recovery_from_partial_creation(self):
        """Test recovery from partially created repository"""
        repo = Repository(self.test_dir)
        
        # Manually create partial structure
        (repo.gitdir / "objects").mkdir(parents=True)
        (repo.gitdir / "refs" / "heads").mkdir(parents=True)
        # Intentionally skip creating HEAD and config
        
        # Repository should not be considered valid
        self.assertFalse(repo.exists())
        
        # But we should be able to complete creation
        self.assertTrue(repo.create())
        self.assertTrue(repo.exists())

    def test_recovery_from_corrupted_objects(self):
        """Test recovery from corrupted object database"""
        repo = Repository(self.test_dir)
        repo.create()
        
        # Corrupt some objects by writing invalid data
        objects_dir = repo.gitdir / "objects"
        for i in range(5):
            corrupt_dir = objects_dir / f"{i:02x}"
            corrupt_dir.mkdir(exist_ok=True)
            corrupt_file = corrupt_dir / ("a" * 38)
            corrupt_file.write_bytes(b"corrupted object data")
        
        # Validation should detect corruption
        validation_results = repo.validate()
        object_stats = validation_results['object_stats']
        self.assertGreater(object_stats['corrupt_objects'], 0)
        self.assertFalse(validation_results['overall_valid'])

    def test_recovery_from_missing_refs(self):
        """Test recovery from missing references"""
        repo = Repository(self.test_dir)
        repo.create()
        
        # Remove some reference directories
        import shutil
        shutil.rmtree(repo.gitdir / "refs" / "tags", ignore_errors=True)
        
        # Repository should still be somewhat functional
        self.assertTrue(repo.exists())
        
        # But validation should report the issue
        validation_results = repo.validate()
        self.assertFalse(validation_results['structure_valid'])

if __name__ == "__main__":
    # Run tests with increased verbosity
    unittest.main(verbosity=2)
    
    # Optionally run specific test categories
    if "--concurrent" in sys.argv:
        # Run only concurrent tests
        suite = unittest.TestSuite()
        suite.addTest(TestRepositoryConcurrentAccess('test_concurrent_repository_creation'))
        suite.addTest(TestRepositoryConcurrentAccess('test_concurrent_branch_operations'))
        suite.addTest(TestRepositoryConcurrentAccess('test_concurrent_config_updates'))
        suite.addTest(TestRepositoryConcurrentAccess('test_concurrent_object_creation'))
        suite.addTest(TestRepositoryConcurrentAccess('test_file_locking_contention'))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    
    if "--performance" in sys.argv:
        # Run only performance tests
        suite = unittest.TestSuite()
        suite.addTest(TestRepositoryPerformance('test_repository_creation_performance'))
        suite.addTest(TestRepositoryPerformance('test_repository_validation_performance'))
        suite.addTest(TestRepositoryPerformance('test_repository_config_performance'))
        suite.addTest(TestRepositoryPerformance('test_repository_branch_operations_performance'))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    
    if "--recovery" in sys.argv:
        # Run only recovery tests
        suite = unittest.TestSuite()
        suite.addTest(TestRepositoryRecovery('test_recovery_from_partial_creation'))
        suite.addTest(TestRepositoryRecovery('test_recovery_from_corrupted_objects'))
        suite.addTest(TestRepositoryRecovery('test_recovery_from_missing_refs'))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)