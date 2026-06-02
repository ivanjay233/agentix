# Changelog

All notable changes to agentix are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-06-02

### Added

- **Core orchestration engine** — `OrchestratorEngine` manages pipeline lifecycle, pause/resume, and async execution.
- **Pipeline DSL** — Declarative stage definitions with typed inputs/outputs and dependency resolution via topological sort.
- **Kanban board** — Four-column board (`todo → in_progress → review → done`) with task CRUD operations.
- **Task model** — `Task` dataclass with status transitions, timestamps, and artifact storage.
- **Agent framework** — `BaseAgent` abstract class with `CodexAgent` and `ReviewAgent` implementations.
- **CLI** — Click-based command-line interface with `init`, `run`, `board`, `status`, `pipelines` commands.
- **YAML serialisation** — Pipelines can be imported/exported from/to YAML strings and files.
- **Dependency cycle detection** — Topological sort raises `RuntimeError` on cycle detection.
- **CI/CD** — GitHub Actions workflow for linting (ruff) and testing (pytest) across Python 3.10–3.12.
- **Documentation** — README with quick-start, architecture overview, and CLI reference; CONTRIBUTING.md for contributors.
- **Packaging** — PyPI-compatible `pyproject.toml` with dev extras.
# agentix v0.1.1
# agentix v0.1.2
# agentix v0.1.3
# agentix v0.1.4
# agentix v0.1.5
# agentix v0.1.6
# agentix v0.1.7
# agentix v0.1.8
# agentix v0.1.9
