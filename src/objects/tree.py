import os
import stat
import re
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional, Iterator, Set
from .base import GitObject, ObjectValidationError
from .blob import Blob
from .commit import Commit
import hashlib

class TreeEntry:
    """Represents a single entry in a tree object with enhanced functionality"""
    
    # Git mode constants
    MODE_DIRECTORY = '40000'
    MODE_REGULAR_FILE = '100644'
    MODE_EXECUTABLE_FILE = '100755'
    MODE_SYMLINK = '120000'
    MODE_GITLINK = '160000'  # Git submodule
    
    MODE_TO_TYPE = {
        MODE_DIRECTORY: 'tree',
        MODE_REGULAR_FILE: 'blob',
        MODE_EXECUTABLE_FILE: 'blob',
        MODE_SYMLINK: 'blob',  # Symlinks are stored as blobs
        MODE_GITLINK: 'commit'  # Submodules point to commits
    }
    
    def __init__(self, mode: str, name: str, sha: str, symlink_target: str = None):
        self.mode = mode
        self.name = name
        self.sha = sha
        self.symlink_target = symlink_target  # For symbolic links
        self._obj_type = self.MODE_TO_TYPE.get(mode, 'unknown')
    
    def serialize(self) -> bytes:
        """Serialize tree entry to bytes"""
        entry_data = f"{self.mode} {self.name}\0".encode()
        entry_data += bytes.fromhex(self.sha)
        return entry_data
    
    @classmethod
    def deserialize(cls, data: bytes) -> Tuple['TreeEntry', int]:
        """Deserialize tree entry from bytes, return (entry, bytes_consumed)"""
        if len(data) < 22:  # Minimum: "100644 name\0" + 20 byte SHA
            raise ObjectValidationError("Tree entry data too short")
        
        # Find space separator
        space_pos = data.find(b' ')
        if space_pos == -1:
            raise ObjectValidationError("Invalid tree entry format: missing space")
        
        # Find null terminator
        null_pos = data.find(b'\0', space_pos)
        if null_pos == -1:
            raise ObjectValidationError("Invalid tree entry format: missing null terminator")
        
        # Extract components
        mode = data[:space_pos].decode('utf-8', errors='replace')
        name = data[space_pos+1:null_pos].decode('utf-8', errors='replace')
        
        # Extract SHA (20 bytes after null terminator)
        sha_start = null_pos + 1
        sha_end = sha_start + 20
        if sha_end > len(data):
            raise ObjectValidationError("Invalid tree entry format: incomplete SHA")
        
        sha_bytes = data[sha_start:sha_end]
        sha = sha_bytes.hex()
        
        # Validate mode
        if mode not in cls.MODE_TO_TYPE:
            raise ObjectValidationError(f"Invalid tree entry mode: {mode}")
        
        # Validate name
        if not name or '/' in name or name in ('.', '..'):
            raise ObjectValidationError(f"Invalid tree entry name: {name}")
        
        entry = cls(mode, name, sha)
        return entry, sha_end
    
    def get_object_type(self) -> str:
        """Get the object type for this entry"""
        return self._obj_type
    
    def is_directory(self) -> bool:
        """Check if this entry represents a directory"""
        return self.mode == self.MODE_DIRECTORY
    
    def is_file(self) -> bool:
        """Check if this entry represents a regular file"""
        return self.mode in (self.MODE_REGULAR_FILE, self.MODE_EXECUTABLE_FILE)
    
    def is_executable(self) -> bool:
        """Check if this entry represents an executable file"""
        return self.mode == self.MODE_EXECUTABLE_FILE
    
    def is_symlink(self) -> bool:
        """Check if this entry represents a symbolic link"""
        return self.mode == self.MODE_SYMLINK
    
    def is_gitlink(self) -> bool:
        """Check if this entry represents a git submodule"""
        return self.mode == self.MODE_GITLINK
    
    def to_dict(self) -> Dict[str, str]:
        """Convert entry to dictionary representation"""
        return {
            'mode': self.mode,
            'name': self.name,
            'sha': self.sha,
            'type': self.get_object_type(),
            'is_directory': self.is_directory(),
            'is_executable': self.is_executable(),
            'is_symlink': self.is_symlink(),
            'is_gitlink': self.is_gitlink()
        }
    
    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if not isinstance(other, TreeEntry):
            return False
        return (self.mode == other.mode and 
                self.name == other.name and 
                self.sha == other.sha)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"TreeEntry({self.mode}, '{self.name}', {self.sha[:8]}...)"

class Tree(GitObject):
    """Represents directory structure with enhanced functionality"""
    
    def __init__(self):
        super().__init__()
        self.entries: List[TreeEntry] = []
        self._entry_map: Dict[str, TreeEntry] = {}  # Name -> Entry cache
    
    def serialize(self) -> bytes:
        """Format: tree {size}\0{entries}"""
        # Sort entries by name as required by Git format
        sorted_entries = sorted(self.entries, key=lambda x: x.name)
        entries_data = b''.join(entry.serialize() for entry in sorted_entries)
        header = f"tree {len(entries_data)}\0".encode()
        return header + entries_data
    
    def deserialize(self, data: bytes):
        """Parse tree data with validation"""
        if not data:
            self.entries = []
            self._entry_map = {}
            return
        
        null_pos = data.find(b'\0')
        if null_pos == -1:
            raise ObjectValidationError("Invalid tree format: missing null terminator")
        
        # Parse header
        header = data[:null_pos]
        try:
            obj_type, size_str = self.parse_header(header + b'\0')
            if obj_type != 'tree':
                raise ObjectValidationError(f"Expected tree type, got {obj_type}")
        except ValueError as e:
            raise ObjectValidationError(f"Invalid tree header: {e}")
        
        entries_data = data[null_pos + 1:]
        self.entries = []
        self._entry_map = {}
        
        # Validate total size
        if len(entries_data) != int(size_str):
            raise ObjectValidationError(
                f"Tree size mismatch: header claims {size_str}, actual {len(entries_data)}"
            )
        
        # Parse entries
        position = 0
        entry_names: Set[str] = set()
        
        while position < len(entries_data):
            try:
                entry, consumed = TreeEntry.deserialize(entries_data[position:])
                
                # Check for duplicate entries
                if entry.name in entry_names:
                    raise ObjectValidationError(f"Duplicate tree entry: {entry.name}")
                entry_names.add(entry.name)
                
                self.entries.append(entry)
                self._entry_map[entry.name] = entry
                position += consumed
                
            except ObjectValidationError as e:
                raise ObjectValidationError(f"Failed to parse tree entry at position {position}: {e}")
    
    def add_entry(self, mode: str, name: str, sha: str, symlink_target: str = None):
        """Add an entry to the tree with validation"""
        # Validate name
        if not name or '/' in name or name in ('.', '..'):
            raise ValueError(f"Invalid tree entry name: {name}")
        
        # Validate SHA format
        if not re.match(r'^[a-f0-9]{40}$', sha):
            raise ValueError(f"Invalid SHA format: {sha}")
        
        # Validate mode
        if mode not in TreeEntry.MODE_TO_TYPE:
            raise ValueError(f"Invalid tree entry mode: {mode}")
        
        # Check for duplicates
        if name in self._entry_map:
            raise ValueError(f"Entry already exists: {name}")
        
        entry = TreeEntry(mode, name, sha, symlink_target)
        self.entries.append(entry)
        self._entry_map[name] = entry
        
        # Invalidate cached data
        self._cached_hash = None
        self._cached_serialized = None
        self._size = None
    
    def add_file_entry(self, name: str, sha: str, executable: bool = False):
        """Add a file entry with appropriate mode"""
        mode = TreeEntry.MODE_EXECUTABLE_FILE if executable else TreeEntry.MODE_REGULAR_FILE
        self.add_entry(mode, name, sha)
    
    def add_directory_entry(self, name: str, tree_sha: str):
        """Add a directory entry"""
        self.add_entry(TreeEntry.MODE_DIRECTORY, name, tree_sha)
    
    def add_symlink_entry(self, name: str, target: str, sha: str):
        """Add a symbolic link entry"""
        self.add_entry(TreeEntry.MODE_SYMLINK, name, sha, target)
    
    def add_gitlink_entry(self, name: str, commit_sha: str):
        """Add a git submodule entry"""
        self.add_entry(TreeEntry.MODE_GITLINK, name, commit_sha)
    
    def remove_entry(self, name: str) -> bool:
        """Remove an entry by name"""
        if name not in self._entry_map:
            return False
        
        entry = self._entry_map[name]
        self.entries.remove(entry)
        del self._entry_map[name]
        
        # Invalidate cached data
        self._cached_hash = None
        self._cached_serialized = None
        self._size = None
        
        return True
    
    def find_entry(self, name: str) -> TreeEntry:
        """Find an entry by name"""
        if name not in self._entry_map:
            raise KeyError(f"Entry '{name}' not found")
        return self._entry_map[name]
    
    def get_entry(self, name: str) -> Optional[TreeEntry]:
        """Get an entry by name, returns None if not found"""
        return self._entry_map.get(name)
    
    def has_entry(self, name: str) -> bool:
        """Check if tree contains an entry with given name"""
        return name in self._entry_map
    
    def get_files(self) -> List[TreeEntry]:
        """Get all file entries"""
        return [entry for entry in self.entries if entry.is_file() or entry.is_symlink()]
    
    def get_directories(self) -> List[TreeEntry]:
        """Get all directory entries"""
        return [entry for entry in self.entries if entry.is_directory()]
    
    def get_submodules(self) -> List[TreeEntry]:
        """Get all git submodule entries"""
        return [entry for entry in self.entries if entry.is_gitlink()]
    
    def merge(self, other: 'Tree', strategy: str = 'ours') -> 'Tree':
        """Merge another tree into this one"""
        result = Tree()
        
        if strategy == 'ours':
            # Prefer entries from this tree
            all_entries = {entry.name: entry for entry in self.entries}
            all_entries.update({entry.name: entry for entry in other.entries})
        elif strategy == 'theirs':
            # Prefer entries from other tree
            all_entries = {entry.name: entry for entry in other.entries}
            all_entries.update({entry.name: entry for entry in self.entries})
        elif strategy == 'union':
            # Combine both, error on conflicts
            our_entries = {entry.name: entry for entry in self.entries}
            their_entries = {entry.name: entry for entry in other.entries}
            
            # Check for conflicts
            conflicts = set(our_entries.keys()) & set(their_entries.keys())
            conflicting_different = [name for name in conflicts 
                                   if our_entries[name].sha != their_entries[name].sha]
            
            if conflicting_different:
                raise ValueError(f"Merge conflict in entries: {conflicting_different}")
            
            all_entries = {**our_entries, **their_entries}
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
        
        result.entries = list(all_entries.values())
        result._entry_map = all_entries
        
        return result
    
    def diff(self, other: 'Tree') -> 'TreeDiff':
        """Compute difference between two trees"""
        return TreeDiff(self, other)
    
    def walk(self, repo) -> Iterator[Tuple[str, TreeEntry]]:
        """Recursively walk through tree and subtrees"""
        for entry in self.entries:
            yield ('', entry)
            
            if entry.is_directory():
                try:
                    # This would need access to repository object to load subtrees
                    # For now, just yield the directory entry
                    yield (entry.name, entry)
                except Exception:
                    pass  # Skip inaccessible subtrees
    
    def find_path(self, path: str) -> Optional[TreeEntry]:
        """Find an entry by path (supports nested paths)"""
        parts = path.split('/')
        current_tree = self
        
        for i, part in enumerate(parts):
            if not part:  # Skip empty parts from leading/trailing slashes
                continue
                
            entry = current_tree.get_entry(part)
            if entry is None:
                return None
            
            if i == len(parts) - 1:
                return entry  # Found the target
            
            if not entry.is_directory():
                return None  # Path continues but current entry is not a directory
            
            # In a full implementation, we'd load the subtree here
            # For now, we return None since we can't traverse without repo
            
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tree to dictionary representation"""
        return {
            'type': 'tree',
            'entry_count': len(self.entries),
            'entries': [entry.to_dict() for entry in sorted(self.entries, key=lambda x: x.name)],
            'files': len(self.get_files()),
            'directories': len(self.get_directories()),
            'submodules': len(self.get_submodules()),
        }
    
    def _validate_internal(self) -> bool:
        """Internal validation for tree-specific rules"""
        # Check for duplicate entries
        names = set()
        for entry in self.entries:
            if entry.name in names:
                return False
            names.add(entry.name)
        
        # Validate all entries
        for entry in self.entries:
            if not re.match(r'^[a-f0-9]{40}$', entry.sha):
                return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about the tree"""
        stats = super().get_statistics()
        
        files = self.get_files()
        directories = self.get_directories()
        submodules = self.get_submodules()
        
        stats.update({
            'total_entries': len(self.entries),
            'file_count': len(files),
            'directory_count': len(directories),
            'submodule_count': len(submodules),
            'executable_count': len([f for f in files if f.is_executable()]),
            'symlink_count': len([f for f in files if f.is_symlink()]),
            'entry_names': [entry.name for entry in sorted(self.entries, key=lambda x: x.name)],
        })
        
        return stats
    
    def __contains__(self, name: str) -> bool:
        """Check if tree contains an entry"""
        return name in self._entry_map
    
    def __len__(self) -> int:
        """Number of entries in tree"""
        return len(self.entries)
    
    def __iter__(self) -> Iterator[TreeEntry]:
        """Iterate over entries"""
        return iter(sorted(self.entries, key=lambda x: x.name))
    
    def __repr__(self) -> str:
        """String representation"""
        return f"Tree(entries={len(self.entries)}, hash={self.get_hash()[:8]})"


class TreeDiff:
    """Represents differences between two trees"""
    
    def __init__(self, tree_a: Tree, tree_b: Tree):
        self.tree_a = tree_a
        self.tree_b = tree_b
        self.added: List[TreeEntry] = []
        self.removed: List[TreeEntry] = []
        self.modified: List[Tuple[TreeEntry, TreeEntry]] = []
        self._compute_diff()
    
    def _compute_diff(self):
        """Compute differences between trees"""
        entries_a = {entry.name: entry for entry in self.tree_a.entries}
        entries_b = {entry.name: entry for entry in self.tree_b.entries}
        
        all_names = set(entries_a.keys()) | set(entries_b.keys())
        
        for name in sorted(all_names):
            entry_a = entries_a.get(name)
            entry_b = entries_b.get(name)
            
            if entry_a and not entry_b:
                self.removed.append(entry_a)
            elif entry_b and not entry_a:
                self.added.append(entry_b)
            elif entry_a and entry_b and entry_a.sha != entry_b.sha:
                self.modified.append((entry_a, entry_b))
    
    def is_empty(self) -> bool:
        """Check if there are any differences"""
        return not (self.added or self.removed or self.modified)
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary of changes"""
        return {
            'added': len(self.added),
            'removed': len(self.removed),
            'modified': len(self.modified),
            'total': len(self.added) + len(self.removed) + len(self.modified)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert diff to dictionary representation"""
        return {
            'summary': self.get_summary(),
            'added': [entry.to_dict() for entry in self.added],
            'removed': [entry.to_dict() for entry in self.removed],
            'modified': [
                {'from': entry_a.to_dict(), 'to': entry_b.to_dict()}
                for entry_a, entry_b in self.modified
            ]
        }
    
    def __bool__(self) -> bool:
        """Boolean representation (True if has changes)"""
        return not self.is_empty()
    
    def __repr__(self) -> str:
        """String representation"""
        summary = self.get_summary()
        return (f"TreeDiff(added={summary['added']}, "
                f"removed={summary['removed']}, modified={summary['modified']})")


# Register tree type with the base class
GitObject.register_type('tree')(Tree)