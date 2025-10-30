import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.blob import Blob
from ..objects.tree import Tree
from ..objects.commit import Commit

def cmd_cat_file(args):
    """Display contents and information about git objects"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    # Handle batch processing mode
    if args.batch or args.batch_check:
        return _batch_process_objects(repo, args)
    
    # Handle multiple objects
    if len(args.objects) > 1 and not (args.size or args.type):
        print("Error: Multiple objects only supported with -s or -t options")
        return False
    
    results = []
    for obj_hash in args.objects:
        result = _process_single_object(repo, obj_hash, args)
        results.append(result)
    
    return all(results)

def _process_single_object(repo: Repository, obj_hash: str, args) -> bool:
    """Process a single object based on command line options"""
    try:
        obj = ObjectFactory.read_object(repo, obj_hash)
        
        if args.size:
            size = _get_object_size(obj)
            print(size)
            return True
        elif args.type:
            obj_type = _get_object_type(obj)
            print(obj_type)
            return True
        elif args.pretty_print:
            return _pretty_print_object(obj, obj_hash, args)
        else:
            # Raw content
            raw_data = obj.serialize()
            if args.stream and hasattr(obj, 'data') and isinstance(obj.data, bytes):
                # Stream large objects in chunks
                _stream_object_data(obj.data)
            else:
                sys.stdout.buffer.write(raw_data)
            return True
            
    except FileNotFoundError:
        if not args.batch and not args.batch_check:
            print(f"Error: object {obj_hash} not found")
        return False
    except Exception as e:
        if not args.batch and not args.batch_check:
            print(f"Error reading object {obj_hash}: {e}")
        return False

def _get_object_size(obj) -> int:
    """Calculate the size of an object"""
    if hasattr(obj, 'data'):
        if isinstance(obj.data, bytes):
            return len(obj.data)
        else:
            return len(str(obj.data).encode())
    # For objects without data attribute, use serialized size
    return len(obj.serialize())

def _get_object_type(obj) -> str:
    """Get the type of an object as string"""
    return type(obj).__name__.lower()

def _pretty_print_object(obj, obj_hash: str, args) -> bool:
    """Pretty print an object based on its type"""
    try:
        if isinstance(obj, Blob):
            _pretty_print_blob(obj, args)
        elif isinstance(obj, Tree):
            _pretty_print_tree(obj, obj_hash, args)
        elif isinstance(obj, Commit):
            _pretty_print_commit(obj, obj_hash, args)
        else:
            print(f"Object {obj_hash}: {type(obj).__name__}")
            if hasattr(obj, 'data'):
                if isinstance(obj.data, bytes):
                    try:
                        # Try to decode as text
                        text = obj.data.decode('utf-8')
                        print(text)
                    except UnicodeDecodeError:
                        # Binary data, show hex dump for small files
                        if len(obj.data) <= 1024 and args.verbose:
                            _print_hex_dump(obj.data)
                        else:
                            print(f"[Binary data: {len(obj.data)} bytes]")
                else:
                    print(obj.data)
        return True
    except Exception as e:
        print(f"Error pretty printing object: {e}")
        return False

def _pretty_print_blob(blob: Blob, args):
    """Pretty print a blob object"""
    if blob.data is None:
        print("[Empty blob]")
        return
    
    try:
        # Try to decode as text
        text = blob.data.decode('utf-8')
        print(text, end='')
    except UnicodeDecodeError:
        # Binary data
        if len(blob.data) <= 1024 and args.verbose:
            print("Binary data:")
            _print_hex_dump(blob.data)
        else:
            print(f"[Binary data: {len(blob.data)} bytes]")

def _pretty_print_tree(tree: Tree, obj_hash: str, args):
    """Pretty print a tree object"""
    if args.verbose:
        print(f"tree {obj_hash}\n")
    
    for entry in tree.entries:
        mode = entry.mode
        obj_type = _mode_to_type(entry.mode)
        name = entry.name
        sha = entry.sha
        
        if args.verbose:
            print(f"{mode} {obj_type} {sha}\t{name}")
        else:
            print(f"{mode} {obj_type} {sha}\t{name}")

def _pretty_print_commit(commit: Commit, obj_hash: str, args):
    """Pretty print a commit object"""
    if args.verbose:
        print(f"commit {obj_hash}\n")
    
    print(f"tree {commit.tree}")
    for parent in commit.parents:
        print(f"parent {parent}")
    
    print(f"author {commit.author}")
    print(f"committer {commit.committer}")
    
    if hasattr(commit, 'timestamp') and commit.timestamp:
        from datetime import datetime
        dt = datetime.fromtimestamp(commit.timestamp)
        print(f"date   {dt.strftime('%a %b %d %H:%M:%S %Y %z')}")
    
    print()
    print(commit.message)

def _mode_to_type(mode: str) -> str:
    """Convert file mode to object type"""
    if mode.startswith('100'):
        return 'blob'
    elif mode.startswith('400'):
        return 'tree'
    elif mode.startswith('120'):
        return 'blob'  # symlink
    elif mode.startswith('160'):
        return 'commit'  # gitlink
    else:
        return 'unknown'

def _print_hex_dump(data: bytes, bytes_per_line: int = 16):
    """Print hex dump for binary data"""
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        print(f"{i:08x}: {hex_str:<48} {ascii_str}")

def _stream_object_data(data: bytes, chunk_size: int = 8192):
    """Stream large object data in chunks"""
    for i in range(0, len(data), chunk_size):
        sys.stdout.buffer.write(data[i:i + chunk_size])
        sys.stdout.buffer.flush()

def _batch_process_objects(repo: Repository, args) -> bool:
    """Process multiple objects in batch mode"""
    try:
        if args.batch_check:
            # Format: <sha> <type> <size>
            for line in sys.stdin:
                obj_hash = line.strip()
                if not obj_hash:
                    continue
                try:
                    obj = ObjectFactory.read_object(repo, obj_hash)
                    obj_type = _get_object_type(obj)
                    size = _get_object_size(obj)
                    print(f"{obj_hash} {obj_type} {size}")
                except Exception:
                    print(f"{obj_hash} missing")
        else:
            # Full batch mode
            for line in sys.stdin:
                obj_hash = line.strip()
                if not obj_hash:
                    continue
                try:
                    obj = ObjectFactory.read_object(repo, obj_hash)
                    if args.pretty_print:
                        _pretty_print_object(obj, obj_hash, args)
                    else:
                        raw_data = obj.serialize()
                        sys.stdout.buffer.write(raw_data)
                except Exception as e:
                    print(f"Error processing {obj_hash}: {e}")
        return True
    except KeyboardInterrupt:
        print("\nBatch processing interrupted")
        return False
    except Exception as e:
        print(f"Error in batch processing: {e}")
        return False

def setup_parser(parser):
    """Setup argument parser for cat-file command"""
    parser.add_argument(
        "objects", 
        nargs="*",
        help="The object(s) to display (SHA-1 hashes)"
    )
    
    # Output format options
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-p", "--pretty-print", 
        action="store_true", 
        help="Pretty print the object content based on its type"
    )
    output_group.add_argument(
        "-s", "--size",
        action="store_true",
        help="Print the size of the object"
    )
    output_group.add_argument(
        "-t", "--type",
        action="store_true", 
        help="Print the type of the object"
    )
    
    # Batch processing options
    batch_group = parser.add_mutually_exclusive_group()
    batch_group.add_argument(
        "--batch",
        action="store_true",
        help="Process multiple objects from stdin"
    )
    batch_group.add_argument(
        "--batch-check",
        action="store_true", 
        help="Process multiple objects from stdin, outputting type and size"
    )
    
    # Additional options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show more detailed output"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream large objects instead of loading into memory"
    )

def _handle_short_sha(repo: Repository, short_sha: str) -> Optional[str]:
    """Resolve short SHA to full SHA (basic implementation)"""
    # This is a simplified version - real Git has more sophisticated matching
    objects_dir = repo.gitdir / "objects"
    if not objects_dir.exists():
        return None
    
    prefix = short_sha[:2]
    suffix = short_sha[2:]
    prefix_dir = objects_dir / prefix
    
    if prefix_dir.exists():
        for obj_file in prefix_dir.iterdir():
            if obj_file.name.startswith(suffix):
                return prefix + obj_file.name
    
    return None

# Advanced feature: Object inspection and validation
def _validate_object_integrity(repo: Repository, obj_hash: str) -> bool:
    """Validate that object content matches its hash"""
    try:
        obj = ObjectFactory.read_object(repo, obj_hash)
        calculated_hash = obj.get_hash()
        return calculated_hash == obj_hash
    except Exception:
        return False

if __name__ == "__main__":
    # Test the cat-file command directly
    parser = argparse.ArgumentParser(description="Test cat-file command")
    setup_parser(parser)
    
    # Example test cases
    if len(sys.argv) == 1:
        print("Usage examples:")
        print("  mygit cat-file -p <sha>    # Pretty print object")
        print("  mygit cat-file -t <sha>    # Show object type")
        print("  mygit cat-file -s <sha>    # Show object size")
        print("  mygit cat-file --batch     # Batch process from stdin")
    else:
        test_args = parser.parse_args()
        cmd_cat_file(test_args)