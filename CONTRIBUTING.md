# Contributing to agentix

Thank you for your interest in agentix! This document covers how to set up a development environment, run tests, and submit changes.

---

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Clone & Install

```bash
git clone https://github.com/ivanjay233/agentix.git
cd agentix
make install
```

This installs the package in editable mode with dev dependencies (pytest, etc.).

### Verify

```bash
make test
```

All tests should pass.

---

## Project Structure

```
agentix/
├── agentix/
│   ├── __init__.py          # Package exports
│   ├── core.py              # OrchestratorEngine
│   ├── pipeline.py          # Pipeline definition
│   ├── kanban.py            # KanbanBoard & Task
│   ├── cli.py               # Click CLI
│   └── agents/
│       ├── __init__.py
│       ├── base.py          # BaseAgent (abstract)
│       ├── codex_agent.py   # CodexAgent
│       └── review_agent.py  # ReviewAgent
├── examples/
│   ├── simple_workflow.py   # Content-gen pipeline demo
│   └── pipeline.yaml        # Example YAML
├── tests/
│   └── test_core.py         # Pytest suite
├── pyproject.toml
├── README.md
└── Makefile
```

---

## Running Tests

```bash
# Full test suite
make test

# With coverage
python -m pytest tests/ -v --cov=agentix --cov-report=term-missing

# Single test file
python -m pytest tests/test_core.py -v
```

---

## Coding Guidelines

- Follow **PEP 8**.
- Type-annotate all public functions and methods.
- Write docstrings for public APIs (NumPy or Google style).
- Keep functions short and focused — one responsibility per function.
- Use `async def` for agent processing methods.

### Testing

- Every public class and method should have tests.
- Use `pytest` and `pytest-asyncio`.
- Name test classes `Test<ClassName>` and test methods `test_<behaviour>`.

---

## Pull Request Process

1. Fork the repository and create a feature branch.
2. Make your changes with tests.
3. Run `make test` and ensure everything passes.
4. Update documentation if you're changing public APIs.
5. Open a pull request describing the change and any breaking changes.

---

## Release Process

Maintainers follow these steps:

1. Bump version in `pyproject.toml` and `agentix/__init__.py`.
2. Update `CHANGELOG.md`.
3. Tag the release: `git tag v<version> && git push --tags`.
4. Build and publish: `python -m build && twine upload dist/*`.

---

## Questions?

Open an issue on [GitHub](https://github.com/ivanjay233/agentix/issues) or start a discussion.
