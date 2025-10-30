import argparse
import os
from pathlib import Path
from typing import List, Set
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.tree import Tree

class StagingArea:
    """Manages the staging area (index) for files to be committed"""
    
    def __init__(self, repo: Repository):
        self.repo = repo
        self.index_file = repo.gitdir / "index"
        self.staged_files: Set[str] = set()
        self._load_index()
    
    def _load_index(self):
        """Load existing staged files from index"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.staged_files = set(line.strip() for line in f if line.strip())
            except Exception:
                self.staged_files = set()
    
    def _save_index(self):
        """Save staged files to index"""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, 'w') as f:
            for file_path in sorted(self.staged_files):
                f.write(f"{file_path}\n")
    
    def add_file(self, file_path: str, blob_sha: str):
        """Add a file to the staging area"""
        self.staged_files.add(f"{file_path}|{blob_sha}")
        self._save_index()
    
    def is_ignored(self, file_path: Path) -> bool:
        """Check if file should be ignored based on .gitignore rules"""
        gitignore_path = self.repo.worktree / ".gitignore"
        if not gitignore_path.exists():
            return False
        
        try:
            with open(gitignore_path, 'r') as f:
                ignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            for pattern in ignore_patterns:
                if self._matches_pattern(file_path, pattern):
                    return True
        except Exception:
            pass
        
        return False
    
    def _matches_pattern(self, file_path: Path, pattern: str) -> bool:
        """Check if file path matches gitignore pattern"""
        # Simple pattern matching - can be enhanced for full gitignore spec
        if pattern.startswith('/'):
            pattern = pattern[1:]
            return str(file_path) == pattern
        
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            return pattern in str(file_path)
        
        return pattern in str(file_path)
    
    def get_staged_files(self) -> List[str]:
        """Get list of currently staged files"""
        return [path.split('|')[0] for path in self.staged_files]

def cmd_add(args):
    """Add file contents to the staging area"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        staging = StagingArea(repo)
        added_count = 0
        skipped_count = 0
        
        for file_pattern in args.files:
            if args.dry_run:
                print(f"Dry run: would process pattern '{file_pattern}'")
                continue
                
            paths = _expand_pattern(file_pattern, args.force)
            
            if not paths and not args.force:
                print(f"Warning: '{file_pattern}' matches no files")
                continue
            
            for path in paths:
                if staging.is_ignored(path) and not args.force:
                    if args.verbose:
                        print(f"Skipping ignored file: {path}")
                    skipped_count += 1
                    continue
                
                if path.is_file():
                    if _add_file(repo, staging, path, args.verbose):
                        added_count += 1
                elif path.is_dir() and not args.no_recurse:
                    dir_added, dir_skipped = _add_directory(repo, staging, path, args)
                    added_count += dir_added
                    skipped_count += dir_skipped
        
        if args.dry_run:
            print("Dry run completed - no files were actually added")
            return True
            
        if added_count > 0:
            print(f"Added {added_count} file(s) to staging area")
            if skipped_count > 0 and args.verbose:
                print(f"Skipped {skipped_count} file(s) (ignored or invalid)")
            
            if args.verbose:
                staged_files = staging.get_staged_files()
                if staged_files:
                    print("Currently staged files:")
                    for f in staged_files:
                        print(f"  {f}")
        else:
            print("No files were added")
            
        return True
        
    except Exception as e:
        print(f"Error adding files: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False

def _expand_pattern(pattern: str, force: bool = False) -> List[Path]:
    """Expand file patterns with proper error handling"""
    try:
        paths = list(Path('.').glob(pattern))
        
        # If no matches and pattern doesn't contain wildcards, check if it's a literal file
        if not paths and '*' not in pattern and '?' not in pattern and '[' not in pattern:
            literal_path = Path(pattern)
            if literal_path.exists():
                paths = [literal_path]
        
        return paths
    except Exception:
        return []

def _add_file(repo: Repository, staging: StagingArea, file_path: Path, verbose: bool = False) -> bool:
    """Add a single file to the object database and staging area"""
    try:
        # Check file permissions
        if not os.access(file_path, os.R_OK):
            print(f"Warning: Cannot read file {file_path} (permission denied)")
            return False
        
        # Create blob from file
        blob = ObjectFactory.create_object('blob')
        blob.data = file_path.read_bytes()
        
        # Calculate hash and store object
        sha = blob.get_hash()
        obj_path = repo.gitdir / "objects" / sha[:2] / sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(blob.compress())
        
        # Add to staging area
        staging.add_file(str(file_path), sha)
        
        if verbose:
            print(f"Added {file_path} -> {sha}")
        
        return True
        
    except PermissionError:
        print(f"Error: Permission denied reading {file_path}")
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def _add_directory(repo: Repository, staging: StagingArea, directory: Path, args) -> tuple[int, int]:
    """Recursively add directory contents"""
    added_count = 0
    skipped_count = 0
    
    try:
        for file_path in directory.rglob('*'):
            if not file_path.is_file():
                continue
                
            if staging.is_ignored(file_path) and not args.force:
                if args.verbose:
                    print(f"Skipping ignored file: {file_path}")
                skipped_count += 1
                continue
            
            if _add_file(repo, staging, file_path, args.verbose):
                added_count += 1
            else:
                skipped_count += 1
                
    except Exception as e:
        print(f"Error processing directory {directory}: {e}")
    
    return added_count, skipped_count

def setup_parser(parser):
    """Setup argument parser for add command"""
    parser.add_argument(
        "files", 
        nargs="+", 
        help="Files, directories, or patterns to add"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Allow adding ignored files"
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true", 
        help="Show what would be added without actually adding"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--no-recurse",
        action="store_true",
        help="Don't recursively add directories"
    )
    parser.add_argument(
        "-p", "--patch",
        action="store_true",
        help="Interactively choose hunks of patch between the index and the work tree"
    )

def _interactive_patch_mode():
    """Implement interactive patch mode (placeholder for future implementation)"""
    print("Interactive patch mode not yet implemented")
    print("This would allow you to selectively stage changes within files")
    return False

# Enhanced version with patch mode (commented out for now since it's complex)
"""
def cmd_add_with_patch(args):
    if args.patch:
        return _interactive_patch_mode()
    return cmd_add(args)
"""

if __name__ == "__main__":
    # Test the add command directly
    parser = argparse.ArgumentParser(description="Test add command")
    setup_parser(parser)
    test_args = parser.parse_args([".", "--verbose"])
    cmd_add(test_args)