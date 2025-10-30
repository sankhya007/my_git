import zlib
import struct
import hashlib
from typing import Union, Optional, Iterator, Tuple, Dict, Any
from pathlib import Path
import os
import threading
from functools import lru_cache
import io
from typing import List

class DeltaCompression:
    """Handles delta compression for similar objects"""
    
    @staticmethod
    def create_delta(base_data: bytes, target_data: bytes) -> bytes:
        """Create delta between base and target data"""
        # Simple implementation using xdelta-like approach
        # In production, this would use a proper diff algorithm
        
        if base_data == target_data:
            return b'same'  # Special case for identical data
        
        # Find common prefix and suffix
        prefix_len = 0
        max_prefix = min(len(base_data), len(target_data))
        while prefix_len < max_prefix and base_data[prefix_len] == target_data[prefix_len]:
            prefix_len += 1
        
        suffix_len = 0
        max_suffix = min(len(base_data) - prefix_len, len(target_data) - prefix_len)
        while suffix_len < max_suffix and base_data[-(suffix_len + 1)] == target_data[-(suffix_len + 1)]:
            suffix_len += 1
        
        # Construct delta
        delta_parts = []
        
        # Header: base size and target size
        delta_parts.append(struct.pack('>II', len(base_data), len(target_data)))
        
        # Copy instructions for common regions
        if prefix_len > 0:
            delta_parts.append(struct.pack('>BII', 0x01, 0, prefix_len))  # Copy from base
        
        # Insert instructions for differing middle part
        middle_target = target_data[prefix_len:len(target_data) - suffix_len] if suffix_len > 0 else target_data[prefix_len:]
        if middle_target:
            delta_parts.append(struct.pack('>BI', 0x02, len(middle_target)))  # Insert new data
            delta_parts.append(middle_target)
        
        if suffix_len > 0:
            delta_parts.append(struct.pack('>BII', 0x01, len(base_data) - suffix_len, suffix_len))  # Copy from base
        
        return b''.join(delta_parts)
    
    @staticmethod
    def apply_delta(base_data: bytes, delta: bytes) -> bytes:
        """Apply delta to base data to reconstruct target"""
        if delta == b'same':
            return base_data
        
        # Parse delta header
        if len(delta) < 8:
            raise ValueError("Invalid delta: too short")
        
        base_size, target_size = struct.unpack('>II', delta[:8])
        
        if len(base_data) != base_size:
            raise ValueError(f"Base size mismatch: expected {base_size}, got {len(base_data)}")
        
        result = bytearray()
        pos = 8
        
        while pos < len(delta):
            opcode = delta[pos]
            pos += 1
            
            if opcode == 0x01:  # Copy from base
                if len(delta) - pos < 8:
                    raise ValueError("Invalid copy instruction")
                offset, length = struct.unpack('>II', delta[pos:pos + 8])
                pos += 8
                result.extend(base_data[offset:offset + length])
            
            elif opcode == 0x02:  # Insert new data
                if len(delta) - pos < 4:
                    raise ValueError("Invalid insert instruction")
                length = struct.unpack('>I', delta[pos:pos + 4])[0]
                pos += 4
                if len(delta) - pos < length:
                    raise ValueError("Insert data truncated")
                result.extend(delta[pos:pos + length])
                pos += length
            
            else:
                raise ValueError(f"Unknown delta opcode: {opcode:02x}")
        
        if len(result) != target_size:
            raise ValueError(f"Target size mismatch: expected {target_size}, got {len(result)}")
        
        return bytes(result)

class PackFileWriter:
    """Writes Git pack files with efficient object storage"""
    
    def __init__(self, compression_level: int = 6):
        self.compression_level = compression_level
        self.objects: List[Tuple[str, bytes]] = []  # (sha, data)
        self.offsets: Dict[str, int] = {}
    
    def add_object(self, sha: str, data: bytes):
        """Add an object to the pack"""
        self.objects.append((sha, data))
    
    def write_pack(self, filepath: Path) -> Tuple[str, int]:
        """Write pack file and return pack SHA and object count"""
        # Sort objects by type and size for better delta compression
        self.objects.sort(key=lambda x: (x[1][:4], len(x[1])))  # Rough sort by type and size
        
        with open(filepath, 'wb') as f:
            # Write pack header
            f.write(b'PACK')  # Signature
            f.write(struct.pack('>I', 2))  # Version 2
            f.write(struct.pack('>I', len(self.objects)))  # Object count
            
            # Write objects
            for sha, data in self.objects:
                self.offsets[sha] = f.tell()
                self._write_pack_object(f, data)
            
            # Write trailer (SHA1 of pack content)
            pack_sha = self._calculate_pack_sha(filepath)
            f.write(pack_sha.encode())
        
        return pack_sha, len(self.objects)
    
    def _write_pack_object(self, f, data: bytes):
        """Write a single object to pack file"""
        # Simplified implementation - real Git packs are more complex
        compressed = zlib.compress(data, self.compression_level)
        
        # Write object header (type and size)
        obj_type = 1  # Assume committed object for simplicity
        size = len(data)
        
        # Variable-length size encoding
        header_byte = (obj_type << 4) | (size & 0x0F)
        size >>= 4
        while size > 0:
            header_byte |= 0x80
            f.write(bytes([header_byte]))
            header_byte = size & 0x7F
            size >>= 7
        f.write(bytes([header_byte]))
        
        # Write compressed data
        f.write(compressed)
    
    def _calculate_pack_sha(self, filepath: Path) -> str:
        """Calculate SHA1 of pack file content (excluding trailer)"""
        sha1 = hashlib.sha1()
        with open(filepath, 'rb') as f:
            content = f.read()  # Read entire file for simplicity
            # Exclude the last 20 bytes (trailer)
            sha1.update(content[:-20])
        return sha1.hexdigest()

class PackFileReader:
    """Reads objects from Git pack files"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.index: Dict[str, int] = {}  # sha -> offset
        self._load_index()
    
    def _load_index(self):
        """Load pack file index"""
        # Simplified - real implementation would parse .idx file
        pass
    
    def get_object(self, sha: str) -> Optional[bytes]:
        """Get object data by SHA"""
        if sha not in self.index:
            return None
        
        with open(self.filepath, 'rb') as f:
            f.seek(self.index[sha])
            return self._read_pack_object(f)
    
    def _read_pack_object(self, f) -> bytes:
        """Read a single object from pack file"""
        # Simplified implementation
        header_byte = f.read(1)[0]
        obj_type = (header_byte >> 4) & 0x07
        size = header_byte & 0x0F
        
        shift = 4
        while header_byte & 0x80:
            header_byte = f.read(1)[0]
            size |= (header_byte & 0x7F) << shift
            shift += 7
        
        # Read and decompress data
        compressed = f.read(size)  # This is simplified
        return zlib.decompress(compressed)

class StreamingCompressor:
    """Handles compression of large objects in chunks"""
    
    def __init__(self, compression_level: int = 6, chunk_size: int = 8192):
        self.compression_level = compression_level
        self.chunk_size = chunk_size
        self.compressor = zlib.compressobj(compression_level)
    
    def compress_chunk(self, chunk: bytes, final: bool = False) -> bytes:
        """Compress a chunk of data"""
        return self.compressor.compress(chunk) + (self.compressor.flush(zlib.Z_FINISH) if final else b'')
    
    def compress_stream(self, data_stream: Iterator[bytes]) -> Iterator[bytes]:
        """Compress a stream of data chunks"""
        for chunk in data_stream:
            yield self.compressor.compress(chunk)
        yield self.compressor.flush()

class StreamingDecompressor:
    """Handles decompression of large objects in chunks"""
    
    def __init__(self):
        self.decompressor = zlib.decompressobj()
    
    def decompress_chunk(self, chunk: bytes, final: bool = False) -> bytes:
        """Decompress a chunk of data"""
        return self.decompressor.decompress(chunk) + (self.decompressor.flush() if final else b'')
    
    def decompress_stream(self, compressed_stream: Iterator[bytes]) -> Iterator[bytes]:
        """Decompress a stream of compressed chunks"""
        for chunk in compressed_stream:
            yield self.decompressor.decompress(chunk)
        yield self.decompressor.flush()

class GitCompressor:
    """Handles Git object compression and decompression with advanced features"""
    
    # Compression profiles
    COMPRESSION_PROFILES = {
        'fast': 1,
        'balanced': 6,
        'best': 9,
        'git-default': 3,  # Git's default compression level
    }
    
    def __init__(self, compression_level: Union[int, str] = 'git-default'):
        self.compression_level = self._resolve_compression_level(compression_level)
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._stats = {
            'compressions': 0,
            'decompressions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'bytes_compressed': 0,
            'bytes_decompressed': 0,
        }
    
    def _resolve_compression_level(self, level: Union[int, str]) -> int:
        """Resolve compression level from string or integer"""
        if isinstance(level, str):
            return self.COMPRESSION_PROFILES.get(level, self.COMPRESSION_PROFILES['git-default'])
        return max(0, min(9, level))  # Clamp to valid range
    
    @lru_cache(maxsize=1000)
    def compress_object_cached(self, obj_type: str, data: bytes) -> bytes:
        """Compress object with caching"""
        return self.compress_object(obj_type, data)
    
    def compress_object(self, obj_type: str, data: bytes, use_delta: bool = False, 
                       base_data: bytes = None) -> bytes:
        """Compress a Git object with header and optional delta compression"""
        with self._cache_lock:
            self._stats['compressions'] += 1
            self._stats['bytes_compressed'] += len(data)
        
        header = f"{obj_type} {len(data)}\0".encode()
        full_data = header + data
        
        if use_delta and base_data:
            # Try delta compression
            delta = DeltaCompression.create_delta(base_data, data)
            if len(delta) < len(full_data) * 0.8:  # Use delta if it's significantly smaller
                delta_header = f"delta {len(delta)}\0".encode()
                return zlib.compress(delta_header + delta, self.compression_level)
        
        return zlib.compress(full_data, self.compression_level)
    
    def decompress_object(self, compressed_data: bytes, allow_delta: bool = False,
                         base_objects: Dict[str, bytes] = None) -> tuple:
        """Decompress Git object and return (obj_type, data)"""
        with self._cache_lock:
            self._stats['decompressions'] += 1
            self._stats['bytes_decompressed'] += len(compressed_data)
        
        try:
            full_data = zlib.decompress(compressed_data)
        except zlib.error as e:
            raise ValueError(f"Decompression failed: {e}")
        
        # Find null terminator
        null_pos = full_data.find(b'\0')
        if null_pos == -1:
            raise ValueError("Invalid object format: missing null terminator")
        
        header = full_data[:null_pos].decode('utf-8', errors='replace')
        parts = header.split(' ', 1)
        
        if len(parts) != 2:
            raise ValueError(f"Invalid object header: {header}")
        
        obj_type, size_str = parts
        
        # Handle delta objects
        if allow_delta and obj_type == 'delta':
            if not base_objects:
                raise ValueError("Delta compression requires base objects")
            
            delta_data = full_data[null_pos + 1:]
            expected_size = int(size_str)
            
            if len(delta_data) != expected_size:
                raise ValueError(f"Delta size mismatch: expected {expected_size}, got {len(delta_data)}")
            
            # In real implementation, we'd need to know which base to use
            # This is simplified
            if base_objects:
                base_data = next(iter(base_objects.values()))
                reconstructed_data = DeltaCompression.apply_delta(base_data, delta_data)
                # Parse the reconstructed object
                return self.decompress_object(reconstructed_data, allow_delta, base_objects)
        
        data = full_data[null_pos + 1:]
        
        # Verify size
        try:
            expected_size = int(size_str)
        except ValueError:
            raise ValueError(f"Invalid size in header: {size_str}")
        
        if len(data) != expected_size:
            raise ValueError(f"Object size mismatch: expected {expected_size}, got {len(data)}")
        
        return obj_type, data
    
    def compress_stream(self, obj_type: str, data_stream: Iterator[bytes], 
                       chunk_size: int = 8192) -> Iterator[bytes]:
        """Compress object data as a stream"""
        compressor = StreamingCompressor(self.compression_level, chunk_size)
        
        # First, we need to know the total size for the header
        # This is a limitation of the Git format - we need the size upfront
        # For true streaming, we'd need to buffer or use a different approach
        chunks = list(data_stream)
        total_size = sum(len(chunk) for chunk in chunks)
        
        # Create header
        header = f"{obj_type} {total_size}\0".encode()
        yield compressor.compress_chunk(header, final=False)
        
        # Compress data chunks
        for chunk in chunks:
            yield compressor.compress_chunk(chunk, final=False)
        
        # Finalize compression
        yield compressor.compress_chunk(b'', final=True)
    
    def decompress_stream(self, compressed_stream: Iterator[bytes]) -> Iterator[bytes]:
        """Decompress object data as a stream"""
        decompressor = StreamingDecompressor()
        
        for chunk in compressed_stream:
            yield decompressor.decompress_chunk(chunk, final=False)
        
        yield decompressor.decompress_chunk(b'', final=True)
    
    def create_pack_file(self, objects: Dict[str, bytes], pack_path: Path) -> Tuple[str, int]:
        """Create a pack file from multiple objects"""
        writer = PackFileWriter(self.compression_level)
        
        for sha, data in objects.items():
            writer.add_object(sha, data)
        
        return writer.write_pack(pack_path)
    
    def read_from_pack(self, pack_path: Path, sha: str) -> Optional[bytes]:
        """Read an object from a pack file"""
        reader = PackFileReader(pack_path)
        return reader.get_object(sha)
    
    def optimize_compression_level(self, sample_data: bytes) -> int:
        """Determine optimal compression level based on sample data"""
        # Simple heuristic: use faster compression for small objects
        if len(sample_data) < 1024:
            return self.COMPRESSION_PROFILES['fast']
        elif len(sample_data) < 1024 * 1024:  # 1MB
            return self.COMPRESSION_PROFILES['balanced']
        else:
            return self.COMPRESSION_PROFILES['best']
    
    def get_compression_ratio(self, original_data: bytes, compressed_data: bytes) -> float:
        """Calculate compression ratio"""
        if not original_data:
            return 0.0
        return len(compressed_data) / len(original_data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compression statistics"""
        with self._cache_lock:
            stats = self._stats.copy()
            stats['compression_level'] = self.compression_level
            stats['cache_size'] = len(self._cache)
            stats['cache_hit_ratio'] = (
                stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])
                if (stats['cache_hits'] + stats['cache_misses']) > 0 else 0.0
            )
        return stats
    
    def clear_cache(self):
        """Clear compression cache"""
        with self._cache_lock:
            self._cache.clear()
            self.compress_object_cached.cache_clear()
    
    def set_compression_level(self, level: Union[int, str]):
        """Set compression level"""
        self.compression_level = self._resolve_compression_level(level)
    
    @staticmethod
    def get_available_compression_profiles() -> Dict[str, int]:
        """Get available compression profiles"""
        return GitCompressor.COMPRESSION_PROFILES.copy()

# Global compressor instance
_global_compressor = None

def get_global_compressor() -> GitCompressor:
    """Get the global compressor instance"""
    global _global_compressor
    if _global_compressor is None:
        _global_compressor = GitCompressor()
    return _global_compressor

# Backward compatibility functions
def compress_object(obj_type: str, data: bytes) -> bytes:
    """Compress object using global compressor (backward compatibility)"""
    return get_global_compressor().compress_object(obj_type, data)

def decompress_object(compressed_data: bytes) -> tuple:
    """Decompress object using global compressor (backward compatibility)"""
    return get_global_compressor().decompress_object(compressed_data)