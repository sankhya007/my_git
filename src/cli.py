#!/usr/bin/env python3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="MyGit - a minimal Git implementation")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Import from the commands package
    from .commands import COMMANDS
    
    # Setup all command parsers
    for cmd_name, (cmd_func, parser_setup) in COMMANDS.items():
        cmd_parser = subparsers.add_parser(cmd_name, help=f"{cmd_name} help")
        parser_setup(cmd_parser)
        cmd_parser.set_defaults(func=cmd_func)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        if hasattr(args, 'func'):
            success = args.func(args)
            return 0 if success else 1
        else:
            print(f"Command '{args.command}' not properly configured")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())