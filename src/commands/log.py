import argparse
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.commit import Commit

def cmd_log(args):
    """Show commit logs"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        # Get current HEAD
        head_path = repo.gitdir / "HEAD"
        if not head_path.exists():
            print("No commits yet")
            return True
        
        head_ref = head_path.read_text().strip()
        if head_ref.startswith('ref: '):
            ref_path = repo.gitdir / head_ref[5:]
            if ref_path.exists():
                commit_sha = ref_path.read_text().strip()
            else:
                print("No commits yet")
                return True
        else:
            commit_sha = head_ref
        
        # Walk through commit history
        current_sha = commit_sha
        count = 0
        
        while current_sha and count < (args.limit or float('inf')):
            commit_obj = ObjectFactory.read_object(repo, current_sha)
            if not isinstance(commit_obj, Commit):
                break
            
            _print_commit(commit_obj, current_sha)
            print()  # Empty line between commits
            
            # Move to parent
            current_sha = commit_obj.parents[0] if commit_obj.parents else None
            count += 1
        
        return True
        
    except Exception as e:
        print(f"Error reading log: {e}")
        return False

def _print_commit(commit: Commit, sha: str):
    """Print commit information in a readable format"""
    print(f"commit {sha}")
    print(f"Author: {commit.author}")
    print(f"Date:   {_format_timestamp(commit.timestamp)}")
    print()
    
    # Indent message
    for line in commit.message.splitlines():
        print(f"    {line}")

def _format_timestamp(timestamp: int) -> str:
    """Format timestamp as readable date"""
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%a %b %d %H:%M:%S %Y")

def setup_parser(parser):
    """Setup argument parser for log command"""
    parser.add_argument("-n", "--limit", type=int, help="Limit number of commits to show")
    
# SPACE FOR IMPROVEMENT:
# - Graph output
# - Filtering by author/date
# - Pretty formatting options
# - Follow renames
# - Patch output