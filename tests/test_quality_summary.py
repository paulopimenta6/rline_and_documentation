from __future__ import annotations

import json
from pathlib import Path

from scripts.gerar_resumo_qualidade import build_quality_summary, write_quality_summary

ROOT = Path(__file__).resolve().parents[1]


def test_quality_summary_reports_all_verified_baselines(tmp_path: Path) -> None:
    summary = build_quality_summary(ROOT / "casos")
    output = tmp_path / "quality-summary.json"
    write_quality_summary(summary, output)
    loaded = json.loads(output.read_text(encoding="utf-8"))

    assert loaded["structural_status"] == "pass"
    assert loaded["indicators"]["cases_total"] == 4
    assert loaded["indicators"]["structural_pass_rate"] == 1.0
    assert loaded["indicators"]["manifest_completeness_rate"] == 1.0
    assert all(record["gate"] is False for record in loaded["cases"])
    assert all(record["metrics"]["fac2"] is not None for record in loaded["cases"])
