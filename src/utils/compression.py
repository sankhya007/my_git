import zlib
from typing import Union

class GitCompressor:
    """Handles Git object compression and decompression"""
    
    @staticmethod
    def compress_object(obj_type: str, data: bytes) -> bytes:
        """Compress a Git object with header"""
        header = f"{obj_type} {len(data)}\0".encode()
        full_data = header + data
        return zlib.compress(full_data)
    
    @staticmethod
    def decompress_object(compressed_data: bytes) -> tuple:
        """Decompress Git object and return (obj_type, data)"""
        full_data = zlib.decompress(compressed_data)
        
        # Find null terminator
        null_pos = full_data.find(b'\0')
        if null_pos == -1:
            raise ValueError("Invalid object format: missing null terminator")
        
        header = full_data[:null_pos].decode()
        obj_type, size_str = header.split(' ', 1)
        data = full_data[null_pos + 1:]
        
        # Verify size
        expected_size = int(size_str)
        if len(data) != expected_size:
            raise ValueError(f"Object size mismatch: expected {expected_size}, got {len(data)}")
        
        return obj_type, data
    
    @staticmethod
    def get_compression_level() -> int:
        """Get optimal compression level for Git objects"""
        return zlib.Z_BEST_SPEED  # Balance between speed and size

# SPACE FOR IMPROVEMENT:
# - Delta compression
# - Pack file support
# - Compression level tuning
# - Streaming compression