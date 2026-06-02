.PHONY: install test example clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --cov=agentix

example:
	python examples/simple_workflow.py

clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ .pytest_cache/
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete
