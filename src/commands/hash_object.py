import argparse
from pathlib import Path
from ..objects.factory import ObjectFactory
from ..repository import Repository
import sys

def cmd_hash_object(args):
    """Compute object ID and optionally create blob"""
    repo = Repository()
    
    if not repo.exists() and not args.create:
        print("Not a git repository (or any parent directory)")
        return False
    
    # Read input
    if args.file:
        with open(args.file, 'rb') as f:
            data = f.read()
    else:
        data = sys.stdin.buffer.read()
    
    # Create blob
    blob = ObjectFactory.create_object('blob', data)
    sha = blob.get_hash()
    
    # Write to object store if requested
    if args.create:
        obj_path = repo.gitdir / "objects" / sha[:2] / sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        with open(obj_path, 'wb') as f:
            f.write(blob.compress())
    
    print(sha)
    return True

def setup_parser(parser):
    parser.add_argument("-w", "--create", action="store_true", help="Actually create the object")
    parser.add_argument("file", nargs="?", help="File to hash")
    
# SPACE FOR IMPROVEMENT:
# - Streaming for large files
# - Multiple file support
# - Object type specification
# - Caching optimization