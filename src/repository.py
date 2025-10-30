import os
import configparser
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum


class RepositoryFormat(Enum):
    """Repository format versions"""
    V0 = "0"  # Initial format
    V1 = "1"  # With config support

class ObjectFormat(Enum):
    """Git object formats"""
    SHA1 = "sha1"
    SHA256 = "sha256"

class RepositoryType(Enum):
    """Repository types"""
    REGULAR = "regular"
    BARE = "bare"
    SHARED = "shared"
    WORKTREE = "worktree"

class RepositoryError(Exception):
    """Repository-specific exceptions"""
    pass

class ConfigManager:
    """Manages repository configuration"""
    
    def __init__(self, repo_path: Path):
        self.config_path = repo_path / "config"
        self._config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                self._config.read(self.config_path)
            except configparser.Error as e:
                raise RepositoryError(f"Failed to parse config file: {e}")
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                self._config.write(f)
        except IOError as e:
            raise RepositoryError(f"Failed to save config: {e}")
    
    def get(self, section: str, key: str, default: str = None) -> Optional[str]:
        """Get configuration value"""
        try:
            return self._config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def set(self, section: str, key: str, value: str):
        """Set configuration value"""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, value)
        self.save()
    
    def get_boolean(self, section: str, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        try:
            return self._config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        try:
            return self._config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def sections(self) -> List[str]:
        """Get all configuration sections"""
        return self._config.sections()
    
    def items(self, section: str) -> Dict[str, str]:
        """Get all items in a section"""
        try:
            return dict(self._config.items(section))
        except configparser.NoSectionError:
            return {}

class RepositoryValidator:
    """Validates repository integrity and structure"""
    
    def __init__(self, repo: 'Repository'):
        self.repo = repo
    
    def validate_structure(self) -> bool:
        """Validate repository directory structure"""
        required_dirs = [
            self.repo.gitdir / "objects",
            self.repo.gitdir / "refs" / "heads",
            self.repo.gitdir / "refs" / "tags",
        ]
        
        required_files = [
            self.repo.gitdir / "HEAD",
            self.repo.gitdir / "config",
        ]
        
        # Check directories
        for dir_path in required_dirs:
            if not dir_path.exists() or not dir_path.is_dir():
                return False
        
        # Check files
        for file_path in required_files:
            if not file_path.exists() or not file_path.is_file():
                return False
        
        return True
    
    def validate_config(self) -> bool:
        """Validate repository configuration"""
        try:
            config = self.repo.config
            
            # Check core section
            if not config.get('core', 'repositoryformatversion'):
                return False
            
            # Check filemode if present
            filemode = config.get('core', 'filemode')
            if filemode and filemode not in ['true', 'false']:
                return False
            
            return True
        except Exception:
            return False
    
    def validate_objects(self) -> Dict[str, Any]:
        """Validate object database integrity"""
        objects_dir = self.repo.gitdir / "objects"
        stats = {
            'total_objects': 0,
            'valid_objects': 0,
            'corrupt_objects': 0,
            'object_types': {},
        }
        
        if not objects_dir.exists():
            return stats
        
        # Walk through object database
        for entry in objects_dir.iterdir():
            if entry.is_dir() and len(entry.name) == 2:
                for obj_file in entry.iterdir():
                    if obj_file.is_file() and len(obj_file.name) == 38:
                        stats['total_objects'] += 1
                        
                        # Verify object can be read and decompressed
                        try:
                            from objects.factory import ObjectFactory
                            obj_sha = entry.name + obj_file.name
                            obj = ObjectFactory.read_object(self.repo, obj_sha)
                            
                            # Verify hash matches filename
                            if obj.get_hash() == obj_sha:
                                stats['valid_objects'] += 1
                                
                                # Count by type
                                obj_type = type(obj).__name__.lower()
                                stats['object_types'][obj_type] = stats['object_types'].get(obj_type, 0) + 1
                            else:
                                stats['corrupt_objects'] += 1
                                
                        except Exception:
                            stats['corrupt_objects'] += 1
        
        return stats
    
    def validate_refs(self) -> Dict[str, Any]:
        """Validate reference integrity"""
        refs_dir = self.repo.gitdir / "refs"
        stats = {
            'branches': 0,
            'tags': 0,
            'invalid_refs': 0,
        }
        
        if not refs_dir.exists():
            return stats
        
        # Check branches
        heads_dir = refs_dir / "heads"
        if heads_dir.exists():
            for branch_file in heads_dir.iterdir():
                if branch_file.is_file():
                    stats['branches'] += 1
                    if not self._validate_ref_content(branch_file):
                        stats['invalid_refs'] += 1
        
        # Check tags
        tags_dir = refs_dir / "tags"
        if tags_dir.exists():
            for tag_file in tags_dir.iterdir():
                if tag_file.is_file():
                    stats['tags'] += 1
                    if not self._validate_ref_content(tag_file):
                        stats['invalid_refs'] += 1
        
        return stats
    
    def _validate_ref_content(self, ref_file: Path) -> bool:
        """Validate reference file content"""
        try:
            content = ref_file.read_text().strip()
            # Should be a 40-character SHA-1 or start with "ref: "
            return (len(content) == 40 and all(c in '0123456789abcdef' for c in content.lower()) or
                    content.startswith('ref: '))
        except Exception:
            return False
    
    def comprehensive_validate(self) -> Dict[str, Any]:
        """Perform comprehensive repository validation"""
        results = {
            'structure_valid': self.validate_structure(),
            'config_valid': self.validate_config(),
            'object_stats': self.validate_objects(),
            'ref_stats': self.validate_refs(),
            'overall_valid': False,
        }
        
        results['overall_valid'] = (
            results['structure_valid'] and 
            results['config_valid'] and
            results['object_stats']['corrupt_objects'] == 0 and
            results['ref_stats']['invalid_refs'] == 0
        )
        
        return results

class Repository:
    """Represents a Git repository with enhanced functionality"""
    
    def __init__(self, path: str = ".", bare: bool = False, create: bool = False):
        self.worktree = Path(path).resolve()
        
        if bare:
            self.gitdir = self.worktree
            self.worktree = None
        else:
            self.gitdir = self.worktree / ".mygit"
        
        self.bare = bare
        self.config = ConfigManager(self.gitdir)
        self.validator = RepositoryValidator(self)
        
        # Set default configuration if creating new repository
        if create and not self.exists():
            self._setup_default_config()
    
    def create(self, bare: bool = False, shared: bool = False, 
               object_format: ObjectFormat = ObjectFormat.SHA1) -> bool:
        """Initialize a new repository with enhanced options"""
        try:
            # Create directory structure
            dirs = [
                self.gitdir / "objects",
                self.gitdir / "refs" / "heads",
                self.gitdir / "refs" / "tags",
                self.gitdir / "info",
                self.gitdir / "hooks",
            ]
            
            for dir_path in dirs:
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create initial files
            (self.gitdir / "HEAD").write_text("ref: refs/heads/main\n")
            (self.gitdir / "description").write_text("Unnamed repository; edit this file to name it.\n")
            
            # Create info files
            (self.gitdir / "info" / "exclude").write_text("# Add file patterns to ignore\n")
            
            # Create sample hooks
            self._create_sample_hooks()
            
            # Setup configuration
            self._setup_default_config()
            
            # Set repository type and format
            self.config.set('core', 'repositoryformatversion', RepositoryFormat.V1.value)
            self.config.set('core', 'filemode', 'true')
            self.config.set('core', 'bare', str(bare).lower())
            self.config.set('core', 'sharedrepository', str(shared).lower())
            self.config.set('extensions', 'objectformat', object_format.value)
            
            # Set permissions for shared repositories
            if shared:
                self._setup_shared_permissions()
            
            return True
            
        except Exception as e:
            raise RepositoryError(f"Error creating repository: {e}")
    
    def _setup_default_config(self):
        """Setup default repository configuration"""
        # Core configuration
        self.config.set('core', 'repositoryformatversion', RepositoryFormat.V1.value)
        self.config.set('core', 'filemode', 'true')
        self.config.set('core', 'bare', 'false')
        self.config.set('core', 'logallrefupdates', 'true')
        self.config.set('core', 'ignorecase', 'true')
        
        # User configuration (if available from environment)
        user_name = os.getenv('GIT_AUTHOR_NAME') or os.getenv('USER') or 'Unknown'
        user_email = os.getenv('GIT_AUTHOR_EMAIL') or f"{user_name}@localhost"
        
        self.config.set('user', 'name', user_name)
        self.config.set('user', 'email', user_email)
        
        # MyGit-specific configuration
        self.config.set('mygit', 'version', '1.0')
        self.config.set('mygit', 'created', str(os.path.getctime(self.gitdir)))
    
    def _create_sample_hooks(self):
        """Create sample hook files"""
        hooks_dir = self.gitdir / "hooks"
        sample_hooks = {
            'pre-commit.sample': '#!/bin/sh\necho "Pre-commit hook: add your checks here"',
            'post-commit.sample': '#!/bin/sh\necho "Post-commit hook: add your notifications here"',
            'pre-push.sample': '#!/bin/sh\necho "Pre-push hook: add your validations here"',
        }
        
        for hook_name, content in sample_hooks.items():
            hook_path = hooks_dir / hook_name
            hook_path.write_text(content)
            if not os.name == 'nt':  # Make executable on Unix-like systems
                hook_path.chmod(0o755)
    
    def _setup_shared_permissions(self):
        """Setup permissions for shared repositories"""
        if os.name != 'nt':  # Unix-like systems
            try:
                # Set setgid bit for directories
                for root, dirs, files in os.walk(self.gitdir):
                    for d in dirs:
                        os.chmod(Path(root) / d, 0o2775)
                    for f in files:
                        os.chmod(Path(root) / f, 0o664)
            except OSError:
                pass  # Ignore permission errors
    
    def exists(self) -> bool:
        """Check if repository exists and is valid"""
        if not self.gitdir.exists():
            return False
        
        # Basic structure check
        required = [
            self.gitdir / "objects",
            self.gitdir / "refs",
            self.gitdir / "HEAD",
        ]
        
        return all(path.exists() for path in required)
    
    def get_type(self) -> RepositoryType:
        """Get repository type"""
        if self.bare:
            return RepositoryType.BARE
        elif self.config.get_boolean('core', 'sharedrepository'):
            return RepositoryType.SHARED
        else:
            return RepositoryType.REGULAR
    
    def get_object_format(self) -> ObjectFormat:
        """Get object format"""
        format_str = self.config.get('extensions', 'objectformat', ObjectFormat.SHA1.value)
        return ObjectFormat(format_str)
    
    def get_branches(self) -> Dict[str, str]:
        """Get all branches and their HEAD commits"""
        branches = {}
        heads_dir = self.gitdir / "refs" / "heads"
        
        if heads_dir.exists():
            for branch_file in heads_dir.iterdir():
                if branch_file.is_file():
                    try:
                        commit_sha = branch_file.read_text().strip()
                        branches[branch_file.name] = commit_sha
                    except Exception:
                        continue
        
        return branches
    
    def get_current_branch(self) -> Optional[str]:
        """Get current branch name"""
        try:
            head_content = (self.gitdir / "HEAD").read_text().strip()
            if head_content.startswith('ref: refs/heads/'):
                return head_content[16:]  # Remove 'ref: refs/heads/'
            return None
        except Exception:
            return None
    
    def set_current_branch(self, branch_name: str):
        """Set current branch"""
        head_file = self.gitdir / "HEAD"
        head_file.write_text(f"ref: refs/heads/{branch_name}\n")
    
    def get_HEAD(self) -> str:
        """Get current HEAD commit SHA"""
        try:
            head_content = (self.gitdir / "HEAD").read_text().strip()
            if head_content.startswith('ref: '):
                # Follow symbolic reference
                ref_path = self.gitdir / head_content[5:]
                if ref_path.exists():
                    return ref_path.read_text().strip()
                else:
                    raise RepositoryError(f"Reference not found: {head_content[5:]}")
            else:
                # Detached HEAD
                return head_content
        except Exception as e:
            raise RepositoryError(f"Failed to get HEAD: {e}")
    
    def validate(self) -> Dict[str, Any]:
        """Validate repository integrity"""
        return self.validator.comprehensive_validate()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics"""
        validation = self.validate()
        branches = self.get_branches()
        
        return {
            'type': self.get_type().value,
            'object_format': self.get_object_format().value,
            'current_branch': self.get_current_branch(),
            'branch_count': len(branches),
            'branches': list(branches.keys()),
            'validation': validation,
            'config_sections': self.config.sections(),
            'bare': self.bare,
            'worktree': str(self.worktree) if self.worktree else None,
            'gitdir': str(self.gitdir),
        }
    
    def is_detached_head(self) -> bool:
        """Check if HEAD is detached"""
        try:
            head_content = (self.gitdir / "HEAD").read_text().strip()
            return not head_content.startswith('ref: ')
        except Exception:
            return False
    
    def get_remote_url(self, remote_name: str = "origin") -> Optional[str]:
        """Get remote URL"""
        return self.config.get(f'remote "{remote_name}"', 'url')
    
    def set_remote_url(self, remote_name: str, url: str):
        """Set remote URL"""
        self.config.set(f'remote "{remote_name}"', 'url', url)
    
    def __repr__(self) -> str:
        """String representation"""
        repo_type = self.get_type().value
        branch = self.get_current_branch() or "detached"
        return f"Repository({self.worktree}, type={repo_type}, branch={branch})"
    
    def __str__(self) -> str:
        """Human-readable representation"""
        stats = self.get_statistics()
        return (f"Repository at {self.worktree}\n"
                f"Type: {stats['type']} | Branch: {stats['current_branch']} | "
                f"Branches: {stats['branch_count']}")

def find_repository(start_path: Path = Path(".")) -> Optional[Repository]:
    """Find repository starting from given path"""
    current = start_path.resolve()
    
    while current != current.parent:
        # Check for both .mygit and .git directories
        for repo_dir in ['.mygit', '.git']:
            repo_path = current / repo_dir
            if repo_path.exists() and repo_path.is_dir():
                # Check if it's a bare repository
                config_path = repo_path / "config"
                if config_path.exists():
                    try:
                        repo = Repository(str(current))
                        if repo.exists():
                            return repo
                    except RepositoryError:
                        continue
        
        current = current.parent
    
    return None

def create_bare_repository(path: str) -> Repository:
    """Create a bare repository"""
    repo_path = Path(path)
    repo_path.mkdir(parents=True, exist_ok=True)
    
    repo = Repository(path, bare=True, create=True)
    repo.create(bare=True)
    
    return repo

def create_shared_repository(path: str, group: str = None) -> Repository:
    """Create a shared repository"""
    repo = Repository(path, create=True)
    repo.create(shared=True)
    
    return repo