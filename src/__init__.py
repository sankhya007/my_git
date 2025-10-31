"""
MyGit - A minimal Git implementation in Python

This package provides an educational implementation of Git version control system.
MyGit demonstrates the core concepts of Git internals including object storage,
content-addressable storage, and version control operations.

Key Components:
- Repository management and initialization
- Git object system (blobs, trees, commits) 
- Command-line interface with advanced features
- Cross-platform file operations
- Object caching and compression systems
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

# Import command registry for extension
from .commands import get_registry

# Package-level imports
__all__ = [
    # Core repository management
    'Repository',
    
    # CLI interface
    'main',
    
    # Object system
    'GitObject', 
    'Blob',
    'Tree', 
    'Commit',
    'ObjectFactory',
    
    # Utility systems
    'get_utility_manager',
    
    # Command system
    'get_registry',
]

# Performance monitoring and initialization
import sys
import os
from pathlib import Path

def _initialize_package():
    """Initialize package-level configurations and checks"""
    # Add package directory to path for easier imports
    package_dir = Path(__file__).parent
    if str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))
    
    # Check for basic dependencies
    try:
        import zlib
        import hashlib
        import argparse
    except ImportError as e:
        print(f"Warning: Missing required module: {e}")
    
    # Initialize utility system if needed
    try:
        from .utils import get_utility_manager
        utility_manager = get_utility_manager()
        utility_manager.initialize_default_utilities()
    except Exception as e:
        print(f"Warning: Utility system initialization failed: {e}")

# Auto-initialize when package is imported
_initialize_package()

# Version compatibility check
def check_compatibility():
    """Check Python version compatibility"""
    if sys.version_info < (3, 7):
        raise RuntimeError("MyGit requires Python 3.7 or higher")
    
    return True

# Run compatibility check
check_compatibility()

# Export version information
def get_version_info():
    """Get comprehensive version information"""
    return {
        'mygit_version': __version__,
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'platform': sys.platform,
    }

# Context manager for batch operations
class MyGitContext:
    """Context manager for MyGit operations"""
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources if needed
        pass
    
    def create_repository(self, path: str = ".", **kwargs):
        """Create a new repository with context management"""
        from .repository import Repository
        return Repository(path, create=True, **kwargs)

# Helper function for quick setup - FIXED: Import Repository inside function
def init_repository(path: str = ".", **kwargs):
    """Quickly initialize a new repository"""
    from .repository import Repository
    return Repository(path, create=True, **kwargs)

# Export helper functions
__all__.extend([
    'get_version_info',
    'MyGitContext',
    'init_repository',
])

# Package metadata for discovery
PACKAGE_METADATA = {
    'name': 'mygit',
    'version': __version__,
    'description': 'A minimal Git implementation in Python',
    'author': __author__,
    'email': __email__,
    'python_requires': '>=3.7',
    'keywords': ['git', 'vcs', 'version-control', 'education'],
    'classifiers': [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
}

# Backward compatibility exports
# These ensure existing code continues to work
Repository = Repository
main = main
GitObject = GitObject
Blob = Blob
Tree = Tree
Commit = Commit
ObjectFactory = ObjectFactory

# Development mode detection
def is_development_mode() -> bool:
    """Check if running in development mode"""
    return os.getenv('MYGIT_DEVELOPMENT', '0') == '1'

# Performance optimization for production
if not is_development_mode():
    # Production optimizations would go here
    pass

print(f"MyGit {__version__} initialized successfully")