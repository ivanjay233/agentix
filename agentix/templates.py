"""Pipeline config presets and templates for common workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Preset pipeline configurations
# ---------------------------------------------------------------------------

PRESETS: Dict[str, Dict[str, Any]] = {
    "code-review": {
        "name": "code-review",
        "description": "Automated code review pipeline with linting and analysis",
        "stages": [
            {
                "name": "lint",
                "agent_type": "review_agent",
                "input_keys": ["source_code"],
                "output_keys": ["lint_results"],
                "depends_on": [],
            },
            {
                "name": "analyze",
                "agent_type": "review_agent",
                "input_keys": ["source_code"],
                "output_keys": ["analysis"],
                "depends_on": [],
            },
            {
                "name": "report",
                "agent_type": "codex",
                "input_keys": ["lint_results", "analysis"],
                "output_keys": ["final_report"],
                "depends_on": ["lint", "analyze"],
            },
        ],
    },
    "data-pipeline": {
        "name": "data-pipeline",
        "description": "ETL data processing workflow",
        "stages": [
            {
                "name": "extract",
                "agent_type": "pass-through",
                "input_keys": ["source"],
                "output_keys": ["raw_data"],
                "depends_on": [],
            },
            {
                "name": "validate",
                "agent_type": "review_agent",
                "input_keys": ["raw_data"],
                "output_keys": ["validation"],
                "depends_on": ["extract"],
            },
            {
                "name": "transform",
                "agent_type": "codex",
                "input_keys": ["raw_data"],
                "output_keys": ["transformed"],
                "depends_on": ["validate"],
            },
            {
                "name": "load",
                "agent_type": "pass-through",
                "input_keys": ["transformed"],
                "output_keys": ["result"],
                "depends_on": ["transform"],
            },
        ],
    },
    "ci-cd": {
        "name": "ci-cd",
        "description": "CI/CD pipeline with test and deploy stages",
        "stages": [
            {
                "name": "build",
                "agent_type": "codex",
                "input_keys": ["source"],
                "output_keys": ["build_artifact"],
                "depends_on": [],
            },
            {
                "name": "test",
                "agent_type": "review_agent",
                "input_keys": ["build_artifact"],
                "output_keys": ["test_results"],
                "depends_on": ["build"],
            },
            {
                "name": "package",
                "agent_type": "pass-through",
                "input_keys": ["build_artifact"],
                "output_keys": ["package"],
                "depends_on": ["test"],
            },
            {
                "name": "deploy",
                "agent_type": "pass-through",
                "input_keys": ["package"],
                "output_keys": ["deployment"],
                "depends_on": ["package"],
            },
        ],
    },
    "content-generation": {
        "name": "content-generation",
        "description": "Multi-stage content generation with review",
        "stages": [
            {
                "name": "research",
                "agent_type": "codex",
                "input_keys": ["topic"],
                "output_keys": ["research_notes"],
                "depends_on": [],
            },
            {
                "name": "draft",
                "agent_type": "codex",
                "input_keys": ["research_notes", "topic"],
                "output_keys": ["draft_content"],
                "depends_on": ["research"],
            },
            {
                "name": "review",
                "agent_type": "review_agent",
                "input_keys": ["draft_content"],
                "output_keys": ["review_feedback"],
                "depends_on": ["draft"],
            },
            {
                "name": "finalize",
                "agent_type": "codex",
                "input_keys": ["draft_content", "review_feedback"],
                "output_keys": ["final_content"],
                "depends_on": ["review"],
            },
        ],
    },
    "simple": {
        "name": "simple",
        "description": "Two-stage pipeline for quick testing",
        "stages": [
            {
                "name": "process",
                "agent_type": "codex",
                "input_keys": ["input_data"],
                "output_keys": ["processed"],
                "depends_on": [],
            },
            {
                "name": "output",
                "agent_type": "pass-through",
                "input_keys": ["processed"],
                "output_keys": ["result"],
                "depends_on": ["process"],
            },
        ],
    },
}


def list_presets() -> List[str]:
    """Return names of all available presets.

    Returns
    -------
    list of str
        Sorted preset names.
    """
    return sorted(PRESETS.keys())


def get_preset(name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a preset configuration by name.

    Parameters
    ----------
    name : str
        Name of the preset.

    Returns
    -------
    dict or None
        The preset config, or None if not found.
    """
    return PRESETS.get(name)


def get_preset_description(name: str) -> Optional[str]:
    """Return the description of a preset.

    Parameters
    ----------
    name : str
        Preset name.

    Returns
    -------
    str or None
        Description string.
    """
    preset = PRESETS.get(name)
    return preset.get("description") if preset else None


def render_preset_yaml(name: str) -> Optional[str]:
    """Render a preset as a YAML string.

    Parameters
    ----------
    name : str
        Preset name.

    Returns
    -------
    str or None
        YAML representation.
    """
    import yaml

    preset = PRESETS.get(name)
    if preset is None:
        return None
    data = {"name": preset["name"], "stages": preset["stages"]}
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
