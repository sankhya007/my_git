
# MyGit - A Minimal Git Implementation in Python

## Overview

MyGit is an educational implementation of Git version control system written in Python. This project aims to demonstrate the core concepts of Git internals while providing a functional version control system with advanced features like object caching, compression, and cross-platform support.

## Features

- **Repository Management**: Initialize and manage repositories (mygit init)
- **Object Storage System**: Blobs, trees, commits with SHA-1/SHA-256 support
- **Staging Area**: Add files to staging (mygit add)
- **Commit System**: Create commits with author metadata (mygit commit)
- **History Viewing**: Browse commit history (mygit log)
- **Object Inspection**: Examine stored objects (mygit cat-file, mygit hash-object)
- **Advanced Features**: Object caching, delta compression, streaming support
- **Cross-Platform**: Windows, Linux, and macOS compatibility

## Project Structure

```
mygit/
├── setup.py
├── src/
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface with color support
│   ├── repository.py          # Repository management with validation
│   ├── objects/               # Git object system
│   │   ├── __init__.py        # Object system manager
│   │   ├── base.py            # Base GitObject class
│   │   ├── blob.py            # File content storage
│   │   ├── tree.py            # Directory structure
│   │   ├── commit.py          # Commit metadata
│   │   └── factory.py         # Object factory with caching
│   ├── commands/              # CLI command implementations
│   │   ├── __init__.py        # Command registry system
│   │   ├── init.py            # Repository initialization
│   │   ├── hash_object.py     # Object hashing
│   │   ├── cat_file.py        # Object inspection
│   │   ├── add.py             # Staging files
│   │   ├── commit.py          # Creating commits
│   │   └── log.py             # History viewing
│   └── utils/                 # Utility systems
│       ├── __init__.py        # Utility manager
│       ├── file_utils.py      # Cross-platform file operations
│       ├── hash_utils.py      # Hashing and compression
│       └── compression.py     # Advanced compression features
├── tests/
│   ├── test_objects.py
│   ├── test_commands.py
│   └── test_repository.py
├── requirements.txt
└── README.md
```

## Installation

### Method 1: Install as Package (Recommended)
```bash
# Clone or download the project
git clone <repository-url>
cd my_git

# Install in development mode
pip install -e .
```

### Method 2: Run Directly
```bash
# From project root
python src/cli.py --help

# Or using module execution
python -m src.cli --help
```

### Method 3: Development Setup
```bash
# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Quick Start

```bash
# Initialize repository
mygit init

# Create and stage files
echo "Hello, MyGit!" > README.md
mygit add README.md

# Commit changes
mygit commit -m "Initial commit"

# View history
mygit log

# Inspect objects
mygit hash-object README.md
mygit cat-file -p <object-hash>
```

## Available Commands

### Basic Commands
- `mygit init` - Initialize a new repository
- `mygit add <files>` - Add files to staging area
- `mygit commit -m "message"` - Create a new commit
- `mygit log` - Show commit history

### Inspection Commands
- `mygit cat-file <object>` - Display object contents
- `mygit hash-object <file>` - Calculate object hash

### Advanced Features
- Colorized terminal output
- Progress indicators for large operations
- Configurable compression levels
- Object caching for performance
- Cross-platform file locking

## Core Concepts Implemented

### Object System
- **Blob**: File content storage with encoding detection
- **Tree**: Directory structure with entry metadata
- **Commit**: Snapshot metadata with GPG signing support
- **Factory Pattern**: Object creation with caching and pooling

### Storage System
- Content-addressable storage using SHA-1/SHA-256
- Zlib compression with configurable levels
- Delta compression for similar objects
- Streaming support for large files
- Object database in `.mygit/objects` directory

### Advanced Features
- **Object Validation**: Integrity checking and format validation
- **Memory Management**: Streaming and chunked processing
- **Caching System**: LRU caches for objects and hashes
- **Plugin System**: Extensible object types and commands
- **Error Handling**: Comprehensive exception hierarchy

### Repository Structure
```
.mygit/
├── HEAD              # Current branch reference
├── config           # Repository configuration
├── objects/         # Compressed object storage
│   ├── pack/        # Pack files for efficiency
│   └── [0-9a-f]{2}/ # SHA-based object storage
├── refs/            # References
│   ├── heads/       # Branch references
│   └── tags/        # Tag references
└── hooks/           # Git hooks (sample implementations)
```

## Technical Details

### Dependencies
- **Python 3.7+** - No external dependencies (standard library only)
- **Cross-Platform** - Windows (msvcrt), Unix (fcntl) file locking
- **Unicode Support** - Full UTF-8 encoding support

### Object Formats
```
Blob:   "blob {size}\0{content}"
Tree:   "tree {size}\0{mode} {name}\0{sha}..."
Commit: "commit {size}\0tree {sha}
         parent {sha}
         author {name} <email> {timestamp} {timezone}
         committer {name} <email> {timestamp} {timezone}
         {message}"
```

### Performance Features
- **Object Pooling**: Reusable object instances
- **LRU Caching**: Frequently accessed objects
- **Streaming Compression**: Memory-efficient large file handling
- **Batch Operations**: Efficient multi-object processing

## Development Status

### ✅ Implemented
- [x] Basic object system (blob, tree, commit)
- [x] Repository initialization and management
- [x] Object storage and retrieval
- [x] CLI interface with argument parsing
- [x] Cross-platform file operations
- [x] Advanced compression and caching
- [x] Object validation and integrity checking

### 🚧 In Progress
- [ ] Complete command implementations
- [ ] Branching and merging
- [ ] Remote repository support

### 📋 Planned Features
- [ ] Enhanced diff functionality
- [ ] Conflict resolution
- [ ] Git protocol implementation
- [ ] Hook system
- [ ] Performance optimizations

## Space for Improvement

### High Priority
- Complete command implementations in `commands/` directory
- Branching and merging functionality
- Proper staging area with index file
- `.gitignore` file support

### Medium Priority
- Remote repository support (fetch, push, pull)
- Performance optimizations for large repositories
- Enhanced error handling and recovery
- Comprehensive test coverage

### Advanced Features
- Git protocol implementation
- Interactive rebase and cherry-pick
- Submodule support
- Bisect functionality
- Worktree support

## Learning Resources

This project is excellent for understanding:
- **Git Internals**: Object model, references, pack files
- **Content-Addressable Storage**: SHA-based object retrieval
- **Version Control Design**: Delta compression, branching models
- **Python Architecture**: Package structure, CLI development, caching
- **Cross-Platform Development**: File system abstractions, locking mechanisms

## Contributing

### Extending MyGit
1. **Add New Commands**: Implement in `commands/` directory
2. **Enhance Objects**: Extend object types in `objects/` 
3. **Improve Utilities**: Add features to utility systems
4. **Add Tests**: Expand test coverage in `tests/`

### Development Setup
```bash
git clone <repository>
cd my_git
pip install -e .
# Implement features and test with:
python -m src.cli <command>
```

## License

Educational Purpose - Feel free to use, modify, and learn from this implementation.

## Important Note

**This is an educational implementation** and should not be used for production version control. Always use the official Git client for important projects. This implementation focuses on clarity and learning rather than performance or security.

---
## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

### First Time Contributors
If you're new to open source, check out these issues labeled `good-first-issue` to get started.

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/your-username/my_git.git
cd my_git

# Set up development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .

# Run tests
python -m pytest tests/

*MyGit - Understanding Git, one commit at a time.*