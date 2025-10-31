import os
import threading
from typing import Type, Dict, Optional, Any, List
from pathlib import Path
from functools import lru_cache
from .base import GitObject, ObjectValidationError
from .blob import Blob
from .commit import Commit
from .tree import Tree

class ObjectCache:
    """LRU cache for Git objects to improve performance"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, GitObject] = {}
        self._lock = threading.RLock()
    
    def get(self, sha: str) -> Optional[GitObject]:
        """Get object from cache"""
        with self._lock:
            return self._cache.get(sha)
    
    def set(self, sha: str, obj: GitObject):
        """Add object to cache"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Remove oldest item (first key)
                if self._cache:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
            self._cache[sha] = obj
    
    def invalidate(self, sha: str = None):
        """Invalidate cache entry or entire cache"""
        with self._lock:
            if sha:
                self._cache.pop(sha, None)
            else:
                self._cache.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'usage_percentage': (len(self._cache) / self.max_size) * 100 if self.max_size > 0 else 0,
                'cached_objects': list(self._cache.keys())[:10]  # First 10 for preview
            }

class ObjectPool:
    """Object pool for efficient object reuse"""
    
    def __init__(self):
        self._pools: Dict[Type, List[GitObject]] = {}
        self._lock = threading.RLock()
    
    def acquire(self, obj_class: Type[GitObject]) -> GitObject:
        """Acquire an object from the pool"""
        with self._lock:
            if obj_class not in self._pools:
                self._pools[obj_class] = []
            
            if self._pools[obj_class]:
                return self._pools[obj_class].pop()
            else:
                return obj_class()
    
    def release(self, obj: GitObject):
        """Release an object back to the pool"""
        with self._lock:
            obj_class = type(obj)
            if obj_class not in self._pools:
                self._pools[obj_class] = []
            
            # Reset object state before returning to pool
            obj.__init__()
            self._pools[obj_class].append(obj)
    
    def clear(self, obj_class: Type[GitObject] = None):
        """Clear object pool"""
        with self._lock:
            if obj_class:
                self._pools.pop(obj_class, None)
            else:
                self._pools.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            stats = {}
            for obj_class, objects in self._pools.items():
                stats[obj_class.__name__] = len(objects)
            return stats

class PluginRegistry:
    """Registry for plugin object types"""
    
    def __init__(self):
        self._plugin_types: Dict[str, Type[GitObject]] = {}
        self._lock = threading.RLock()
    
    def register_type(self, obj_type: str, obj_class: Type[GitObject]):
        """Register a new object type"""
        with self._lock:
            if not issubclass(obj_class, GitObject):
                raise ValueError(f"Plugin class must inherit from GitObject: {obj_class}")
            self._plugin_types[obj_type] = obj_class
    
    def unregister_type(self, obj_type: str):
        """Unregister an object type"""
        with self._lock:
            self._plugin_types.pop(obj_type, None)
    
    def get_type(self, obj_type: str) -> Optional[Type[GitObject]]:
        """Get object class for type"""
        with self._lock:
            return self._plugin_types.get(obj_type)
    
    def list_types(self) -> List[str]:
        """List all registered plugin types"""
        with self._lock:
            return list(self._plugin_types.keys())
    
    def has_type(self, obj_type: str) -> bool:
        """Check if type is registered"""
        with self._lock:
            return obj_type in self._plugin_types

class ObjectFactory:
    """Creates and manages Git objects with enhanced functionality"""
    
    # Core object types
    _core_types = {
        'blob': Blob,
        'commit': Commit,
        'tree': Tree,
    }
    
    # Singleton instance
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize factory components"""
        self._cache = ObjectCache(max_size=1000)
        self._pool = ObjectPool()
        self._plugins = PluginRegistry()
        self._validation_enabled = True
    
    @classmethod
    def get_instance(cls) -> 'ObjectFactory':
        """Get singleton instance"""
        return cls()
    
    def create_object(self, obj_type: str, data: bytes = None, 
                     validate: bool = None) -> GitObject:
        """Create a new Git object with optional validation"""
        # Determine validation setting
        if validate is None:
            validate = self._validation_enabled
        
        # Get object class (check plugins first, then core types)
        obj_class = self._plugins.get_type(obj_type)
        if not obj_class:
            obj_class = self._core_types.get(obj_type)
        
        if not obj_class:
            raise ValueError(f"Unknown object type: {obj_type}")
        
        # Acquire object from pool
        obj = self._pool.acquire(obj_class)
        
        # Initialize with data if provided
        if data:
            try:
                obj.deserialize(data)
                
                # Validate object if requested
                if validate and not obj.validate():
                    self._pool.release(obj)
                    raise ObjectValidationError(f"Object validation failed for type: {obj_type}")
                    
            except Exception as e:
                self._pool.release(obj)
                raise e
        
        return obj
    
    def read_object(self, repo, sha: str, use_cache: bool = True, 
                   validate: bool = None) -> GitObject:
        """Read object from repository by SHA with caching"""
        # Check cache first
        if use_cache:
            cached_obj = self._cache.get(sha)
            if cached_obj:
                return cached_obj
        
        # Read from disk
        path = repo.gitdir / "objects" / sha[:2] / sha[2:]
        if not path.exists():
            raise FileNotFoundError(f"Object {sha} not found")
        
        try:
            with open(path, 'rb') as f:
                compressed = f.read()
            
            raw = GitObject.decompress(compressed)
            
            # Extract object type and validate header
            null_pos = raw.find(b'\0')
            if null_pos == -1:
                raise ObjectValidationError("Invalid object format: missing null terminator")
            
            header = raw[:null_pos]
            try:
                obj_type_str, size_str = header.split(b' ', 1)
                obj_type = obj_type_str.decode('ascii')
                expected_size = int(size_str)
            except (ValueError, UnicodeDecodeError) as e:
                raise ObjectValidationError(f"Invalid object header: {e}")
            
            # Validate size
            actual_size = len(raw) - null_pos - 1
            if actual_size != expected_size:
                raise ObjectValidationError(
                    f"Object size mismatch: expected {expected_size}, got {actual_size}"
                )
            
            # Create object
            obj = self.create_object(obj_type, raw, validate)
            
            # Verify SHA matches
            actual_sha = obj.get_hash()
            if actual_sha != sha:
                raise ObjectValidationError(
                    f"Object SHA mismatch: expected {sha}, got {actual_sha}"
                )
            
            # Cache the object
            if use_cache:
                self._cache.set(sha, obj)
            
            return obj
            
        except Exception as e:
            # Invalidate cache entry if read fails
            self._cache.invalidate(sha)
            raise e
    
    def write_object(self, repo, obj: GitObject, use_cache: bool = True) -> str:
        """Write object to repository and return SHA"""
        sha = obj.get_hash()
        
        # Check if object already exists
        obj_path = repo.gitdir / "objects" / sha[:2] / sha[2:]
        if obj_path.exists():
            return sha
        
        # Create directory if needed
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write object
        try:
            with open(obj_path, 'wb') as f:
                f.write(obj.compress())
            
            # Cache the object
            if use_cache:
                self._cache.set(sha, obj)
            
            return sha
            
        except Exception as e:
            # Remove partially written file
            if obj_path.exists():
                try:
                    obj_path.unlink()
                except OSError:
                    pass
            raise e
    
    def batch_read_objects(self, repo, sha_list: List[str], 
                          use_cache: bool = True) -> Dict[str, GitObject]:
        """Read multiple objects efficiently"""
        results = {}
        
        for sha in sha_list:
            try:
                obj = self.read_object(repo, sha, use_cache)
                results[sha] = obj
            except Exception as e:
                results[sha] = e  # Store error for this SHA
        
        return results
    
    def batch_write_objects(self, repo, objects: List[GitObject],
                           use_cache: bool = True) -> Dict[GitObject, str]:
        """Write multiple objects efficiently"""
        results = {}
        
        for obj in objects:
            try:
                sha = self.write_object(repo, obj, use_cache)
                results[obj] = sha
            except Exception as e:
                results[obj] = e  # Store error for this object
        
        return results
    
    def register_plugin_type(self, obj_type: str, obj_class: Type[GitObject]):
        """Register a plugin object type"""
        self._plugins.register_type(obj_type, obj_class)
    
    def unregister_plugin_type(self, obj_type: str):
        """Unregister a plugin object type"""
        self._plugins.unregister_type(obj_type)
    
    def list_available_types(self) -> List[str]:
        """List all available object types (core + plugins)"""
        core_types = list(self._core_types.keys())
        plugin_types = self._plugins.list_types()
        return sorted(set(core_types + plugin_types))
    
    def enable_validation(self, enable: bool = True):
        """Enable or disable object validation"""
        self._validation_enabled = enable
    
    def is_validation_enabled(self) -> bool:
        """Check if validation is enabled"""
        return self._validation_enabled
    
    def clear_cache(self):
        """Clear object cache"""
        self._cache.invalidate()
    
    def clear_pool(self):
        """Clear object pool"""
        self._pool.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self._cache.stats()
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return self._pool.stats()
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """Get plugin statistics"""
        return {
            'registered_types': self._plugins.list_types(),
            'total_plugins': len(self._plugins.list_types())
        }
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """Get comprehensive factory statistics"""
        return {
            'cache': self.get_cache_stats(),
            'pool': self.get_pool_stats(),
            'plugins': self.get_plugin_stats(),
            'validation_enabled': self._validation_enabled,
            'available_types': self.list_available_types(),
        }
    
    def prefetch_objects(self, repo, sha_list: List[str]):
        """Prefetch objects into cache"""
        for sha in sha_list:
            try:
                self.read_object(repo, sha, use_cache=True)
            except Exception:
                pass  # Ignore errors during prefetch
    
    def cleanup(self):
        """Clean up resources"""
        self.clear_cache()
        self.clear_pool()

# Global factory instance
_global_factory = None

def get_global_factory() -> ObjectFactory:
    """Get the global object factory instance"""
    global _global_factory
    if _global_factory is None:
        _global_factory = ObjectFactory()
    return _global_factory

# Backward compatibility functions
def create_object(obj_type: str, data: bytes = None) -> GitObject:
    """Create object using global factory (backward compatibility)"""
    return get_global_factory().create_object(obj_type, data)

def read_object(repo, sha: str) -> GitObject:
    """Read object using global factory (backward compatibility)"""
    return get_global_factory().read_object(repo, sha)

# Plugin example
class Tag(Commit):
    """Example plugin object type for Git tags"""
    
    def serialize(self) -> bytes:
        """Tag serialization would be different from commit"""
        # Simplified implementation
        return super().serialize()
    
    def deserialize(self, data: bytes):
        """Tag deserialization"""
        # Simplified implementation
        super().deserialize(data)

# Register the plugin type
def register_builtin_plugins():
    """Register built-in plugin types"""
    factory = get_global_factory()
    factory.register_plugin_type('tag', Tag)

# Auto-register plugins
register_builtin_plugins()