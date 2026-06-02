"""Schema-based validation for pipeline YAML configurations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


STAGE_SCHEMA = {
    "name": {"type": str, "required": True},
    "agent_type": {"type": str, "required": True},
    "input_keys": {"type": list, "required": False, "default": []},
    "output_keys": {"type": list, "required": False, "default": []},
    "depends_on": {"type": list, "required": False, "default": []},
}


def validate_pipeline_config(data: Dict[str, Any]) -> List[str]:
    """Validate a pipeline configuration dict against the schema.

    Parameters
    ----------
    data : dict
        Parsed pipeline configuration (from YAML or JSON).

    Returns
    -------
    list of str
        List of validation error messages (empty if valid).

    Examples
    --------
    >>> errors = validate_pipeline_config({"name": "test", "stages": [{"name": "s1", "agent_type": "codex"}]})
    >>> errors
    []
    >>> errors = validate_pipeline_config({"stages": [{}]})
    >>> len(errors) > 0
    True
    """
    errors: List[str] = []

    if not isinstance(data, dict):
        errors.append("Root must be a dictionary/mapping.")
        return errors

    # Validate name
    if "name" not in data:
        errors.append("Missing required field: 'name' (pipeline name).")
    elif not isinstance(data["name"], str):
        errors.append("'name' must be a string.")

    # Validate stages
    stages = data.get("stages", [])

    if not isinstance(stages, list):
        errors.append("'stages' must be a list.")
        return errors

    if not stages:
        errors.append("Pipeline must have at least one stage.")

    stage_names: set = set()
    for i, stage in enumerate(stages):
        stage_errors = _validate_stage(stage, i)
        errors.extend(stage_errors)

        if isinstance(stage, dict) and "name" in stage:
            if stage["name"] in stage_names:
                errors.append(f"Stage {i}: duplicate stage name '{stage['name']}'.")
            stage_names.add(stage["name"])

    # Validate dependency references
    if isinstance(stages, list):
        for i, stage in enumerate(stages):
            if not isinstance(stage, dict):
                continue
            for dep in stage.get("depends_on", []):
                if dep not in stage_names:
                    errors.append(f"Stage {i} ('{stage.get('name', '?')}'): depends_on '{dep}' not found.")

    return errors


def _validate_stage(stage: Any, index: int) -> List[str]:
    """Validate a single stage definition."""
    errors: List[str] = []

    if not isinstance(stage, dict):
        errors.append(f"Stage {index}: must be a dictionary/mapping.")
        return errors

    for field_name, rules in STAGE_SCHEMA.items():
        value = stage.get(field_name)

        if rules["required"] and value is None:
            errors.append(f"Stage {index}: missing required field '{field_name}'.")
            continue

        if value is not None and not isinstance(value, rules["type"]):
            errors.append(
                f"Stage {index} ('{stage.get('name', '?')}'): "
                f"'{field_name}' must be of type {rules['type'].__name__}, "
                f"got {type(value).__name__}."
            )

    return errors
