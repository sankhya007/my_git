import hashlib
import zlib
from typing import Union

def sha1_hash(data: Union[str, bytes]) -> str:
    """Calculate SHA-1 hash of data"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha1(data).hexdigest()

def compress_data(data: Union[str, bytes]) -> bytes:
    """Compress data using zlib"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return zlib.compress(data)

def decompress_data(compressed_data: bytes) -> bytes:
    """Decompress zlib-compressed data"""
    return zlib.decompress(compressed_data)

def validate_sha1(sha: str) -> bool:
    """Validate if string is a valid SHA-1 hash"""
    return len(sha) == 40 and all(c in '0123456789abcdef' for c in sha.lower())

# SPACE FOR IMPROVEMENT:
# - Support for multiple hash algorithms
# - Streaming hash calculation
# - Hash caching
# - Collision detection