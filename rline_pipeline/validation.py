"""Evidence classification and versioned validation-policy loading."""

from __future__ import annotations

from importlib.resources import files
import json
from typing import Any, Mapping

from .errors import PipelineValidationError

VALIDATION_POLICY_VERSION = 1
VALIDATION_POLICY_FILENAME = "validation-policy-v1.json"


def load_validation_policy() -> Mapping[str, Any]:
    """Load and minimally validate the policy bundled with the package."""

    resource = files("rline_pipeline.policies").joinpath(VALIDATION_POLICY_FILENAME)
    try:
        with resource.open("r", encoding="utf-8") as stream:
            policy = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineValidationError(f"falha ao carregar politica de validacao: {error}") from error
    if policy.get("schema_version") != VALIDATION_POLICY_VERSION:
        raise PipelineValidationError("versao inesperada da politica de validacao")
    classes = policy.get("evidence_classes")
    expected = {"software_regression", "model_intercomparison", "field_validation"}
    if not isinstance(classes, dict) or set(classes) != expected:
        raise PipelineValidationError("classes de evidencia incompletas na politica de validacao")
    return policy


def classify_evidence() -> dict[str, str]:
    """Return the operational status of each evidence class."""

    policy = load_validation_policy()
    classes = policy["evidence_classes"]
    return {
        name: "gate" if definition["gate"] else "descriptive"
        for name, definition in classes.items()
    }
