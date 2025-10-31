import argparse
from pathlib import Path
from ..repository import Repository
from ..objects.blob import Blob
from ..objects.factory import ObjectFactory

def cmd_add(args):
    """Add file contents to the staging area"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        factory = ObjectFactory.get_instance()
        added_count = 0
        
        for file_pattern in args.files:
            path = Path(file_pattern)
            
            if not path.exists():
                print(f"Warning: '{file_pattern}' matches no files")
                continue
            
            if path.is_file():
                # Create blob from file
                blob = Blob.from_file(str(path))
                # Write object to repository
                sha = factory.write_object(repo, blob)
                
                if args.verbose:
                    print(f"Added {file_pattern} -> {sha[:8]}")
                added_count += 1
            else:
                print(f"Skipping {file_pattern} (not a file)")
        
        if added_count > 0:
            print(f"Added {added_count} file(s) to staging area")
        else:
            print("No files were added")
            
        return True
        
    except Exception as e:
        print(f"Error adding files: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False

def setup_parser(parser):
    """Setup argument parser for add command"""
    parser.add_argument(
        "files",
        nargs="+",
        help="Files to add"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )