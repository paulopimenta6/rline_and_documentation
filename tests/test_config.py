from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from rline_pipeline import ConfigValidationError, load_case_config
from rline_pipeline.generation import generate_case, validate_generated_case_inputs

from Caso_Pipeline.scripts._pipeline_common import (
    BASE as CANONICAL_CASE,
    REFERENCE_AERMOD_TITLE,
    REFERENCE_CONFIG,
    REFERENCE_RLINE_METEOROLOGY_PATH,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "casos" / "caso1_referencia" / "config.json"


def _base_data() -> dict:
    return json.loads(BASE_CONFIG.read_text(encoding="utf-8"))


def _set_nested(data: dict, path: tuple[str, ...], value: object) -> None:
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def test_loads_versioned_config_and_decimal_grid() -> None:
    config = load_case_config(BASE_CONFIG)

    assert config.schema_version == 1
    assert config.numero_receptores == 806
    assert config.periodos_esperados == 120
    assert config.emissao_rline == pytest.approx(0.02)


def test_canonical_inputs_match_their_declared_historical_layout() -> None:
    validate_generated_case_inputs(
        CANONICAL_CASE,
        REFERENCE_CONFIG,
        aermod_title=REFERENCE_AERMOD_TITLE,
        rline_meteorology_path=REFERENCE_RLINE_METEOROLOGY_PATH,
    )


@pytest.mark.parametrize(
    ("field_path", "value", "message"),
    [
        (("schema_version",), 1.0, "schema_version"),
        (("comprimento",), 0.0, "comprimento"),
        (("qs",), -0.001, "qs"),
        (("width",), 0.0, "width"),
        (("grid", "xn"), 0, "xn"),
        (("grid", "xdelta"), 0.0, "xdelta"),
        (("grid", "ydelta"), math.inf, "finita"),
        (("transecto_x",), 1200.0, "transecto_x"),
        (("y_rodovia",), 1000.0, "y_rodovia"),
        (("emis_fator",), -1.0, "emis_fator"),
        (("periodos_esperados",), 0, "periodos_esperados"),
    ],
)
def test_rejects_invalid_config(
    tmp_path: Path,
    field_path: tuple[str, ...],
    value: object,
    message: str,
) -> None:
    data = _base_data()
    _set_nested(data, field_path, value)

    with pytest.raises(ConfigValidationError, match=message):
        load_case_config(_write_config(tmp_path, data))


def test_rejects_missing_and_unknown_fields(tmp_path: Path) -> None:
    missing = _base_data()
    del missing["width"]
    with pytest.raises(ConfigValidationError, match="width"):
        load_case_config(_write_config(tmp_path, missing))

    unknown = _base_data()
    unknown["campo_desconhecido"] = 1
    with pytest.raises(ConfigValidationError, match="campo_desconhecido"):
        load_case_config(_write_config(tmp_path, unknown))


def test_generation_is_deterministic_and_does_not_round_coordinates(tmp_path: Path) -> None:
    data = _base_data()
    data.update(
        {
            "nome": "decimal_exato",
            "comprimento": 0.5,
            "y_rodovia": 0.0,
            "transecto_x": 0.3,
            "grid": {
                "xini": 0.1,
                "xn": 3,
                "xdelta": 0.2,
                "yini": -0.1,
                "yn": 3,
                "ydelta": 0.1,
            },
        }
    )
    config_path = _write_config(tmp_path, data)
    output = tmp_path / "generated"

    generate_case(config_path, output_dir=output)
    expected_files = [
        output / "controles_aermod" / "RLINE_TEST.INP",
        output / "rodada_rline" / "Receptor_Road.txt",
        output / "rodada_rline" / "Source_Road.txt",
        output / "rodada_rline" / "Line_Source_Inputs.txt",
        output / "metadados.txt",
    ]
    first_contents = {path.relative_to(output): path.read_bytes() for path in expected_files}

    generate_case(config_path, output_dir=output)
    second_contents = {path.relative_to(output): path.read_bytes() for path in expected_files}

    assert second_contents == first_contents
    receptors = (output / "rodada_rline" / "Receptor_Road.txt").read_text(encoding="utf-8")
    assert "  0.3 0.0 0.0\n" in receptors
    assert "0.30000000000000004" not in receptors


@pytest.mark.parametrize(
    ("grid_updates", "message"),
    [
        ({"xn": 1}, "xn"),
        ({"xini": 1.0e16, "xdelta": 1.0}, "perdem unicidade"),
        ({"xn": 3, "xdelta": 1.0e308}, "extensao X.*finita"),
        ({"xn": 1001, "yn": 1000}, "limite operacional"),
    ],
)
def test_rejects_grids_that_cannot_be_represented_safely(
    tmp_path: Path, grid_updates: dict[str, float | int], message: str
) -> None:
    data = _base_data()
    data["grid"].update(grid_updates)

    with pytest.raises(ConfigValidationError, match=message):
        load_case_config(_write_config(tmp_path, data))


def test_changed_inputs_invalidate_derived_results(tmp_path: Path) -> None:
    data = _base_data()
    config_path = _write_config(tmp_path, data)
    case_dir = tmp_path / "case"
    generate_case(config_path, output_dir=case_dir)

    derived = (
        case_dir / "rodada_aermod" / "CONC_PLOT.PLT",
        case_dir / "rodada_rline" / "Output_Road_Numerical.csv",
        case_dir / "graficos" / "conc_periodo_rline.png",
        case_dir / "resumo.txt",
    )
    for path in derived:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("old result\n", encoding="utf-8")

    generate_case(config_path, output_dir=case_dir)
    assert all(path.exists() for path in derived)

    data["qs"] *= 2
    config_path.write_text(json.dumps(data), encoding="utf-8")
    generate_case(config_path, output_dir=case_dir)

    assert all(not path.exists() for path in derived)
