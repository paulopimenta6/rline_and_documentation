from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from rline_pipeline.example_data import generate_onsite_text
from scripts.gerar_dados_exemplo import create_example_bundle


def test_meteorology_is_deterministic_and_scenario_specific() -> None:
    first, first_qa = generate_onsite_text("smoke-crosswind", seed=17)
    second, second_qa = generate_onsite_text("smoke-crosswind", seed=17)
    parallel, parallel_qa = generate_onsite_text("smoke-near-parallel", seed=17)

    assert first == second
    assert first_qa == second_qa
    assert first != parallel
    assert first_qa["periods"] == parallel_qa["periods"] == 24
    assert len(first.splitlines()) == 24 * 3
    assert first_qa["synthetic"] is True


def test_legacy_generator_has_no_import_side_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.rglob("*"))
    module = importlib.import_module("Caso_Pipeline.scripts.gerar_dados_onsite")
    importlib.reload(module)
    assert set(tmp_path.rglob("*")) == before


def test_safe_bundle_has_small_grid_controls_qa_and_manifest(tmp_path: Path) -> None:
    output = Path("build/examples") / f"pytest-{tmp_path.name}"
    destination = create_example_bundle(
        scenario_name="smoke-crosswind",
        seed=42,
        name=f"pytest-{tmp_path.name}",
        output=output,
    )
    try:
        config = json.loads((destination / "case/config.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (destination / "example-manifest.json").read_text(encoding="utf-8")
        )
        qa = json.loads(
            (destination / "meteorology/synthetic-data-qa.json").read_text(encoding="utf-8")
        )

        assert config["grid"]["xn"] == config["grid"]["yn"] == 5
        assert config["periodos_esperados"] == 24
        assert manifest["generator"] == "rline-safe-example-v1"
        assert manifest["evidence_class"] == "software-regression"
        assert qa["synthetic"] is True
        assert "1988/3/1 TO 1988/3/1" in (
            destination / "meteorology/ONSITE_S1.INP"
        ).read_text(encoding="utf-8")

        with pytest.raises(ValueError, match="ja existe"):
            create_example_bundle(
                scenario_name="smoke-crosswind",
                seed=42,
                name=f"pytest-{tmp_path.name}",
                output=output,
            )
        create_example_bundle(
            scenario_name="smoke-crosswind",
            seed=42,
            name=f"pytest-{tmp_path.name}",
            output=output,
            replace_generated=True,
        )
        (destination / "EXECUCAO.md").write_text("alterado\n", encoding="utf-8")
        with pytest.raises(ValueError, match="arquivo foi alterado"):
            create_example_bundle(
                scenario_name="smoke-crosswind",
                seed=42,
                name=f"pytest-{tmp_path.name}",
                output=output,
                replace_generated=True,
            )
    finally:
        import shutil

        shutil.rmtree(destination, ignore_errors=True)


def test_safe_bundle_rejects_destinations_outside_build() -> None:
    with pytest.raises(ValueError, match="build/examples"):
        create_example_bundle(
            scenario_name="smoke-crosswind",
            seed=42,
            name="unsafe",
            output=Path("outside-example"),
        )


def test_unknown_scenario_is_rejected() -> None:
    with pytest.raises(ValueError, match="cenario desconhecido"):
        generate_onsite_text("not-a-scenario")
