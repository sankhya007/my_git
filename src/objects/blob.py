from .base import GitObject

class Blob(GitObject):
    """Represents file content"""
    
    def __init__(self, data: bytes = None):
        super().__init__(data)
    
    def serialize(self) -> bytes:
        """Format: blob {size}\0{content}"""
        if self.data is None:
            return b""
        header = f"blob {len(self.data)}\0".encode()
        return header + self.data
    
    def deserialize(self, data: bytes):
        """Parse blob data"""
        # Find null terminator after header
        null_pos = data.find(b'\0')
        if null_pos == -1:
            raise ValueError("Invalid blob format")
        
        # Extract content after header
        self.data = data[null_pos + 1:]
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Blob':
        """Create blob from file"""
        with open(filepath, 'rb') as f:
            return cls(f.read())
    
    # SPACE FOR IMPROVEMENT:
    # - Handle different file encodings
    # - Support for file permissions
    # - Delta compression for similar blobs
    # - Large file support (streaming)