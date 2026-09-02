from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from rline_pipeline import (
    PipelineValidationError,
    merge_one_to_one,
    parse_aermod,
    parse_rline,
    validate_aermod_completion,
    validate_rline_output,
)
from rline_pipeline.plotting import concentration_pivot


def _rline_text(*, include_last: bool = True, valid_header: bool = True) -> str:
    column_header = (
        " Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_HWY,"
        if valid_header
        else " Year, Day, Hour, X, Y, Z, Concentration,"
    )
    header = [
        "RLINEv1_2",
        "SOURCE FILE: Source.txt (1 Sources)",
        "RECEPTOR FILE: Receptor.txt (2 Receptors)",
        "SURFACE FILE: met.sfc",
        "Error Limit: 1.000E-03",
        "Displacement Height: 5.000*z0",
        "Concentrations from: Plume and Meander",
        "Roadway configurations used: N",
        "Roadway #Lanes Option: Y",
        "Integraton option: Numerical",
        " ",
        column_header,
    ]
    rows = [
        "1988,61,1,0.0,0.0,0.0,1.0, ",
        "1988,61,1,1.0,0.0,0.0,2.0, ",
        "1988,61,2,0.0,0.0,0.0,3.0, ",
        "1988,61,2,1.0,0.0,0.0,4.0, ",
    ]
    if not include_last:
        rows.pop()
    return "\n".join(header + rows) + "\n"


def test_parser_keeps_real_last_rline_row(real_results: dict[str, tuple]) -> None:
    _config, _aermod, rline, _period, _merged = real_results["caso1_referencia"]

    assert len(rline) == 806 * 120
    last = rline.iloc[-1]
    assert (int(last["Year"]), int(last["JD"]), int(last["Hour"])) == (1988, 65, 24)
    assert (last["X"], last["Y"], last["C"]) == pytest.approx((1000.0, 300.0, 199.287))


def test_parser_requires_every_period_for_every_receptor(tmp_path: Path) -> None:
    complete = tmp_path / "complete.csv"
    complete.write_text(_rline_text(), encoding="utf-8")
    parsed = parse_rline(complete, expected_receptors=2, expected_periods=2)
    assert len(parsed) == 4

    truncated = tmp_path / "truncated.csv"
    truncated.write_text(_rline_text(include_last=False), encoding="utf-8")
    with pytest.raises(PipelineValidationError, match="cada receptor.*2 periodos"):
        parse_rline(truncated, expected_receptors=2, expected_periods=2)


def test_parser_validates_rline_column_names(tmp_path: Path) -> None:
    path = tmp_path / "bad_header.csv"
    path.write_text(_rline_text(valid_header=False), encoding="utf-8")

    with pytest.raises(PipelineValidationError, match="colunas RLINE inesperadas"):
        parse_rline(path, expected_receptors=2, expected_periods=2)


def test_parser_rejects_wrong_receptor_height(tmp_path: Path) -> None:
    path = tmp_path / "wrong_z.csv"
    path.write_text(_rline_text(), encoding="utf-8")
    expected = pd.DataFrame({"X": [0.0, 1.0], "Y": [0.0, 0.0], "Z": [1.5, 1.5]})

    with pytest.raises(PipelineValidationError, match="correspondencia.*nao e bijetiva"):
        parse_rline(
            path,
            expected_receptors=2,
            expected_periods=2,
            expected_coordinates=expected,
            coordinate_tolerance=0.001,
        )


def test_tolerant_merge_is_bijective_without_rounding() -> None:
    aermod = pd.DataFrame({"X": [0.0, 1.0], "Y": [0.0, 0.0], "conc": [10.0, 20.0]})
    rline = pd.DataFrame({"X": [0.0005, 1.0005], "Y": [0.0, 0.0], "C": [5.0, 10.0]})

    with pytest.raises(PipelineValidationError, match="correspondencia exata"):
        merge_one_to_one(aermod, rline)

    merged = merge_one_to_one(aermod, rline, coordinate_tolerance=0.001)
    assert merged["X"].tolist() == [0.0, 1.0]
    assert merged["ratio"].tolist() == [2.0, 2.0]


def test_concentration_pivot_is_independent_of_row_order() -> None:
    shuffled = pd.DataFrame(
        {
            "X": [1.0, 0.0, 1.0, 0.0],
            "Y": [1.0, 0.0, 0.0, 1.0],
            "conc": [11.0, 0.0, 1.0, 10.0],
        }
    )

    pivot = concentration_pivot(shuffled)

    assert pivot.index.tolist() == [0.0, 1.0]
    assert pivot.columns.tolist() == [0.0, 1.0]
    assert pivot.to_numpy().tolist() == [[0.0, 1.0], [10.0, 11.0]]


def _standalone_inputs(tmp_path: Path, *, month: int = 3) -> tuple[Path, Path]:
    receptors = tmp_path / "Receptor_Road.txt"
    receptors.write_text(
        "receptors\nX Y Z\n---\n0.0 0.0 0.0\n1.0 0.0 0.0\n",
        encoding="utf-8",
    )
    meteorology = tmp_path / "ONSITE.SFC"
    meteorology.write_text(
        f"VERSION: 26135\n1988 {month} 1 61 1 met fields\n1988 {month} 1 61 2 met fields\n",
        encoding="utf-8",
    )
    return receptors, meteorology


def test_standalone_validation_rejects_invalid_calendar(tmp_path: Path) -> None:
    output = tmp_path / "output.csv"
    output.write_text(_rline_text(), encoding="utf-8")
    receptors, meteorology = _standalone_inputs(tmp_path, month=13)

    with pytest.raises(PipelineValidationError, match="periodo meteorologico invalido"):
        validate_rline_output(output, receptors, meteorology)


def test_standalone_validation_rejects_missing_value_sentinel(tmp_path: Path) -> None:
    output = tmp_path / "output.csv"
    output.write_text(
        _rline_text().replace("1988,61,1,0.0,0.0,0.0,1.0", "1988,61,1,0.0,0.0,0.0,-99.0"),
        encoding="utf-8",
    )
    receptors, meteorology = _standalone_inputs(tmp_path)

    with pytest.raises(PipelineValidationError, match="sentinela"):
        validate_rline_output(output, receptors, meteorology)


def test_aermod_parser_rejects_false_declared_receptor_count(tmp_path: Path) -> None:
    output = tmp_path / "CONC_PLOT.PLT"
    output.write_text(
        "\n".join(
            [
                "* AERMOD",
                "* AERMET",
                "* MODELING OPTIONS USED",
                "* PLOT FILE OF PERIOD VALUES",
                "* FOR A TOTAL OF 999 RECEPTORS.",
                "* FORMAT",
                "* X Y AVERAGE CONC ZELEV ZHILL ZFLAG AVE GRP NUM HRS NET ID",
                "* ____________",
                "0.0 0.0 1.0 0.0 0.0 0.0 PERIOD ALL 00000001 RCART",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(PipelineValidationError, match="declara 999 receptores"):
        parse_aermod(output)


def test_aermod_completion_rejects_missing_hours(tmp_path: Path) -> None:
    report = tmp_path / "AERMOD.out"
    report.write_text(
        "A Total of 0 Fatal Error Message(s)\n"
        "A Total of 2 Hours Were Processed\n"
        "A Total of 1 Missing Hours Identified\n"
        "AERMOD Finishes Successfully\n",
        encoding="utf-8",
    )

    with pytest.raises(PipelineValidationError, match="missing.*zero"):
        validate_aermod_completion(report, 2)
