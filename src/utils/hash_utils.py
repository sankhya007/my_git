import hashlib
import zlib
import threading
import time
from typing import Union, Optional, Iterator, Dict, Any, List
from pathlib import Path
from functools import lru_cache
from enum import Enum

class HashAlgorithm(Enum):
    """Supported hash algorithms"""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"

class CompressionLevel(Enum):
    """Compression levels"""
    NO_COMPRESSION = 0
    BEST_SPEED = 1
    BALANCED = 6
    BEST_COMPRESSION = 9

class HashCollisionError(Exception):
    """Exception raised when hash collision is detected"""
    pass

class HashCache:
    """LRU cache for hash calculations"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl  # Time-to-live in seconds
        self._cache: Dict[str, tuple[str, float]] = {}  # key -> (hash, timestamp)
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[str]:
        """Get cached hash value"""
        with self._lock:
            if key in self._cache:
                hash_value, timestamp = self._cache[key]
                if time.time() - timestamp <= self.ttl:
                    return hash_value
                else:
                    # Expired entry
                    del self._cache[key]
            return None
    
    def set(self, key: str, hash_value: str):
        """Cache hash value"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (hash_value, time.time())
    
    def invalidate(self, key: str = None):
        """Invalidate cache entry or entire cache"""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            current_time = time.time()
            valid_entries = {k: v for k, v in self._cache.items() 
                           if current_time - v[1] <= self.ttl}
            
            return {
                'total_entries': len(self._cache),
                'valid_entries': len(valid_entries),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'hit_ratio': 'N/A',  # Would need hit/miss tracking
            }

class StreamingHasher:
    """Calculate hash of streaming data"""
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA1):
        self.algorithm = algorithm
        self._hash_obj = self._create_hash_object()
        self._total_size = 0
    
    def _create_hash_object(self):
        """Create appropriate hash object based on algorithm"""
        if self.algorithm == HashAlgorithm.MD5:
            return hashlib.md5()
        elif self.algorithm == HashAlgorithm.SHA1:
            return hashlib.sha1()
        elif self.algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256()
        elif self.algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512()
        elif self.algorithm == HashAlgorithm.BLAKE2B:
            return hashlib.blake2b()
        elif self.algorithm == HashAlgorithm.BLAKE2S:
            return hashlib.blake2s()
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
    
    def update(self, data: bytes):
        """Update hash with new data"""
        self._hash_obj.update(data)
        self._total_size += len(data)
    
    def hexdigest(self) -> str:
        """Get final hash value"""
        return self._hash_obj.hexdigest()
    
    def copy(self) -> 'StreamingHasher':
        """Create a copy of the current hasher state"""
        new_hasher = StreamingHasher(self.algorithm)
        new_hasher._hash_obj = self._hash_obj.copy()
        new_hasher._total_size = self._total_size
        return new_hasher
    
    @property
    def total_size(self) -> int:
        """Get total size of data processed"""
        return self._total_size
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hasher statistics"""
        return {
            'algorithm': self.algorithm.value,
            'total_size': self._total_size,
            'digest_size': self._hash_obj.digest_size,
            'block_size': self._hash_obj.block_size,
        }

class CollisionDetector:
    """Detect and handle hash collisions"""
    
    def __init__(self):
        self._hash_map: Dict[str, List[bytes]] = {}  # hash -> list of original data
        self._collisions: Dict[str, List[bytes]] = {}  # hash -> colliding data
        self._lock = threading.RLock()
    
    def check_collision(self, data: bytes, hash_value: str) -> bool:
        """Check for hash collision and record if found"""
        with self._lock:
            if hash_value in self._hash_map:
                # Check if this is actually different data
                existing_data_list = self._hash_map[hash_value]
                for existing_data in existing_data_list:
                    if existing_data != data:
                        # Collision detected!
                        if hash_value not in self._collisions:
                            self._collisions[hash_value] = []
                        self._collisions[hash_value].extend([existing_data, data])
                        return True
                # Same data, not a collision
                return False
            else:
                self._hash_map[hash_value] = [data]
                return False
    
    def get_collisions(self) -> Dict[str, List[bytes]]:
        """Get all detected collisions"""
        with self._lock:
            return self._collisions.copy()
    
    def has_collisions(self) -> bool:
        """Check if any collisions have been detected"""
        with self._lock:
            return len(self._collisions) > 0
    
    def clear(self):
        """Clear collision records"""
        with self._lock:
            self._hash_map.clear()
            self._collisions.clear()

# Global instances
_hash_cache = HashCache()
_collision_detector = CollisionDetector()

def sha1_hash(data: Union[str, bytes], use_cache: bool = True) -> str:
    """Calculate SHA-1 hash of data with caching support"""
    return calculate_hash(data, HashAlgorithm.SHA1, use_cache)

def calculate_hash(data: Union[str, bytes], algorithm: HashAlgorithm = HashAlgorithm.SHA1,
                  use_cache: bool = True, check_collision: bool = False) -> str:
    """Calculate hash of data with multiple algorithm support"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Create cache key
    cache_key = f"{algorithm.value}:{len(data)}:{hash(data)}"  # Simplified key
    
    # Check cache
    if use_cache:
        cached_hash = _hash_cache.get(cache_key)
        if cached_hash:
            return cached_hash
    
    # Calculate hash
    if algorithm == HashAlgorithm.MD5:
        hash_value = hashlib.md5(data).hexdigest()
    elif algorithm == HashAlgorithm.SHA1:
        hash_value = hashlib.sha1(data).hexdigest()
    elif algorithm == HashAlgorithm.SHA256:
        hash_value = hashlib.sha256(data).hexdigest()
    elif algorithm == HashAlgorithm.SHA512:
        hash_value = hashlib.sha512(data).hexdigest()
    elif algorithm == HashAlgorithm.BLAKE2B:
        hash_value = hashlib.blake2b(data).hexdigest()
    elif algorithm == HashAlgorithm.BLAKE2S:
        hash_value = hashlib.blake2s(data).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    # Check for collisions
    if check_collision:
        if _collision_detector.check_collision(data, hash_value):
            raise HashCollisionError(f"Hash collision detected for {algorithm.value}: {hash_value}")
    
    # Cache the result
    if use_cache:
        _hash_cache.set(cache_key, hash_value)
    
    return hash_value

@lru_cache(maxsize=1000)
def calculate_hash_cached(data: bytes, algorithm: str = 'sha1') -> str:
    """Calculate hash with functools.lru_cache (for immutable data)"""
    return calculate_hash(data, HashAlgorithm(algorithm), use_cache=False)

def streaming_hash(data_stream: Iterator[bytes], 
                  algorithm: HashAlgorithm = HashAlgorithm.SHA1) -> str:
    """Calculate hash of streaming data without loading everything into memory"""
    hasher = StreamingHasher(algorithm)
    
    for chunk in data_stream:
        hasher.update(chunk)
    
    return hasher.hexdigest()

def streaming_hash_file(file_path: Path, 
                       algorithm: HashAlgorithm = HashAlgorithm.SHA1,
                       chunk_size: int = 8192) -> str:
    """Calculate hash of file using streaming"""
    def file_chunk_generator():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    return streaming_hash(file_chunk_generator(), algorithm)

def compress_data(data: Union[str, bytes], 
                 level: Union[int, CompressionLevel] = CompressionLevel.BALANCED,
                 use_cache: bool = True) -> bytes:
    """Compress data using zlib with configurable level"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Resolve compression level
    if isinstance(level, CompressionLevel):
        level = level.value
    
    # Create cache key
    cache_key = f"compress:{level}:{len(data)}:{hash(data)}"
    
    # Check cache
    if use_cache:
        cached_result = _hash_cache.get(cache_key)
        if cached_result:
            # Cache stores hex string, we need to convert back to bytes
            return bytes.fromhex(cached_result)
    
    # Compress data
    compressed = zlib.compress(data, level)
    
    # Cache the result (store as hex for consistency)
    if use_cache:
        _hash_cache.set(cache_key, compressed.hex())
    
    return compressed

def decompress_data(compressed_data: bytes, use_cache: bool = True) -> bytes:
    """Decompress zlib-compressed data"""
    # Create cache key
    cache_key = f"decompress:{len(compressed_data)}:{hash(compressed_data)}"
    
    # Check cache
    if use_cache:
        cached_result = _hash_cache.get(cache_key)
        if cached_result:
            return bytes.fromhex(cached_result)
    
    # Decompress data
    try:
        decompressed = zlib.decompress(compressed_data)
    except zlib.error as e:
        raise ValueError(f"Decompression failed: {e}")
    
    # Cache the result
    if use_cache:
        _hash_cache.set(cache_key, decompressed.hex())
    
    return decompressed

def streaming_compress(data_stream: Iterator[bytes],
                      level: Union[int, CompressionLevel] = CompressionLevel.BALANCED) -> Iterator[bytes]:
    """Compress streaming data"""
    if isinstance(level, CompressionLevel):
        level = level.value
    
    compressor = zlib.compressobj(level)
    
    for chunk in data_stream:
        yield compressor.compress(chunk)
    
    yield compressor.flush()

def streaming_decompress(compressed_stream: Iterator[bytes]) -> Iterator[bytes]:
    """Decompress streaming data"""
    decompressor = zlib.decompressobj()
    
    for chunk in compressed_stream:
        yield decompressor.decompress(chunk)
    
    yield decompressor.flush()

def validate_sha1(sha: str) -> bool:
    """Validate if string is a valid SHA-1 hash"""
    return len(sha) == 40 and all(c in '0123456789abcdef' for c in sha.lower())

def validate_hash(hash_value: str, algorithm: HashAlgorithm = HashAlgorithm.SHA1) -> bool:
    """Validate if string is a valid hash for the given algorithm"""
    expected_lengths = {
        HashAlgorithm.MD5: 32,
        HashAlgorithm.SHA1: 40,
        HashAlgorithm.SHA256: 64,
        HashAlgorithm.SHA512: 128,
        HashAlgorithm.BLAKE2B: 128,
        HashAlgorithm.BLAKE2S: 64,
    }
    
    expected_length = expected_lengths.get(algorithm)
    if expected_length is None:
        return False
    
    return (len(hash_value) == expected_length and 
            all(c in '0123456789abcdef' for c in hash_value.lower()))

def get_hash_length(algorithm: HashAlgorithm) -> int:
    """Get expected hash length in hexadecimal characters"""
    lengths = {
        HashAlgorithm.MD5: 32,
        HashAlgorithm.SHA1: 40,
        HashAlgorithm.SHA256: 64,
        HashAlgorithm.SHA512: 128,
        HashAlgorithm.BLAKE2B: 128,
        HashAlgorithm.BLAKE2S: 64,
    }
    return lengths[algorithm]

def compare_hashes(hash1: str, hash2: str, algorithm: HashAlgorithm = HashAlgorithm.SHA1) -> bool:
    """Compare two hashes with validation"""
    if not validate_hash(hash1, algorithm) or not validate_hash(hash2, algorithm):
        raise ValueError("One or both hashes are invalid")
    
    return hash1.lower() == hash2.lower()

def get_compression_ratio(original_data: bytes, compressed_data: bytes) -> float:
    """Calculate compression ratio"""
    if not original_data:
        return 0.0
    return len(compressed_data) / len(original_data)

def get_compression_statistics(data: bytes, 
                              level: Union[int, CompressionLevel] = CompressionLevel.BALANCED) -> Dict[str, Any]:
    """Get detailed compression statistics"""
    original_size = len(data)
    compressed = compress_data(data, level, use_cache=False)
    compressed_size = len(compressed)
    
    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'compression_ratio': get_compression_ratio(data, compressed),
        'space_saved': original_size - compressed_size,
        'space_saved_percentage': ((original_size - compressed_size) / original_size) * 100,
        'compression_level': level.value if isinstance(level, CompressionLevel) else level,
    }

def get_available_algorithms() -> List[HashAlgorithm]:
    """Get list of available hash algorithms"""
    return list(HashAlgorithm)

def get_algorithm_info(algorithm: HashAlgorithm) -> Dict[str, Any]:
    """Get information about a hash algorithm"""
    info = {
        HashAlgorithm.MD5: {
            'name': 'MD5',
            'description': 'Message Digest Algorithm 5',
            'security': 'broken',
            'digest_size': 16,
            'block_size': 64,
        },
        HashAlgorithm.SHA1: {
            'name': 'SHA-1',
            'description': 'Secure Hash Algorithm 1',
            'security': 'weak',
            'digest_size': 20,
            'block_size': 64,
        },
        HashAlgorithm.SHA256: {
            'name': 'SHA-256',
            'description': 'Secure Hash Algorithm 256-bit',
            'security': 'strong',
            'digest_size': 32,
            'block_size': 64,
        },
        HashAlgorithm.SHA512: {
            'name': 'SHA-512',
            'description': 'Secure Hash Algorithm 512-bit',
            'security': 'strong',
            'digest_size': 64,
            'block_size': 128,
        },
        HashAlgorithm.BLAKE2B: {
            'name': 'BLAKE2b',
            'description': 'BLAKE2b hash function',
            'security': 'strong',
            'digest_size': 64,
            'block_size': 128,
        },
        HashAlgorithm.BLAKE2S: {
            'name': 'BLAKE2s',
            'description': 'BLAKE2s hash function',
            'security': 'strong',
            'digest_size': 32,
            'block_size': 64,
        },
    }
    
    return info.get(algorithm, {})

def get_global_cache_stats() -> Dict[str, Any]:
    """Get statistics for the global hash cache"""
    return _hash_cache.stats()

def get_collision_stats() -> Dict[str, Any]:
    """Get collision detection statistics"""
    collisions = _collision_detector.get_collisions()
    return {
        'total_collisions': len(collisions),
        'colliding_hashes': list(collisions.keys()),
        'has_collisions': _collision_detector.has_collisions(),
    }

def clear_hash_cache():
    """Clear the global hash cache"""
    _hash_cache.invalidate()

def clear_collision_detector():
    """Clear collision detection records"""
    _collision_detector.clear()

# Performance benchmarking
def benchmark_hash_performance(data: bytes, iterations: int = 1000) -> Dict[str, Any]:
    """Benchmark performance of different hash algorithms"""
    results = {}
    
    for algorithm in HashAlgorithm:
        start_time = time.time()
        
        for _ in range(iterations):
            calculate_hash(data, algorithm, use_cache=False)
        
        end_time = time.time()
        duration = end_time - start_time
        
        results[algorithm.value] = {
            'total_time': duration,
            'average_time': duration / iterations,
            'iterations_per_second': iterations / duration,
        }
    
    return results

def benchmark_compression_performance(data: bytes, iterations: int = 100) -> Dict[str, Any]:
    """Benchmark performance of different compression levels"""
    results = {}
    
    for level in CompressionLevel:
        start_time = time.time()
        
        for _ in range(iterations):
            compress_data(data, level, use_cache=False)
        
        end_time = time.time()
        duration = end_time - start_time
        
        compressed = compress_data(data, level, use_cache=False)
        stats = get_compression_statistics(data, level)
        
        results[level.value] = {
            'total_time': duration,
            'average_time': duration / iterations,
            'iterations_per_second': iterations / duration,
            'compression_stats': stats,
        }
    
    return results