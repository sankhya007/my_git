from abc import ABC, abstractmethod
from typing import Dict, Any
import hashlib
import zlib

class GitObject(ABC):
    """Base class for all Git objects"""
    
    def __init__(self, data: bytes = None):
        self.data = data
    
    @abstractmethod
    def serialize(self) -> bytes:
        """Convert object to bytes for storage"""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes):
        """Load object from bytes"""
        pass
    
    def get_hash(self) -> str:
        """Calculate SHA-1 hash of serialized object"""
        serialized = self.serialize()
        return hashlib.sha1(serialized).hexdigest()
    
    def compress(self) -> bytes:
        """Compress object data for storage"""
        return zlib.compress(self.serialize())
    
    @staticmethod
    def decompress(data: bytes) -> bytes:
        """Decompress object data"""
        return zlib.decompress(data)
    
    # SPACE FOR IMPROVEMENT:
    # - Add object validation
    # - Support for SHA-256
    # - Object caching
    # - Memory optimization for large objects