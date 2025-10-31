import argparse
import sys
import os
import zlib

from pathlib import Path
from typing import List, Optional, Iterator
from ..objects.factory import ObjectFactory
from ..repository import Repository
from ..objects.blob import Blob
from ..objects.tree import Tree
from ..objects.commit import Commit
from typing import Dict

class ObjectHasher:
    """Handles efficient object hashing and creation"""
    
    def __init__(self, repo: Optional[Repository] = None):
        self.repo = repo
        self.cache: Dict[str, str] = {}  # content_hash -> object_sha
    
    def hash_data(self, data: bytes, obj_type: str = "blob", create: bool = False) -> str:
        """Hash data and optionally create object"""
        obj = ObjectFactory.create_object(obj_type, data)
        sha = obj.get_hash()
        
        # Check cache first
        content_hash = self._get_content_hash(data)
        if content_hash in self.cache:
            return self.cache[content_hash]
        
        # Create object if requested
        if create and self.repo:
            self._store_object(obj, sha)
            self.cache[content_hash] = sha
        
        return sha
    
    def hash_file(self, file_path: Path, obj_type: str = "blob", create: bool = False, 
                  stream: bool = False) -> str:
        """Hash a file and optionally create object"""
        if stream and obj_type == "blob" and file_path.stat().st_size > 1024 * 1024:  # 1MB
            return self._hash_large_file(file_path, create)
        else:
            data = file_path.read_bytes()
            return self.hash_data(data, obj_type, create)
    
    def _hash_large_file(self, file_path: Path, create: bool) -> str:
        """Hash large files using streaming to avoid memory issues"""
        # For large files, we need to read, hash, and potentially write in chunks
        blob = Blob()
        
        if create and self.repo:
            # Stream directly to object storage
            return self._stream_file_to_object(file_path)
        else:
            # Just calculate hash without storing
            return self._calculate_file_hash(file_path)
    
    def _stream_file_to_object(self, file_path: Path) -> str:
        """Stream file directly to object storage while hashing"""
        import hashlib
        import zlib
        
        # Read file and build object in memory for now
        # In a more advanced implementation, this would stream to temp files
        data = file_path.read_bytes()
        
        blob = Blob(data)
        sha = blob.get_hash()
        self._store_object(blob, sha)
        
        return sha
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file without loading entire content into memory"""
        import hashlib
        
        sha1 = hashlib.sha1()
        file_size = 0
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha1.update(chunk)
                file_size += len(chunk)
        
        # Create header and final hash
        header = f"blob {file_size}\0".encode()
        sha1_header = hashlib.sha1(header)
        sha1_header.update(sha1.digest())
        
        return sha1_header.hexdigest()
    
    def _store_object(self, obj, sha: str):
        """Store object in repository"""
        if not self.repo:
            return
        
        obj_path = self.repo.gitdir / "objects" / sha[:2] / sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(obj_path, 'wb') as f:
            f.write(obj.compress())
    
    def _get_content_hash(self, data: bytes) -> str:
        """Get a quick hash of content for caching"""
        import hashlib
        return hashlib.md5(data).hexdigest()  # md5 is fine for cache

class BatchProcessor:
    """Process multiple files in batch mode"""
    
    def __init__(self, hasher: ObjectHasher):
        self.hasher = hasher
    
    def process_files(self, files: List[Path], obj_type: str, create: bool, 
                     stream: bool, verbose: bool) -> bool:
        """Process multiple files"""
        success = True
        
        for file_path in files:
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                success = False
                continue
            
            try:
                sha = self.hasher.hash_file(file_path, obj_type, create, stream)
                
                if verbose:
                    size = file_path.stat().st_size
                    print(f"{sha}  {size:8d}  {file_path}")
                else:
                    print(sha)
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                success = False
        
        return success
    
    def process_stdin_batch(self, create: bool, obj_type: str) -> bool:
        """Process multiple files from stdin (one per line)"""
        success = True
        
        for line in sys.stdin:
            file_path_str = line.strip()
            if not file_path_str:
                continue
            
            file_path = Path(file_path_str)
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                success = False
                continue
            
            try:
                sha = self.hasher.hash_file(file_path, obj_type, create, False)
                print(f"{sha} {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                success = False
        
        return success

def cmd_hash_object(args):
    """Compute object ID and optionally create object"""
    from pathlib import Path
    from ..objects.blob import Blob
    
    try:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File '{args.file}' not found")
            return False
            
        # Create blob from file
        blob = Blob.from_file(str(path))
        sha = blob.get_hash()
        
        if args.verbose:
            print(f"File: {args.file}")
            print(f"Size: {blob.get_size()} bytes")
            print(f"Type: {args.type}")
        
        # Write to object database if requested
        if args.write:
            from ..repository import find_repository
            from ..objects.factory import ObjectFactory
            
            repo = find_repository()
            if repo:
                factory = ObjectFactory.get_instance()
                written_sha = factory.write_object(repo, blob)
                if args.verbose:
                    print(f"Written to object database: {written_sha}")
                else:
                    print(written_sha)
            else:
                print(f"Error: Not in a git repository")
                return False
        else:
            # Just print the hash
            print(sha)
            
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def validate_object_type(obj_type: str) -> bool:
    """Validate that the object type is supported"""
    supported_types = ['blob', 'tree', 'commit']
    return obj_type in supported_types

def setup_parser(parser):
    """Setup argument parser for hash-object command"""
    
    # Main file argument (required)
    parser.add_argument(
        "file", 
        help="File to hash"
    )
    
    # Object options
    parser.add_argument(
        "-t", "--type",
        type=str,
        default="blob",
        choices=['blob', 'tree', 'commit'],
        help="Type of object to create (default: blob)"
    )
    parser.add_argument(
        "-w", "--write",
        action="store_true", 
        help="Actually write the object into the object database"
    )
    
    # Behavior options
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error on missing files or empty input"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output including file sizes and paths"
    )

def _display_usage_examples():
    """Display usage examples"""
    examples = """
Examples:
  # Hash a file without storing
  mygit hash-object file.txt

  # Hash and store object
  mygit hash-object -w file.txt

  # Hash from stdin
  echo "hello" | mygit hash-object -w

  # Hash multiple files
  mygit hash-object -w file1.txt file2.txt

  # Batch process files
  find . -name "*.txt" | mygit hash-object --batch -w

  # Hash as different object type
  mygit hash-object -t tree data.txt

  # Verbose output with file sizes
  mygit hash-object -v *.py

  # Stream large files
  mygit hash-object --stream -w large_file.iso
"""
    print(examples)

if __name__ == "__main__":
    # Test the hash-object command directly
    parser = argparse.ArgumentParser(
        description="Compute object ID and optionally create git objects",
        epilog="Use -h for more options"
    )
    setup_parser(parser)
    
    if len(sys.argv) == 1:
        _display_usage_examples()
        sys.exit(0)
    
    try:
        args = parser.parse_args()
        
        # Validate object type
        if not validate_object_type(args.type):
            print(f"Error: Unsupported object type '{args.type}'. Supported types: blob, tree, commit")
            sys.exit(1)
        
        # Handle stdin indicator
        if args.file == '-':
            args.file = None
        
        success = cmd_hash_object(args)
        sys.exit(0 if success else 1)
        
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)