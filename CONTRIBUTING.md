# Contributing to dedupe

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yksanjo/dedupe.git
cd dedupe

# Install development dependencies
make dev
# or: pip install -r requirements.txt
```

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run integration tests
make test-integration
```

## Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type check
make type-check

# Run all checks
make check
```

## Project Structure

```
dedupe/
├── dedupe              # Main executable script
├── tests/              # Test suite
│   ├── test_hash_engine.py
│   ├── test_traverser.py
│   ├── test_state_db.py
│   └── test_cleaner.py
├── .github/workflows/  # CI/CD configuration
├── README.md
├── LICENSE
├── Makefile
└── pyproject.toml
```

## Making Changes

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Make your changes** with clear, focused commits
3. **Add tests** for new functionality
4. **Run checks**: `make check`
5. **Submit a pull request**

## Code Style

- Follow PEP 8
- Use Black for formatting (`make format`)
- Add docstrings for public functions
- Keep functions focused and small

## Reporting Issues

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
