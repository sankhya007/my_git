import argparse
from pathlib import Path
from ..repository import Repository

def cmd_init(args):
    """Initialize a new repository"""
    repo = Repository(args.path)
    
    if repo.exists():
        print(f"Repository already exists at {repo.gitdir}")
        return False
    
    if repo.create():
        print(f"Initialized empty MyGit repository in {repo.gitdir}")
        return True
    else:
        print("Failed to initialize repository")
        return False

def setup_parser(parser):
    """Setup argument parser for init command"""
    parser.add_argument("path", nargs="?", default=".", help="Where to create the repository")
    
# SPACE FOR IMPROVEMENT:
# - Template repositories
# - Shared repository support
# - Custom directory structure
# - Initial branch configuration