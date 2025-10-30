from typing import List, Dict
from .base import GitObject
import time

class Commit(GitObject):
    """Represents a commit snapshot"""
    
    def __init__(self):
        super().__init__()
        self.tree = ""
        self.parents: List[str] = []
        self.author = ""
        self.committer = ""
        self.message = ""
        self.timestamp = int(time.time())
    
    def serialize(self) -> bytes:
        """Format commit data"""
        lines = [
            f"tree {self.tree}",
            *[f"parent {parent}" for parent in self.parents],
            f"author {self.author}",
            f"committer {self.committer}",
            f"timestamp {self.timestamp}",
            "",
            self.message
        ]
        content = "\n".join(lines).encode()
        header = f"commit {len(content)}\0".encode()
        return header + content
    
    def deserialize(self, data: bytes):
        """Parse commit data"""
        null_pos = data.find(b'\0')
        if null_pos == -1:
            raise ValueError("Invalid commit format")
        
        content = data[null_pos + 1:].decode()
        lines = content.split('\n')
        
        for line in lines:
            if line.startswith('tree '):
                self.tree = line[5:]
            elif line.startswith('parent '):
                self.parents.append(line[7:])
            elif line.startswith('author '):
                self.author = line[7:]
            elif line.startswith('committer '):
                self.committer = line[10:]
            elif line.startswith('timestamp '):
                self.timestamp = int(line[10:])
            elif line == '':
                # Rest is message
                msg_start = lines.index(line) + 1
                self.message = '\n'.join(lines[msg_start:])
                break
    
    # SPACE FOR IMPROVEMENT:
    # - GPG signing
    # - Multiple author formats
    # - Commit notes
    # - Commit templates