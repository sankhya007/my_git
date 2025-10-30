from .base import GitObject
from typing import List, Dict, Tuple
import stat

class TreeEntry:
    """Represents a single entry in a tree object"""
    
    def __init__(self, mode: str, name: str, sha: str):
        self.mode = mode  # File mode (e.g., '100644' for regular file)
        self.name = name  # File/directory name
        self.sha = sha    # SHA-1 of the object
    
    def serialize(self) -> bytes:
        """Serialize tree entry to bytes"""
        return f"{self.mode} {self.name}\0".encode() + bytes.fromhex(self.sha)
    
    @classmethod
    def deserialize(cls, data: bytes) -> Tuple['TreeEntry', int]:
        """Deserialize tree entry from bytes, return (entry, bytes_consumed)"""
        # Find space separator
        space_pos = data.find(b' ')
        if space_pos == -1:
            raise ValueError("Invalid tree entry format")
        
        # Find null terminator
        null_pos = data.find(b'\0', space_pos)
        if null_pos == -1:
            raise ValueError("Invalid tree entry format")
        
        mode = data[:space_pos].decode()
        name = data[space_pos+1:null_pos].decode()
        sha = data[null_pos+1:null_pos+21].hex()  # 20 bytes for SHA-1
        
        return cls(mode, name, sha), null_pos + 21

class Tree(GitObject):
    """Represents directory structure"""
    
    def __init__(self):
        super().__init__()
        self.entries: List[TreeEntry] = []
    
    def serialize(self) -> bytes:
        """Format: tree {size}\0{entries}"""
        entries_data = b''.join(entry.serialize() for entry in sorted(self.entries, key=lambda x: x.name))
        header = f"tree {len(entries_data)}\0".encode()
        return header + entries_data
    
    def deserialize(self, data: bytes):
        """Parse tree data"""
        null_pos = data.find(b'\0')
        if null_pos == -1:
            raise ValueError("Invalid tree format")
        
        entries_data = data[null_pos + 1:]
        self.entries = []
        
        while entries_data:
            entry, consumed = TreeEntry.deserialize(entries_data)
            self.entries.append(entry)
            entries_data = entries_data[consumed:]
    
    def add_entry(self, mode: str, name: str, sha: str):
        """Add an entry to the tree"""
        self.entries.append(TreeEntry(mode, name, sha))
    
    def find_entry(self, name: str) -> TreeEntry:
        """Find an entry by name"""
        for entry in self.entries:
            if entry.name == name:
                return entry
        raise ValueError(f"Entry '{name}' not found")
    
    # SPACE FOR IMPROVEMENT:
    # - Handle symbolic links
    # - Support for git submodules
    # - Tree merging capabilities
    # - Efficient tree diffing