from __future__ import annotations

import json
from pathlib import Path

import pytest

from rline_pipeline import PipelineValidationError, classify_evidence, load_case_results
from rline_pipeline.provenance import sha256_file, verify_baseline_manifest

ROOT = Path(__file__).resolve().parents[1]


def _write_manifest_root(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "Caso_Pipeline").mkdir()
    shared = tmp_path / "Caso_Pipeline/met.sfc"
    shared.write_text("shared\n", encoding="utf-8")
    case = tmp_path / "casos/example"
    case.mkdir(parents=True)
    output = case / "result.txt"
    output.write_text("result\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "evidence_class": "legacy-baseline",
        "files": {"result.txt": sha256_file(output)},
        "shared_inputs": {
            "meteorology_sfc": {
                "path": "Caso_Pipeline/met.sfc",
                "sha256": sha256_file(shared),
            }
        },
    }
    (case / "baseline-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return case, output


def test_baseline_manifest_detects_tampering(tmp_path: Path) -> None:
    case, output = _write_manifest_root(tmp_path)
    assert verify_baseline_manifest(case)["meteorology_sfc"].name == "met.sfc"

    output.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(PipelineValidationError, match="hash da baseline diverge"):
        verify_baseline_manifest(case)


def test_baseline_manifest_rejects_path_escape(tmp_path: Path) -> None:
    case, _output = _write_manifest_root(tmp_path)
    manifest_path = case / "baseline-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = {"../outside.txt": "0" * 64}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(PipelineValidationError, match="escapa da raiz"):
        verify_baseline_manifest(case)


def test_evidence_policy_keeps_cross_model_results_descriptive() -> None:
    classes = classify_evidence()
    assert classes == {
        "software_regression": "gate",
        "model_intercomparison": "descriptive",
        "field_validation": "descriptive",
    }


def test_case_loader_rejects_unknown_evidence_mode() -> None:
    with pytest.raises(PipelineValidationError, match="evidence_mode"):
        load_case_results(ROOT / "casos/caso1_referencia", evidence_mode="implicit")
