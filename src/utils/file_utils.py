import os
import hashlib
from pathlib import Path
from typing import List

def read_file_chunks(file_path: Path, chunk_size: 8192):
    """Read file in chunks to handle large files"""
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-1 hash of file content"""
    sha1 = hashlib.sha1()
    for chunk in read_file_chunks(file_path):
        sha1.update(chunk)
    return sha1.hexdigest()

def find_git_root(start_path: Path = Path('.')) -> Path:
    """Find the root of the git repository"""
    current = start_path.resolve()
    while current != current.parent:  # Stop at filesystem root
        if (current / '.mygit').exists() or (current / '.git').exists():
            return current
        current = current.parent
    return start_path

def list_files_recursive(directory: Path, ignore_dirs: List[str] = None) -> List[Path]:
    """List all files recursively, ignoring specified directories"""
    if ignore_dirs is None:
        ignore_dirs = ['.mygit', '.git', '__pycache__', '.pytest_cache']
    
    files = []
    for item in directory.iterdir():
        if item.name in ignore_dirs:
            continue
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(list_files_recursive(item, ignore_dirs))
    return files

# SPACE FOR IMPROVEMENT:
# - File permission handling
# - Symbolic link support
# - File locking mechanisms
# - Cross-platform path handling