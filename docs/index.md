# Agentix

**Three agents. One board. Nobody waiting on a human.**

Agentix is a Python framework for multi-agent workflow orchestration using
Kanban boards. It provides a clean, async-native API for defining pipelines
with dependency graphs, tracking progress with visual boards, and executing
stages through pluggable agents.

## Features

- **Pipeline orchestration** — define stages with dependencies, topological execution
- **Kanban boards** — track task progress across todo/in_progress/review/done columns
- **Pluggable agents** — BaseAgent abstraction with CodexAgent and ReviewAgent built-in
- **YAML/JSON import/export** — serialize and share pipeline definitions
- **CLI interface** — manage pipelines from the command line
- **Concurrent execution** — run independent stages in parallel
- **Dry-run validation** — validate pipelines without executing them
- **Templates** — pre-built pipeline configurations for common workflows
- **Metrics** — stage timing and performance tracking
- **Reports** — generate Markdown pipeline summaries
