# MyGit - A Minimal Git Implementation in Python

## Overview

MyGit is a educational implementation of Git version control system written in Python. This project aims to demonstrate the core concepts of Git internals while providing a functional version control system.

## Features

- Repository initialization (mygit init)
- Object storage system (blobs, trees, commits)
- Basic staging area (mygit add)
- Commit creation (mygit commit)
- Commit history viewing (mygit log)
- Object inspection (mygit cat-file, mygit hash-object)

## Project Structure

```
    mygit/
    ├── setup.py
    ├── src/
    │   ├── cli.py
    │   ├── repository.py
    │   ├── objects/
    │   │   ├── base.py
    │   │   ├── blob.py
    │   │   ├── tree.py
    │   │   ├── commit.py
    │   │   └── factory.py
    │   ├── commands/
    │   │   ├── init.py
    │   │   ├── hash_object.py
    │   │   ├── cat_file.py
    │   │   ├── add.py
    │   │   ├── commit.py
    │   │   └── log.py
    │   └── utils/
    │       ├── file_utils.py
    │       ├── hash_utils.py
    │       └── compression.py
    ├── tests/
    │   ├── test_objects.py
    │   ├── test_commands.py
    │   └── test_repository.py
    ├── requirements.txt
    └── README.md
```

## Installation

1. Clone or download the project
2. Navigate to the project directory
3. Install in development mode:

pip install -e .

## Quick Start

Initialize a new repository:

mygit init

Create a file and add it to version control:

echo "Hello, World!" > hello.txt
mygit add hello.txt

Commit your changes:

mygit commit -m "Add hello.txt"

View commit history:

mygit log

## Available Commands

- mygit init - Initialize a new repository
- mygit add <files> - Add files to staging area
- mygit commit -m "message" - Create a new commit
- mygit log - Show commit history
- mygit cat-file <object> - Display object contents
- mygit hash-object <file> - Calculate object hash

## Core Concepts Implemented

### Object Types
- Blob: Stores file contents
- Tree: Stores directory structure
- Commit: Stores snapshot metadata

### Storage System
- Content-addressable storage using SHA-1 hashing
- Zlib compression for efficient storage
- Object database in .mygit/objects directory

### Repository Structure
- .mygit/ - Repository metadata
- objects/ - Compressed object storage
- refs/ - Branch and tag references
- HEAD - Current branch reference

## Space for Improvement

### High Priority
- Branching and merging functionality
- Proper staging area implementation
- .gitignore file support
- Conflict resolution

### Medium Priority
- Remote repository support
- Performance optimizations
- Better error handling and recovery
- Enhanced diff functionality

### Advanced Features
- Git protocol implementation
- Hook system support
- Submodule support
- Interactive rebase

## Technical Details

### Dependencies
- Python 3.7+
- Standard library only (no external dependencies)

### Object Format
Blob: "blob {size}\0{content}"
Tree: "tree {size}\0{mode} {name}\0{sha}..."
Commit: "commit {size}\0tree {sha}\nparent {sha}\n..."

### Hash Algorithm
- SHA-1 for content addressing
- 40-character hexadecimal hashes
- Content-based integrity checking

## Learning Resources

This project is excellent for understanding:
- Git internals and data structures
- Content-addressable storage systems
- Version control system design
- Python package structure and CLI development

## Contributing

Feel free to extend this implementation by:
1. Adding new Git commands
2. Improving error handling
3. Optimizing performance
4. Adding test coverage
5. Implementing advanced Git features

## License

Educational purpose - feel free to use and modify.

## Note

This is an educational implementation and should not be used for production version control. Always use the official Git client for important projects.