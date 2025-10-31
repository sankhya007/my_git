"""
Git Object System for MyGit

This package provides a complete implementation of Git's object model with enhanced
features for educational and production use. The object system forms the foundation
of Git's content-addressable storage and version control capabilities.

Key Components:
- GitObject: Base class for all Git objects with enhanced serialization
- Blob: File content storage with encoding detection and delta compression
- Tree: Directory structure representation with advanced merging capabilities  
- Commit: Snapshot metadata with GPG signing and template support
- ObjectFactory: Factory pattern for object creation with caching and pooling

Advanced Features:
- Multiple hash algorithms (SHA-1, SHA-256)
- Streaming support for large objects
- Object validation and integrity checking
- Delta compression for efficient storage
- Memory-efficient handling of large files
- Plugin system for custom object types
- Comprehensive error handling and recovery
"""

from __future__ import annotations
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Type, Optional, Any, Set
from enum import Enum
import warnings
import sys
import time
import atexit

# Import core object classes FIRST to avoid forward reference issues
from .base import GitObject, ObjectValidationError, ObjectSerializationError
from .blob import Blob, BlobDelta
from .tree import Tree, TreeEntry, TreeDiff
from .commit import Commit, CommitTemplate
from .factory import ObjectFactory, ObjectCache, ObjectPool, PluginRegistry

class ObjectType(Enum):
    """Enumeration of supported Git object types"""
    BLOB = "blob"
    TREE = "tree" 
    COMMIT = "commit"
    TAG = "tag"
    OFS_DELTA = "ofs-delta"
    REF_DELTA = "ref-delta"

class ObjectSystem:
    """
    Central management system for Git objects providing:
    - Type registration and discovery
    - Serialization format management
    - Object validation and integrity checking
    - Performance monitoring and optimization
    - Plugin system for custom object types
    """
    
    def __init__(self):
        self._object_types: Dict[ObjectType, Type[GitObject]] = {}
        self._custom_types: Dict[str, Type[GitObject]] = {}
        self._serialization_formats: Set[str] = {'default', 'streaming', 'compact'}
        self._validation_enabled: bool = True
        self._performance_stats: Dict[str, Any] = {
            'objects_created': 0,
            'objects_serialized': 0,
            'objects_deserialized': 0,
            'validation_checks': 0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
        self._initialized = False
    
    def register_object_type(self, 
                           obj_type: ObjectType, 
                           obj_class: Type[GitObject],
                           override: bool = False) -> None:
        """
        Register a Git object type with the system
        
        Args:
            obj_type: The type of Git object
            obj_class: The class implementing the object
            override: Whether to override existing registration
            
        Raises:
            ValueError: If type already registered and override is False
            TypeError: If obj_class doesn't inherit from GitObject
        """
        if not issubclass(obj_class, GitObject):
            raise TypeError(f"Object class must inherit from GitObject: {obj_class}")
        
        if obj_type in self._object_types and not override:
            raise ValueError(f"Object type {obj_type} already registered")
        
        self._object_types[obj_type] = obj_class
    
    def register_custom_type(self, 
                           type_name: str, 
                           obj_class: Type[GitObject],
                           description: str = "") -> None:
        """
        Register a custom object type for extension support
        
        Args:
            type_name: Unique name for the custom type
            obj_class: The class implementing the custom object
            description: Human-readable description of the type
        """
        if not issubclass(obj_class, GitObject):
            raise TypeError(f"Custom object class must inherit from GitObject: {obj_class}")
        
        self._custom_types[type_name] = obj_class
    
    def get_object_class(self, obj_type: ObjectType) -> Optional[Type[GitObject]]:
        """Get the class for a specific object type"""
        return self._object_types.get(obj_type)
    
    def get_custom_class(self, type_name: str) -> Optional[Type[GitObject]]:
        """Get the class for a custom object type"""
        return self._custom_types.get(type_name)
    
    def create_object(self, obj_type: ObjectType, data: bytes = None, **kwargs) -> GitObject:
        """Create a new object instance of the specified type"""
        obj_class = self.get_object_class(obj_type)
        if not obj_class:
            raise ValueError(f"Unknown object type: {obj_type}")
        
        obj = obj_class(**kwargs)
        if data is not None:
            obj.deserialize(data)
        
        self._performance_stats['objects_created'] += 1
        return obj
    
    def validate_object(self, obj: GitObject) -> bool:
        """Validate object integrity and format"""
        if not self._validation_enabled:
            return True
        
        self._performance_stats['validation_checks'] += 1
        
        try:
            return obj.validate()
        except Exception as e:
            warnings.warn(f"Object validation failed: {e}")
            return False
    
    def get_supported_types(self) -> List[ObjectType]:
        """Get list of supported object types"""
        return list(self._object_types.keys())
    
    def get_custom_types(self) -> List[str]:
        """Get list of registered custom types"""
        return list(self._custom_types.keys())
    
    def enable_validation(self, enabled: bool = True) -> None:
        """Enable or disable object validation"""
        self._validation_enabled = enabled
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset performance statistics"""
        self._performance_stats = {
            'objects_created': 0,
            'objects_serialized': 0,
            'objects_deserialized': 0,
            'validation_checks': 0,
            'cache_hits': 0,
            'cache_misses': 0,
        }
    
    def initialize_default_types(self) -> None:
        """Initialize with default Git object types"""
        if self._initialized:
            return
        
        # Register core object types
        self.register_object_type(ObjectType.BLOB, Blob)
        self.register_object_type(ObjectType.TREE, Tree)
        self.register_object_type(ObjectType.COMMIT, Commit)
        
        self._initialized = True

# Global object system instance
_object_system = ObjectSystem()

def get_object_system() -> ObjectSystem:
    """Get the global object system instance"""
    return _object_system

def create_object(obj_type: ObjectType, data: bytes = None, **kwargs) -> GitObject:
    """Create a new object using the global object system"""
    return _object_system.create_object(obj_type, data, **kwargs)

def validate_object(obj: Any) -> bool:
    """Validate an object using the global object system"""
    if not isinstance(obj, GitObject):
        return False
    return _object_system.validate_object(obj)

def register_object_type(obj_type: ObjectType, obj_class: Type[GitObject], **kwargs) -> None:
    """Register an object type with the global system"""
    _object_system.register_object_type(obj_type, obj_class, **kwargs)

def register_custom_type(type_name: str, obj_class: Type[GitObject], **kwargs) -> None:
    """Register a custom object type with the global system"""
    _object_system.register_custom_type(type_name, obj_class, **kwargs)

# Initialize default object types
_object_system.initialize_default_types()

# Version information
__version__ = "2.0.0"
__author__ = "MyGit Object System Team"
__description__ = "Advanced Git object system with enhanced features"

# Performance monitoring
class PerformanceMonitor:
    """Monitor and report object system performance"""
    
    def __init__(self):
        self.start_time = time.time()
        self.operation_count = 0
        atexit.register(self.report)
    
    def record_operation(self):
        """Record an operation for performance tracking"""
        self.operation_count += 1
    
    def report(self):
        """Report performance statistics at exit"""
        if self.operation_count > 0:
            duration = time.time() - self.start_time
            ops_per_second = self.operation_count / duration
            print(f"Object System Performance: {self.operation_count} operations "
                  f"in {duration:.2f}s ({ops_per_second:.2f} ops/sec)")

_performance_monitor = PerformanceMonitor()

# Plugin system for extensibility
class ObjectPlugin:
    """Base class for object system plugins"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
    
    def register_types(self, object_system: ObjectSystem) -> None:
        """Register custom object types - override in subclasses"""
        pass
    
    def initialize(self) -> None:
        """Initialize plugin - override in subclasses"""
        pass
    
    def cleanup(self) -> None:
        """Cleanup plugin resources - override in subclasses"""
        pass

# Auto-discovery for plugins
def discover_plugins() -> List[ObjectPlugin]:
    """Discover and load object system plugins"""
    plugins = []
    
    # Look for plugins in the plugins directory
    plugins_dir = Path(__file__).parent / "plugins"
    if plugins_dir.exists():
        for py_file in plugins_dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name.startswith("test_"):
                continue
            
            module_name = f"{__package__}.plugins.{py_file.stem}"
            try:
                module = importlib.import_module(module_name, package=__package__)
                
                # Look for plugin classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, ObjectPlugin) and 
                        obj != ObjectPlugin):
                        plugin = obj()
                        plugins.append(plugin)
                        
            except ImportError as e:
                warnings.warn(f"Failed to load plugin from {py_file}: {e}")
    
    return plugins

# Load and initialize plugins
_plugins = discover_plugins()
for plugin in _plugins:
    try:
        plugin.register_types(_object_system)
        plugin.initialize()
    except Exception as e:
        warnings.warn(f"Failed to initialize plugin {plugin.name}: {e}")

# Export public API with comprehensive documentation
__all__ = [
    # Core classes
    'GitObject',
    'Blob', 
    'Tree',
    'TreeEntry',
    'Commit',
    'ObjectFactory',
    
    # Advanced features
    'BlobDelta',
    'TreeDiff', 
    'CommitTemplate',
    'ObjectCache',
    'ObjectPool',
    'PluginRegistry',
    
    # Error classes
    'ObjectValidationError',
    'ObjectSerializationError',
    
    # Management system
    'ObjectSystem',
    'ObjectType',
    'ObjectPlugin',
    
    # Utility functions
    'get_object_system',
    'create_object', 
    'validate_object',
    'register_object_type',
    'register_custom_type',
    
    # Constants and metadata
    '__version__',
    '__author__',
    '__description__',
]

# Type checking support
if False:  # For mypy and other type checkers
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from .base import GitObject
        from .blob import Blob, BlobDelta
        from .tree import Tree, TreeEntry, TreeDiff
        from .commit import Commit, CommitTemplate
        from .factory import ObjectFactory, ObjectCache, ObjectPool, PluginRegistry

# Runtime type checking decorator
def expect_object_type(expected_type: ObjectType):
    """
    Decorator to validate that a function returns the expected object type
    
    Usage:
        @expect_object_type(ObjectType.BLOB)
        def create_blob(): ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, GitObject):
                try:
                    actual_type = ObjectType(result.__class__.__name__.lower())
                    if actual_type != expected_type:
                        raise TypeError(f"Expected {expected_type}, got {actual_type}")
                except ValueError:
                    # If the class name doesn't match any ObjectType, skip validation
                    pass
            return result
        return wrapper
    return decorator

# Context manager for batch operations
class ObjectBatchContext:
    """Context manager for batch object operations"""
    
    def __init__(self, object_system: ObjectSystem = None):
        self.object_system = object_system or _object_system
        self.operations = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.execute_batch()
    
    def add_operation(self, operation_type: str, *args, **kwargs):
        """Add an operation to the batch"""
        self.operations.append((operation_type, args, kwargs))
    
    def execute_batch(self):
        """Execute all batched operations"""
        # This would be implemented to optimize batch operations
        # For now, it's a placeholder for future optimization
        pass

# Utility function for common object operations
def calculate_object_hash(data: bytes, obj_type: ObjectType = ObjectType.BLOB) -> str:
    """Calculate the hash of serialized object data"""
    obj = create_object(obj_type, data)
    return obj.get_hash()

def serialize_objects(objects: List[GitObject]) -> List[bytes]:
    """Serialize multiple objects efficiently"""
    return [obj.serialize() for obj in objects]

def deserialize_objects(serialized_data: List[bytes], obj_type: ObjectType) -> List[GitObject]:
    """Deserialize multiple objects efficiently"""
    return [create_object(obj_type, data) for data in serialized_data]

# Initialize performance monitoring
def _enable_performance_monitoring():
    """Enable detailed performance monitoring"""
    # This would hook into the object system for detailed metrics
    pass

# Auto-configure based on environment
def _auto_configure():
    """Auto-configure the object system based on environment"""
    import os
    
    # Enable validation in development
    if os.getenv('MYGIT_DEVELOPMENT', '0') == '1':
        _object_system.enable_validation(True)
    
    # Disable validation for performance in production
    if os.getenv('MYGIT_PRODUCTION', '0') == '1':
        _object_system.enable_validation(False)

_auto_configure()