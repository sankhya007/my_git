"""
MyGit - A minimal Git implementation in Python

This package provides a educational implementation of Git version control system.
"""

__version__ = "0.1.0"
__author__ = "MyGit Developer"
__email__ = "mygit@example.com"

# Import main classes for easier access
from .repository import Repository

# Import CLI for direct access
from .cli import main

# Import object system components
from .objects import GitObject, Blob, Tree, Commit, ObjectFactory

# Import utility system
from .utils import get_utility_manager

# Package-level imports
__all__ = [
    'Repository',
    'main',
    'GitObject', 
    'Blob',
    'Tree', 
    'Commit',
    'ObjectFactory',
    'get_utility_manager'
]