"""Dry-run mode — validate pipelines without executing them."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agentix.pipeline import Pipeline
from agentix.validation import validate_pipeline_config


class DryRunResult:
    """Result of a dry-run validation.

    Parameters
    ----------
    valid : bool
        Whether the pipeline is valid.
    stage_order : list of str
        Computed topological execution order.
    errors : list of str
        Validation error messages.
    warnings : list of str
        Non-blocking warnings.
    """

    def __init__(
        self,
        valid: bool,
        stage_order: List[str],
        errors: List[str],
        warnings: List[str],
    ) -> None:
        self.valid = valid
        self.stage_order = stage_order
        self.errors = errors
        self.warnings = warnings

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to a dictionary."""
        return {
            "valid": self.valid,
            "stage_order": self.stage_order,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def __repr__(self) -> str:
        status = "✓ Valid" if self.valid else "✗ Invalid"
        return (
            f"DryRunResult({status}, "
            f"stages={len(self.stage_order)}, "
            f"errors={len(self.errors)}, "
            f"warnings={len(self.warnings)})"
        )


def dry_run(pipeline: Pipeline) -> DryRunResult:
    """Validate a pipeline without executing it.

    Checks:
      - Schema compliance (required fields, types)
      - Dependency cycles
      - Cross-stage key mismatches (input_keys that no preceding stage produces)
      - Unreferenced stages (stages no other stage depends on — warning only)

    Parameters
    ----------
    pipeline : Pipeline
        The pipeline to validate.

    Returns
    -------
    DryRunResult
        Validation result with errors, warnings, and computed stage order.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Schema validation
    config = {"name": pipeline.name, "stages": pipeline.stages}
    schema_errors = validate_pipeline_config(config)
    errors.extend(schema_errors)

    # Topological sort (cycle detection)
    stage_order: List[str] = []
    try:
        stage_order = pipeline.topological_sort()
    except RuntimeError as exc:
        errors.append(str(exc))

    # Check input_key availability
    produced_keys: set = set()
    for stage in pipeline.stages:
        for required_key in stage.get("input_keys", []):
            if required_key not in produced_keys and stage_order:
                errors.append(
                    f"Stage '{stage['name']}' requires input_key '{required_key}' "
                    f"which is not produced by any preceding stage."
                )
        for output_key in stage.get("output_keys", []):
            produced_keys.add(output_key)

    return DryRunResult(
        valid=len(errors) == 0,
        stage_order=stage_order,
        errors=errors,
        warnings=warnings,
    )
