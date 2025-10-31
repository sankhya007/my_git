#!/usr/bin/env python3
import argparse
import sys
import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# Configure logging
def setup_logging(verbose: bool = False, log_file: Optional[Path] = None):
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )

class Color:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def colorize(text: str, color: str) -> str:
    """Colorize text for terminal output"""
    if not sys.stdout.isatty():
        return text  # No colors if not in terminal
    return f"{color}{text}{Color.END}"

class CLIError(Exception):
    """Custom exception for CLI errors"""
    pass

class CommandRegistry:
    """Manages command registration and discovery"""
    
    def __init__(self):
        self._commands: Dict[str, Dict[str, Any]] = {}
        self._categories: Dict[str, List[str]] = {
            'basic': ['init', 'add', 'commit', 'log'],
            'inspection': ['cat-file', 'hash-object'],
            'advanced': [],  # Will be populated dynamically
        }
    
    def register_command(self, name: str, func, parser_setup, 
                        category: str = 'basic', description: str = None,
                        aliases: List[str] = None):
        """Register a command with metadata"""
        self._commands[name] = {
            'func': func,
            'parser_setup': parser_setup,
            'category': category,
            'description': description or f"{name} command",
            'aliases': aliases or []
        }
        
        # Add to category
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)
    
    def get_command(self, name: str) -> Optional[Dict[str, Any]]:
        """Get command by name"""
        # Check exact match first
        if name in self._commands:
            return self._commands[name]
        
        # Check aliases
        for cmd_name, cmd_info in self._commands.items():
            if name in cmd_info.get('aliases', []):
                return cmd_info
        
        return None
    
    def list_commands(self, category: str = None) -> List[str]:
        """List all commands or commands in a category"""
        if category:
            return self._categories.get(category, [])
        return list(self._commands.keys())
    
    def get_categories(self) -> List[str]:
        """Get all command categories"""
        return list(self._categories.keys())
    
    def setup_parser(self, parser: argparse.ArgumentParser):
        """Setup argument parser with all registered commands"""
        subparsers = parser.add_subparsers(
            dest="command",
            title="available commands",
            description="Run 'mygit <command> --help' for command-specific help",
            metavar="<command>"
        )
        
        # Add commands grouped by category
        for category in self.get_categories():
            category_commands = self.list_commands(category)
            if category_commands:
                for cmd_name in sorted(category_commands):
                    cmd_info = self._commands[cmd_name]
                    cmd_parser = subparsers.add_parser(
                        cmd_name,
                        help=cmd_info['description'],
                        aliases=cmd_info.get('aliases', []),
                        description=cmd_info['description']
                    )
                    cmd_info['parser_setup'](cmd_parser)
                    cmd_parser.set_defaults(func=cmd_info['func'])

class ProgressIndicator:
    """Shows progress for long-running operations"""
    
    def __init__(self, message: str, total: int = 100):
        self.message = message
        self.total = total
        self.current = 0
        self._spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self._spinner_index = 0
    
    def update(self, progress: int, message: str = None):
        """Update progress"""
        self.current = progress
        if message:
            self.message = message
        self._render()
    
    def increment(self, amount: int = 1, message: str = None):
        """Increment progress"""
        self.current += amount
        if message:
            self.message = message
        self._render()
    
    def _render(self):
        """Render progress indicator"""
        if not sys.stderr.isatty():
            return  # No progress bars if not in terminal
        
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        bar_length = 30
        filled_length = int(bar_length * self.current // self.total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        spinner = self._spinner_chars[self._spinner_index]
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        
        sys.stderr.write(f"\r{spinner} {self.message} [{bar}] {percentage:.1f}%")
        sys.stderr.flush()
    
    def finish(self, message: str = None):
        """Finish progress indicator"""
        if sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 80 + "\r")  # Clear line
            if message:
                print(colorize(message, Color.GREEN))
        elif message:
            print(message)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.finish("Done!")
        else:
            self.finish("Failed!")

def print_banner():
    """Print MyGit banner with platform-specific characters"""
    import platform
    
    if platform.system() == 'Windows':
        # ASCII banner for Windows - properly aligned
        banner = f"""
{colorize('=' * 35, Color.CYAN)}
{colorize('|', Color.CYAN)}   {colorize('MyGit -- Git Implementation', Color.BOLD + Color.MAGENTA)}   {colorize('|', Color.CYAN)}
{colorize('|', Color.CYAN)}   Educational Version Control   {colorize('|', Color.CYAN)}
{colorize('=' * 35, Color.CYAN)}
"""
    else:
        # Unicode banner for Unix-like systems - properly aligned
        banner = f"""
{colorize('╔════════════════════════════════════════════╗', Color.CYAN)}
{colorize('║', Color.CYAN)}        {colorize('MyGit', Color.BOLD + Color.MAGENTA)} - Minimal Git Implementation        {colorize('║', Color.CYAN)}
{colorize('║', Color.CYAN)}        Educational Git Implementation        {colorize('║', Color.CYAN)}
{colorize('╚════════════════════════════════════════════╝', Color.CYAN)}
"""
    print(banner)

def print_usage_examples():
    """Print usage examples"""
    examples = f"""
{colorize('Usage Examples:', Color.BOLD + Color.YELLOW)}

{colorize('Basic Workflow:', Color.CYAN)}
  {colorize('mygit init', Color.GREEN)}                          {colorize('# Initialize repository', Color.WHITE)}
  {colorize('mygit add README.md', Color.GREEN)}                 {colorize('# Stage files', Color.WHITE)}
  {colorize('mygit commit -m "Initial commit"', Color.GREEN)}    {colorize('# Create commit', Color.WHITE)}
  {colorize('mygit log', Color.GREEN)}                           {colorize('# View history', Color.WHITE)}

{colorize('Object Inspection:', Color.CYAN)}
  {colorize('mygit hash-object file.txt', Color.GREEN)}          {colorize('# Calculate object hash', Color.WHITE)}
  {colorize('mygit cat-file -p <hash>', Color.GREEN)}            {colorize('# View object content', Color.WHITE)}

{colorize('Advanced Usage:', Color.CYAN)}
  {colorize('mygit --verbose add .', Color.GREEN)}               {colorize('# Verbose output', Color.WHITE)}
  {colorize('mygit --log-file debug.log commit', Color.GREEN)}   {colorize('# Log to file', Color.WHITE)}
"""
    print(examples)

def handle_keyboard_interrupt():
    """Handle Ctrl+C gracefully"""
    print(f"\n{colorize('Operation cancelled by user', Color.YELLOW)}")
    sys.exit(130)

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 7):
        print(f"{colorize('Error: MyGit requires Python 3.7 or higher', Color.RED)}")
        sys.exit(1)

def load_commands() -> CommandRegistry:
    """Load and register all commands"""
    registry = CommandRegistry()
    
    try:
        from .commands import COMMANDS
        
        # Register commands from the commands package
        for cmd_name, (cmd_func, parser_setup) in COMMANDS.items():
            # Determine category based on command name
            if cmd_name in ['init', 'add', 'commit', 'log']:
                category = 'basic'
            elif cmd_name in ['cat-file', 'hash-object']:
                category = 'inspection'
            else:
                category = 'advanced'
            
            registry.register_command(
                name=cmd_name,
                func=cmd_func,
                parser_setup=parser_setup,
                category=category
            )
        
        # Register additional commands that might not be in COMMANDS
        # This allows for dynamic command registration
        
    except ImportError as e:
        raise CLIError(f"Failed to load commands: {e}")
    
    return registry

def main():
    """Main CLI entry point with enhanced functionality"""
    import sys
    
    # Set up signal handler for Ctrl+C
    import signal
    signal.signal(signal.SIGINT, lambda sig, frame: handle_keyboard_interrupt())
    
    # Check Python version
    check_python_version()
    
    # Create main parser
    parser = argparse.ArgumentParser(
        description="MyGit - A minimal Git implementation in Python",
        epilog="Run 'mygit <command> --help' for command-specific help.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    
    # Global options
    global_group = parser.add_argument_group('global options')
    global_group.add_argument(
        '-h', '--help',
        action='store_true',
        help='Show this help message and exit'
    )
    global_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    global_group.add_argument(
        '--version',
        action='store_true',
        help='Show version information'
    )
    global_group.add_argument(
        '--log-file',
        type=Path,
        help='Write logs to specified file'
    )
    global_group.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    # Load commands and setup subparsers
    try:
        registry = load_commands()
        registry.setup_parser(parser)
    except CLIError as e:
        print(f"{colorize(f'Error: {e}', Color.RED)}")
        sys.exit(1)
    
    # Parse arguments
    if len(sys.argv) == 1:
        print_banner()
        print_usage_examples()
        parser.print_help()
        return 0
    
    args = parser.parse_args()
    
    # Handle global options
    if args.help and not hasattr(args, 'func'):
        print_banner()
        parser.print_help()
        return 0
    
    if args.version:
        from . import __version__
        print(f"MyGit version {__version__}")
        return 0
    
    if args.no_color:
    # Disable colors by replacing colorize function
    # Use a different approach to avoid global declaration issues
        import types
        import sys
        # Create a new module-level colorize function that doesn't use colors
        sys.modules[__name__].colorize = lambda text, color: text
    
    # Setup logging
    setup_logging(args.verbose, args.log_file)
    logger = logging.getLogger('mygit')
    
    try:
        # Execute command
        if hasattr(args, 'func'):
            logger.debug(f"Executing command: {args.command}")
            logger.debug(f"Command arguments: {args}")
            
            success = args.func(args)
            if success:
                logger.debug("Command completed successfully")
                return 0
            else:
                logger.error("Command failed")
                return 1
        else:
            # No command specified but not help/version
            if args.command:
                print(f"{colorize(f'Error: Unknown command "{args.command}"', Color.RED)}")
                print(f"Run {colorize('mygit --help', Color.CYAN)} for available commands.")
            else:
                parser.print_help()
            return 1
            
    except CLIError as e:
        print(f"{colorize(f'Error: {e}', Color.RED)}")
        logger.error(f"CLI error: {e}")
        return 1
    except Exception as e:
        print(f"{colorize(f'Unexpected error: {e}', Color.RED)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        logger.exception("Unexpected error occurred")
        return 1

# Utility functions for command implementations
def confirm_action(prompt: str, default: bool = False) -> bool:
    """Ask for user confirmation"""
    choices = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{choices}]: ").strip().lower()
    
    if response in ['y', 'yes']:
        return True
    elif response in ['n', 'no']:
        return False
    else:
        return default

def print_success(message: str):
    """Print success message"""
    print(f"{colorize('✓', Color.GREEN)} {message}")

def print_error(message: str):
    """Print error message"""
    print(f"{colorize('✗', Color.RED)} {message}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{colorize('⚠', Color.YELLOW)} {message}")

def print_info(message: str):
    """Print info message"""
    print(f"{colorize('ℹ', Color.CYAN)} {message}")

def format_file_size(size: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

if __name__ == "__main__":
    sys.exit(main())