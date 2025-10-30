"""
Utility System for MyGit

This package provides a comprehensive suite of utility functions and classes that form
the foundation of MyGit's operations. The utilities are organized into specialized
modules for file operations, hashing, compression, and system integration.

Key Modules:
- file_utils: Advanced file system operations with cross-platform support
- hash_utils: Cryptographic hashing and data integrity verification  
- compression: Efficient data compression with streaming support
- system_utils: Platform-specific system integration and process management

Advanced Features:
- Cross-platform file system operations with proper error handling
- Multiple hash algorithms (SHA-1, SHA-256, BLAKE2) with streaming support
- Configurable compression with performance optimization
- Comprehensive file locking for concurrent access
- Memory-efficient streaming for large files
- Platform detection and adaptive behavior
- Comprehensive error handling and recovery mechanisms
"""

import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from functools import lru_cache
import warnings

class UtilityCategory(Enum):
    """Categories for organizing utility functions"""
    FILE_SYSTEM = "file_system"
    HASHING = "hashing"
    COMPRESSION = "compression" 
    SYSTEM = "system"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DEBUGGING = "debugging"

class UtilityManager:
    """
    Central management system for utility functions providing:
    - Function registration and discovery
    - Performance monitoring and optimization
    - Cross-platform compatibility management
    - Resource management and cleanup
    - Plugin system for custom utilities
    """
    
    def __init__(self):
        self._utilities: Dict[str, Dict[str, Any]] = {}
        self._categories: Dict[UtilityCategory, List[str]] = {}
        self._performance_stats: Dict[str, Any] = {
            'file_operations': 0,
            'hash_operations': 0,
            'compression_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors_handled': 0,
        }
        self._platform = self._detect_platform()
        self._initialized = False
    
    def _detect_platform(self) -> str:
        """Detect the current operating system platform"""
        if sys.platform.startswith('win'):
            return 'windows'
        elif sys.platform.startswith('darwin'):
            return 'macos'
        elif sys.platform.startswith('linux'):
            return 'linux'
        else:
            return 'unknown'
    
    def register_utility(self,
                        name: str,
                        function: Callable,
                        category: UtilityCategory,
                        description: str = "",
                        version: str = "1.0.0",
                        platform_specific: bool = False,
                        thread_safe: bool = True,
                        memory_efficient: bool = False) -> None:
        """
        Register a utility function with comprehensive metadata
        
        Args:
            name: Unique name for the utility
            function: The utility function or class
            category: Utility category for organization
            description: Human-readable description
            version: Utility version for compatibility
            platform_specific: Whether utility is platform-specific
            thread_safe: Whether utility is thread-safe
            memory_efficient: Whether utility is memory-efficient
        """
        self._utilities[name] = {
            'function': function,
            'category': category,
            'description': description or f"{name} utility",
            'version': version,
            'platform_specific': platform_specific,
            'thread_safe': thread_safe,
            'memory_efficient': memory_efficient,
            'usage_count': 0,
        }
        
        # Add to category
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)
    
    def get_utility(self, name: str) -> Optional[Callable]:
        """Get utility function by name"""
        if name in self._utilities:
            utility = self._utilities[name]
            utility['usage_count'] += 1
            return utility['function']
        return None
    
    def get_utility_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a utility"""
        if name in self._utilities:
            info = self._utilities[name].copy()
            info.pop('function', None)  # Remove function for serialization
            return info
        return None
    
    def list_utilities(self, 
                      category: UtilityCategory = None,
                      platform_compatible: bool = True) -> List[str]:
        """List utilities with filtering options"""
        if category:
            utility_names = self._categories.get(category, [])
        else:
            utility_names = list(self._utilities.keys())
        
        if platform_compatible:
            utility_names = [
                name for name in utility_names
                if not self._utilities[name].get('platform_specific', False) or
                self._is_platform_compatible(name)
            ]
        
        return sorted(utility_names)
    
    def _is_platform_compatible(self, utility_name: str) -> bool:
        """Check if utility is compatible with current platform"""
        utility = self._utilities.get(utility_name)
        if not utility or not utility.get('platform_specific', False):
            return True
        
        # Platform-specific compatibility checks would go here
        return True
    
    def get_categories(self) -> List[UtilityCategory]:
        """Get all utility categories"""
        return list(self._categories.keys())
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics for all utilities"""
        return {name: info['usage_count'] for name, info in self._utilities.items()}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def record_operation(self, operation_type: str) -> None:
        """Record an operation for performance tracking"""
        if operation_type in self._performance_stats:
            self._performance_stats[operation_type] += 1
    
    def initialize_default_utilities(self) -> None:
        """Initialize with default utility functions"""
        if self._initialized:
            return
        
        # Import and register core utilities
        from .file_utils import (
            read_file_chunks, calculate_file_hash, find_git_root, 
            list_files_recursive, FileLock, get_file_permissions,
            atomic_write, safe_rename, normalize_path
        )
        
        from .hash_utils import (
            sha1_hash, compress_data, decompress_data, validate_sha1,
            calculate_hash, streaming_hash, HashAlgorithm, HashCache,
            CollisionDetector, get_compression_ratio
        )
        
        from .compression import (
            GitCompressor, DeltaCompression, PackFileWriter, PackFileReader,
            StreamingCompressor, StreamingDecompressor
        )
        
        # Register file utilities
        self.register_utility(
            name='read_file_chunks',
            function=read_file_chunks,
            category=UtilityCategory.FILE_SYSTEM,
            description='Read file in chunks for memory-efficient processing',
            memory_efficient=True
        )
        
        self.register_utility(
            name='calculate_file_hash',
            function=calculate_file_hash,
            category=UtilityCategory.HASHING,
            description='Calculate hash of file content with multiple algorithms'
        )
        
        self.register_utility(
            name='find_git_root',
            function=find_git_root,
            category=UtilityCategory.FILE_SYSTEM,
            description='Find the root directory of a Git repository'
        )
        
        self.register_utility(
            name='FileLock',
            function=FileLock,
            category=UtilityCategory.SYSTEM,
            description='Cross-platform file locking mechanism',
            platform_specific=True,
            thread_safe=True
        )
        
        # Register hash utilities
        self.register_utility(
            name='sha1_hash',
            function=sha1_hash,
            category=UtilityCategory.HASHING,
            description='Calculate SHA-1 hash of data with caching'
        )
        
        self.register_utility(
            name='calculate_hash',
            function=calculate_hash,
            category=UtilityCategory.HASHING,
            description='Calculate hash with multiple algorithm support'
        )
        
        self.register_utility(
            name='HashCache',
            function=HashCache,
            category=UtilityCategory.PERFORMANCE,
            description='LRU cache for hash calculations'
        )
        
        # Register compression utilities
        self.register_utility(
            name='GitCompressor',
            function=GitCompressor,
            category=UtilityCategory.COMPRESSION,
            description='Git object compression with advanced features'
        )
        
        self.register_utility(
            name='DeltaCompression',
            function=DeltaCompression,
            category=UtilityCategory.COMPRESSION,
            description='Delta compression for similar objects'
        )
        
        self._initialized = True

# Global utility manager instance
_utility_manager = UtilityManager()

def get_utility_manager() -> UtilityManager:
    """Get the global utility manager instance"""
    return _utility_manager

def get_utility(name: str) -> Optional[Callable]:
    """Get utility function by name"""
    return _utility_manager.get_utility(name)

def register_utility(name: str, function: Callable, category: UtilityCategory, **kwargs) -> None:
    """Register a utility with the global manager"""
    _utility_manager.register_utility(name, function, category, **kwargs)

def list_utilities(category: UtilityCategory = None, **kwargs) -> List[str]:
    """List available utilities"""
    return _utility_manager.list_utilities(category, **kwargs)

# Import core utility modules
from .file_utils import (
    read_file_chunks,
    calculate_file_hash,
    find_git_root,
    list_files_recursive,
    FileLock,
    get_file_permissions,
    atomic_write,
    safe_rename,
    normalize_path,
    get_file_info,
    is_git_repository,
    get_repository_files
)

from .hash_utils import (
    sha1_hash,
    compress_data,
    decompress_data,
    validate_sha1,
    calculate_hash,
    streaming_hash,
    streaming_hash_file,
    HashAlgorithm,
    HashCache,
    CollisionDetector,
    StreamingHasher,
    get_compression_ratio,
    get_available_algorithms
)

from .compression import (
    GitCompressor,
    DeltaCompression,
    PackFileWriter,
    PackFileReader,
    StreamingCompressor,
    StreamingDecompressor,
    get_global_compressor
)

# Initialize default utilities
_utility_manager.initialize_default_utilities()

# Version information
__version__ = "2.1.0"
__author__ = "MyGit Utilities Team"
__description__ = "Comprehensive utility system for MyGit operations"

# Performance monitoring
import time
import atexit
from threading import Lock

class PerformanceMonitor:
    """Monitor and report utility system performance"""
    
    def __init__(self):
        self.start_time = time.time()
        self.operation_count = 0
        self.error_count = 0
        self._lock = Lock()
        atexit.register(self.report)
    
    def record_operation(self, success: bool = True):
        """Record an operation for performance tracking"""
        with self._lock:
            self.operation_count += 1
            if not success:
                self.error_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        duration = time.time() - self.start_time
        return {
            'operations': self.operation_count,
            'errors': self.error_count,
            'duration_seconds': duration,
            'operations_per_second': self.operation_count / duration if duration > 0 else 0,
            'error_rate': self.error_count / self.operation_count if self.operation_count > 0 else 0,
        }
    
    def report(self):
        """Report performance statistics at exit"""
        stats = self.get_stats()
        if stats['operations'] > 0:
            print(f"Utility System Performance: "
                  f"{stats['operations']} operations, "
                  f"{stats['errors']} errors, "
                  f"{stats['operations_per_second']:.2f} ops/sec")

_performance_monitor = PerformanceMonitor()

# Utility decorators for enhanced functionality
def timed_utility(func):
    """Decorator to time utility function execution"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            _performance_monitor.record_operation(success=True)
            return result
        except Exception as e:
            _performance_monitor.record_operation(success=False)
            raise e
        finally:
            # Log timing information for performance analysis
            duration = time.time() - start_time
            if duration > 1.0:  # Log slow operations
                warnings.warn(f"Slow utility operation: {func.__name__} took {duration:.2f}s")
    return wrapper

def memoized_utility(maxsize: int = 128):
    """Decorator to memoize utility function results"""
    def decorator(func):
        return lru_cache(maxsize=maxsize)(timed_utility(func))
    return decorator

def platform_specific(allowed_platforms: List[str]):
    """Decorator to make utility platform-specific"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_platform = _utility_manager._platform
            if current_platform not in allowed_platforms:
                raise NotImplementedError(
                    f"Utility {func.__name__} not supported on {current_platform}. "
                    f"Supported platforms: {allowed_platforms}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Common utility patterns and helpers
class UtilityPatterns:
    """Common utility patterns and helper methods"""
    
    @staticmethod
    def retry_operation(operation: Callable, 
                       max_attempts: int = 3, 
                       delay: float = 1.0,
                       exceptions: tuple = (Exception,)):
        """
        Retry an operation with exponential backoff
        
        Args:
            operation: The operation to retry
            max_attempts: Maximum number of retry attempts
            delay: Initial delay between attempts (seconds)
            exceptions: Exceptions that should trigger retry
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return operation()
            except exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
                continue
        
        raise last_exception
    
    @staticmethod
    def batch_operations(operations: List[Callable], 
                        batch_size: int = 100,
                        parallel: bool = False):
        """
        Execute operations in batches for better performance
        
        Args:
            operations: List of operations to execute
            batch_size: Number of operations per batch
            parallel: Whether to execute batches in parallel
        """
        results = []
        
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            
            if parallel:
                # Parallel execution would be implemented here
                batch_results = [op() for op in batch]
            else:
                batch_results = [op() for op in batch]
            
            results.extend(batch_results)
        
        return results
    
    @staticmethod
    def safe_file_operation(operation: Callable, 
                          cleanup: Callable = None,
                          *args, **kwargs):
        """
        Execute file operation with proper cleanup on failure
        
        Args:
            operation: File operation to execute
            cleanup: Cleanup function to call on failure
            *args, **kwargs: Arguments for the operation
        """
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            if cleanup:
                try:
                    cleanup()
                except Exception as cleanup_error:
                    warnings.warn(f"Cleanup failed: {cleanup_error}")
            raise e

# Context managers for resource management
class TemporaryFileContext:
    """Context manager for temporary file operations"""
    
    def __init__(self, prefix: str = "mygit_temp", suffix: str = ".tmp"):
        self.prefix = prefix
        self.suffix = suffix
        self.temp_files = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def create_temp_file(self, content: bytes = None) -> Path:
        """Create a temporary file"""
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(
            prefix=self.prefix,
            suffix=self.suffix,
            delete=False
        )
        
        if content:
            temp_file.write(content)
        
        temp_path = Path(temp_file.name)
        temp_file.close()
        self.temp_files.append(temp_path)
        
        return temp_path
    
    def cleanup(self):
        """Clean up all temporary files"""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                warnings.warn(f"Failed to delete temporary file {temp_file}: {e}")
        
        self.temp_files.clear()

class ResourcePool:
    """Pool for managing reusable resources"""
    
    def __init__(self, factory: Callable, max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self._pool = []
        self._lock = Lock()
    
    def acquire(self):
        """Acquire a resource from the pool"""
        with self._lock:
            if self._pool:
                return self._pool.pop()
            else:
                return self.factory()
    
    def release(self, resource):
        """Release a resource back to the pool"""
        with self._lock:
            if len(self._pool) < self.max_size:
                self._pool.append(resource)
            else:
                # Resource pool full, discard the resource
                if hasattr(resource, 'close'):
                    resource.close()

# Export public API with comprehensive documentation
__all__ = [
    # Core utility functions
    'read_file_chunks',
    'calculate_file_hash', 
    'find_git_root',
    'list_files_recursive',
    'sha1_hash',
    'compress_data',
    'decompress_data',
    'validate_sha1',
    'GitCompressor',
    
    # Advanced utilities
    'FileLock',
    'get_file_permissions',
    'atomic_write',
    'safe_rename',
    'normalize_path',
    'calculate_hash',
    'streaming_hash',
    'HashAlgorithm',
    'HashCache',
    'CollisionDetector',
    'DeltaCompression',
    'StreamingCompressor',
    
    # Management system
    'UtilityManager',
    'UtilityCategory',
    'get_utility_manager',
    'get_utility',
    'register_utility',
    'list_utilities',
    
    # Patterns and helpers
    'UtilityPatterns',
    'TemporaryFileContext',
    'ResourcePool',
    
    # Decorators
    'timed_utility',
    'memoized_utility',
    'platform_specific',
    
    # Constants and metadata
    '__version__',
    '__author__',
    '__description__',
]

# Backward compatibility exports
# These ensure existing code continues to work
read_file_chunks = read_file_chunks
calculate_file_hash = calculate_file_hash
find_git_root = find_git_root
list_files_recursive = list_files_recursive
sha1_hash = sha1_hash
compress_data = compress_data
decompress_data = decompress_data
validate_sha1 = validate_sha1
GitCompressor = GitCompressor

# Auto-configure based on environment
def _auto_configure():
    """Auto-configure the utility system based on environment"""
    import os
    
    # Enable performance monitoring in development
    if os.getenv('MYGIT_DEVELOPMENT', '0') == '1':
        # Development-specific configuration
        pass
    
    # Optimize for production
    if os.getenv('MYGIT_PRODUCTION', '0') == '1':
        # Production-specific configuration
        pass
    
    # Platform-specific optimizations
    if _utility_manager._platform == 'windows':
        # Windows-specific configuration
        pass
    elif _utility_manager._platform in ['linux', 'macos']:
        # Unix-specific configuration
        pass

_auto_configure()

# Initialize performance monitoring
def _enable_performance_monitoring():
    """Enable detailed performance monitoring"""
    # Additional performance monitoring setup would go here
    pass

# Utility system health check
def health_check() -> Dict[str, Any]:
    """Perform a health check of the utility system"""
    stats = _utility_manager.get_performance_stats()
    usage_stats = _utility_manager.get_usage_stats()
    performance_stats = _performance_monitor.get_stats()
    
    return {
        'utility_manager': {
            'registered_utilities': len(_utility_manager.list_utilities()),
            'categories': len(_utility_manager.get_categories()),
            'performance_stats': stats,
            'usage_stats': usage_stats,
        },
        'performance_monitor': performance_stats,
        'platform': _utility_manager._platform,
        'version': __version__,
    }

# Example usage and documentation
if __name__ == "__main__":
    # Demonstrate utility system capabilities
    print("MyGit Utility System")
    print("===================")
    
    # Show registered utilities by category
    for category in _utility_manager.get_categories():
        utilities = _utility_manager.list_utilities(category=category)
        print(f"\n{category.value.upper()} Utilities:")
        for utility in utilities:
            info = _utility_manager.get_utility_info(utility)
            if info:
                print(f"  - {utility}: {info['description']}")
    
    # Perform health check
    health = health_check()
    print(f"\nSystem Health: {health['utility_manager']['registered_utilities']} utilities registered")