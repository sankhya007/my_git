import argparse
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.commit import Commit
from ..objects.tree import Tree
from ..objects.blob import Blob

class CommitWalker:
    """Walks through commit history with various traversal strategies"""
    
    def __init__(self, repo: Repository):
        self.repo = repo
        self.visited: Set[str] = set()
    
    def get_start_commit(self, revision: str = "HEAD") -> Optional[str]:
        """Get the starting commit SHA from a revision reference"""
        if revision == "HEAD":
            return self._get_head_commit()
        else:
            return self._resolve_reference(revision)
    
    def _get_head_commit(self) -> Optional[str]:
        """Get the current HEAD commit"""
        head_path = self.repo.gitdir / "HEAD"
        if not head_path.exists():
            return None
        
        head_ref = head_path.read_text().strip()
        if head_ref.startswith('ref: '):
            ref_path = self.repo.gitdir / head_ref[5:]
            if ref_path.exists():
                return ref_path.read_text().strip()
        else:
            # Detached HEAD
            return head_ref
        
        return None
    
    def _resolve_reference(self, revision: str) -> Optional[str]:
        """Resolve a revision reference to a commit SHA"""
        # Try branches/tags first
        ref_paths = [
            self.repo.gitdir / "refs" / "heads" / revision,
            self.repo.gitdir / "refs" / "tags" / revision,
        ]
        
        for ref_path in ref_paths:
            if ref_path.exists():
                return ref_path.read_text().strip()
        
        # Try as direct SHA (full or partial)
        if len(revision) >= 4:
            return self._find_commit_by_partial_sha(revision)
        
        return None
    
    def _find_commit_by_partial_sha(self, partial_sha: str) -> Optional[str]:
        """Find a commit by partial SHA"""
        objects_dir = self.repo.gitdir / "objects"
        if not objects_dir.exists():
            return None
        
        prefix = partial_sha[:2]
        suffix = partial_sha[2:]
        prefix_dir = objects_dir / prefix
        
        if prefix_dir.exists():
            for obj_file in prefix_dir.iterdir():
                if obj_file.name.startswith(suffix):
                    full_sha = prefix + obj_file.name
                    try:
                        obj = ObjectFactory.read_object(self.repo, full_sha)
                        if isinstance(obj, Commit):
                            return full_sha
                    except Exception:
                        continue
        return None
    
    def walk_commits(self, start_sha: str, limit: Optional[int] = None, 
                    follow: bool = False) -> List[Commit]:
        """Walk through commit history"""
        commits = []
        queue = [start_sha]
        self.visited.clear()
        
        while queue and (limit is None or len(commits) < limit):
            current_sha = queue.pop(0)
            
            if current_sha in self.visited:
                continue
            self.visited.add(current_sha)
            
            try:
                commit = ObjectFactory.read_object(self.repo, current_sha)
                if not isinstance(commit, Commit):
                    continue
                
                commits.append(commit)
                
                # Add parents to queue
                if follow and commit.parents:
                    # In follow mode, only follow first parent (simplified)
                    queue.extend(commit.parents[:1])
                else:
                    queue.extend(commit.parents)
                    
            except Exception:
                continue
        
        return commits

class CommitFilter:
    """Filters commits based on various criteria"""
    
    @staticmethod
    def filter_by_author(commits: List[Commit], author_pattern: str) -> List[Commit]:
        """Filter commits by author name/email"""
        pattern = re.compile(author_pattern, re.IGNORECASE)
        return [c for c in commits if pattern.search(c.author)]
    
    @staticmethod
    def filter_by_date(commits: List[Commit], since: Optional[datetime] = None, 
                      until: Optional[datetime] = None) -> List[Commit]:
        """Filter commits by date range"""
        filtered = []
        
        for commit in commits:
            commit_time = datetime.fromtimestamp(commit.timestamp)
            
            if since and commit_time < since:
                continue
            if until and commit_time > until:
                continue
            
            filtered.append(commit)
        
        return filtered
    
    @staticmethod
    def filter_by_message(commits: List[Commit], message_pattern: str) -> List[Commit]:
        """Filter commits by message content"""
        pattern = re.compile(message_pattern, re.IGNORECASE)
        return [c for c in commits if pattern.search(c.message)]
    
    @staticmethod
    def filter_by_path(commits: List[Commit], repo: Repository, paths: List[str]) -> List[Commit]:
        """Filter commits that affect specific paths"""
        # This is a simplified implementation
        # A full implementation would need to compute diffs
        filtered = []
        
        for commit in commits:
            if CommitFilter._commit_affects_paths(commit, repo, paths):
                filtered.append(commit)
        
        return filtered
    
    @staticmethod
    def _commit_affects_paths(commit: Commit, repo: Repository, paths: List[str]) -> bool:
        """Check if a commit affects any of the specified paths"""
        try:
            # Get the tree for this commit
            tree_obj = ObjectFactory.read_object(repo, commit.tree)
            if not isinstance(tree_obj, Tree):
                return False
            
            # Simplified: check if any path matches tree entries
            for path in paths:
                path_parts = Path(path).parts
                if CommitFilter._path_in_tree(tree_obj, path_parts, repo):
                    return True
                    
        except Exception:
            pass
        
        return False
    
    @staticmethod
    def _path_in_tree(tree: Tree, path_parts: tuple, repo: Repository) -> bool:
        """Recursively check if path exists in tree"""
        if not path_parts:
            return True
        
        current_part = path_parts[0]
        remaining_parts = path_parts[1:]
        
        for entry in tree.entries:
            if entry.name == current_part:
                if not remaining_parts:
                    return True
                elif entry.mode.startswith('40000'):  # Directory
                    try:
                        sub_tree = ObjectFactory.read_object(repo, entry.sha)
                        if isinstance(sub_tree, Tree):
                            return CommitFilter._path_in_tree(sub_tree, remaining_parts, repo)
                    except Exception:
                        pass
                else:  # File
                    return not remaining_parts
        
        return False

class LogFormatter:
    """Formats commit log output in various styles"""
    
    @staticmethod
    def format_oneline(commit: Commit, sha: str, show_graph: bool = False, 
                      graph_chars: str = "") -> str:
        """Format commit as one line"""
        short_sha = sha[:7]
        first_line = commit.message.splitlines()[0] if commit.message else ""
        
        if show_graph:
            return f"{graph_chars} {short_sha} {first_line}"
        else:
            return f"{short_sha} {first_line}"
    
    @staticmethod
    def format_short(commit: Commit, sha: str) -> str:
        """Format commit in short style"""
        short_sha = sha[:7]
        author_name = commit.author.split('<')[0].strip()
        first_line = commit.message.splitlines()[0] if commit.message else ""
        
        return f"{short_sha} {author_name}: {first_line}"
    
    @staticmethod
    def format_medium(commit: Commit, sha: str) -> str:
        """Format commit in medium style (default)"""
        lines = []
        lines.append(f"commit {sha}")
        
        if hasattr(commit, 'parents') and commit.parents:
            parent_str = ' '.join(commit.parents)
            lines.append(f"Merge: {parent_str}")
        
        lines.append(f"Author: {commit.author}")
        lines.append(f"Date:   {LogFormatter._format_timestamp(commit.timestamp)}")
        lines.append("")
        
        # Indent message
        for line in commit.message.splitlines():
            lines.append(f"    {line}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_full(commit: Commit, sha: str) -> str:
        """Format commit in full style"""
        lines = []
        lines.append(f"commit {sha}")
        lines.append(f"Author: {commit.author}")
        lines.append(f"Commit: {commit.committer}")
        lines.append(f"Date:   {LogFormatter._format_timestamp(commit.timestamp)}")
        lines.append("")
        
        # Indent message
        for line in commit.message.splitlines():
            lines.append(f"    {line}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_raw(commit: Commit, sha: str) -> str:
        """Format commit in raw object format"""
        return commit.serialize().decode('utf-8', errors='replace')
    
    @staticmethod
    def _format_timestamp(timestamp: int) -> str:
        """Format timestamp as readable date"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%a %b %d %H:%M:%S %Y %z")

class GraphGenerator:
    """Generates ASCII graph for commit history"""
    
    @staticmethod
    def generate_graph(commits: List[Commit]) -> List[str]:
        """Generate ASCII graph lines for commits"""
        # Simplified graph implementation
        # A full implementation would track multiple branches
        graph_lines = []
        
        for i, commit in enumerate(commits):
            if i == 0:
                graph_chars = "*"
            else:
                graph_chars = "|"
            
            graph_lines.append(graph_chars)
        
        return graph_lines

class DiffGenerator:
    """Generates diffs for commits"""
    
    @staticmethod
    def generate_patch(commit: Commit, repo: Repository) -> str:
        """Generate patch for a commit"""
        # Simplified diff implementation
        # A full implementation would compute actual file differences
        
        if not commit.parents:
            return DiffGenerator._generate_initial_diff(commit, repo)
        else:
            return DiffGenerator._generate_commit_diff(commit, repo)
    
    @staticmethod
    def _generate_initial_diff(commit: Commit, repo: Repository) -> str:
        """Generate diff for initial commit"""
        try:
            tree_obj = ObjectFactory.read_object(repo, commit.tree)
            if not isinstance(tree_obj, Tree):
                return ""
            
            diff_lines = [f"diff --git a/initial b/initial", "new file mode 100644"]
            
            for entry in tree_obj.entries:
                if entry.mode.startswith('100'):  # Regular file
                    blob = ObjectFactory.read_object(repo, entry.sha)
                    if isinstance(blob, Blob):
                        content = blob.data.decode('utf-8', errors='replace')
                        lines = content.splitlines()
                        
                        diff_lines.extend([
                            f"--- /dev/null",
                            f"+++ b/{entry.name}",
                            "@@ -0,0 +1 @@",
                        ] + [f"+{line}" for line in lines] + [""])
            
            return '\n'.join(diff_lines)
        except Exception:
            return "Unable to generate diff\n"
    
    @staticmethod
    def _generate_commit_diff(commit: Commit, repo: Repository) -> str:
        """Generate diff for regular commit"""
        # Simplified - just show changed files
        try:
            parent_commit = ObjectFactory.read_object(repo, commit.parents[0])
            if not isinstance(parent_commit, Commit):
                return ""
            
            current_tree = ObjectFactory.read_object(repo, commit.tree)
            parent_tree = ObjectFactory.read_object(repo, parent_commit.tree)
            
            if not isinstance(current_tree, Tree) or not isinstance(parent_tree, Tree):
                return ""
            
            diff_lines = []
            
            # Compare tree entries (simplified)
            current_files = {entry.name: entry for entry in current_tree.entries}
            parent_files = {entry.name: entry for entry in parent_tree.entries}
            
            all_files = set(current_files.keys()) | set(parent_files.keys())
            
            for filename in sorted(all_files):
                if filename in current_files and filename not in parent_files:
                    diff_lines.append(f"diff --git a/{filename} b/{filename}")
                    diff_lines.append("new file mode 100644")
                elif filename not in current_files and filename in parent_files:
                    diff_lines.append(f"diff --git a/{filename} b/{filename}")
                    diff_lines.append("deleted file mode 100644")
                elif filename in current_files and filename in parent_files:
                    if current_files[filename].sha != parent_files[filename].sha:
                        diff_lines.append(f"diff --git a/{filename} b/{filename}")
                        diff_lines.append("modified file mode 100644")
            
            if not diff_lines:
                diff_lines.append("No changes detected")
            
            return '\n'.join(diff_lines)
        except Exception:
            return "Unable to generate diff\n"

def cmd_log(args):
    """Show commit history with advanced options"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        # Initialize components
        walker = CommitWalker(repo)
        formatter = LogFormatter()
        filterer = CommitFilter()
        
        # Get starting commit
        start_sha = walker.get_start_commit(args.revision)
        if not start_sha:
            print("No commits yet")
            return True
        
        # Walk commit history
        commits = walker.walk_commits(start_sha, args.limit, args.follow)
        
        if not commits:
            print("No commits found")
            return True
        
        # Apply filters
        if args.author:
            commits = filterer.filter_by_author(commits, args.author)
        
        if args.since or args.until:
            since_date = _parse_date(args.since) if args.since else None
            until_date = _parse_date(args.until) if args.until else None
            commits = filterer.filter_by_date(commits, since_date, until_date)
        
        if args.grep:
            commits = filterer.filter_by_message(commits, args.grep)
        
        if args.paths:
            commits = filterer.filter_by_path(commits, repo, args.paths)
        
        # Generate graph if needed
        graph_lines = []
        if args.graph:
            graph_lines = GraphGenerator.generate_graph(commits)
        
        # Output commits
        for i, commit in enumerate(commits):
            commit_sha = commit.get_hash()
            
            if args.oneline:
                graph_char = graph_lines[i] if args.graph and i < len(graph_lines) else ""
                line = formatter.format_oneline(commit, commit_sha, args.graph, graph_char)
                print(line)
            elif args.format == "short":
                print(formatter.format_short(commit, commit_sha))
            elif args.format == "full":
                print(formatter.format_full(commit, commit_sha))
            elif args.format == "raw":
                print(formatter.format_raw(commit, commit_sha))
            else:  # medium (default)
                print(formatter.format_medium(commit, commit_sha))
            
            # Show patch if requested
            if args.patch and i == 0:  # Only show for first commit in simplified version
                patch = DiffGenerator.generate_patch(commit, repo)
                if patch:
                    print("\n" + patch)
            
            # Add separator between commits (except for oneline)
            if not args.oneline and i < len(commits) - 1:
                print()
        
        return True
        
    except Exception as e:
        print(f"Error reading log: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False

def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string into datetime object"""
    try:
        # Relative dates (e.g., "1 week ago")
        if 'ago' in date_str.lower():
            return _parse_relative_date(date_str)
        
        # Absolute dates
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Default to current date if parsing fails
        return datetime.now()
    except Exception:
        return None

def _parse_relative_date(date_str: str) -> Optional[datetime]:
    """Parse relative date strings like '1 week ago'"""
    try:
        parts = date_str.lower().split()
        if len(parts) < 2 or parts[-1] != 'ago':
            return None
        
        quantity = int(parts[0])
        unit = parts[1]
        
        now = datetime.now()
        
        if unit.startswith('day'):
            return now - timedelta(days=quantity)
        elif unit.startswith('week'):
            return now - timedelta(weeks=quantity)
        elif unit.startswith('month'):
            return now - timedelta(days=quantity * 30)
        elif unit.startswith('year'):
            return now - timedelta(days=quantity * 365)
        elif unit.startswith('hour'):
            return now - timedelta(hours=quantity)
        elif unit.startswith('minute'):
            return now - timedelta(minutes=quantity)
        else:
            return None
    except Exception:
        return None

def setup_parser(parser):
    """Setup argument parser for log command"""
    # Output format options
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--oneline",
        action="store_true",
        help="Print each commit on a single line"
    )
    format_group.add_argument(
        "--format",
        choices=["short", "medium", "full", "raw"],
        default="medium",
        help="Set the output format"
    )
    
    # Filtering options
    parser.add_argument(
        "-n", "--limit",
        type=int,
        help="Limit number of commits to show"
    )
    parser.add_argument(
        "--author",
        help="Filter by author name/email"
    )
    parser.add_argument(
        "--since", "--after",
        help="Show commits more recent than specific date"
    )
    parser.add_argument(
        "--until", "--before", 
        help="Show commits older than specific date"
    )
    parser.add_argument(
        "--grep",
        help="Filter commits by message content"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Show only commits affecting specified paths"
    )
    
    # Advanced options
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Draw ASCII graph of commit history"
    )
    parser.add_argument(
        "-p", "--patch",
        action="store_true",
        help="Show patch (diff) for each commit"
    )
    parser.add_argument(
        "--follow",
        action="store_true", 
        help="Follow file renames"
    )
    parser.add_argument(
        "revision",
        nargs="?",
        default="HEAD",
        help="Start from specific revision (commit, branch, or tag)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )

def _display_usage_examples():
    """Display usage examples"""
    examples = """
Examples:
  # Basic log
  mygit log
  
  # Oneline format
  mygit log --oneline
  
  # With ASCII graph
  mygit log --graph --oneline
  
  # Limit number of commits
  mygit log -n 10
  
  # Filter by author
  mygit log --author "john"
  
  # Filter by date
  mygit log --since "2024-01-01"
  mygit log --until "1 week ago"
  
  # Filter by message
  mygit log --grep "bugfix"
  
  # Show patches
  mygit log -p
  
  # Follow specific path
  mygit log -- src/
  
  # Start from specific branch
  mygit log develop
  
  # Custom format
  mygit log --format=short
"""
    print(examples)

if __name__ == "__main__":
    # Test the log command directly
    parser = argparse.ArgumentParser(
        description="Show commit history",
        epilog="Use -h for more options"
    )
    setup_parser(parser)
    
    if len(sys.argv) == 1:
        _display_usage_examples()
        sys.exit(0)
    
    try:
        args = parser.parse_args()
        success = cmd_log(args)
        sys.exit(0 if success else 1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)