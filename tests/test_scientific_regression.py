from __future__ import annotations

from pathlib import Path

import pytest

from scripts.scientific_regression import (
    OutputFormatError,
    compare_outputs,
    read_rline_output,
)
import scripts.scientific_regression as scientific_regression


def write_output(
    path: Path,
    rows: list[tuple[int, int, int, float, float, float, float, float]],
    *,
    concentration_columns: tuple[str, str] = ("C_A", "C_B"),
) -> None:
    lines = [
        "RLINEv1_2",
        (
            "Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, "
            f"{concentration_columns[0]}, {concentration_columns[1]},"
        ),
    ]
    lines.extend(", ".join(str(value) for value in row) + "," for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def test_parser_preserves_duplicate_ordered_keys_and_all_concentrations(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output.csv"
    rows = [
        (6, 1, 7, 9.01, 21.16, 2.0, 10.0, 20.0),
        (6, 1, 7, 9.01, 21.16, 2.0, 11.0, 21.0),
    ]
    write_output(output, rows)

    table = read_rline_output(output)

    assert table.concentration_columns == ("C_A", "C_B")
    assert table.keys[0] == table.keys[1]
    assert table.concentrations == ((10.0, 20.0), (11.0, 21.0))


def test_comparison_applies_relative_and_absolute_tolerances_to_each_column(
    tmp_path: Path,
) -> None:
    golden = tmp_path / "golden.csv"
    actual = tmp_path / "actual.csv"
    write_output(
        golden,
        [(12, 264, 1, 10.0, 20.0, 1.5, 100.0, 0.0)],
    )
    write_output(
        actual,
        [(12, 264, 1, 10.0, 20.0, 1.5, 101.9, 0.0000005)],
    )

    comparison = compare_outputs(
        actual,
        golden,
        relative_tolerance=0.02,
        absolute_tolerance=1.0e-6,
        expected_rows=1,
    )

    assert comparison["passed"]
    assert comparison["keys_match"]
    assert [column["column"] for column in comparison["columns"]] == ["C_A", "C_B"]
    assert comparison["columns"][0]["max_relative_difference"] == pytest.approx(0.019)
    assert comparison["columns"][1]["zero_reference_mismatches"] == 1


def test_comparison_rejects_key_changes_and_reports_first_row(tmp_path: Path) -> None:
    golden = tmp_path / "golden.csv"
    actual = tmp_path / "actual.csv"
    write_output(golden, [(9, 1, 2, 18.0, 0.0, 1.5, 10.0, 20.0)])
    write_output(actual, [(9, 1, 3, 18.0, 0.0, 1.5, 10.0, 20.0)])

    comparison = compare_outputs(
        actual,
        golden,
        relative_tolerance=0.0,
        absolute_tolerance=0.0,
    )

    assert not comparison["passed"]
    assert not comparison["keys_match"]
    assert comparison["first_key_mismatch"] == {
        "row": 1,
        "golden": [9, 1, 2, 18.0, 0.0, 1.5],
        "actual": [9, 1, 3, 18.0, 0.0, 1.5],
    }


def test_comparison_rejects_a_single_concentration_column_failure(tmp_path: Path) -> None:
    golden = tmp_path / "golden.csv"
    actual = tmp_path / "actual.csv"
    write_output(golden, [(81, 357, 6, 0.0, 0.0, 1.0, 100.0, 100.0)])
    write_output(actual, [(81, 357, 6, 0.0, 0.0, 1.0, 100.5, 102.1)])

    comparison = compare_outputs(
        actual,
        golden,
        relative_tolerance=0.02,
        absolute_tolerance=0.0,
    )

    assert not comparison["passed"]
    assert comparison["columns"][0]["passed"]
    assert not comparison["columns"][1]["passed"]
    assert comparison["failed_values"] == 1


def test_parser_rejects_non_finite_concentrations(tmp_path: Path) -> None:
    output = tmp_path / "output.csv"
    write_output(output, [(9, 1, 2, 18.0, 0.0, 1.5, float("nan"), 20.0)])

    with pytest.raises(OutputFormatError, match="non-finite concentration"):
        read_rline_output(output)


def test_parser_rejects_negative_concentrations(tmp_path: Path) -> None:
    output = tmp_path / "output.csv"
    write_output(output, [(9, 1, 2, 18.0, 0.0, 1.5, -99.0, 20.0)])

    with pytest.raises(OutputFormatError, match="missing-data sentinel"):
        read_rline_output(output)


@pytest.mark.parametrize("tolerance", [float("nan"), float("inf")])
def test_comparison_rejects_non_finite_tolerances(tmp_path: Path, tolerance: float) -> None:
    golden = tmp_path / "golden.csv"
    actual = tmp_path / "actual.csv"
    rows = [(9, 1, 2, 18.0, 0.0, 1.5, 10.0, 20.0)]
    write_output(golden, rows)
    write_output(actual, rows)

    with pytest.raises(ValueError, match="finite and non-negative"):
        compare_outputs(
            actual,
            golden,
            relative_tolerance=tolerance,
            absolute_tolerance=0.0,
        )


def test_logged_command_stops_child_when_wait_is_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class InterruptedProcess:
        pid = 123

        def wait(self, *, timeout: int) -> int:
            raise InterruptedError("received signal 15")

    process = InterruptedProcess()
    stopped: list[object] = []
    monkeypatch.setattr(
        scientific_regression.subprocess, "Popen", lambda *_args, **_kwargs: process
    )
    monkeypatch.setattr(
        scientific_regression,
        "_stop_process_group",
        lambda child, _log: stopped.append(child) or 143,
    )

    with pytest.raises(InterruptedError, match="signal 15"):
        scientific_regression._run_logged_command(
            ["model"],
            cwd=tmp_path,
            log_path=tmp_path / "model.log",
            timeout_seconds=10,
        )

    assert stopped == [process]


def test_full_pipeline_is_isolated_and_stops_after_canonical_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    (root / "Caso_Pipeline").mkdir(parents=True)
    for index in range(4):
        case = root / "casos" / f"caso{index + 1}_test"
        case.mkdir(parents=True)
        (case / "config.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(scientific_regression, "ROOT", root)
    monkeypatch.setattr(
        scientific_regression,
        "CORRECTED_BINARY",
        root / "build" / "rline-patched" / "RLINE.x",
    )
    for variable in (
        "DIR_RODADA_AERMOD",
        "DIR_RODADA_RLINE",
        "DIR_GRAFICOS",
        "INP_AERMOD",
        "RUN_LOG_DIR",
    ):
        monkeypatch.setenv(variable, f"/hostile/{variable}")

    calls: list[dict[str, str]] = []

    def fake_run(*_args: object, **kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs["environment"]))  # type: ignore[arg-type]
        return {"passed": False, "status": "failed"}

    monkeypatch.setattr(scientific_regression, "_run_logged_command", fake_run)

    result = scientific_regression._run_full_pipeline(
        tmp_path / "workspace",
        tmp_path / "logs",
        tmp_path / "artifacts",
        1234,
    )

    assert not result["passed"]
    assert result["configured_cases"]["status"] == "skipped"
    assert len(calls) == 1
    environment = calls[0]
    assert environment["RLINE_TIMEOUT_SECONDS"] == "1234"
    assert environment["PIPELINE_STEP_TIMEOUT_SECONDS"] == "1234"
    assert all(
        not environment.get(name, "").startswith("/hostile/")
        for name in (
            "DIR_RODADA_AERMOD",
            "DIR_RODADA_RLINE",
            "DIR_GRAFICOS",
            "INP_AERMOD",
            "RUN_LOG_DIR",
        )
    )
