"""
Git object system for MyGit

This package contains implementations of Git objects:
- Blob: File content storage
- Tree: Directory structure  
- Commit: Snapshot metadata
"""

from .base import GitObject
from .blob import Blob
from .tree import Tree, TreeEntry
from .commit import Commit
from .factory import ObjectFactory

__all__ = [
    'GitObject',
    'Blob', 
    'Tree',
    'TreeEntry',
    'Commit',
    'ObjectFactory'
]