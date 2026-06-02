# Contributing to Agentix

Thank you for your interest in contributing! Here's how you can help.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ivanjay233/agentix.git
   cd agentix
   ```

2. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
make test        # full test suite with coverage
make test-quick  # quick run without coverage
```

## Code Style

This project uses `ruff` for linting and formatting:

```bash
make lint    # check for issues
make format  # auto-fix issues
```

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Run tests and ensure they pass
4. Submit a pull request describing your changes

## Commit Messages

Follow conventional commits format:
- `feat:` new features
- `fix:` bug fixes
- `refactor:` code restructuring
- `test:` adding tests
- `docs:` documentation changes
- `ci:` CI/CD changes
- `chore:` maintenance tasks
