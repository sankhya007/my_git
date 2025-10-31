import argparse
import time
from pathlib import Path
from ..repository import Repository
from ..objects.commit import Commit
from ..objects.tree import Tree
from ..objects.blob import Blob
from ..objects.factory import ObjectFactory

def cmd_commit(args):
    """Record changes to the repository"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        factory = ObjectFactory.get_instance()
        
        # Create a tree from staged files (simplified)
        tree = Tree()
        
        # Look for any files in the working directory
        for file_path in Path('.').iterdir():
            if file_path.is_file() and file_path.name != '.mygit':
                blob = Blob.from_file(str(file_path))
                blob_sha = factory.write_object(repo, blob)
                tree.add_file_entry(file_path.name, blob_sha)
        
        # Write the tree
        tree_sha = factory.write_object(repo, tree)
        
        # Create commit
        commit = Commit()
        commit.tree = tree_sha
        commit.author = "MyGit User <mygit@example.com>"
        commit.committer = "MyGit User <mygit@example.com>"
        commit.message = args.message
        commit.timestamp = int(time.time())
        
        # Write commit
        commit_sha = factory.write_object(repo, commit)
        
        print(f"Created commit: {commit_sha}")
        print(f"Tree: {tree_sha}")
        print(f"Message: {args.message}")
        print(f"Files: {len(tree.entries)}")
        
        return True
        
    except Exception as e:
        print(f"Error creating commit: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_parser(parser):
    parser.add_argument("-m", "--message", required=True, help="Commit message")