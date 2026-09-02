from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from Caso_Pipeline.scripts._pipeline_common import (
    BASE as CANONICAL_CASE,
    REFERENCE_AERMOD_TITLE,
    REFERENCE_CONFIG,
    REFERENCE_RLINE_METEOROLOGY_PATH,
)
from rline_pipeline import PipelineValidationError, calculate_metrics, load_case_results
from rline_pipeline.plotting import (
    plot_cases_summary,
    render_comparison_plot,
    render_concentration_plot,
)
from scripts.teste_casos import main as validation_main

EXPECTED = {
    "caso1_referencia": {
        "receptors": 806,
        "r2": 0.9584248202,
        "segment": 0.9584248202,
        "max_aermod": 48966.60398,
        "max_rline": 154045.225,
        "mean_aermod": 2116.61685825062,
        "mean_rline": 5975.720678167184,
    },
    "caso2_rodovia_curta": {
        "receptors": 441,
        "r2": 0.6788,
        "segment": 0.9790,
        "max_aermod": 48378.5627,
        "max_rline": 150076.9175,
        "mean_aermod": 1140.7284508616779,
        "mean_rline": 3251.6906545564066,
    },
    "caso3_emissao_alta": {
        "receptors": 441,
        "r2": 0.9638,
        "segment": 0.9638,
        "max_aermod": 244833.01988,
        "max_rline": 770226.2166666667,
        "mean_aermod": 15316.642427006802,
        "mean_rline": 42898.46228337491,
    },
    "caso4_rodovia_larga": {
        "receptors": 441,
        "r2": 0.9551,
        "segment": 0.9551,
        "max_aermod": 90142.03895,
        "max_rline": 256727.5925,
        "mean_aermod": 6119.981375442177,
        "mean_rline": 14875.677936936885,
    },
}


def test_canonical_historical_results_satisfy_current_contract(tmp_path: Path) -> None:
    case_dir = tmp_path / "Caso_Pipeline"
    shutil.copytree(CANONICAL_CASE, case_dir)
    shutil.copy2(case_dir / "dados_aermet" / "ONSITE.SFC", case_dir / "rodada_rline")

    config, aermod, rline, period, merged = load_case_results(
        case_dir,
        config=REFERENCE_CONFIG,
        expected_aermod_title=REFERENCE_AERMOD_TITLE,
        expected_rline_meteorology_path=REFERENCE_RLINE_METEOROLOGY_PATH,
    )

    assert config.numero_receptores == 806
    assert len(aermod) == len(period) == len(merged) == 806
    assert len(rline) == 806 * 120


def test_every_versioned_case_is_complete(
    case_paths: dict[str, Path], real_results: dict[str, tuple]
) -> None:
    assert set(case_paths) == set(EXPECTED)

    for name, result in real_results.items():
        config, aermod, rline, period, merged = result
        expected = EXPECTED[name]
        period_counts = rline.groupby(["X", "Y"]).size()
        metrics = calculate_metrics(merged, config)

        assert config.periodos_esperados == 120
        assert len(aermod) == expected["receptors"]
        assert len(period) == expected["receptors"]
        assert len(merged) == expected["receptors"]
        assert len(rline) == expected["receptors"] * 120
        assert period_counts.min() == period_counts.max() == 120
        assert metrics["correlacao_log"] > 0
        assert metrics["correlacao_log_trecho"] > 0
        assert metrics["r2_global"] == pytest.approx(expected["r2"], abs=5e-4)
        assert metrics["r2_trecho"] == pytest.approx(expected["segment"], abs=5e-4)
        assert metrics["max_aermod"] == pytest.approx(expected["max_aermod"], rel=1e-10)
        assert metrics["max_rline"] == pytest.approx(expected["max_rline"], rel=1e-10)
        assert metrics["media_aermod"] == pytest.approx(expected["mean_aermod"], rel=1e-10)
        assert metrics["media_rline"] == pytest.approx(expected["mean_rline"], rel=1e-10)


def test_validation_cli_reports_all_configured_cases(
    case_paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = validation_main(["--casos-dir", str(next(iter(case_paths.values())).parent)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Casos reportados: 4/4" in output
    for name in case_paths:
        assert f"=== {name} ===" in output
    assert "T8 INFO picos/zeros" in output
    assert "INTERCOMPARACAO REPORTADA SEM GATE CIENTIFICO" in output


def test_real_plots_are_written_only_to_tmp(tmp_path: Path, real_results: dict[str, tuple]) -> None:
    config, aermod, _rline, _period, merged = real_results["caso2_rodovia_curta"]
    concentration = render_concentration_plot(
        aermod, merged, config, tmp_path / "concentration.png"
    )
    comparison = render_comparison_plot(merged, config, tmp_path / "comparison.png")

    assert concentration.stat().st_size > 0
    assert comparison.stat().st_size > 0


def test_summary_uses_all_cases_and_real_segment_r2(
    tmp_path: Path, case_paths: dict[str, Path]
) -> None:
    output = tmp_path / "summary.png"
    records = plot_cases_summary(case_paths.values(), output)

    assert output.stat().st_size > 0
    assert len(records) == len(EXPECTED)
    for record in records:
        config = record["config"]
        metrics = record["metrics"]
        assert metrics["r2_trecho"] == pytest.approx(EXPECTED[config.nome]["segment"], abs=5e-4)


def test_incomplete_case_fails_before_writing_outputs(
    tmp_path: Path, case_paths: dict[str, Path]
) -> None:
    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    source_config = case_paths["caso1_referencia"] / "config.json"
    (incomplete / "config.json").write_bytes(source_config.read_bytes())

    with pytest.raises(PipelineValidationError, match="log AERMOD nao encontrado"):
        load_case_results(incomplete)
    assert list(incomplete.iterdir()) == [incomplete / "config.json"]
