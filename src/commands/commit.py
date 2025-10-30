import argparse
import time
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..repository import Repository
from ..objects.factory import ObjectFactory
from ..objects.commit import Commit
from ..objects.tree import Tree, TreeEntry
from ..objects.blob import Blob

class CommitConfig:
    """Manages commit configuration and author information"""
    
    def __init__(self, repo: Repository):
        self.repo = repo
        self.config_file = repo.gitdir / "config"
    
    def get_author(self) -> str:
        """Get author information from config or environment"""
        # Try to read from repo config
        author = self._read_config_value("user.name", "user.email")
        if author:
            return author
        
        # Fall back to environment variables
        name = os.getenv('GIT_AUTHOR_NAME') or os.getenv('GIT_COMMITTER_NAME')
        email = os.getenv('GIT_AUTHOR_EMAIL') or os.getenv('GIT_COMMITTER_EMAIL')
        
        if name and email:
            return f"{name} <{email}>"
        
        # Final fallback
        return "Unknown Author <unknown@example.com>"
    
    def _read_config_value(self, name_key: str, email_key: str) -> Optional[str]:
        """Read user name and email from config file"""
        if not self.config_file.exists():
            return None
        
        try:
            config_data = {}
            with open(self.config_file, 'r') as f:
                current_section = None
                for line in f:
                    line = line.strip()
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                    elif '=' in line and current_section == 'user':
                        key, value = line.split('=', 1)
                        config_data[key.strip()] = value.strip()
            
            name = config_data.get(name_key.replace('user.', ''))
            email = config_data.get(email_key.replace('user.', ''))
            
            if name and email:
                return f"{name} <{email}>"
        except Exception:
            pass
        
        return None

class StagingManager:
    """Manages the staging area and tracks files to commit"""
    
    def __init__(self, repo: Repository):
        self.repo = repo
        self.index_file = repo.gitdir / "index"
        self.staged_files: Dict[str, str] = {}  # path -> sha
    
    def load_staged_files(self) -> bool:
        """Load staged files from index"""
        if not self.index_file.exists():
            return False
        
        try:
            with open(self.index_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '|' in line:
                        path, sha = line.split('|', 1)
                        self.staged_files[path] = sha
            return True
        except Exception:
            return False
    
    def get_staged_files(self) -> Dict[str, str]:
        """Get all staged files"""
        return self.staged_files.copy()
    
    def clear_staging_area(self):
        """Clear the staging area after commit"""
        try:
            if self.index_file.exists():
                self.index_file.unlink()
            self.staged_files.clear()
        except Exception:
            pass

class CommitMessageHandler:
    """Handles commit message creation and validation"""
    
    @staticmethod
    def get_commit_message(args) -> str:
        """Get commit message from various sources"""
        if args.message:
            return args.message
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"Error reading message file: {e}")
                sys.exit(1)
        elif args.template:
            return CommitMessageHandler._get_template_message(args.template)
        else:
            # Interactive mode
            return CommitMessageHandler._get_interactive_message()
    
    @staticmethod
    def _get_template_message(template: str) -> str:
        """Get message from template"""
        # Simple template support - can be extended
        templates = {
            "default": "Update files\n\n# Enter commit details above this line",
            "feature": "feat: new feature\n\n# Describe the feature\n# Benefits: \n# Testing: ",
            "fix": "fix: bug fix\n\n# Describe the fix\n# Issue: \n# Testing: ",
        }
        return templates.get(template, templates["default"])
    
    @staticmethod
    def _get_interactive_message() -> str:
        """Get message interactively from editor"""
        try:
            import tempfile
            import subprocess
            
            # Create temp file with default message
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False) as f:
                f.write("# Please enter the commit message for your changes.\n")
                f.write("# Lines starting with '#' will be ignored.\n")
                f.write("# An empty message aborts the commit.\n")
                f.write("\n")
                temp_path = f.name
            
            # Open editor
            editor = os.getenv('EDITOR', 'vim')
            subprocess.call([editor, temp_path])
            
            # Read result
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Clean up
            os.unlink(temp_path)
            
            # Remove comment lines
            lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
            message = '\n'.join(lines).strip()
            
            if not message:
                print("Aborting commit due to empty commit message.")
                sys.exit(1)
                
            return message
        except Exception as e:
            print(f"Error with interactive editor: {e}")
            print("Please use -m or --file to provide commit message.")
            sys.exit(1)

def cmd_commit(args):
    """Record changes to the repository"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        # Initialize managers
        config = CommitConfig(repo)
        staging = StagingManager(repo)
        
        # Load staged files
        if not staging.load_staged_files():
            if not args.allow_empty:
                print("No changes staged for commit.")
                print("Use 'mygit add' to stage files, or use --allow-empty to create empty commit.")
                return False
        
        # Handle amend mode
        if args.amend:
            return _amend_commit(repo, config, staging, args)
        
        # Get commit message
        message_handler = CommitMessageHandler()
        commit_message = message_handler.get_commit_message(args)
        
        # Validate message
        if not commit_message.strip():
            print("Aborting commit due to empty commit message.")
            return False
        
        # Create commit
        success = _create_commit(repo, config, staging, commit_message, args)
        
        if success and not args.no_verify:
            _run_commit_hooks(repo, 'post-commit')
        
        return success
        
    except Exception as e:
        print(f"Error creating commit: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False

def _create_commit(repo: Repository, config: CommitConfig, staging: StagingManager, 
                  message: str, args) -> bool:
    """Create a new commit"""
    # Create tree from staged files
    if staging.get_staged_files():
        tree_sha = _create_tree_from_staged_files(repo, staging.get_staged_files())
    else:
        # Empty commit - reuse previous tree or create empty tree
        tree_sha = _get_previous_tree(repo) or _create_empty_tree(repo)
    
    # Create commit object
    commit = Commit()
    commit.tree = tree_sha
    commit.author = config.get_author()
    commit.committer = config.get_author()
    commit.message = message
    commit.timestamp = int(time.time())
    
    # Handle parent commit
    parent_sha = _get_parent_commit(repo)
    if parent_sha:
        commit.parents = [parent_sha]
    
    # Run pre-commit hooks
    if not args.no_verify and not _run_commit_hooks(repo, 'pre-commit'):
        print("Pre-commit hook failed, aborting commit.")
        return False
    
    # Store commit
    commit_sha = commit.get_hash()
    obj_path = repo.gitdir / "objects" / commit_sha[:2] / commit_sha[2:]
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.write_bytes(commit.compress())
    
    # Update HEAD
    _update_head(repo, commit_sha)
    
    # Clear staging area
    staging.clear_staging_area()
    
    # Output results
    _print_commit_summary(commit_sha, commit, staging.get_staged_files(), args)
    
    return True

def _amend_commit(repo: Repository, config: CommitConfig, staging: StagingManager, args) -> bool:
    """Amend the previous commit"""
    parent_sha = _get_parent_commit(repo)
    if not parent_sha:
        print("No previous commit to amend.")
        return False
    
    try:
        # Get previous commit
        old_commit = ObjectFactory.read_object(repo, parent_sha)
        if not isinstance(old_commit, Commit):
            print("Previous HEAD is not a commit.")
            return False
        
        # Get message for amend
        message_handler = CommitMessageHandler()
        new_message = message_handler.get_commit_message(args)
        if not new_message.strip():
            new_message = old_commit.message
        
        # Create new commit with previous commit's parent
        commit = Commit()
        commit.tree = _create_tree_from_staged_files(repo, staging.get_staged_files()) if staging.get_staged_files() else old_commit.tree
        commit.author = config.get_author()
        commit.committer = config.get_author()
        commit.message = new_message
        commit.timestamp = int(time.time())
        commit.parents = old_commit.parents  # Keep the same parent chain
        
        # Store commit
        commit_sha = commit.get_hash()
        obj_path = repo.gitdir / "objects" / commit_sha[:2] / commit_sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(commit.compress())
        
        # Update HEAD
        _update_head(repo, commit_sha)
        
        # Clear staging area
        staging.clear_staging_area()
        
        print(f"Amended commit {commit_sha}")
        if args.verbose:
            print(f"  {len(staging.get_staged_files())} files changed")
            print(f"  Message: {new_message.splitlines()[0]}")
        
        return True
        
    except Exception as e:
        print(f"Error amending commit: {e}")
        return False

def _create_tree_from_staged_files(repo: Repository, staged_files: Dict[str, str]) -> str:
    """Create a tree from staged files (much more efficient than scanning directory)"""
    tree = Tree()
    
    # Organize files by directory
    dir_structure: Dict[str, Tree] = {}
    
    for file_path, blob_sha in staged_files.items():
        path = Path(file_path)
        
        if len(path.parts) == 1:
            # File in root directory
            tree.add_entry('100644', path.name, blob_sha)
        else:
            # File in subdirectory
            dir_path = str(path.parent)
            if dir_path not in dir_structure:
                dir_structure[dir_path] = Tree()
            dir_structure[dir_path].add_entry('100644', path.name, blob_sha)
    
    # Create and store subdirectory trees
    for dir_path, dir_tree in dir_structure.items():
        tree_sha = dir_tree.get_hash()
        obj_path = repo.gitdir / "objects" / tree_sha[:2] / tree_sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(dir_tree.compress())
        
        # Add to parent tree
        tree.add_entry('40000', Path(dir_path).name, tree_sha)
    
    # Store main tree
    tree_sha = tree.get_hash()
    obj_path = repo.gitdir / "objects" / tree_sha[:2] / tree_sha[2:]
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.write_bytes(tree.compress())
    
    return tree_sha

def _get_parent_commit(repo: Repository) -> Optional[str]:
    """Get the current HEAD commit SHA"""
    head_path = repo.gitdir / "HEAD"
    if not head_path.exists():
        return None
    
    try:
        head_ref = head_path.read_text().strip()
        if head_ref.startswith('ref: '):
            ref_path = repo.gitdir / head_ref[5:]
            if ref_path.exists():
                return ref_path.read_text().strip()
        else:
            # Detached HEAD
            return head_ref
    except Exception:
        pass
    
    return None

def _get_previous_tree(repo: Repository) -> Optional[str]:
    """Get the tree SHA from the previous commit"""
    parent_sha = _get_parent_commit(repo)
    if not parent_sha:
        return None
    
    try:
        parent_commit = ObjectFactory.read_object(repo, parent_sha)
        if isinstance(parent_commit, Commit):
            return parent_commit.tree
    except Exception:
        pass
    
    return None

def _create_empty_tree(repo: Repository) -> str:
    """Create an empty tree object"""
    tree = Tree()
    tree_sha = tree.get_hash()
    obj_path = repo.gitdir / "objects" / tree_sha[:2] / tree_sha[2:]
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.write_bytes(tree.compress())
    return tree_sha

def _update_head(repo: Repository, commit_sha: str):
    """Update HEAD to point to the new commit"""
    head_path = repo.gitdir / "HEAD"
    
    if head_path.exists():
        head_ref = head_path.read_text().strip()
        if head_ref.startswith('ref: '):
            ref_path = repo.gitdir / head_ref[5:]
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(commit_sha + '\n')
            return
    
    # Default to master branch
    refs_head = repo.gitdir / "refs" / "heads" / "master"
    refs_head.parent.mkdir(parents=True, exist_ok=True)
    refs_head.write_text(commit_sha + '\n')
    head_path.write_text("ref: refs/heads/master\n")

def _run_commit_hooks(repo: Repository, hook_name: str) -> bool:
    """Run commit hooks if they exist"""
    hooks_dir = repo.gitdir / "hooks"
    hook_script = hooks_dir / hook_name
    
    if not hook_script.exists():
        return True
    
    try:
        import subprocess
        result = subprocess.run([str(hook_script)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{hook_name} hook failed:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return False
        return True
    except Exception as e:
        print(f"Error running {hook_name} hook: {e}")
        return False

def _print_commit_summary(commit_sha: str, commit: Commit, staged_files: Dict[str, str], args):
    """Print a summary of the commit"""
    short_sha = commit_sha[:7]
    first_line = commit.message.splitlines()[0] if commit.message else ""
    
    print(f"[{commit.get_current_branch() or 'detached HEAD'} {short_sha}] {first_line}")
    
    if args.verbose:
        print(f"  {len(staged_files)} file(s) changed")
        if staged_files:
            print("  Files committed:")
            for file_path in sorted(staged_files.keys()):
                print(f"    {file_path}")
    else:
        print(f"  {len(staged_files)} file(s) changed")

def setup_parser(parser):
    """Setup argument parser for commit command"""
    # Message options (mutually exclusive)
    message_group = parser.add_mutually_exclusive_group(required=True)
    message_group.add_argument(
        "-m", "--message",
        help="Commit message"
    )
    message_group.add_argument(
        "-F", "--file",
        help="Read commit message from file"
    )
    message_group.add_argument(
        "-t", "--template",
        help="Use template for commit message"
    )
    
    # Commit options
    parser.add_argument(
        "--amend",
        action="store_true",
        help="Amend the previous commit"
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true", 
        help="Allow empty commit (no changes)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Bypass commit hooks"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )

# Add this method to the Commit class or as a helper
def _get_current_branch(commit: Commit) -> Optional[str]:
    """Get the current branch name (simplified)"""
    # This would need to be implemented by reading HEAD
    return None

if __name__ == "__main__":
    # Test the commit command directly
    parser = argparse.ArgumentParser(description="Test commit command")
    setup_parser(parser)
    
    if len(sys.argv) == 1:
        print("Usage examples:")
        print("  mygit commit -m \"message\"          # Basic commit")
        print("  mygit commit --amend -m \"message\"  # Amend previous commit")
        print("  mygit commit --allow-empty         # Create empty commit")
        print("  mygit commit -v                    # Verbose output")
    else:
        test_args = parser.parse_args()
        cmd_commit(test_args)