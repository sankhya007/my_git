"""
Command implementations for MyGit CLI

This package contains all the command implementations for the MyGit CLI interface.
"""

# Import command functions
from .init import cmd_init, setup_parser as init_parser
from .hash_object import cmd_hash_object, setup_parser as hash_object_parser
from .cat_file import cmd_cat_file, setup_parser as cat_file_parser
from .add import cmd_add, setup_parser as add_parser
from .commit import cmd_commit, setup_parser as commit_parser
from .log import cmd_log, setup_parser as log_parser

# Registry of available commands
COMMANDS = {
    'init': (cmd_init, init_parser),
    'hash-object': (cmd_hash_object, hash_object_parser),
    'cat-file': (cmd_cat_file, cat_file_parser),
    'add': (cmd_add, add_parser),
    'commit': (cmd_commit, commit_parser),
    'log': (cmd_log, log_parser),
}

__all__ = ['COMMANDS']