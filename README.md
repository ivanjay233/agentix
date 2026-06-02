# agentix

> **Three agents. One board. Nobody waiting on a human.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![CI](https://github.com/ivanjay233/agentix/actions/workflows/ci.yml/badge.svg)](https://github.com/ivanjay233/agentix/actions)
[![PyPI](https://img.shields.io/badge/pypi-v0.1.0-orange?style=flat-square)](https://pypi.org/project/agentix/)

agentix is a **Python framework for multi-agent workflow orchestration** inspired by Kanban boards. Define pipelines as directed stages, each handled by a specialised agent, and watch tasks flow from *todo* → *in_progress* → *review* → *done* — automatically.

---

## Quick Start

```bash
pip install agentix

# Create a pipeline definition
agentix init my_pipeline

# Run it
agentix run my_pipeline --inputs '{"topic": "hello world"}'

# Inspect the board
agentix board my_pipeline
```

### Programmatic usage

```python
import asyncio
from agentix import OrchestratorEngine

engine = OrchestratorEngine()

engine.create_pipeline(
    name="content_gen",
    stages=[
        {"name": "write",   "agent_type": "codex", "input_keys": ["topic"], "output_keys": ["draft"]},
        {"name": "review",  "agent_type": "review","input_keys": ["draft"],"output_keys": ["report"]},
        {"name": "format",  "agent_type": "codex", "input_keys": ["draft","report"], "output_keys": ["final"]},
    ],
)

result = asyncio.run(engine.run("content_gen", inputs={"topic": "hello world"}))
print(result["final"])
```

---

## Architecture

agentix is built on three layers:

```
┌─────────────────────────────────────────────────┐
│                    Pipeline                       │
│  (stages with dependencies, serialised as YAML)   │
├─────────────────────────────────────────────────┤
│                  Kanban Board                     │
│  todo → in_progress → review → done               │
├─────────────────────────────────────────────────┤
│                    Agents                          │
│  BaseAgent → CodexAgent, ReviewAgent, ...         │
└─────────────────────────────────────────────────┘
```

| Layer | Role |
|---|---|
| **Pipeline** | Defines *what* happens — a directed graph of stages, each with typed inputs and outputs |
| **Kanban Board** | Tracks *where* things are — tasks move through four columns automatically |
| **Agents** | Do the *work* — pluggable modules that consume and produce artifacts |

### Built-in agents

| Agent | CLI | Purpose |
|---|---|---|
| `CodexAgent` | `codex` (optional) | Generates code from a prompt |
| `ReviewAgent` | — | Validates syntax, checks anti-patterns, scores quality |

Extend with custom agents by subclassing `BaseAgent`:

```python
from agentix.agents.base import BaseAgent

class MyAgent(BaseAgent):
    async def process(self, task):
        # your logic here
        return {"result": "done"}
```

---

## Installation

```bash
# From PyPI (once published)
pip install agentix

# From source
git clone https://github.com/ivanjay233/agentix.git
cd agentix
make install
```

### Dependencies

- `pyyaml` — pipeline serialisation
- `httpx` — HTTP client for API-based agents
- `click` — CLI interface
- `rich` — beautiful terminal output
- `pydantic` — data validation (coming in future releases)

---

## CLI Reference

```text
Usage: agentix [OPTIONS] COMMAND [ARGS]...

  agentix — Three agents. One board. Nobody waiting on a human.

Commands:
  init       Initialise a new pipeline and board.
  run        Execute a pipeline.
  board      Display the Kanban board for a pipeline.
  status     Show pipeline execution status.
  pipelines  List all registered pipelines.
```

---

## Use Cases

- **Content generation pipelines** — write → review → format
- **Code refactoring workflows** — analyse → plan → refactor → test
- **Data processing ETLs** — extract → validate → transform → load
- **Research paper summaries** — fetch → summarise → fact-check → format
- **Multi-agent chat workflows** — delegate sub-tasks to specialised agents

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding guidelines, and the pull-request process.

---

## License

MIT — see [LICENSE](LICENSE) for details.
