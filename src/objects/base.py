from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, ClassVar, Iterator
import hashlib
import zlib
import os
import io
from pathlib import Path
from functools import lru_cache

class GitObject(ABC):
    """Base class for all Git objects with enhanced functionality"""
    
    # Object type registry
    _object_types: ClassVar[Dict[str, type]] = {}
    
    # Configuration
    DEFAULT_HASH_ALGORITHM = 'sha1'
    SUPPORTED_HASH_ALGORITHMS = ['sha1', 'sha256']
    COMPRESSION_LEVEL = 6
    CACHE_SIZE = 1000
    
    def __init__(self, data: bytes = None):
        self.data = data
        self._cached_hash: Optional[str] = None
        self._cached_serialized: Optional[bytes] = None
        self._size: Optional[int] = None
        
    @classmethod
    def register_type(cls, obj_type: str):
        """Class decorator to register object types"""
        def wrapper(obj_class):
            cls._object_types[obj_type] = obj_class
            return obj_class
        return wrapper
    
    @classmethod
    def get_object_class(cls, obj_type: str):
        """Get object class by type name"""
        return cls._object_types.get(obj_type)
    
    @classmethod
    def get_supported_types(cls) -> list:
        """Get list of supported object types"""
        return list(cls._object_types.keys())
    
    @abstractmethod
    def serialize(self) -> bytes:
        """Convert object to bytes for storage"""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes):
        """Load object from bytes"""
        pass
    
    def get_hash(self, algorithm: str = None) -> str:
        """Calculate hash of serialized object with optional algorithm"""
        if self._cached_hash and algorithm == self.DEFAULT_HASH_ALGORITHM:
            return self._cached_hash
            
        algorithm = algorithm or self.DEFAULT_HASH_ALGORITHM
        serialized = self.serialize()
        
        if algorithm == 'sha1':
            hash_obj = hashlib.sha1(serialized)
        elif algorithm == 'sha256':
            hash_obj = hashlib.sha256(serialized)
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        result = hash_obj.hexdigest()
        
        # Cache the default algorithm hash
        if algorithm == self.DEFAULT_HASH_ALGORITHM:
            self._cached_hash = result
            
        return result
    
    def get_size(self) -> int:
        """Get the size of the serialized object"""
        if self._size is None:
            self._size = len(self.serialize())
        return self._size
    
    def compress(self, level: int = None) -> bytes:
        """Compress object data for storage with configurable level"""
        level = level or self.COMPRESSION_LEVEL
        serialized = self.serialize()
        return zlib.compress(serialized, level)
    
    @staticmethod
    def decompress(data: bytes) -> bytes:
        """Decompress object data"""
        return zlib.decompress(data)
    
    @staticmethod
    @lru_cache(maxsize=CACHE_SIZE)
    def decompress_cached(data: bytes) -> bytes:
        """Decompress object data with caching"""
        return zlib.decompress(data)
    
    def validate(self) -> bool:
        """Validate object integrity and structure"""
        try:
            # Basic validation - serialization should work
            serialized = self.serialize()
            
            # Verify we can deserialize our own serialization
            test_obj = self.__class__()
            test_obj.deserialize(serialized)
            
            # Verify hash consistency
            original_hash = self.get_hash()
            test_hash = test_obj.get_hash()
            
            if original_hash != test_hash:
                return False
                
            return self._validate_internal()
            
        except Exception:
            return False
    
    def _validate_internal(self) -> bool:
        """Internal validation for subclass-specific rules"""
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary representation"""
        return {
            'type': self.__class__.__name__.lower(),
            'size': self.get_size(),
            'hash': self.get_hash(),
            'data_preview': self._get_data_preview()
        }
    
    def _get_data_preview(self, max_length: int = 100) -> str:
        """Get a preview of the object data"""
        if self.data is None:
            return "None"
        
        try:
            if isinstance(self.data, bytes):
                preview = self.data[:max_length].decode('utf-8', errors='replace')
                if len(self.data) > max_length:
                    preview += "..."
                return preview
            else:
                return str(self.data)[:max_length]
        except Exception:
            return f"<binary data: {len(self.data)} bytes>"
    
    @classmethod
    def create_header(cls, obj_type: str, data_size: int) -> bytes:
        """Create standardized object header"""
        return f"{obj_type} {data_size}\0".encode()
    
    @classmethod
    def parse_header(cls, header_data: bytes) -> tuple[str, int]:
        """Parse object header and return (type, size)"""
        try:
            header_str = header_data.decode('utf-8')
            if '\0' not in header_str:
                raise ValueError("Invalid header format: missing null terminator")
            
            type_size_part = header_str.split('\0')[0]
            parts = type_size_part.split(' ')
            
            if len(parts) != 2:
                raise ValueError("Invalid header format: expected 'type size'")
            
            obj_type = parts[0]
            size = int(parts[1])
            
            return obj_type, size
            
        except Exception as e:
            raise ValueError(f"Failed to parse object header: {e}")
    
    def stream_serialize(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Generator for streaming serialization (for large objects)"""
        serialized = self.serialize()
        for i in range(0, len(serialized), chunk_size):
            yield serialized[i:i + chunk_size]
    
    def stream_compress(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Generator for streaming compression (for large objects)"""
        for chunk in self.stream_serialize(chunk_size):
            yield zlib.compress(chunk, self.COMPRESSION_LEVEL)
    @classmethod
    def calculate_hash_from_stream(cls, data_stream, obj_type: str = "blob") -> str:
        """Calculate hash from a stream of data without loading everything into memory"""
        sha1 = hashlib.sha1()
        total_size = 0
        
        # Process data in chunks to update size and hash
        chunks = []
        for chunk in data_stream:
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            chunks.append(chunk)
            total_size += len(chunk)
        
        # Create header
        header = f"{obj_type} {total_size}\0".encode()
        sha1.update(header)
        
        # Update with data
        for chunk in chunks:
            sha1.update(chunk)
        
        return sha1.hexdigest()
    
    def memory_efficient_serialize(self, temp_dir: Path = None) -> Path:
        """Serialize large object to temporary file to avoid memory issues"""
        if temp_dir is None:
            temp_dir = Path("/tmp") if os.name != 'nt' else Path(os.environ.get('TEMP', 'C:/Temp'))
        
        temp_file = temp_dir / f"gitobj_{os.getpid()}_{id(self)}.tmp"
        
        try:
            with open(temp_file, 'wb') as f:
                # Write header
                header = self.create_header(
                    self.__class__.__name__.lower(), 
                    self.get_size()
                )
                f.write(header)
                
                # Write data in chunks if it's large
                if self.data and len(self.data) > 1024 * 1024:  # 1MB
                    for i in range(0, len(self.data), 8192):
                        f.write(self.data[i:i + 8192])
                else:
                    if self.data:
                        f.write(self.data)
            
            return temp_file
            
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the object"""
        serialized = self.serialize()
        compressed = self.compress()
        
        return {
            'type': self.__class__.__name__.lower(),
            'uncompressed_size': len(serialized),
            'compressed_size': len(compressed),
            'compression_ratio': len(compressed) / len(serialized) if serialized else 0,
            'hash_sha1': self.get_hash('sha1'),
            'hash_sha256': self.get_hash('sha256') if 'sha256' in self.SUPPORTED_HASH_ALGORITHMS else None,
        }
    
    def __eq__(self, other) -> bool:
        """Equality comparison based on content"""
        if not isinstance(other, GitObject):
            return False
        return self.get_hash() == other.get_hash()
    
    def __repr__(self) -> str:
        """String representation of the object"""
        return f"{self.__class__.__name__}(hash={self.get_hash()[:8]}, size={self.get_size()})"
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        stats = self.get_statistics()
        return (f"{self.__class__.__name__} | "
                f"Hash: {stats['hash_sha1'][:8]}... | "
                f"Size: {stats['uncompressed_size']} bytes | "
                f"Compressed: {stats['compressed_size']} bytes")


class ObjectValidationError(Exception):
    """Exception raised when object validation fails"""
    pass


class ObjectSerializationError(Exception):
    """Exception raised when object serialization fails"""
    pass


class LargeObjectManager:
    """Manager for handling large objects efficiently"""
    
    def __init__(self, max_memory_size: int = 10 * 1024 * 1024):  # 10MB default
        self.max_memory_size = max_memory_size
        self.temp_files: set[Path] = set()
    
    def should_use_disk(self, obj: GitObject) -> bool:
        """Determine if object should be processed on disk due to size"""
        return obj.get_size() > self.max_memory_size
    
    def create_disk_backed_object(self, obj: GitObject) -> Path:
        """Create a disk-backed representation of a large object"""
        temp_file = obj.memory_efficient_serialize()
        self.temp_files.add(temp_file)
        return temp_file
    
    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass  # Ignore cleanup errors
        self.temp_files.clear()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()


# Global large object manager instance
_large_object_manager = LargeObjectManager()

def get_large_object_manager() -> LargeObjectManager:
    """Get the global large object manager"""
    return _large_object_manager