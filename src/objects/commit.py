import time
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from email.utils import parseaddr
from .base import GitObject, ObjectValidationError

class Commit(GitObject):
    """Represents a commit snapshot with enhanced functionality"""
    
    def __init__(self):
        super().__init__()
        self.tree = ""
        self.parents: List[str] = []
        self.author = ""
        self.committer = ""
        self.message = ""
        self.timestamp = int(time.time())
        self.timezone = "+0000"  # Default timezone
        self.gpgsig: Optional[str] = None
        self.notes: List[str] = []
        self.extra_headers: Dict[str, str] = {}
        self.template: Optional[str] = None
    
    def serialize(self) -> bytes:
        """Format commit data with all optional fields"""
        lines = [
            f"tree {self.tree}",
            *[f"parent {parent}" for parent in self.parents],
            f"author {self._format_person_info(self.author, self.timestamp, self.timezone)}",
            f"committer {self._format_person_info(self.committer, self.timestamp, self.timezone)}",
        ]
        
        # Add extra headers
        for key, value in self.extra_headers.items():
            lines.append(f"{key} {value}")
        
        # Add GPG signature if present
        if self.gpgsig:
            lines.append(f"gpgsig {self.gpgsig}")
        
        # Add commit notes if present
        for note in self.notes:
            lines.append(f"note {note}")
        
        # Add template reference if present
        if self.template:
            lines.append(f"template {self.template}")
        
        # Empty line before message
        lines.append("")
        
        # Message
        lines.append(self.message)
        
        content = "\n".join(lines).encode()
        header = f"commit {len(content)}\0".encode()
        return header + content
    
    def deserialize(self, data: bytes):
        """Parse commit data with all optional fields"""
        null_pos = data.find(b'\0')
        if null_pos == -1:
            raise ObjectValidationError("Invalid commit format: missing null terminator")
        
        content = data[null_pos + 1:].decode('utf-8', errors='replace')
        lines = content.split('\n')
        
        self.parents = []
        self.notes = []
        self.extra_headers = {}
        
        message_lines = []
        in_message = False
        in_gpgsig = False
        gpgsig_lines = []
        
        for line in lines:
            if in_gpgsig:
                if line.startswith(' '):
                    gpgsig_lines.append(line[1:])
                else:
                    self.gpgsig = '\n'.join(gpgsig_lines)
                    in_gpgsig = False
                    # Continue processing this line
                continue
            
            if in_message:
                message_lines.append(line)
                continue
            
            if line.startswith('tree '):
                self.tree = line[5:]
            elif line.startswith('parent '):
                self.parents.append(line[7:])
            elif line.startswith('author '):
                author_info = line[7:]
                self.author, self.timestamp, self.timezone = self._parse_person_info(author_info)
            elif line.startswith('committer '):
                committer_info = line[10:]
                self.committer, _, _ = self._parse_person_info(committer_info)
            elif line.startswith('gpgsig '):
                in_gpgsig = True
                gpgsig_lines = [line[7:]]
            elif line.startswith('note '):
                self.notes.append(line[5:])
            elif line.startswith('template '):
                self.template = line[9:]
            elif line == '':
                in_message = True
            else:
                # Handle extra headers (mergetag, etc.)
                if ' ' in line:
                    key, value = line.split(' ', 1)
                    self.extra_headers[key] = value
        
        self.message = '\n'.join(message_lines).strip()
    
    def _format_person_info(self, person: str, timestamp: int, timezone: str) -> str:
        """Format person information with timestamp and timezone"""
        return f"{person} {timestamp} {timezone}"
    
    def _parse_person_info(self, info: str) -> tuple[str, int, str]:
        """Parse person information string into components"""
        # Expected format: "Name <email> timestamp timezone"
        parts = info.rsplit(' ', 2)
        if len(parts) != 3:
            raise ObjectValidationError(f"Invalid person info format: {info}")
        
        person_str, timestamp_str, timezone = parts
        
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise ObjectValidationError(f"Invalid timestamp: {timestamp_str}")
        
        return person_str, timestamp, timezone
    
    def set_author(self, name: str, email: str, timestamp: int = None, timezone: str = None):
        """Set author information with validation"""
        self.author = self._format_person(name, email)
        if timestamp is not None:
            self.timestamp = timestamp
        if timezone is not None:
            self.timezone = timezone
    
    def set_committer(self, name: str, email: str):
        """Set committer information with validation"""
        self.committer = self._format_person(name, email)
    
    def _format_person(self, name: str, email: str) -> str:
        """Format person name and email according to Git standards"""
        # Remove any existing angle brackets and sanitize
        name = name.strip()
        email = email.strip().strip('<>')
        
        # Validate email format
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValueError(f"Invalid email format: {email}")
        
        return f"{name} <{email}>"
    
    def parse_person(self, person_str: str) -> tuple[str, str]:
        """Parse person string into name and email"""
        name, email = parseaddr(person_str)
        if not name or not email:
            raise ValueError(f"Could not parse person string: {person_str}")
        return name, email
    
    def add_parent(self, parent_sha: str):
        """Add a parent commit with validation"""
        if not re.match(r'^[a-f0-9]{40}$', parent_sha):
            raise ValueError(f"Invalid parent SHA: {parent_sha}")
        self.parents.append(parent_sha)
    
    def set_message(self, message: str, template: str = None):
        """Set commit message with optional template"""
        self.message = message.strip()
        if template:
            self.template = template
    
    def add_note(self, note: str):
        """Add a commit note"""
        self.notes.append(note.strip())
    
    def set_gpgsig(self, signature: str):
        """Set GPG signature"""
        self.gpgsig = signature
    
    def verify_signature(self) -> bool:
        """Verify GPG signature (placeholder implementation)"""
        if not self.gpgsig:
            return False
        
        # In a real implementation, this would verify the signature
        # against the commit content and the author's public key
        try:
            # Placeholder: check if signature looks valid
            return self.gpgsig.startswith('-----BEGIN PGP SIGNATURE-----')
        except Exception:
            return False
    
    def is_merge_commit(self) -> bool:
        """Check if this is a merge commit"""
        return len(self.parents) >= 2
    
    def is_root_commit(self) -> bool:
        """Check if this is a root commit (no parents)"""
        return len(self.parents) == 0
    
    def get_author_info(self) -> Dict[str, Any]:
        """Get structured author information"""
        name, email = self.parse_person(self.author)
        return {
            'name': name,
            'email': email,
            'timestamp': self.timestamp,
            'timezone': self.timezone,
            'date': datetime.fromtimestamp(self.timestamp).isoformat()
        }
    
    def get_committer_info(self) -> Dict[str, Any]:
        """Get structured committer information"""
        name, email = self.parse_person(self.committer)
        return {
            'name': name,
            'email': email
        }
    
    def get_summary(self) -> str:
        """Get the first line of the commit message (summary)"""
        if not self.message:
            return ""
        return self.message.split('\n')[0]
    
    def get_body(self) -> str:
        """Get the commit message body (excluding summary)"""
        if not self.message:
            return ""
        
        lines = self.message.split('\n')
        if len(lines) <= 1:
            return ""
        
        return '\n'.join(lines[1:]).strip()
    
    def _validate_internal(self) -> bool:
        """Internal validation for commit-specific rules"""
        # Validate tree SHA
        if not re.match(r'^[a-f0-9]{40}$', self.tree):
            return False
        
        # Validate parent SHAs
        for parent in self.parents:
            if not re.match(r'^[a-f0-9]{40}$', parent):
                return False
        
        # Validate author and committer formats
        try:
            self.parse_person(self.author)
            self.parse_person(self.committer)
        except ValueError:
            return False
        
        # Validate timestamp
        if self.timestamp <= 0:
            return False
        
        # Validate timezone format
        if not re.match(r'^[+-]\d{4}$', self.timezone):
            return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about the commit"""
        stats = super().get_statistics()
        
        stats.update({
            'tree_sha': self.tree,
            'parent_count': len(self.parents),
            'is_merge': self.is_merge_commit(),
            'is_root': self.is_root_commit(),
            'author_info': self.get_author_info(),
            'committer_info': self.get_committer_info(),
            'message_summary': self.get_summary(),
            'message_line_count': len(self.message.split('\n')) if self.message else 0,
            'has_gpgsig': bool(self.gpgsig),
            'gpgsig_valid': self.verify_signature() if self.gpgsig else None,
            'note_count': len(self.notes),
            'template': self.template,
            'extra_headers_count': len(self.extra_headers),
        })
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert commit to dictionary representation"""
        base_dict = super().to_dict()
        
        base_dict.update({
            'tree': self.tree,
            'parents': self.parents,
            'author': self.author,
            'committer': self.committer,
            'message': self.message,
            'timestamp': self.timestamp,
            'timezone': self.timezone,
            'gpgsig_present': bool(self.gpgsig),
            'notes': self.notes,
            'template': self.template,
            'summary': self.get_summary(),
        })
        
        return base_dict
    
    def apply_template(self, template_text: str) -> str:
        """Apply a template to the commit message"""
        # Simple template substitution
        # In real Git, this would be more sophisticated
        template_vars = {
            'summary': self.get_summary(),
            'body': self.get_body(),
            'author_name': self.get_author_info()['name'],
            'author_email': self.get_author_info()['email'],
            'timestamp': self.timestamp,
            'date': datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d'),
        }
        
        result = template_text
        for key, value in template_vars.items():
            result = result.replace(f'{{{key}}}', str(value))
        
        return result
    
    def generate_changelog_entry(self, style: str = "conventional") -> str:
        """Generate a changelog entry in various styles"""
        summary = self.get_summary()
        
        if style == "conventional":
            # Conventional Commits style
            types = ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore']
            for commit_type in types:
                if summary.lower().startswith(f"{commit_type}:"):
                    return summary
        
        elif style == "github":
            # GitHub-style with hash
            return f"- {summary} ({self.get_hash()[:7]})"
        
        elif style == "simple":
            # Simple bullet point
            return f"• {summary}"
        
        return summary
    
    def __repr__(self) -> str:
        """String representation of the commit"""
        short_hash = self.get_hash()[:8]
        summary = self.get_summary()[:50] + "..." if len(self.get_summary()) > 50 else self.get_summary()
        parent_info = f", parents={len(self.parents)}" if self.parents else ""
        return f"Commit({short_hash}, '{summary}'{parent_info})"
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        return (f"Commit {self.get_hash()[:8]} | "
                f"Author: {self.get_author_info()['name']} | "
                f"Message: {self.get_summary()}")


class CommitTemplate:
    """Manages commit message templates"""
    
    BUILTIN_TEMPLATES = {
        "conventional": """{summary}

{body}

# Types: feat, fix, docs, style, refactor, test, chore
# Scope: (optional) what part of the codebase is affected
# Breaking: ! after type/scope for breaking changes""",
        
        "detailed": """{summary}

# Detailed description of changes
# 
# Why this change is being made?
# What side effects might this have?
# 
# Related issues: #123, #456
{body}""",
        
        "simple": """{summary}

{body}"""
    }
    
    @classmethod
    def get_template(cls, name: str) -> str:
        """Get a template by name"""
        return cls.BUILTIN_TEMPLATES.get(name, cls.BUILTIN_TEMPLATES["simple"])
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """List available template names"""
        return list(cls.BUILTIN_TEMPLATES.keys())


# Register commit type with the base class
GitObject.register_type('commit')(Commit)