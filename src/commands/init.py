import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from ..repository import Repository

class RepositoryTemplate:
    """Handles repository templates and initial configuration"""
    
    BUILTIN_TEMPLATES = {
        "default": {
            "description": "Default template with basic structure",
            "files": {
                "README.md": "# Project Title\n\nProject description...",
                ".gitignore": "# Default gitignore\n__pycache__/\n*.pyc\n",
            }
        },
        "python": {
            "description": "Python project template",
            "files": {
                "README.md": "# Python Project\n\nA Python project.",
                ".gitignore": """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
""",
                "requirements.txt": "# Project dependencies\n",
                "setup.py": "# Package setup file\n"
            }
        },
        "empty": {
            "description": "Completely empty repository",
            "files": {}
        }
    }
    
    @classmethod
    def apply_template(cls, repo_path: Path, template_name: str, verbose: bool = False):
        """Apply a template to the new repository"""
        template = cls.BUILTIN_TEMPLATES.get(template_name, cls.BUILTIN_TEMPLATES["default"])
        
        for filename, content in template["files"].items():
            file_path = repo_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            if verbose:
                print(f"  Created {filename}")

class SharedRepositoryManager:
    """Manages shared repository configuration"""
    
    @staticmethod
    def configure_shared_repository(repo: Repository, args):
        """Configure repository for shared access"""
        if not args.shared:
            return
        
        # Set up group permissions and configuration
        config_file = repo.gitdir / "config"
        
        # Read existing config or create new
        config_content = []
        if config_file.exists():
            config_content = config_file.read_text().splitlines()
        
        # Add or update shared configuration
        core_section = False
        updated = False
        
        new_config = []
        for line in config_content:
            if line.strip() == '[core]':
                core_section = True
                new_config.append(line)
            elif core_section and line.strip().startswith('sharedRepository'):
                # Update existing setting
                new_config.append(f'\tsharedRepository = {args.shared}')
                updated = True
            elif core_section and line.strip().startswith('[') and line.strip() != '[core]':
                # Insert before next section
                if not updated:
                    new_config.append(f'\tsharedRepository = {args.shared}')
                    updated = True
                new_config.append(line)
            else:
                new_config.append(line)
        
        # Add if not found
        if not updated:
            if '[core]' not in new_config:
                new_config.append('[core]')
            new_config.append(f'\tsharedRepository = {args.shared}')
        
        config_file.write_text('\n'.join(new_config))
        
        # Set directory permissions (Unix-like systems)
        if hasattr(os, 'chmod'):
            try:
                # Set group writable and setgid bit
                os.chmod(repo.gitdir, 0o2775)
                for root, dirs, files in os.walk(repo.gitdir):
                    for d in dirs:
                        os.chmod(Path(root) / d, 0o2775)
                    for f in files:
                        os.chmod(Path(root) / f, 0o664)
            except OSError:
                pass  # Permission changes might fail on some systems

class BranchConfigurator:
    """Handles initial branch configuration"""
    
    @staticmethod
    def configure_initial_branch(repo: Repository, branch_name: str, verbose: bool = False):
        """Configure the initial branch"""
        # Update HEAD to point to the specified branch
        head_file = repo.gitdir / "HEAD"
        head_file.write_text(f"ref: refs/heads/{branch_name}\n")
        
        # Create the branch reference file
        branch_ref = repo.gitdir / "refs" / "heads" / branch_name
        branch_ref.parent.mkdir(parents=True, exist_ok=True)
        
        if verbose:
            print(f"  Initialized default branch '{branch_name}'")

class RepositoryValidator:
    """Validates repository creation parameters"""
    
    @staticmethod
    def validate_path(path: Path, bare: bool) -> tuple[bool, str]:
        """Validate the repository path"""
        if path.exists():
            if path.is_file():
                return False, f"Path {path} is a file, not a directory"
            if any(path.iterdir()) and not bare:
                return False, f"Directory {path} is not empty"
        
        # Check if we can create the directory
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".mygit_test"
            test_file.touch()
            test_file.unlink()
            return True, ""
        except (OSError, PermissionError) as e:
            return False, f"Cannot create repository: {e}"

def cmd_init(args):
    """Initialize a new repository with advanced options"""
    repo_path = Path(args.path).resolve()
    
    # Handle bare repositories
    if args.bare:
        repo = Repository(repo_path, bare=True)
        repo_path = repo_path  # Use the path directly for bare repo
    else:
        repo = Repository(repo_path)
    
    # Validate path
    is_valid, error_msg = RepositoryValidator.validate_path(repo_path, args.bare)
    if not is_valid:
        print(f"Error: {error_msg}")
        return False
    
    if repo.exists():
        print(f"Repository already exists at {repo.gitdir}")
        return False
    
    try:
        # Create repository structure
        if repo.create():
            success = _initialize_repository(repo, args)
            if success:
                _print_success_message(repo, args)
            return success
        else:
            print("Failed to initialize repository structure")
            return False
            
    except Exception as e:
        print(f"Error initializing repository: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False

def _initialize_repository(repo: Repository, args) -> bool:
    """Perform the actual repository initialization"""
    try:
        # Apply template if specified
        if args.template and args.template != "default":
            if args.verbose:
                print(f"Applying template: {args.template}")
            RepositoryTemplate.apply_template(
                repo.worktree if not args.bare else repo.gitdir,
                args.template,
                args.verbose
            )
        
        # Configure shared repository settings
        if args.shared:
            if args.verbose:
                print("Configuring shared repository settings")
            SharedRepositoryManager.configure_shared_repository(repo, args)
        
        # Configure initial branch
        initial_branch = args.initial_branch
        if args.verbose:
            print(f"Setting initial branch to: {initial_branch}")
        BranchConfigurator.configure_initial_branch(repo, initial_branch, args.verbose)
        
        # Create custom directory structure
        if args.objects_dir or args.refs_dir:
            _create_custom_structure(repo, args)
        
        # Create initial commit if requested
        if args.initial_commit:
            if args.verbose:
                print("Creating initial commit")
            _create_initial_commit(repo, args)
        
        return True
        
    except Exception as e:
        print(f"Error during repository initialization: {e}")
        return False

def _create_custom_structure(repo: Repository, args):
    """Create custom directory structure"""
    if args.objects_dir:
        custom_objects = repo.gitdir / args.objects_dir
        custom_objects.mkdir(parents=True, exist_ok=True)
        
        # Update config to use custom objects directory
        _update_config(repo, "core.objectsdir", args.objects_dir)
    
    if args.refs_dir:
        custom_refs = repo.gitdir / args.refs_dir
        custom_refs.mkdir(parents=True, exist_ok=True)
        
        # Update config to use custom refs directory
        _update_config(repo, "core.refsdir", args.refs_dir)

def _update_config(repo: Repository, key: str, value: str):
    """Update repository configuration"""
    config_file = repo.gitdir / "config"
    
    if config_file.exists():
        content = config_file.read_text()
    else:
        content = ""
    
    # Simple config update - could be enhanced with proper config parser
    section, setting = key.split('.', 1)
    
    if f"[{section}]" not in content:
        content += f"\n[{section}]\n\t{setting} = {value}\n"
    else:
        # Update existing setting (simplified)
        lines = content.splitlines()
        new_lines = []
        in_section = False
        
        for line in lines:
            if line.strip() == f"[{section}]":
                in_section = True
                new_lines.append(line)
            elif in_section and line.strip().startswith('['):
                in_section = False
                new_lines.append(f"\t{setting} = {value}")
                new_lines.append(line)
            elif in_section and line.strip().startswith(setting):
                new_lines.append(f"\t{setting} = {value}")
            else:
                new_lines.append(line)
        
        if in_section and not any(line.strip().startswith(setting) for line in new_lines):
            new_lines.append(f"\t{setting} = {value}")
        
        content = '\n'.join(new_lines)
    
    config_file.write_text(content)

def _create_initial_commit(repo: Repository, args):
    """Create an initial commit if there are files to commit"""
    try:
        from ..objects.factory import ObjectFactory
        from ..objects.commit import Commit
        from ..objects.tree import Tree
        import time
        
        # Check if there are any files to commit
        worktree = repo.worktree if not args.bare else repo.gitdir
        files = list(worktree.rglob('*'))
        files = [f for f in files if f.is_file() and f.name != '.mygit' and not f.name.startswith('.')]
        
        if not files:
            if args.verbose:
                print("  No files found for initial commit")
            return
        
        # Create a tree from the files (simplified)
        tree = Tree()
        for file_path in files:
            if file_path.is_file() and file_path.name != '.mygit':
                # Create blob (simplified - would need proper implementation)
                blob = ObjectFactory.create_object('blob')
                blob.data = file_path.read_bytes()
                blob_sha = blob.get_hash()
                
                # Store blob
                obj_path = repo.gitdir / "objects" / blob_sha[:2] / blob_sha[2:]
                obj_path.parent.mkdir(parents=True, exist_ok=True)
                obj_path.write_bytes(blob.compress())
                
                tree.add_entry('100644', file_path.name, blob_sha)
        
        # Store tree
        tree_sha = tree.get_hash()
        obj_path = repo.gitdir / "objects" / tree_sha[:2] / tree_sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(tree.compress())
        
        # Create commit
        commit = Commit()
        commit.tree = tree_sha
        commit.author = _get_author()
        commit.committer = _get_author()
        commit.message = args.initial_commit_message
        commit.timestamp = int(time.time())
        
        commit_sha = commit.get_hash()
        obj_path = repo.gitdir / "objects" / commit_sha[:2] / commit_sha[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(commit.compress())
        
        # Update branch reference
        branch_ref = repo.gitdir / "refs" / "heads" / args.initial_branch
        branch_ref.write_text(commit_sha + '\n')
        
        if args.verbose:
            print(f"  Created initial commit: {commit_sha[:8]}")
            
    except Exception as e:
        if args.verbose:
            print(f"  Could not create initial commit: {e}")

def _get_author() -> str:
    """Get author information"""
    name = os.getenv('GIT_AUTHOR_NAME', 'Unknown Author')
    email = os.getenv('GIT_AUTHOR_EMAIL', 'unknown@example.com')
    return f"{name} <{email}>"

def _print_success_message(repo: Repository, args):
    """Print appropriate success message"""
    if args.bare:
        print(f"Initialized empty shared MyGit repository in {repo.gitdir}")
    elif args.shared:
        print(f"Initialized shared MyGit repository in {repo.gitdir}")
    else:
        print(f"Initialized empty MyGit repository in {repo.gitdir}")
    
    if args.verbose:
        print(f"  Template: {args.template}")
        print(f"  Initial branch: {args.initial_branch}")
        if args.shared:
            print(f"  Shared mode: {args.shared}")
        if args.bare:
            print("  Repository type: bare")

def setup_parser(parser):
    """Setup argument parser for init command"""
    parser.add_argument(
        "path", 
        nargs="?", 
        default=".", 
        help="Where to create the repository"
    )
    
    # Template options
    parser.add_argument(
        "--template",
        choices=["default", "python", "empty"],
        default="default",
        help="Use specified template for initial repository structure"
    )
    
    # Branch configuration
    parser.add_argument(
        "--initial-branch",
        default="main",
        help="Use specified name for the initial branch (default: main)"
    )
    
    # Shared repository options
    parser.add_argument(
        "--shared",
        type=str,
        choices=["group", "all", "world", "umask", "0xxx"],
        metavar="PERM",
        help="Create a shared repository for multiple users"
    )
    
    # Repository type
    parser.add_argument(
        "--bare",
        action="store_true",
        help="Create a bare repository (no working directory)"
    )
    
    # Initial commit
    parser.add_argument(
        "--initial-commit",
        action="store_true",
        help="Create an initial commit with existing files"
    )
    parser.add_argument(
        "--initial-commit-message",
        default="Initial commit",
        help="Message for the initial commit"
    )
    
    # Custom structure
    parser.add_argument(
        "--objects-dir",
        help="Use custom directory for objects (instead of objects/)"
    )
    parser.add_argument(
        "--refs-dir", 
        help="Use custom directory for refs (instead of refs/)"
    )
    
    # Verbose output
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output during initialization"
    )

def _display_usage_examples():
    """Display usage examples"""
    examples = """
Examples:
  # Basic repository
  mygit init
  
  # Repository with specific path
  mygit init /path/to/myproject
  
  # Python project template
  mygit init --template python
  
  # Shared repository for team
  mygit init --shared=group
  
  # Bare repository (for servers)
  mygit init --bare
  
  # Custom initial branch
  mygit init --initial-branch develop
  
  # With initial commit
  mygit init --initial-commit -m "Project setup"
  
  # Verbose output
  mygit init --verbose
"""
    print(examples)

if __name__ == "__main__":
    # Test the init command directly
    parser = argparse.ArgumentParser(
        description="Initialize a new MyGit repository",
        epilog="Use -h for more options"
    )
    setup_parser(parser)
    
    if len(sys.argv) == 1:
        _display_usage_examples()
        sys.exit(0)
    
    try:
        args = parser.parse_args()
        success = cmd_init(args)
        sys.exit(0 if success else 1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)