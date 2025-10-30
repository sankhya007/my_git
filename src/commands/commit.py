import argparse
import time
import os
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.commit import Commit
from ..objects.tree import Tree
from pathlib import Path


def cmd_commit(args):
    """Record changes to the repository"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        # Create tree object from current directory
        tree_sha = _create_tree_from_directory(repo, Path('.'))
        
        # Create commit object
        commit = Commit()
        commit.tree = tree_sha
        commit.author = _get_author()
        commit.committer = _get_author()
        commit.message = args.message
        commit.timestamp = int(time.time())
        
        # Handle parent commit (if exists)
        head_path = repo.gitdir / "HEAD"
        if head_path.exists():
            head_ref = head_path.read_text().strip()
            if head_ref.startswith('ref: '):
                ref_path = repo.gitdir / head_ref[5:]
                if ref_path.exists():
                    commit.parents = [ref_path.read_text().strip()]
        
        # Store commit
        commit_sha = commit.get_hash()
        obj_path = repo.gitdir / "objects" / commit_sha[:2] / commit_sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(commit.compress())
        
        # Update HEAD
        if head_path.exists():
            head_ref = head_path.read_text().strip()
            if head_ref.startswith('ref: '):
                ref_path = repo.gitdir / head_ref[5:]
                ref_path.parent.mkdir(parents=True, exist_ok=True)
                ref_path.write_text(commit_sha + '\n')
        else:
            # Direct HEAD (detached state)
            head_path.write_text(commit_sha + '\n')
        
        print(f"Committed {commit_sha}")
        print(f"  {len(commit.message.splitlines())} files changed")
        return True
        
    except Exception as e:
        print(f"Error creating commit: {e}")
        return False

def _create_tree_from_directory(repo: Repository, directory: Path) -> str:
    """Create a tree object from directory contents"""
    tree = Tree()
    
    for item in sorted(directory.iterdir()):
        if item.name == '.mygit':
            continue
            
        if item.is_file():
            # Create blob for file
            blob = ObjectFactory.create_object('blob')
            blob.data = item.read_bytes()
            blob_sha = blob.get_hash()
            
            # Store blob
            obj_path = repo.gitdir / "objects" / blob_sha[:2] / blob_sha[2:]
            obj_path.parent.mkdir(parents=True, exist_ok=True)
            obj_path.write_bytes(blob.compress())
            
            # Add to tree (100644 = regular file)
            tree.add_entry('100644', item.name, blob_sha)
            
        elif item.is_dir():
            # Recursively create tree for subdirectory
            sub_tree_sha = _create_tree_from_directory(repo, item)
            tree.add_entry('40000', item.name, sub_tree_sha)
    
    # Store tree object
    tree_sha = tree.get_hash()
    obj_path = repo.gitdir / "objects" / tree_sha[:2] / tree_sha[2:]
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.write_bytes(tree.compress())
    
    return tree_sha

def _get_author() -> str:
    """Get author information from environment or config"""
    name = os.getenv('GIT_AUTHOR_NAME', 'Unknown Author')
    email = os.getenv('GIT_AUTHOR_EMAIL', 'unknown@example.com')
    return f"{name} <{email}>"

def setup_parser(parser):
    """Setup argument parser for commit command"""
    parser.add_argument("-m", "--message", required=True, help="Commit message")
    
# SPACE FOR IMPROVEMENT:
# - Amend commits
# - Commit signing
# - Template messages
# - Commit hooks
# - Partial commits