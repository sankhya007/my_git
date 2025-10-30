import os
import hashlib
import platform
import time
import fcntl  # Unix file locking
import msvcrt  # Windows file locking
import tempfile
from pathlib import Path
from typing import List, Iterator, Optional, Dict, Any, Set, Union
from enum import Enum
import stat
import shutil
from contextlib import contextmanager

class FileLockType(Enum):
    """Types of file locks"""
    SHARED = "shared"
    EXCLUSIVE = "exclusive"
    NON_BLOCKING = "non_blocking"

class Platform(Enum):
    """Platform types"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"

def get_platform() -> Platform:
    """Detect the current platform"""
    system = platform.system().lower()
    if system == 'windows':
        return Platform.WINDOWS
    elif system == 'linux':
        return Platform.LINUX
    elif system == 'darwin':
        return Platform.MACOS
    else:
        return Platform.UNKNOWN

class FileLock:
    """Cross-platform file locking mechanism"""
    
    def __init__(self, file_path: Path, lock_type: FileLockType = FileLockType.EXCLUSIVE):
        self.file_path = file_path
        self.lock_type = lock_type
        self._lock_file = None
        self._is_locked = False
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
    
    def acquire(self, timeout: float = 10.0) -> bool:
        """Acquire file lock with optional timeout"""
        if self._is_locked:
            return True
        
        start_time = time.time()
        lock_file_path = self.file_path.with_suffix(self.file_path.suffix + '.lock')
        
        while time.time() - start_time < timeout:
            try:
                self._lock_file = open(lock_file_path, 'w')
                
                if get_platform() == Platform.WINDOWS:
                    # Windows file locking
                    try:
                        if self.lock_type == FileLockType.SHARED:
                            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    except IOError:
                        self._lock_file.close()
                        self._lock_file = None
                        time.sleep(0.1)
                        continue
                
                else:
                    # Unix file locking
                    lock_op = fcntl.LOCK_EX if self.lock_type == FileLockType.EXCLUSIVE else fcntl.LOCK_SH
                    if self.lock_type == FileLockType.NON_BLOCKING:
                        lock_op |= fcntl.LOCK_NB
                    
                    try:
                        fcntl.flock(self._lock_file.fileno(), lock_op)
                    except (IOError, BlockingIOError):
                        self._lock_file.close()
                        self._lock_file = None
                        time.sleep(0.1)
                        continue
                
                self._is_locked = True
                return True
                
            except Exception:
                if self._lock_file:
                    self._lock_file.close()
                    self._lock_file = None
                time.sleep(0.1)
        
        return False
    
    def release(self):
        """Release file lock"""
        if self._is_locked and self._lock_file:
            try:
                if get_platform() != Platform.WINDOWS:
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                
                # Remove lock file
                lock_file_path = self.file_path.with_suffix(self.file_path.suffix + '.lock')
                if lock_file_path.exists():
                    lock_file_path.unlink()
                    
            except Exception:
                pass  # Ignore cleanup errors
            
            self._is_locked = False
            self._lock_file = None
    
    @property
    def is_locked(self) -> bool:
        """Check if lock is currently held"""
        return self._is_locked

def read_file_chunks(file_path: Path, chunk_size: int = 8192, 
                    encoding: str = None) -> Iterator[bytes]:
    """Read file in chunks to handle large files with encoding support"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    try:
        mode = 'rb' if encoding is None else 'r'
        with open(file_path, mode, encoding=encoding) as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                if encoding and isinstance(chunk, str):
                    chunk = chunk.encode(encoding)
                yield chunk
    except PermissionError:
        raise PermissionError(f"Permission denied reading file: {file_path}")
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"Encoding error reading {file_path}: {e}")

def read_file_text(file_path: Path, encoding: str = 'utf-8', 
                  errors: str = 'replace') -> str:
    """Read entire file as text with proper encoding handling"""
    try:
        return file_path.read_text(encoding=encoding, errors=errors)
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"Failed to decode {file_path} with {encoding}: {e}")

def write_file_text(file_path: Path, content: str, encoding: str = 'utf-8',
                   create_parents: bool = True) -> None:
    """Write text to file with proper encoding and directory creation"""
    if create_parents:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        file_path.write_text(content, encoding=encoding)
    except UnicodeEncodeError as e:
        raise UnicodeEncodeError(f"Failed to encode content for {file_path}: {e}")

def calculate_file_hash(file_path: Path, algorithm: str = 'sha1', 
                       chunk_size: int = 8192) -> str:
    """Calculate hash of file content with multiple algorithm support"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if algorithm.lower() == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm.lower() == 'sha256':
        hash_obj = hashlib.sha256()
    elif algorithm.lower() == 'md5':
        hash_obj = hashlib.md5()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    try:
        for chunk in read_file_chunks(file_path, chunk_size):
            hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except PermissionError:
        raise PermissionError(f"Permission denied reading file: {file_path}")

def get_file_permissions(file_path: Path) -> Dict[str, Any]:
    """Get detailed file permissions and metadata"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        stat_info = file_path.stat()
        mode = stat_info.st_mode
        
        return {
            'readable': os.access(file_path, os.R_OK),
            'writable': os.access(file_path, os.W_OK),
            'executable': os.access(file_path, os.X_OK),
            'mode_octal': oct(mode)[-3:],
            'mode_symbolic': _format_mode(mode),
            'is_symlink': file_path.is_symlink(),
            'size': stat_info.st_size,
            'modified_time': stat_info.st_mtime,
            'created_time': getattr(stat_info, 'st_birthtime', stat_info.st_ctime),  # Creation time if available
            'owner_uid': stat_info.st_uid,
            'group_gid': stat_info.st_gid,
        }
    except OSError as e:
        raise OSError(f"Failed to get permissions for {file_path}: {e}")

def _format_mode(mode: int) -> str:
    """Convert numeric mode to symbolic representation"""
    symbols = ['---', '--x', '-w-', '-wx', 'r--', 'r-x', 'rw-', 'rwx']
    result = ''
    
    # File type
    if stat.S_ISDIR(mode):
        result += 'd'
    elif stat.S_ISLNK(mode):
        result += 'l'
    elif stat.S_ISREG(mode):
        result += '-'
    else:
        result += '?'
    
    # Permissions
    for who in "USR", "GRP", "OTH":
        perm_bits = (mode >> 6, mode >> 3, mode)["USRGRPOTH".index(who) // 3] & 0x7
        result += symbols[perm_bits]
    
    return result

def handle_symlink(file_path: Path, follow: bool = True) -> Path:
    """Handle symbolic links with optional following"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if file_path.is_symlink():
        if follow:
            try:
                return file_path.resolve()
            except (OSError, RuntimeError):
                # If resolution fails, return the symlink itself
                return file_path
        else:
            return file_path
    else:
        return file_path

def list_files_recursive(directory: Path, 
                        ignore_dirs: List[str] = None,
                        ignore_patterns: List[str] = None,
                        follow_symlinks: bool = False,
                        include_hidden: bool = False) -> List[Path]:
    """List all files recursively with advanced filtering"""
    if ignore_dirs is None:
        ignore_dirs = ['.mygit', '.git', '__pycache__', '.pytest_cache', '.DS_Store']
    
    if ignore_patterns is None:
        ignore_patterns = ['*.pyc', '*.pyo', '*.so', '*.egg-info']
    
    files = []
    
    try:
        for item in directory.iterdir():
            # Skip hidden files if not included
            if not include_hidden and item.name.startswith('.'):
                continue
            
            # Skip ignored directories
            if item.name in ignore_dirs:
                continue
            
            # Skip items matching ignore patterns
            if any(_matches_pattern(item.name, pattern) for pattern in ignore_patterns):
                continue
            
            if item.is_file():
                files.append(item)
            elif item.is_dir():
                files.extend(list_files_recursive(
                    item, ignore_dirs, ignore_patterns, follow_symlinks, include_hidden
                ))
            elif item.is_symlink() and follow_symlinks:
                try:
                    target = handle_symlink(item, follow=True)
                    if target.is_file():
                        files.append(item)  # Keep symlink path
                    elif target.is_dir():
                        files.extend(list_files_recursive(
                            target, ignore_dirs, ignore_patterns, follow_symlinks, include_hidden
                        ))
                except (OSError, RuntimeError):
                    # Skip broken symlinks
                    continue
    except PermissionError:
        # Skip directories we can't access
        pass
    
    return files

def _matches_pattern(filename: str, pattern: str) -> bool:
    """Check if filename matches pattern (simple glob support)"""
    if pattern.startswith('*'):
        return filename.endswith(pattern[1:])
    elif pattern.endswith('*'):
        return filename.startswith(pattern[:-1])
    else:
        return filename == pattern

def find_git_root(start_path: Path = Path('.')) -> Optional[Path]:
    """Find the root of the git repository with cross-platform support"""
    current = start_path.resolve()
    
    while current != current.parent:  # Stop at filesystem root
        # Check for both .mygit and .git directories
        if (current / '.mygit').exists() or (current / '.git').exists():
            return current
        
        # Handle case sensitivity on different filesystems
        for item in current.iterdir():
            if item.name.lower() in ('.mygit', '.git') and item.is_dir():
                return current
        
        current = current.parent
    
    return None

def safe_rename(source: Path, target: Path, overwrite: bool = False) -> bool:
    """Safely rename a file with error handling and optional overwrite"""
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    
    if target.exists():
        if overwrite:
            try:
                target.unlink()
            except OSError as e:
                raise OSError(f"Failed to remove existing target {target}: {e}")
        else:
            raise FileExistsError(f"Target file already exists: {target}")
    
    try:
        source.rename(target)
        return True
    except OSError as e:
        raise OSError(f"Failed to rename {source} to {target}: {e}")

def atomic_write(file_path: Path, content: bytes, mode: str = 'wb') -> bool:
    """Atomically write to a file using temporary file and rename"""
    temp_file = None
    try:
        # Create temporary file in the same directory
        temp_file = tempfile.NamedTemporaryFile(
            mode=mode,
            dir=file_path.parent,
            delete=False,
            prefix=f".{file_path.name}.tmp."
        )
        
        # Write content
        if isinstance(content, str):
            content = content.encode('utf-8')
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        
        # Atomically replace the original file
        safe_rename(Path(temp_file.name), file_path, overwrite=True)
        return True
        
    except Exception as e:
        # Clean up temporary file on error
        if temp_file and Path(temp_file.name).exists():
            try:
                Path(temp_file.name).unlink()
            except OSError:
                pass
        raise e

def get_file_size(file_path: Path, human_readable: bool = False) -> Union[int, str]:
    """Get file size in bytes or human-readable format"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    size = file_path.stat().st_size
    
    if human_readable:
        return _format_size(size)
    else:
        return size

def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def copy_file_with_metadata(source: Path, target: Path, 
                           preserve_metadata: bool = True) -> bool:
    """Copy file while preserving metadata and permissions"""
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    
    try:
        # Copy file content
        with open(source, 'rb') as src_file, open(target, 'wb') as dst_file:
            for chunk in read_file_chunks(source):
                dst_file.write(chunk)
        
        if preserve_metadata:
            # Copy permissions
            stat_info = source.stat()
            target.chmod(stat_info.st_mode)
            
            # Try to copy timestamps (platform dependent)
            try:
                os.utime(target, (stat_info.st_atime, stat_info.st_mtime))
            except OSError:
                pass  # Ignore if we can't set timestamps
        
        return True
        
    except Exception as e:
        # Clean up on error
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass
        raise e

def normalize_path(path: Path) -> Path:
    """Normalize path for cross-platform compatibility"""
    # Resolve symlinks and absolute path
    resolved = path.resolve()
    
    # On Windows, ensure consistent casing
    if get_platform() == Platform.WINDOWS:
        try:
            # Get the actual case from the filesystem
            return Path(resolved).resolve()
        except (OSError, RuntimeError):
            return resolved
    else:
        return resolved

def is_same_file(file1: Path, file2: Path) -> bool:
    """Check if two paths refer to the same file"""
    try:
        return normalize_path(file1).samefile(normalize_path(file2))
    except (OSError, RuntimeError):
        return False

def get_file_info(file_path: Path) -> Dict[str, Any]:
    """Get comprehensive file information"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    permissions = get_file_permissions(file_path)
    
    info = {
        'path': str(file_path),
        'absolute_path': str(file_path.resolve()),
        'name': file_path.name,
        'stem': file_path.stem,
        'suffix': file_path.suffix,
        'parent': str(file_path.parent),
        'exists': True,
        'is_file': file_path.is_file(),
        'is_dir': file_path.is_dir(),
        'is_symlink': file_path.is_symlink(),
        'size': get_file_size(file_path),
        'size_human': get_file_size(file_path, human_readable=True),
        'hash_sha1': calculate_file_hash(file_path, 'sha1'),
        'hash_sha256': calculate_file_hash(file_path, 'sha256'),
    }
    
    info.update(permissions)
    return info

# Utility function for common Git operations
def is_git_repository(path: Path = Path('.')) -> bool:
    """Check if the given path is within a Git repository"""
    return find_git_root(path) is not None

def get_repository_files(repo_path: Path = None) -> List[Path]:
    """Get all files in a Git repository (excluding .git directory)"""
    if repo_path is None:
        repo_path = find_git_root() or Path('.')
    
    return list_files_recursive(
        repo_path,
        ignore_dirs=['.mygit', '.git'],
        follow_symlinks=False,
        include_hidden=False
    )