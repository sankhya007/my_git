"""
Command implementations for MyGit CLI

This package contains all the command implementations for the MyGit CLI interface.
The command registry system provides a flexible way to manage, discover, and extend
Git commands with advanced features like aliases, categories, and dynamic loading.
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Any, Optional, Type
from enum import Enum

class CommandCategory(Enum):
    """Categories for organizing commands"""
    BASIC = "basic"           # Essential commands for daily use
    INSPECTION = "inspection" # Examining repository state
    HISTORY = "history"       # Working with commit history
    BRANCHING = "branching"   # Branch operations
    REMOTE = "remote"         # Remote repository operations
    ADVANCED = "advanced"     # Advanced features
    INTERNAL = "internal"     # Internal/plumbing commands
    EXPERIMENTAL = "experimental" # Experimental features

class CommandMetadata:
    """Metadata container for command information"""
    
    def __init__(self, 
                 name: str,
                 function: Callable,
                 parser_setup: Callable,
                 category: CommandCategory = CommandCategory.BASIC,
                 description: str = "",
                 aliases: List[str] = None,
                 version: str = "1.0",
                 enabled: bool = True,
                 experimental: bool = False,
                 min_repo_version: str = None):
        self.name = name
        self.function = function
        self.parser_setup = parser_setup
        self.category = category
        self.description = description or f"{name} command"
        self.aliases = aliases or []
        self.version = version
        self.enabled = enabled
        self.experimental = experimental
        self.min_repo_version = min_repo_version
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            'name': self.name,
            'category': self.category.value,
            'description': self.description,
            'aliases': self.aliases,
            'version': self.version,
            'enabled': self.enabled,
            'experimental': self.experimental,
            'min_repo_version': self.min_repo_version,
        }
    
    def __repr__(self) -> str:
        return f"CommandMetadata({self.name}, category={self.category.value})"

class CommandRegistry:
    """
    Registry for managing Git commands with advanced features including
    dynamic loading, aliases, categories, and version management.
    """
    
    def __init__(self):
        self._commands: Dict[str, CommandMetadata] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command_name
        self._categories: Dict[CommandCategory, List[str]] = {}
        self._initialized = False
    
    def register_command(self, 
                        name: str,
                        function: Callable,
                        parser_setup: Callable,
                        category: CommandCategory = CommandCategory.BASIC,
                        description: str = "",
                        aliases: List[str] = None,
                        version: str = "1.0",
                        enabled: bool = True,
                        experimental: bool = False) -> None:
        """
        Register a command with comprehensive metadata
        
        Args:
            name: Primary command name
            function: Command implementation function
            parser_setup: Argument parser setup function
            category: Command category for organization
            description: Help text description
            aliases: Alternative command names
            version: Command version for compatibility
            enabled: Whether command is currently enabled
            experimental: Mark as experimental feature
        """
        metadata = CommandMetadata(
            name=name,
            function=function,
            parser_setup=parser_setup,
            category=category,
            description=description,
            aliases=aliases or [],
            version=version,
            enabled=enabled,
            experimental=experimental
        )
        
        self._commands[name] = metadata
        
        # Register aliases
        for alias in metadata.aliases:
            if alias in self._aliases:
                raise ValueError(f"Alias '{alias}' already registered for command '{self._aliases[alias]}'")
            self._aliases[alias] = name
        
        # Add to category
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)
    
    def get_command(self, name: str) -> Optional[CommandMetadata]:
        """Get command metadata by name or alias"""
        # Check exact match first
        if name in self._commands:
            return self._commands[name]
        
        # Check aliases
        if name in self._aliases:
            actual_name = self._aliases[name]
            return self._commands.get(actual_name)
        
        return None
    
    def get_command_function(self, name: str) -> Optional[Callable]:
        """Get command function by name or alias"""
        metadata = self.get_command(name)
        return metadata.function if metadata else None
    
    def is_command_available(self, name: str) -> bool:
        """Check if command is available and enabled"""
        metadata = self.get_command(name)
        return metadata is not None and metadata.enabled
    
    def list_commands(self, 
                     category: CommandCategory = None,
                     include_experimental: bool = False,
                     include_disabled: bool = False) -> List[str]:
        """List commands with filtering options"""
        if category:
            command_names = self._categories.get(category, [])
        else:
            command_names = list(self._commands.keys())
        
        filtered_commands = []
        for name in command_names:
            metadata = self._commands[name]
            if (not metadata.enabled and not include_disabled):
                continue
            if (metadata.experimental and not include_experimental):
                continue
            filtered_commands.append(name)
        
        return sorted(filtered_commands)
    
    def list_commands_with_metadata(self, 
                                   category: CommandCategory = None,
                                   include_experimental: bool = False,
                                   include_disabled: bool = False) -> Dict[str, Dict[str, Any]]:
        """List commands with full metadata"""
        commands = {}
        for name in self.list_commands(category, include_experimental, include_disabled):
            metadata = self._commands[name]
            commands[name] = metadata.to_dict()
        return commands
    
    def get_categories(self) -> List[CommandCategory]:
        """Get all command categories"""
        return list(self._categories.keys())
    
    def get_commands_by_category(self) -> Dict[CommandCategory, List[str]]:
        """Get all commands organized by category"""
        return {cat: sorted(names) for cat, names in self._categories.items()}
    
    def enable_command(self, name: str) -> bool:
        """Enable a command"""
        metadata = self.get_command(name)
        if metadata:
            metadata.enabled = True
            return True
        return False
    
    def disable_command(self, name: str) -> bool:
        """Disable a command"""
        metadata = self.get_command(name)
        if metadata:
            metadata.enabled = False
            return True
        return False
    
    def add_alias(self, command_name: str, alias: str) -> bool:
        """Add an alias to an existing command"""
        if command_name not in self._commands:
            return False
        if alias in self._aliases:
            return False
        
        self._aliases[alias] = command_name
        self._commands[command_name].aliases.append(alias)
        return True
    
    def remove_alias(self, alias: str) -> bool:
        """Remove a command alias"""
        if alias not in self._aliases:
            return False
        
        command_name = self._aliases[alias]
        if command_name in self._commands:
            self._commands[command_name].aliases.remove(alias)
        del self._aliases[alias]
        return True
    
    def load_commands_from_module(self, module_name: str) -> None:
        """Dynamically load commands from a module"""
        try:
            module = importlib.import_module(module_name)
            self._discover_commands_in_module(module)
        except ImportError as e:
            print(f"Warning: Could not load commands from {module_name}: {e}")
    
    def load_commands_from_directory(self, directory: Path) -> None:
        """Dynamically load commands from a directory"""
        if not directory.exists():
            return
        
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name.startswith("test_"):
                continue
            
            module_name = f"{directory.parent.name}.{directory.name}.{py_file.stem}"
            try:
                self.load_commands_from_module(module_name)
            except ImportError:
                continue
    
    def _discover_commands_in_module(self, module) -> None:
        """Discover and register commands in a module"""
        for name, obj in inspect.getmembers(module):
            if (name.startswith('cmd_') and 
                inspect.isfunction(obj) and 
                not name.startswith('_')):
                
                command_name = name[4:].replace('_', '-')
                parser_func_name = f"setup_parser"
                parser_func = getattr(module, parser_func_name, None)
                
                if parser_func and inspect.isfunction(parser_func):
                    # Extract description from docstring
                    description = obj.__doc__ or f"Execute {command_name} command"
                    description = description.strip().split('\n')[0] if description else ""
                    
                    self.register_command(
                        name=command_name,
                        function=obj,
                        parser_setup=parser_func,
                        description=description
                    )
    
    def initialize_default_commands(self) -> None:
        """Initialize with default MyGit commands"""
        if self._initialized:
            return
        
        # Import and register core commands
        from .init import cmd_init, setup_parser as init_parser
        from .hash_object import cmd_hash_object, setup_parser as hash_object_parser
        from .cat_file import cmd_cat_file, setup_parser as cat_file_parser
        from .add import cmd_add, setup_parser as add_parser
        from .commit import cmd_commit, setup_parser as commit_parser
        from .log import cmd_log, setup_parser as log_parser
        
        # Register commands with proper categorization
        self.register_command(
            name='init',
            function=cmd_init,
            parser_setup=init_parser,
            category=CommandCategory.BASIC,
            description='Initialize a new repository',
            aliases=['initialize', 'create']
        )
        
        self.register_command(
            name='hash-object',
            function=cmd_hash_object,
            parser_setup=hash_object_parser,
            category=CommandCategory.INTERNAL,
            description='Compute object ID and optionally create object',
            aliases=['hash']
        )
        
        self.register_command(
            name='cat-file',
            function=cmd_cat_file,
            parser_setup=cat_file_parser,
            category=CommandCategory.INSPECTION,
            description='Display object content and information',
            aliases=['show', 'display']
        )
        
        self.register_command(
            name='add',
            function=cmd_add,
            parser_setup=add_parser,
            category=CommandCategory.BASIC,
            description='Add file contents to the staging area',
            aliases=['stage']
        )
        
        self.register_command(
            name='commit',
            function=cmd_commit,
            parser_setup=commit_parser,
            category=CommandCategory.BASIC,
            description='Record changes to the repository',
            aliases=['save', 'record']
        )
        
        self.register_command(
            name='log',
            function=cmd_log,
            parser_setup=log_parser,
            category=CommandCategory.HISTORY,
            description='Show commit history',
            aliases=['history', 'commits']
        )
        
        self._initialized = True

# Global command registry instance
_registry = CommandRegistry()

def get_registry() -> CommandRegistry:
    """Get the global command registry"""
    return _registry

def initialize_commands() -> None:
    """Initialize the command registry with default commands"""
    _registry.initialize_default_commands()

def register_command(name: str, function: Callable, parser_setup: Callable, **kwargs) -> None:
    """Convenience function to register a command"""
    _registry.register_command(name, function, parser_setup, **kwargs)

def get_command_function(name: str) -> Optional[Callable]:
    """Get command function by name"""
    return _registry.get_command_function(name)

def list_commands(category: CommandCategory = None, **kwargs) -> List[str]:
    """List available commands"""
    return _registry.list_commands(category, **kwargs)

# Initialize default commands
initialize_commands()

# Legacy COMMANDS dictionary for backward compatibility
COMMANDS = {}
for cmd_name in _registry.list_commands():
    metadata = _registry.get_command(cmd_name)
    if metadata:
        COMMANDS[cmd_name] = (metadata.function, metadata.parser_setup)

# Export public API
__all__ = [
    'COMMANDS',  # Legacy support
    'CommandRegistry',
    'CommandCategory', 
    'CommandMetadata',
    'get_registry',
    'initialize_commands',
    'register_command',
    'get_command_function',
    'list_commands',
]

# Plugin system hooks
def register_plugin_commands(registry: CommandRegistry) -> None:
    """
    Hook for plugins to register additional commands.
    Plugins should implement this function to add their commands.
    """
    pass

# Auto-discover and register plugin commands
try:
    register_plugin_commands(_registry)
except Exception as e:
    # Silently fail plugin registration to not break core functionality
    pass

# Version information
__version__ = "1.0.0"
__author__ = "MyGit Development Team"
__description__ = "Advanced command registry system for MyGit CLI"