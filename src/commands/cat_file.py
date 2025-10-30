import argparse
import sys
from ..repository import Repository
from ..objects.factory import ObjectFactory

def cmd_cat_file(args):
    """Display contents of a git object"""
    repo = Repository()
    
    if not repo.exists():
        print("Not a git repository")
        return False
    
    try:
        obj = ObjectFactory.read_object(repo, args.object)
        
        if args.pretty_print:
            # Pretty print based on object type
            if hasattr(obj, 'data'):
                if isinstance(obj.data, bytes):
                    sys.stdout.buffer.write(obj.data)
                else:
                    print(obj.data)
            else:
                print(f"Object {args.object}: {type(obj).__name__}")
        else:
            # Raw content
            raw_data = obj.serialize()
            sys.stdout.buffer.write(raw_data)
        
        return True
        
    except FileNotFoundError:
        print(f"Error: object {args.object} not found")
        return False
    except Exception as e:
        print(f"Error reading object: {e}")
        return False

def setup_parser(parser):
    """Setup argument parser for cat-file command"""
    parser.add_argument("object", help="The object to display")
    parser.add_argument("-p", "--pretty-print", action="store_true", 
                       help="Pretty print the object content")
    
# SPACE FOR IMPROVEMENT:
# - Support for multiple object types
# - Size and type queries (-s, -t flags)
# - Batch processing mode
# - Streaming for large objects