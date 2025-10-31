# MyGit - A Minimal Git Implementation in Python

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 📖 Overview

MyGit is an educational implementation of Git version control system written in Python. This project demonstrates the core concepts of Git internals while providing a functional version control system with advanced features like object caching, compression, and cross-platform support.

**🎯 Learning Focus**: Understand Git internals, content-addressable storage, and version control systems through clean, readable Python code.

## ✨ Features

### ✅ Core Features
- **Repository Management**: Initialize and manage repositories (`mygit init`)
- **Object Storage System**: Blobs, trees, commits with SHA-1/SHA-256 support
- **Staging Area**: Add files to staging (`mygit add`)
- **Commit System**: Create commits with author metadata (`mygit commit`)
- **History Viewing**: Browse commit history (`mygit log`)
- **Object Inspection**: Examine stored objects (`mygit cat-file`, `mygit hash-object`)

### 🚀 Advanced Features
- **Object Caching**: LRU caching for performance optimization
- **Compression System**: Zlib compression with configurable levels
- **Delta Compression**: Efficient storage of similar objects
- **Streaming Support**: Memory-efficient large file handling
- **Cross-Platform**: Windows, Linux, and macOS compatibility
- **Colorized Output**: Beautiful terminal interface with progress indicators

## 🏗️ Architecture
    mygit/
    ├── src/
    │ ├── objects/ # Git object system
    │ │ ├── blob.py # File content storage
    │ │ ├── tree.py # Directory structure
    │ │ ├── commit.py # Commit metadata
    │ │ └── factory.py # Object factory with caching
    │ ├── commands/ # CLI command implementations
    │ │ ├── init.py # Repository initialization
    │ │ ├── add.py # Staging files
    │ │ ├── commit.py # Creating commits
    │ │ └── log.py # History viewing
    │ └── utils/ # Utility systems
    │ ├── hash_utils.py # Hashing and compression
    │ └── file_utils.py # Cross-platform file operations

## 🚀 Quick Start

### Installation

#### Method 1: Install as Package (Recommended)
```bash
# Clone the repository
git clone https://github.com/sankhya007/my_git.git
cd my_git

# Install in development mode
pip install -e .
```

#### Method 2: Run Directly
```bash
python src/cli.py --help
# or
python -m src.cli --help
```

### Basic Usage
```bash
# Initialize a new repository
mygit init

# Create and stage files
echo "Hello, MyGit!" > README.md
mygit add README.md

# Commit changes
mygit commit -m "Initial commit"

# View commit history
mygit log

# Inspect objects
mygit hash-object README.md
mygit cat-file -p <object-hash>
```

## 📚 Available Commands

### Basic Workflow
| Command | Description |
|----------|-------------|
| mygit init | Initialize new repository |
| mygit add <file> | Stage files for commit |
| mygit commit -m "message" | Create new commit |
| mygit log | Display commit history |

### Object Inspection
| Command | Description |
|----------|-------------|
| mygit cat-file <object> | Display object contents |
| mygit hash-object <file> | Calculate object hash |

## 🔧 Advanced Configuration

### Compression Settings
```python
# In .mygit/config
[compression]
level = 6          # 1-9, higher = better compression
algorithm = zlib   # zlib, lzma
enable_delta = true
```

### Performance Tuning
```python
[cache]
max_size = 1000    # Maximum objects in cache
strategy = lru     # Cache replacement strategy
```

## 🧪 Testing
Run the test suite to verify your installation:
```bash
# Run all tests
python -m pytest tests/

# Run specific test module
python -m pytest tests/test_objects.py

# Run with coverage
python -m pytest --cov=src tests/
```

## 🤝 Contributing
We welcome contributions! Please see our Contributing Guide for details.

### First Time Contributors
Check out issues labeled good-first-issue to get started with the codebase.

### Development Setup
```bash
# Fork and clone
git clone https://github.com/your-username/my_git.git
cd my_git

# Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .

# Run tests
python -m pytest tests/
```

## 📖 Learning Resources
This project is excellent for understanding:
- Git Internals: Object model, references, pack files
- Content-Addressable Storage: SHA-based object retrieval
- Version Control Design: Delta compression, branching models
- Python Architecture: Package structure, CLI development, caching

**Recommended Reading**
- Pro Git Book
- Git Internals PDF

## 🐛 Troubleshooting
### Common Issues

**Issue:** Command not found after installation  
**Solution:**
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Issue:** Permission errors on Windows  
**Solution:** Run as administrator or adjust permissions

**Issue:** Large file performance  
**Solution:** Adjust compression settings in config

## 📊 Performance Notes
- Small Repositories: Comparable performance to Git  
- Large Files: Streaming prevents memory issues  
- Compression: Configurable levels for speed/size tradeoff  
- Caching: Significant performance improvement for repeated operations  

## 🔮 Roadmap
**Phase 1: Core Complete ✅**
- Basic object system
- Repository management
- Commit history

**Phase 2: In Progress 🚧**
- Branching and merging
- Remote repository support
- Enhanced diff functionality

**Phase 3: Planned 📋**
- Git protocol implementation
- Hook system
- Performance optimizations

## 👥 Contributors
<a href="https://github.com/sankhya007/my_git/graphs/contributors">
<img src="https://contrib.rocks/image?repo=sankhya007/my_git" />
</a>
We appreciate all contributions! See our Contributors Guide to get started.

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Important Note
This is an educational implementation and should not be used for production version control. Always use the official Git client for important projects.

**MyGit - Understanding Git, one commit at a time. 🎓**

If you find this project helpful, please give it a ⭐ on GitHub!
