"""
MyGit - A minimal Git implementation in Python

This package provides a educational implementation of Git version control system.
"""

__version__ = "0.1.0"
__author__ = "MyGit Developer"
__email__ = "mygit@example.com"

# Import main classes for easier access
from .repository import Repository

# Package-level imports
__all__ = ['Repository']