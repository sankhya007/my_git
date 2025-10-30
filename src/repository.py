import os
from pathlib import Path
from typing import Optional

class Repository:
    """Represents a Git repository"""
    
    def __init__(self, path: str = "."):
        self.worktree = Path(path)
        self.gitdir = self.worktree / ".mygit"
        
    def create(self) -> bool:
        """Initialize a new repository"""
        try:
            # Create directory structure
            dirs = [
                self.gitdir / "objects",
                self.gitdir / "refs" / "heads",
                self.gitdir / "refs" / "tags",
            ]
            
            for dir_path in dirs:
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create initial files
            (self.gitdir / "HEAD").write_text("ref: refs/heads/main\n")
            (self.gitdir / "description").write_text("Unnamed repository; edit this file to name it.\n")
            
            return True
        except Exception as e:
            print(f"Error creating repository: {e}")
            return False
    
    def exists(self) -> bool:
        """Check if repository exists"""
        return self.gitdir.exists()
    
    # SPACE FOR IMPROVEMENT:
    # - Add config file support
    # - Handle bare repositories
    # - Support for different object formats
    # - Repository validation