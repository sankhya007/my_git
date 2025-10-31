import argparse
from pathlib import Path
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.commit import Commit
from datetime import datetime

def cmd_log(args):
    """Show commit history"""
    try:
        # Use current directory instead of find_repository()
        repo = Repository()
        
        if not repo.exists():
            print("Not a git repository")
            return False
        
        # Look for commit objects in the object database
        objects_dir = repo.gitdir / "objects"
        commits = []
        
        if objects_dir.exists():
            # Walk through all objects
            for prefix_dir in objects_dir.iterdir():
                if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
                    for obj_file in prefix_dir.iterdir():
                        if obj_file.is_file():
                            obj_sha = prefix_dir.name + obj_file.name
                            try:
                                # Try to read as commit
                                obj = ObjectFactory.read_object(repo, obj_sha)
                                if isinstance(obj, Commit):
                                    commits.append((obj_sha, obj))
                            except Exception:
                                # Skip objects that can't be read as commits
                                continue
        
        if not commits:
            print("No commits yet")
            return True
        
        # Sort commits by timestamp (newest first)
        commits.sort(key=lambda x: x[1].timestamp, reverse=True)
        
        print(f"Found {len(commits)} commit(s):")
        print("=" * 50)
        
        # Display commits
        for sha, commit in commits:
            if args.oneline:
                # One-line format
                short_sha = sha[:7]
                first_line = commit.message.split('\n')[0] if commit.message else ""
                print(f"{short_sha} {first_line}")
            else:
                # Full format
                print(f"commit {sha}")
                print(f"Author: {commit.author}")
                print(f"Date:   {_format_timestamp(commit.timestamp)}")
                print("")
                
                # Print message with indentation
                for line in commit.message.splitlines():
                    print(f"    {line}")
                
                print("")  # Empty line between commits
        
        return True
        
    except Exception as e:
        print(f"Error reading log: {e}")
        return False

def _format_timestamp(timestamp):
    """Format timestamp as readable date"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%a %b %d %H:%M:%S %Y %z")

def setup_parser(parser):
    """Setup argument parser for log command"""
    parser.add_argument(
        "--oneline",
        action="store_true",
        help="Print each commit on a single line"
    )