import argparse
import os
from pathlib import Path
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.tree import Tree

def cmd_add(args):
    """Add file contents to the index"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        for file_pattern in args.files:
            # Handle glob patterns
            paths = list(Path('.').glob(file_pattern))
            if not paths:
                print(f"Warning: {file_pattern} matches no files")
                continue
                
            for path in paths:
                if path.is_file():
                    _add_file(repo, path)
                elif path.is_dir():
                    # Recursively add directory contents
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            _add_file(repo, file_path)
        
        print("Files added successfully")
        return True
        
    except Exception as e:
        print(f"Error adding files: {e}")
        return False

def _add_file(repo: Repository, file_path: Path):
    """Add a single file to the object database"""
    # Create blob from file
    blob = ObjectFactory.create_object('blob')
    blob.data = file_path.read_bytes()
    
    # Calculate hash and store object
    sha = blob.get_hash()
    obj_path = repo.gitdir / "objects" / sha[:2] / sha[2:]
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.write_bytes(blob.compress())
    
    print(f"Added {file_path} -> {sha}")
    
    # SPACE FOR IMPROVEMENT:
    # - Implement proper staging area
    # - Handle file permissions
    # - Support for .gitignore
    # - Conflict detection

def setup_parser(parser):
    """Setup argument parser for add command"""
    parser.add_argument("files", nargs="+", help="Files to add")
    
# SPACE FOR IMPROVEMENT:
# - Interactive mode
# - Patch mode (-p)
# - Dry-run option
# - Force add for ignored files