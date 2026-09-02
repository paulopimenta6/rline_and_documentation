#!/usr/bin/env python3
"""Generate the machine-readable data contract for the quality dashboard."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    PipelineValidationError,
    calculate_metrics,
    load_case_results,
    load_validation_policy,
    verify_baseline_manifest,
)

DEFAULT_OUTPUT = ROOT / "build" / "reports" / "quality-summary.json"
SUMMARY_SCHEMA = ROOT / "rline_pipeline" / "schemas" / "quality-summary-v1.schema.json"


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def build_quality_summary(cases_dir: Path) -> dict[str, Any]:
    """Evaluate all configured baselines and return a serialisable summary."""

    case_dirs = sorted(path.parent for path in cases_dir.glob("*/config.json"))
    records: list[dict[str, Any]] = []
    valid_count = 0
    manifest_count = 0
    for case_dir in case_dirs:
        record: dict[str, Any] = {
            "name": case_dir.name,
            "evidence_class": "model_intercomparison",
            "gate": False,
            "structural_status": "fail",
            "baseline_status": "fail",
        }
        try:
            verify_baseline_manifest(case_dir)
        except PipelineValidationError as error:
            record["baseline_error"] = str(error)
        else:
            record["baseline_status"] = "pass"
            manifest_count += 1

        try:
            config, _aermod, _rline, _period, merged = load_case_results(case_dir)
            record["metrics"] = calculate_metrics(merged, config)
            record["receptors"] = config.numero_receptores
            record["periods"] = config.periodos_esperados
        except PipelineValidationError as error:
            record["structural_error"] = str(error)
        else:
            record["structural_status"] = "pass"
            valid_count += 1
        records.append(record)

    total = len(case_dirs)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "structural_status": (
            "pass" if total > 0 and valid_count == manifest_count == total else "fail"
        ),
        "policy": load_validation_policy(),
        "indicators": {
            "cases_total": total,
            "cases_structurally_valid": valid_count,
            "baselines_verified": manifest_count,
            "structural_pass_rate": _rate(valid_count, total),
            "manifest_completeness_rate": _rate(manifest_count, total),
            "python_line_coverage": None,
            "deterministic_run_rate": None,
            "golden_conformance_rate": None,
        },
        "cases": records,
        "limitations": [
            "Intercomparacoes entre modelos sao descritivas e nao sao gates de aceitacao.",
            "Indicadores nulos exigem artefatos externos da CI ou uma simulacao nova.",
            "Resultados historicos usam o RLINE standalone original; consulte o manifesto.",
        ],
    }
    schema = json.loads(SUMMARY_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(summary),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise PipelineValidationError(f"resumo de qualidade invalido: {errors[0].message}")
    return summary


def write_quality_summary(summary: dict[str, Any], output: Path) -> None:
    """Atomically publish a quality summary."""

    output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-dir", type=Path, default=ROOT / "casos")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = build_quality_summary(args.cases_dir)
        write_quality_summary(summary, args.output)
    except (OSError, PipelineValidationError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 2
    print(f"Resumo de qualidade: {args.output}")
    return 0 if summary["structural_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
