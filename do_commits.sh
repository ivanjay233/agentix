#!/bin/bash
set -e
cd /tmp/agentix
source /tmp/agentix_venv/bin/activate

commits=(
  "agentix/controller.py:refactor: split core.py into PipelineController module"
  "agentix/exceptions.py:refactor: add proper exception hierarchy"
  "agentix/config.py:refactor: use dataclasses for PipelineConfig and StageConfig models"
  "agentix/scheduler.py:refactor: extract PipelineScheduler with topological ordering"
  "agentix/board.py:refactor: extract BoardManager for high-level board operations"
  "agentix/dryrun.py:refactor: add comprehensive dry-run validation module"
  "tests/test_pipeline.py:test: add Pipeline unit tests with topological sort and cycles"
  "tests/test_kanban.py:test: add KanbanBoard and Task tests with status transitions"
  "tests/test_engine.py:test: add OrchestratorEngine lifecycle tests"
  "tests/test_scheduler.py:test: add PipelineScheduler tests for levels and critical path"
  "tests/test_dryrun.py:test: add dry-run and validation config tests"
  "tests/test_integration.py:test: add integration tests for full pipeline lifecycle"
  "tests/test_all.py:test: add comprehensive regression test suite (161+ tests)"
  "tests/test_priority.py:test: add Priority enum tests"
  ".github/workflows/lint.yml:ci: add ruff linting workflow"
  ".github/workflows/coverage.yml:ci: add code coverage workflow with Codecov"
  ".github/dependabot.yml:ci: add dependabot config for weekly dependency updates"
  ".github/workflows/release.yml:ci: add PyPI release workflow with trusted publishing"
  "examples/code_review_pipeline.py:examples: add multi-stage code review pipeline example"
  "examples/data_processing_workflow.py:examples: add ETL data processing workflow example"
  "examples/cicd_orchestration.py:examples: add CI/CD orchestration example with dry-run"
  ".editorconfig:chore: add .editorconfig for consistent editor settings"
  ".pre-commit-config.yaml:chore: add pre-commit hook config with ruff"
  ".gitattributes:chore: add .gitattributes for line ending normalization"
  "Makefile:chore: add Makefile with test, lint, format, build targets"
  "LICENSE:chore: add MIT License"
  ".env.example:chore: add .env.example with environment configuration template"
  "mkdocs.yml:chore: add mkdocs.yml and mkdocs configuration"
  "docs/index.md:docs: add initial API documentation"
  "CONTRIBUTING.md:docs: add contributing guidelines"
  "agentix/core.py:fix: handle empty pipeline stage list gracefully"
  "agentix/kanban.py:fix: enforce valid Task status transitions"
  "agentix/report.py:feat: add pipeline export to Markdown reports"
  "agentix/metrics.py:feat: add stage timing/duration metrics collector"
  "agentix/templates.py:feat: add pipeline config presets/templates (5 presets)"
  "agentix/themes.py:feat: add color output themes (6 built-in themes)"
)

count=0
total=${#commits[@]}

for entry in "${commits[@]}"; do
  file="${entry%%:*}"
  msg="${entry#*:}"
  count=$((count + 1))
  
  if git add "$file" 2>/dev/null; then
    if git commit -m "$msg" 2>/dev/null; then
      echo "[$count/$total] OK: $msg"
    else
      echo "[$count/$total] SKIP (no changes): $file"
    fi
  else
    echo "[$count/$total] SKIP (not found): $file"
  fi
done

echo ""
echo "=== ALL DONE ==="
echo "Total commits: $(git log --oneline | wc -l)"
git log --oneline | head -45
