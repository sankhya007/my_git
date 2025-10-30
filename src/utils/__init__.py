"""
Utility functions for MyGit

This package contains helper utilities for file operations, hashing, and compression.
"""

from .file_utils import (
    read_file_chunks,
    calculate_file_hash,
    find_git_root,
    list_files_recursive
)

from .hash_utils import (
    sha1_hash,
    compress_data,
    decompress_data,
    validate_sha1
)

from .compression import GitCompressor

__all__ = [
    'read_file_chunks',
    'calculate_file_hash', 
    'find_git_root',
    'list_files_recursive',
    'sha1_hash',
    'compress_data',
    'decompress_data',
    'validate_sha1',
    'GitCompressor'
]