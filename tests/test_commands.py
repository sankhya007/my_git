import unittest
import tempfile
import os
import time
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys
from io import StringIO

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commands.init import cmd_init
from src.commands.add import cmd_add
from src.commands.commit import cmd_commit
from src.commands.log import cmd_log
from src.commands.hash_object import cmd_hash_object
from src.commands.cat_file import cmd_cat_file
from src.repository import Repository
from src.objects.factory import ObjectFactory

class TestCommands(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.test_dir = tempfile.mkdtemp(prefix="mygit_test_")
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Capture stdout/stderr for testing output
        self.stdout_capture = StringIO()
        self.stderr_capture = StringIO()
        
        # Set up environment for consistent testing
        os.environ['GIT_AUTHOR_NAME'] = 'Test User'
        os.environ['GIT_AUTHOR_EMAIL'] = 'test@example.com'
        os.environ['GIT_COMMITTER_NAME'] = 'Test User'
        os.environ['GIT_COMMITTER_EMAIL'] = 'test@example.com'

    def tearDown(self):
        """Clean up after each test"""
        os.chdir(self.original_cwd)
        
        # Remove test directory
        import shutil
        try:
            shutil.rmtree(self.test_dir)
        except OSError:
            pass  # Directory might already be removed
        
        # Clean up environment
        for var in ['GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL']:
            os.environ.pop(var, None)

    def _create_test_file(self, filename: str, content: str = "test content") -> Path:
        """Helper to create a test file"""
        file_path = Path(filename)
        file_path.write_text(content)
        return file_path

    def _run_command_with_args(self, command_func, **kwargs):
        """Helper to run command with arguments"""
        # Create mock args object
        class Args:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        args = Args(**kwargs)
        return command_func(args)

    @patch('sys.stdout', new_callable=StringIO)
    def test_init_command_basic(self, mock_stdout):
        """Test basic repository initialization"""
        # Test successful initialization
        success = self._run_command_with_args(cmd_init, path=".")
        self.assertTrue(success)
        
        # Check repository structure was created
        repo = Repository()
        self.assertTrue(repo.exists())
        self.assertTrue((Path(".mygit") / "objects").exists())
        self.assertTrue((Path(".mygit") / "refs" / "heads").exists())
        self.assertTrue((Path(".mygit") / "HEAD").exists())
        
        # Check HEAD content
        head_content = (Path(".mygit") / "HEAD").read_text()
        self.assertIn("ref: refs/heads/main", head_content)

    @patch('sys.stdout', new_callable=StringIO)
    def test_init_command_custom_path(self, mock_stdout):
        """Test initialization with custom path"""
        custom_path = "subdir/repo"
        success = self._run_command_with_args(cmd_init, path=custom_path)
        self.assertTrue(success)
        
        repo = Repository(custom_path)
        self.assertTrue(repo.exists())

    @patch('sys.stdout', new_callable=StringIO)
    def test_init_command_already_exists(self, mock_stdout):
        """Test initialization when repository already exists"""
        # Create repository first
        self._run_command_with_args(cmd_init, path=".")
        
        # Try to create again
        success = self._run_command_with_args(cmd_init, path=".")
        self.assertFalse(success)  # Should fail

    @patch('sys.stdout', new_callable=StringIO)
    def test_init_command_with_templates(self, mock_stdout):
        """Test initialization with different templates"""
        for template in ["default", "python", "empty"]:
            with self.subTest(template=template):
                test_dir = tempfile.mkdtemp(prefix=f"test_{template}_")
                os.chdir(test_dir)
                
                success = self._run_command_with_args(
                    cmd_init, path=".", template=template, verbose=True
                )
                self.assertTrue(success)
                
                os.chdir(self.test_dir)
                import shutil
                shutil.rmtree(test_dir)

    @patch('sys.stdout', new_callable=StringIO)
    def test_add_command_basic(self, mock_stdout):
        """Test basic file addition"""
        # Initialize repository first
        self._run_command_with_args(cmd_init, path=".")
        
        # Create test file
        test_file = self._create_test_file("test.txt", "Hello, World!")
        
        # Add file to staging
        success = self._run_command_with_args(
            cmd_add, files=["test.txt"], verbose=True
        )
        self.assertTrue(success)
        
        # Check if object was created
        repo = Repository()
        objects_dir = repo.gitdir / "objects"
        self.assertTrue(any(objects_dir.rglob("*")), "No objects created")

    @patch('sys.stdout', new_callable=StringIO)
    def test_add_command_multiple_files(self, mock_stdout):
        """Test adding multiple files"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Create multiple files
        files = ["file1.txt", "file2.txt", "file3.txt"]
        for filename in files:
            self._create_test_file(filename, f"content for {filename}")
        
        success = self._run_command_with_args(cmd_add, files=files)
        self.assertTrue(success)

    @patch('sys.stdout', new_callable=StringIO)
    def test_add_command_with_patterns(self, mock_stdout):
        """Test adding files with patterns"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Create files with different extensions
        self._create_test_file("test.py", "python code")
        self._create_test_file("test.txt", "text content")
        self._create_test_file("data.json", '{"key": "value"}')
        
        # Add only Python files
        success = self._run_command_with_args(cmd_add, files=["*.py"])
        self.assertTrue(success)

    @patch('sys.stdout', new_callable=StringIO)
    def test_add_command_nonexistent_file(self, mock_stdout):
        """Test adding non-existent files"""
        self._run_command_with_args(cmd_init, path=".")
        
        success = self._run_command_with_args(cmd_add, files=["nonexistent.txt"])
        self.assertFalse(success)

    @patch('sys.stdout', new_callable=StringIO)
    def test_add_command_outside_repository(self, mock_stdout):
        """Test add command outside repository"""
        success = self._run_command_with_args(cmd_add, files=["test.txt"])
        self.assertFalse(success)

    @patch('sys.stdout', new_callable=StringIO)
    def test_commit_command_basic(self, mock_stdout):
        """Test basic commit functionality"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Add and commit a file
        self._create_test_file("test.txt", "commit test")
        self._run_command_with_args(cmd_add, files=["test.txt"])
        
        success = self._run_command_with_args(
            cmd_commit, message="Initial commit", verbose=True
        )
        self.assertTrue(success)
        
        # Verify commit was created
        repo = Repository()
        head_sha = repo.get_HEAD()
        self.assertIsNotNone(head_sha)
        self.assertEqual(len(head_sha), 40)  # Valid SHA-1

    @patch('sys.stdout', new_callable=StringIO)
    def test_commit_command_no_changes(self, mock_stdout):
        """Test commit with no staged changes"""
        self._run_command_with_args(cmd_init, path=".")
        
        success = self._run_command_with_args(
            cmd_commit, message="Empty commit", allow_empty=True
        )
        self.assertTrue(success)

    @patch('sys.stdout', new_callable=StringIO)
    def test_hash_object_command(self, mock_stdout):
        """Test hash-object command"""
        test_content = "Hello, Git!"
        test_file = self._create_test_file("hash_test.txt", test_content)
        
        # Test without storing
        success = self._run_command_with_args(
            cmd_hash_object, file="hash_test.txt"
        )
        self.assertTrue(success)
        
        # Test with storing
        self._run_command_with_args(cmd_init, path=".")
        success = self._run_command_with_args(
            cmd_hash_object, file="hash_test.txt", create=True
        )
        self.assertTrue(success)

    @patch('sys.stdout', new_callable=StringIO)
    def test_cat_file_command(self, mock_stdout):
        """Test cat-file command"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Create and store an object
        test_file = self._create_test_file("cat_test.txt", "content for cat-file")
        result = self._run_command_with_args(
            cmd_hash_object, file="cat_test.txt", create=True
        )
        
        # Get the hash from output (would need to capture stdout)
        # This is simplified - in real test we'd parse the hash
        
        # Test would continue with cat-file command...

    def test_error_conditions(self):
        """Test various error conditions"""
        # Test init in non-writable directory
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("No permission")
            success = self._run_command_with_args(cmd_init, path=".")
            self.assertFalse(success)
        
        # Test add with permission denied
        self._run_command_with_args(cmd_init, path=".")
        test_file = self._create_test_file("protected.txt")
        os.chmod("protected.txt", 0o000)  # Remove read permission
        
        try:
            success = self._run_command_with_args(cmd_add, files=["protected.txt"])
            self.assertFalse(success)
        finally:
            os.chmod("protected.txt", 0o644)  # Restore permission

class TestCommandIntegration(unittest.TestCase):
    """Integration tests for command workflows"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mygit_integration_")
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Set up environment
        os.environ.update({
            'GIT_AUTHOR_NAME': 'Test User',
            'GIT_AUTHOR_EMAIL': 'test@example.com'
        })

    def tearDown(self):
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_complete_workflow(self):
        """Test complete git workflow: init -> add -> commit -> log"""
        # Initialize repository
        self._run_command_with_args(cmd_init, path=".")
        
        # Create and add multiple files
        files = ["README.md", "src/main.py", "tests/test.py"]
        for filepath in files:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {filepath}\n\nContent for {filepath}")
        
        # Add files
        self._run_command_with_args(cmd_add, files=["."], verbose=True)
        
        # Make initial commit
        self._run_command_with_args(
            cmd_commit, message="Initial commit\n\n- Add project structure\n- Add source files"
        )
        
        # Modify a file and make second commit
        Path("README.md").write_text("# Updated README\n\nMore detailed description")
        self._run_command_with_args(cmd_add, files=["README.md"])
        self._run_command_with_args(cmd_commit, message="Update README")
        
        # Check log
        success = self._run_command_with_args(cmd_log, limit=2)
        self.assertTrue(success)

    def test_branching_workflow(self):
        """Test branching and merging workflow"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Initial commit on main
        self._create_test_file("file.txt", "initial content")
        self._run_command_with_args(cmd_add, files=["file.txt"])
        self._run_command_with_args(cmd_commit, message="Initial commit")
        
        # This would test branch creation and switching
        # (when branch command is implemented)

class TestCommandPerformance(unittest.TestCase):
    """Performance tests for commands"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mygit_perf_")
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_add_performance_large_files(self):
        """Test add command performance with large files"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Create a moderately large file (1MB)
        large_file = Path("large.dat")
        with open(large_file, 'wb') as f:
            f.write(os.urandom(1024 * 1024))  # 1MB of random data
        
        # Time the add operation
        start_time = time.time()
        success = self._run_command_with_args(cmd_add, files=["large.dat"])
        end_time = time.time()
        
        self.assertTrue(success)
        execution_time = end_time - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        self.assertLess(execution_time, 5.0, "Add operation too slow")

    def test_commit_performance_many_files(self):
        """Test commit performance with many small files"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Create many small files
        num_files = 100
        for i in range(num_files):
            self._create_test_file(f"file_{i:03d}.txt", f"content {i}")
        
        self._run_command_with_args(cmd_add, files=["."])
        
        start_time = time.time()
        success = self._run_command_with_args(cmd_commit, message=f"Add {num_files} files")
        end_time = time.time()
        
        self.assertTrue(success)
        execution_time = end_time - start_time
        
        # Should handle many files efficiently
        self.assertLess(execution_time, 10.0, "Commit with many files too slow")

class TestCommandEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mygit_edge_")
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_files_with_special_characters(self):
        """Test handling files with special characters in names"""
        self._run_command_with_args(cmd_init, path=".")
        
        special_names = [
            "file with spaces.txt",
            "file-with-dash.txt",
            "file_with_underscore.txt",
            "file.with.dots.txt",
            "café.txt",  # Unicode
            "file[1].txt",  # Brackets
        ]
        
        for filename in special_names:
            self._create_test_file(filename, "content")
        
        success = self._run_command_with_args(cmd_add, files=special_names)
        self.assertTrue(success)

    def test_empty_files(self):
        """Test handling of empty files"""
        self._run_command_with_args(cmd_init, path=".")
        
        empty_file = Path("empty.txt")
        empty_file.touch()  # Create empty file
        
        success = self._run_command_with_args(cmd_add, files=["empty.txt"])
        self.assertTrue(success)
        
        success = self._run_command_with_args(cmd_commit, message="Add empty file")
        self.assertTrue(success)

    def test_binary_files(self):
        """Test handling of binary files"""
        self._run_command_with_args(cmd_init, path=".")
        
        # Create a binary file
        binary_file = Path("binary.dat")
        with open(binary_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03\x04\x05')  # Some binary data
        
        success = self._run_command_with_args(cmd_add, files=["binary.dat"])
        self.assertTrue(success)

    def test_symlink_handling(self):
        """Test handling of symbolic links"""
        if os.name == 'nt':
            self.skipTest("Symbolic links not fully supported on Windows")
        
        self._run_command_with_args(cmd_init, path=".")
        
        # Create a target file
        target = Path("target.txt")
        target.write_text("target content")
        
        # Create symbolic link
        link = Path("link.txt")
        link.symlink_to("target.txt")
        
        # Test adding symlink
        success = self._run_command_with_args(cmd_add, files=["link.txt"])
        self.assertTrue(success)

    def _run_command_with_args(self, command_func, **kwargs):
        """Helper to run command with arguments"""
        class Args:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        args = Args(**kwargs)
        
        # Capture output for tests that need it
        with patch('sys.stdout', new_callable=StringIO), \
             patch('sys.stderr', new_callable=StringIO):
            return command_func(args)

def run_performance_benchmarks():
    """Run performance benchmarks (not a test)"""
    import timeit
    
    def benchmark_init():
        test_dir = tempfile.mkdtemp(prefix="benchmark_")
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        cmd_init(type('Args', (), {'path': '.', 'verbose': False})())
        
        os.chdir(original_cwd)
        import shutil
        shutil.rmtree(test_dir)
    
    time = timeit.timeit(benchmark_init, number=10)
    print(f"Average init time: {time/10:.3f}s")

if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
    
    # Optionally run benchmarks
    if "--benchmark" in sys.argv:
        run_performance_benchmarks()