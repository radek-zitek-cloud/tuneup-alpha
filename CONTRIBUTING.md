# Contributing to TuneUp Alpha

Thank you for your interest in contributing to TuneUp Alpha! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/radek-zitek-cloud/tuneup-alpha.git
   cd tuneup-alpha
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

## Code Style

- Use four-space indentation throughout the repository
- Hard tabs are not permitted in committed files
- Follow PEP 8 guidelines
- Add type hints to all function signatures
- Write docstrings for public modules, classes, and functions

## Testing

Run the test suite before submitting changes:

```bash
pytest
```

For coverage report:

```bash
pytest --cov=tuneup_alpha --cov-report=term-missing
```

## Submitting Changes

1. Create a new branch for your feature or bugfix
2. Make your changes with clear, descriptive commit messages
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request with a clear description of the changes

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Steps to reproduce the issue
- Expected vs actual behavior
- Relevant logs or error messages

## Feature Requests

Feature requests are welcome! Please open an issue describing:
- The use case for the feature
- How it would improve the project
- Any implementation suggestions

See [TODO.md](TODO.md) for a list of planned features and future improvements.

## Code of Conduct

Be respectful and constructive in all interactions. We aim to maintain a welcoming and inclusive community.
