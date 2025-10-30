from typing import Type
from .base import GitObject
from .blob import Blob
from .commit import Commit
from .tree import Tree

class ObjectFactory:
    """Creates and manages Git objects"""
    
    _types = {
        b'blob': Blob,
        b'commit': Commit,
        b'tree': Tree,
    }
    
    @classmethod
    def create_object(cls, obj_type: str, data: bytes = None) -> GitObject:
        """Create a new Git object"""
        obj_class = cls._types.get(obj_type.encode())
        if not obj_class:
            raise ValueError(f"Unknown object type: {obj_type}")
        
        obj = obj_class()
        if data:
            obj.deserialize(data)
        return obj
    
    @classmethod
    def read_object(cls, repo, sha: str) -> GitObject:
        """Read object from repository by SHA"""
        path = repo.gitdir / "objects" / sha[:2] / sha[2:]
        if not path.exists():
            raise FileNotFoundError(f"Object {sha} not found")
        
        with open(path, 'rb') as f:
            compressed = f.read()
        
        raw = GitObject.decompress(compressed)
        
        # Extract object type
        null_pos = raw.find(b'\0')
        if null_pos == -1:
            raise ValueError("Invalid object format")
        
        header = raw[:null_pos]
        obj_type, size_str = header.split(b' ', 1)
        
        return cls.create_object(obj_type.decode(), raw)
    
    # SPACE FOR IMPROVEMENT:
    # - Object caching
    # - Object pooling
    # - Type registry for plugins
    # - Object validation