# Contributing to MyGit

Thank you for your interest in contributing to MyGit! This is an educational Git implementation in Python, and we welcome contributions that help improve the code quality, add features, or fix bugs.

## 🚀 Quick Start

### 1. Fork & Clone
```bash
git clone https://github.com/your-username/my_git.git
cd my_git
``` 
### 2. Setup Development Environment
bash

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

### 3. Create a Feature Branch
bash
git checkout -b feature/your-feature-name

### 4. Make Your Changes & Test
bash
# Run tests
python -m pytest tests/

# Test your changes
python src/cli.py --help

### 5. Submit Pull Request
Push your branch and open a PR with a clear description.

## 🛠️ Development Guidelines

# Code Style
- Follow PEP 8 conventions
- Use type hints for function signatures
- Add docstrings for all public functions/classes
- Keep lines under 88 characters

# Testing
- Write tests for new features in tests/ directory
- Ensure all existing tests pass
- Test on multiple platforms if possible

# Commit Messages
Use conventional commit format:


    feat: add new command implementation
    fix: resolve object compression issue
    docs: update installation instructions
    refactor: improve object factory pattern
    test: add tests for blob serialization

### 📁 Project Structure

    src/
    ├── objects/          # Git object system (blob, tree, commit)
    ├── commands/         # CLI command implementations
    ├── utils/            # Utility functions and helpers
    └── cli.py           # Main command-line interface

### 🎯 Areas Needing Contribution

## High Priority
- Implement missing Git commands (status, branch, checkout)
- Add comprehensive test coverage
- Improve error handling and user feedback
- Add .gitignore support

### Intermediate
- Performance optimizations for large files
- Enhanced compression algorithms
- Better cross-platform compatibility
- Additional Git object types

### Advanced
- Remote repository support
- Branching and merging functionality
- Git protocol implementation
- Hook system

### ❓ Getting Help
- Open an issue for questions
- Check existing issues and discussions
- Review the README.md for project overview

### 📝 Pull Request Process
- Ensure your code passes all tests
- Update documentation if needed
- Add tests for new functionality
- Describe your changes in the PR template
- Request review from maintainers

### 🐛 Reporting Bugs
- Use the bug report template and include:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)

### 💡 Suggesting Features
- Use the feature request template and describe:
- The problem you're solving
- Proposed solution
- Alternative approaches considered

### 🏆 Recognition
- Contributors will be recognized in our README.md and release notes. Great contributions may lead to maintainer status!

Happy coding! 🎉