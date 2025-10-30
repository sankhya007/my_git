import os
import hashlib
from pathlib import Path
from typing import Optional, Iterator, Dict, Any
from .base import GitObject, ObjectValidationError


class Blob(GitObject):
    """Represents file content with enhanced functionality"""
    
    def __init__(self, data: bytes = None, filepath: str = None, encoding: str = 'utf-8', 
                 filemode: str = '100644'):
        super().__init__(data)
        self.filepath = filepath
        self.encoding = encoding
        self.filemode = filemode  # Git file mode (100644, 100755, 120000, etc.)
        self.original_size: Optional[int] = None
        self._delta_base: Optional[str] = None
        self._is_binary: Optional[bool] = None
    
    def serialize(self) -> bytes:
        """Format: blob {size}\0{content}"""
        if self.data is None:
            data_bytes = b""
        else:
            data_bytes = self.data
        
        header = self.create_header("blob", len(data_bytes))
        return header + data_bytes
    
    def deserialize(self, data: bytes):
        """Parse blob data with validation"""
        if not data:
            self.data = b""
            return
        
        # Parse header
        null_pos = data.find(b'\0')
        if null_pos == -1:
            raise ObjectValidationError("Invalid blob format: missing null terminator")
        
        header = data[:null_pos]
        try:
            obj_type, size = self.parse_header(header + b'\0')
            if obj_type != 'blob':
                raise ObjectValidationError(f"Expected blob type, got {obj_type}")
        except ValueError as e:
            raise ObjectValidationError(f"Invalid blob header: {e}")
        
        # Extract content after header
        content = data[null_pos + 1:]
        
        # Validate size
        if len(content) != size:
            raise ObjectValidationError(
                f"Blob size mismatch: header claims {size}, actual {len(content)}"
            )
        
        self.data = content
        self.original_size = size
    
    @classmethod
    def from_file(cls, filepath: str, encoding: str = 'utf-8', 
                  detect_encoding: bool = True) -> 'Blob':
        """Create blob from file with encoding detection"""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        
        # Get file mode
        filemode = cls._get_file_mode(path)
        
        # Read file content
        if detect_encoding:
            data, detected_encoding = cls._read_file_with_encoding_detection(path)
            encoding = detected_encoding
        else:
            data = path.read_bytes()
        
        blob = cls(data, str(path), encoding, filemode)
        blob.original_size = path.stat().st_size
        
        return blob
    
    @classmethod
    def from_text(cls, text: str, encoding: str = 'utf-8') -> 'Blob':
        """Create blob from text string"""
        data = text.encode(encoding)
        blob = cls(data, encoding=encoding)
        blob._is_binary = False
        return blob
    
    @classmethod
    def _read_file_with_encoding_detection(cls, filepath: Path) -> tuple[bytes, str]:
        """Read file with automatic encoding detection"""
        raw_data = filepath.read_bytes()
        
        # Try to detect encoding
        encoding = cls._detect_encoding(raw_data)
        
        return raw_data, encoding
    
    @staticmethod
    def _detect_encoding(data: bytes) -> str:
        """Detect text encoding"""
        import chardet
        
        try:
            result = chardet.detect(data)
            confidence = result.get('confidence', 0)
            encoding = result.get('encoding', 'utf-8')
            
            # Only use detected encoding if confidence is high
            if confidence > 0.7:
                return encoding.lower()
        except ImportError:
            # chardet not available, use basic detection
            pass
        
        # Basic encoding detection
        try:
            data.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            try:
                data.decode('latin-1')
                return 'latin-1'
            except UnicodeDecodeError:
                return 'binary'
    
    @staticmethod
    def _get_file_mode(filepath: Path) -> str:
        """Get Git file mode from file permissions"""
        try:
            stat = filepath.stat()
            
            if filepath.is_symlink():
                return '120000'  # Symbolic link
            
            if os.access(filepath, os.X_OK):
                return '100755'  # Executable file
            
            return '100644'  # Regular file
            
        except (OSError, AttributeError):
            return '100644'  # Default mode
    
    def is_binary(self) -> bool:
        """Check if blob contains binary data"""
        if self._is_binary is not None:
            return self._is_binary
        
        if self.data is None:
            self._is_binary = False
            return False
        
        # Check for null bytes and non-printable characters
        if b'\0' in self.data:
            self._is_binary = True
            return True
        
        # Check for high percentage of non-printable ASCII
        if len(self.data) > 0:
            printable_count = sum(1 for byte in self.data[:1000] if 32 <= byte <= 126 or byte in [9, 10, 13])
            printable_ratio = printable_count / min(len(self.data), 1000)
            
            self._is_binary = printable_ratio < 0.8
        
        return self._is_binary
    
    def get_text(self, encoding: str = None) -> str:
        """Get blob content as text"""
        if self.data is None:
            return ""
        
        encoding = encoding or self.encoding
        
        if encoding == 'binary':
            raise ValueError("Cannot decode binary data as text")
        
        try:
            return self.data.decode(encoding)
        except UnicodeDecodeError:
            # Fallback to utf-8 with error replacement
            return self.data.decode('utf-8', errors='replace')
    
    def set_text(self, text: str, encoding: str = 'utf-8'):
        """Set blob content from text"""
        self.data = text.encode(encoding)
        self.encoding = encoding
        self._is_binary = False
        self._cached_hash = None
        self._cached_serialized = None
        self._size = None
    
    def create_delta(self, base_blob: 'Blob') -> 'BlobDelta':
        """Create delta compression against base blob"""
        return BlobDelta.create_delta(base_blob, self)
    
    def apply_delta(self, delta: 'BlobDelta') -> 'Blob':
        """Apply delta to reconstruct blob"""
        return delta.apply_to_base(self)
    
    def stream_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Stream blob content in chunks (for large files)"""
        if self.data is None:
            return
        
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i:i + chunk_size]
    
    def _validate_internal(self) -> bool:
        """Internal validation for blob-specific rules"""
        if self.data is None:
            return True
        
        # Check that serialization/deserialization works
        try:
            serialized = self.serialize()
            test_blob = Blob()
            test_blob.deserialize(serialized)
            
            # Verify data integrity
            if self.data != test_blob.data:
                return False
                
        except Exception:
            return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about the blob"""
        stats = super().get_statistics()
        
        stats.update({
            'filemode': self.filemode,
            'encoding': self.encoding,
            'is_binary': self.is_binary(),
            'line_count': self._count_lines() if not self.is_binary() else None,
            'filepath': self.filepath,
            'original_size': self.original_size,
        })
        
        return stats
    
    def _count_lines(self) -> int:
        """Count lines in text content"""
        if self.data is None or self.is_binary():
            return 0
        
        try:
            text = self.get_text()
            return text.count('\n') + (1 if text and not text.endswith('\n') else 0)
        except Exception:
            return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert blob to dictionary representation"""
        base_dict = super().to_dict()
        
        base_dict.update({
            'filemode': self.filemode,
            'encoding': self.encoding,
            'is_binary': self.is_binary(),
            'filepath': self.filepath,
            'preview': self._get_content_preview(50),
        })
        
        return base_dict
    
    def _get_content_preview(self, max_lines: int = 5) -> str:
        """Get a preview of the blob content"""
        if self.data is None:
            return "Empty"
        
        if self.is_binary():
            return f"Binary data ({len(self.data)} bytes)"
        
        try:
            text = self.get_text()
            lines = text.splitlines()
            
            if len(lines) <= max_lines:
                return text
            else:
                preview = '\n'.join(lines[:max_lines])
                return f"{preview}\n... ({len(lines) - max_lines} more lines)"
                
        except Exception:
            return f"Data ({len(self.data)} bytes)"
    
    def __repr__(self) -> str:
        """String representation of the blob"""
        file_info = f", file='{self.filepath}'" if self.filepath else ""
        binary_info = ", binary" if self.is_binary() else ""
        return f"Blob(hash={self.get_hash()[:8]}, size={self.get_size()}{file_info}{binary_info})"


class BlobDelta:
    """Represents delta compression between two blobs"""
    
    def __init__(self, base_hash: str, target_hash: str, delta_data: bytes):
        self.base_hash = base_hash
        self.target_hash = target_hash
        self.delta_data = delta_data
    
    @classmethod
    def create_delta(cls, base_blob: Blob, target_blob: Blob) -> 'BlobDelta':
        """Create delta between base and target blobs"""
        # Simple implementation - in real Git this uses xdelta or similar
        # This is a simplified version for educational purposes
        
        base_data = base_blob.data or b""
        target_data = target_blob.data or b""
        
        # Simple diff algorithm (would be replaced with real diff in production)
        delta_data = cls._simple_diff(base_data, target_data)
        
        return cls(base_blob.get_hash(), target_blob.get_hash(), delta_data)
    
    @staticmethod
    def _simple_diff(base: bytes, target: bytes) -> bytes:
        """Simple diff algorithm for educational purposes"""
        # This is a very basic implementation
        # Real Git uses more sophisticated delta compression
        
        if base == target:
            return b"same"
        
        # Find common prefix and suffix
        prefix_len = 0
        while (prefix_len < len(base) and prefix_len < len(target) and 
               base[prefix_len] == target[prefix_len]):
            prefix_len += 1
        
        suffix_len = 0
        while (suffix_len < len(base) - prefix_len and suffix_len < len(target) - prefix_len and
               base[-(suffix_len + 1)] == target[-(suffix_len + 1)]):
            suffix_len += 1
        
        # Construct delta
        delta_parts = []
        
        if prefix_len > 0:
            delta_parts.append(f"prefix:{prefix_len}".encode())
        
        if suffix_len > 0:
            delta_parts.append(f"suffix:{suffix_len}".encode())
        
        # Middle part (changed content)
        middle_target = target[prefix_len:len(target) - suffix_len] if suffix_len > 0 else target[prefix_len:]
        if middle_target:
            delta_parts.append(b"insert:" + middle_target)
        
        return b"|".join(delta_parts)
    
    def apply_to_base(self, base_blob: Blob) -> Blob:
        """Apply delta to base blob to reconstruct target"""
        if base_blob.get_hash() != self.base_hash:
            raise ValueError("Delta base hash does not match provided base blob")
        
        base_data = base_blob.data or b""
        reconstructed_data = self._apply_diff(base_data, self.delta_data)
        
        result_blob = Blob(reconstructed_data)
        if result_blob.get_hash() != self.target_hash:
            raise ValueError("Reconstructed blob hash does not match target hash")
        
        return result_blob
    
    @staticmethod
    def _apply_diff(base: bytes, delta: bytes) -> bytes:
        """Apply simple diff to reconstruct data"""
        if delta == b"same":
            return base
        
        parts = delta.split(b"|")
        result_parts = []
        base_pos = 0
        base_len = len(base)
        
        for part in parts:
            if part.startswith(b"prefix:"):
                length = int(part[7:].decode())
                result_parts.append(base[:length])
                base_pos = length
            elif part.startswith(b"suffix:"):
                length = int(part[7:].decode())
                result_parts.append(base[-length:])
            elif part.startswith(b"insert:"):
                result_parts.append(part[7:])
        
        return b"".join(result_parts)
    
    def get_size(self) -> int:
        """Get size of delta data"""
        return len(self.delta_data)
    
    def get_compression_ratio(self, original_size: int) -> float:
        """Get compression ratio compared to original size"""
        return len(self.delta_data) / original_size if original_size > 0 else 0


# Register blob type with the base class
GitObject.register_type('blob')(Blob)