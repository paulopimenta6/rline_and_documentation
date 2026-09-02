from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import platform
import signal
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
CORRECTED_BINARY = ROOT / "build" / "rline-patched" / "RLINEv1_2_patched.x"
ORIGINAL_BINARY = ROOT / "build" / "rline-original" / "RLINEv1_2_gfortran.x"
DEFAULT_ABSOLUTE_TOLERANCE = 1.0e-6
ABSOLUTE_TOLERANCE_BASIS = (
    "1e-6 output units is used only near a zero golden value; it is more than "
    "eight orders of magnitude below the smallest positive golden concentration (421.154)."
)


class OutputFormatError(ValueError):
    """Raised when an RLINE CSV does not have the expected tabular structure."""


@dataclass(frozen=True)
class OutputSpec:
    filename: str
    expected_rows: int


@dataclass(frozen=True)
class CaseSpec:
    name: str
    directory: Path
    outputs: tuple[OutputSpec, ...]
    relative_tolerance: float
    absolute_tolerance: float
    tolerance_basis: str


@dataclass(frozen=True)
class RlineTable:
    key_columns: tuple[str, ...]
    concentration_columns: tuple[str, ...]
    keys: tuple[tuple[int | float, ...], ...]
    concentrations: tuple[tuple[float, ...], ...]


CASES = (
    CaseSpec(
        name="example-case",
        directory=ROOT / "RLINE_v1_2.Example_Cases" / "Example_case",
        outputs=(
            OutputSpec("Output_Example_Numerical.csv", 1960),
            OutputSpec("Output_Example_Numerical_DailyAve.csv", 196),
        ),
        relative_tolerance=0.019,
        absolute_tolerance=DEFAULT_ABSOLUTE_TOLERANCE,
        tolerance_basis=(
            "Observed corrected maximum 1.789152% (hourly; daily maximum 0.048973%); "
            "the 1.9% limit adds 0.110848 percentage point without masking larger drift."
        ),
    ),
    CaseSpec(
        name="caltrans",
        directory=(ROOT / "RLINE_v1_2.Evaluation_Data" / "Evaluation_data" / "CALTRANS_RLINE"),
        outputs=(OutputSpec("CALTRANS99_Output.csv", 392),),
        relative_tolerance=0.0055,
        absolute_tolerance=DEFAULT_ABSOLUTE_TOLERANCE,
        tolerance_basis=(
            "Observed corrected maximum 0.523329%; the 0.55% limit adds 0.026671 percentage point."
        ),
    ),
    CaseSpec(
        name="idaho-falls",
        directory=(ROOT / "RLINE_v1_2.Evaluation_Data" / "Evaluation_data" / "IdahoFalls_RLINE"),
        outputs=(OutputSpec("IF2009_Output_INF_Case1235.csv", 217),),
        relative_tolerance=0.00095,
        absolute_tolerance=DEFAULT_ABSOLUTE_TOLERANCE,
        tolerance_basis=(
            "Observed corrected maximum 0.088408%; the 0.095% limit adds 0.006592 percentage point."
        ),
    ),
    CaseSpec(
        name="raleigh",
        directory=(ROOT / "RLINE_v1_2.Evaluation_Data" / "Evaluation_data" / "Raleigh_RLINE"),
        outputs=(OutputSpec("Ral2006_Output.csv", 1248),),
        relative_tolerance=0.0033,
        absolute_tolerance=DEFAULT_ABSOLUTE_TOLERANCE,
        tolerance_basis=(
            "Observed corrected maximum 0.314472%; the 0.33% limit adds 0.015528 percentage point."
        ),
    ),
)
EXPECTED_CONFIGURED_CASES = (
    "caso1_referencia",
    "caso2_rodovia_curta",
    "caso3_emissao_alta",
    "caso4_rodovia_larga",
)


def _trim_csv_row(row: Sequence[str]) -> list[str]:
    fields = [field.strip() for field in row]
    while fields and not fields[-1]:
        fields.pop()
    return fields


def _parse_key(fields: Sequence[str], path: Path, line_number: int) -> tuple[int | float, ...]:
    parsed: list[int | float] = []
    for index, field in enumerate(fields):
        try:
            value = float(field)
        except ValueError as error:
            raise OutputFormatError(f"{path}:{line_number}: invalid key value {field!r}") from error
        if not math.isfinite(value):
            raise OutputFormatError(f"{path}:{line_number}: non-finite key value {field!r}")
        if index < 3:
            if not value.is_integer():
                raise OutputFormatError(
                    f"{path}:{line_number}: key column {index + 1} is not an integer"
                )
            parsed.append(int(value))
        else:
            parsed.append(value)
    year, julian_day, period = parsed[:3]
    if year < 1 or not 1 <= julian_day <= 366 or period < 1:
        raise OutputFormatError(f"{path}:{line_number}: invalid time key {tuple(parsed[:3])}")
    return tuple(parsed)


def read_rline_output(path: Path) -> RlineTable:
    """Parse keys and every concentration column from an RLINE CSV output."""

    if not path.is_file():
        raise OutputFormatError(f"RLINE output not found: {path}")

    header: list[str] | None = None
    keys: list[tuple[int | float, ...]] = []
    concentrations: list[tuple[float, ...]] = []

    with path.open(encoding="ascii", newline="") as stream:
        for line_number, raw_row in enumerate(csv.reader(stream), start=1):
            row = _trim_csv_row(raw_row)
            if header is None:
                if row and row[0] == "Year":
                    header = row
                continue
            if not row:
                continue
            if len(row) != len(header):
                raise OutputFormatError(
                    f"{path}:{line_number}: expected {len(header)} fields, found {len(row)}"
                )

            keys.append(_parse_key(row[:6], path, line_number))
            values: list[float] = []
            for field in row[6:]:
                try:
                    value = float(field)
                except ValueError as error:
                    raise OutputFormatError(
                        f"{path}:{line_number}: invalid concentration {field!r}"
                    ) from error
                if not math.isfinite(value):
                    raise OutputFormatError(
                        f"{path}:{line_number}: non-finite concentration {field!r}"
                    )
                if value < 0.0:
                    raise OutputFormatError(
                        f"{path}:{line_number}: negative concentration or missing-data sentinel"
                    )
                values.append(value)
            concentrations.append(tuple(values))

    if header is None:
        raise OutputFormatError(f"RLINE table header not found: {path}")
    if len(header) < 7:
        raise OutputFormatError(f"RLINE table has no concentration columns: {path}")
    if header[0:2] != ["Year", "Julian_Day"]:
        raise OutputFormatError(f"unexpected RLINE time keys in {path}: {header[:2]}")
    if header[2] not in {"Hour", "# Hours"}:
        raise OutputFormatError(f"unexpected RLINE period key in {path}: {header[2]}")
    if header[3:6] != ["X-Coordinate", "Y-Coordinate", "Z-Coordinate"]:
        raise OutputFormatError(f"unexpected RLINE coordinate keys in {path}: {header[3:6]}")
    if not all(column.startswith("C_") for column in header[6:]):
        raise OutputFormatError(f"unexpected concentration columns in {path}: {header[6:]}")
    if not keys:
        raise OutputFormatError(f"RLINE table has no data rows: {path}")

    return RlineTable(
        key_columns=tuple(header[:6]),
        concentration_columns=tuple(header[6:]),
        keys=tuple(keys),
        concentrations=tuple(concentrations),
    )


def _column_statistics(
    actual: RlineTable,
    golden: RlineTable,
    column_index: int,
    relative_tolerance: float,
    absolute_tolerance: float,
) -> dict[str, Any]:
    differences: list[float] = []
    relative_differences: list[float] = []
    failed_count = 0
    exact_match_count = 0
    zero_reference_mismatches = 0
    worst_index = 0
    worst_ratio = -1.0

    for row_index, (actual_row, golden_row) in enumerate(
        zip(actual.concentrations, golden.concentrations, strict=True)
    ):
        actual_value = actual_row[column_index]
        golden_value = golden_row[column_index]
        difference = abs(actual_value - golden_value)
        allowed = absolute_tolerance + relative_tolerance * abs(golden_value)
        ratio = difference / abs(golden_value) if golden_value != 0.0 else None

        differences.append(difference)
        if ratio is not None:
            relative_differences.append(ratio)
            ranking = ratio
        else:
            ranking = difference / absolute_tolerance if absolute_tolerance else difference
            if difference != 0.0:
                zero_reference_mismatches += 1
        if ranking > worst_ratio:
            worst_ratio = ranking
            worst_index = row_index
        if difference > allowed:
            failed_count += 1
        if difference == 0.0:
            exact_match_count += 1

    actual_value = actual.concentrations[worst_index][column_index]
    golden_value = golden.concentrations[worst_index][column_index]
    return {
        "column": golden.concentration_columns[column_index],
        "values": len(differences),
        "failed_values": failed_count,
        "exact_match_values": exact_match_count,
        "zero_reference_mismatches": zero_reference_mismatches,
        "max_absolute_difference": max(differences),
        "max_relative_difference": max(relative_differences) if relative_differences else None,
        "median_relative_difference": statistics.median(relative_differences)
        if relative_differences
        else None,
        "worst_row": worst_index + 1,
        "worst_key": list(golden.keys[worst_index]),
        "worst_golden_value": golden_value,
        "worst_actual_value": actual_value,
        "passed": failed_count == 0,
    }


def compare_tables(
    actual: RlineTable,
    golden: RlineTable,
    *,
    relative_tolerance: float,
    absolute_tolerance: float,
    expected_rows: int | None = None,
) -> dict[str, Any]:
    """Compare ordered keys and every concentration value in two RLINE tables."""

    if (
        not math.isfinite(relative_tolerance)
        or not math.isfinite(absolute_tolerance)
        or relative_tolerance < 0.0
        or absolute_tolerance < 0.0
    ):
        raise ValueError("comparison tolerances must be finite and non-negative")

    schema_matches = (
        actual.key_columns == golden.key_columns
        and actual.concentration_columns == golden.concentration_columns
    )
    row_count_matches = len(actual.keys) == len(golden.keys)
    expected_row_count_matches = expected_rows is None or len(golden.keys) == expected_rows
    keys_match = row_count_matches and actual.keys == golden.keys
    first_key_mismatch: dict[str, Any] | None = None

    if row_count_matches and not keys_match:
        mismatch_index = next(
            index
            for index, (actual_key, golden_key) in enumerate(
                zip(actual.keys, golden.keys, strict=True)
            )
            if actual_key != golden_key
        )
        first_key_mismatch = {
            "row": mismatch_index + 1,
            "golden": list(golden.keys[mismatch_index]),
            "actual": list(actual.keys[mismatch_index]),
        }

    column_statistics: list[dict[str, Any]] = []
    if schema_matches and row_count_matches:
        column_statistics = [
            _column_statistics(
                actual,
                golden,
                column_index,
                relative_tolerance,
                absolute_tolerance,
            )
            for column_index in range(len(golden.concentration_columns))
        ]

    relative_values = [
        column["max_relative_difference"]
        for column in column_statistics
        if column["max_relative_difference"] is not None
    ]
    median_values = (
        [
            abs(actual_value - golden_value) / abs(golden_value)
            for actual_row, golden_row in zip(
                actual.concentrations, golden.concentrations, strict=row_count_matches
            )
            for actual_value, golden_value in zip(actual_row, golden_row, strict=schema_matches)
            if golden_value != 0.0
        ]
        if schema_matches and row_count_matches
        else []
    )
    concentrations_pass = bool(column_statistics) and all(
        column["passed"] for column in column_statistics
    )

    return {
        "passed": (
            schema_matches
            and row_count_matches
            and expected_row_count_matches
            and keys_match
            and concentrations_pass
        ),
        "relative_tolerance": relative_tolerance,
        "absolute_tolerance": absolute_tolerance,
        "golden_rows": len(golden.keys),
        "actual_rows": len(actual.keys),
        "expected_rows": expected_rows,
        "expected_row_count_matches": expected_row_count_matches,
        "schema_matches": schema_matches,
        "golden_key_columns": list(golden.key_columns),
        "actual_key_columns": list(actual.key_columns),
        "golden_concentration_columns": list(golden.concentration_columns),
        "actual_concentration_columns": list(actual.concentration_columns),
        "keys_match": keys_match,
        "first_key_mismatch": first_key_mismatch,
        "max_absolute_difference": max(
            (column["max_absolute_difference"] for column in column_statistics),
            default=None,
        ),
        "max_relative_difference": max(relative_values, default=None),
        "median_relative_difference": statistics.median(median_values) if median_values else None,
        "failed_values": sum(column["failed_values"] for column in column_statistics),
        "columns": column_statistics,
    }


def compare_outputs(
    actual_path: Path,
    golden_path: Path,
    *,
    relative_tolerance: float,
    absolute_tolerance: float,
    expected_rows: int | None = None,
) -> dict[str, Any]:
    actual = read_rline_output(actual_path)
    golden = read_rline_output(golden_path)
    return compare_tables(
        actual,
        golden,
        relative_tolerance=relative_tolerance,
        absolute_tolerance=absolute_tolerance,
        expected_rows=expected_rows,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_environment(**updates: str) -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in ("HOME", "PATH", "TMPDIR", "LD_LIBRARY_PATH", "VIRTUAL_ENV", "CONDA_PREFIX")
        if key in os.environ
    }
    environment.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
            "TZ": "UTC",
            "MPLBACKEND": "Agg",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    environment.update(updates)
    return environment


def _stop_process_group(process: subprocess.Popen[str], log: Any) -> int:
    if process.poll() is not None:
        return int(process.returncode)
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        log.write("\nprocess group ignored TERM; sending KILL\n")
        log.flush()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.wait()


def _run_logged_command(
    command: Sequence[str],
    *,
    cwd: Path,
    log_path: Path,
    timeout_seconds: int,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return_code: int | None = None
    status = "failed"
    error_message: str | None = None
    process: subprocess.Popen[str] | None = None

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"cwd={cwd}\ncommand={shlex.join(command)}\n")
        log.flush()
        try:
            process = subprocess.Popen(
                list(command),
                cwd=cwd,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            return_code = process.wait(timeout=timeout_seconds)
            status = "passed" if return_code == 0 else "failed"
        except subprocess.TimeoutExpired:
            status = "timeout"
            error_message = f"command exceeded {timeout_seconds} seconds"
            log.write(f"\n{error_message}\n")
            return_code = _stop_process_group(process, log)
        except (KeyboardInterrupt, InterruptedError):
            if process is not None:
                _stop_process_group(process, log)
            raise
        except OSError as error:
            error_message = str(error)
            log.write(f"\nfailed to start command: {error}\n")
        except BaseException:
            if process is not None:
                _stop_process_group(process, log)
            raise

    return {
        "command": list(command),
        "cwd": str(cwd),
        "log": str(log_path),
        "timeout_seconds": timeout_seconds,
        "duration_seconds": round(time.monotonic() - started, 3),
        "return_code": return_code,
        "status": status,
        "error": error_message,
        "passed": status == "passed",
    }


def _run_model(
    binary: Path,
    case: CaseSpec,
    *,
    variant: str,
    run_number: int,
    workspace: Path,
    log_dir: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Path]]:
    run_directory = workspace / "epa" / case.name / variant / f"run-{run_number}"
    shutil.copytree(case.directory, run_directory)
    for output in case.outputs:
        (run_directory / output.filename).unlink(missing_ok=True)

    log_path = log_dir / f"epa-{case.name}-{variant}-{run_number}.log"
    print(f"[{case.name}] running {variant} RLINE (run {run_number})", flush=True)
    process = _run_logged_command(
        [str(binary)],
        cwd=run_directory,
        log_path=log_path,
        timeout_seconds=timeout_seconds,
        environment=_clean_environment(),
    )

    comparisons: dict[str, Any] = {}
    generated_outputs: dict[str, Path] = {}
    if process["passed"]:
        for output in case.outputs:
            generated = run_directory / output.filename
            generated_outputs[output.filename] = generated
            try:
                comparisons[output.filename] = compare_outputs(
                    generated,
                    case.directory / output.filename,
                    relative_tolerance=case.relative_tolerance,
                    absolute_tolerance=case.absolute_tolerance,
                    expected_rows=output.expected_rows,
                )
            except (OSError, OutputFormatError, ValueError) as error:
                comparisons[output.filename] = {
                    "passed": False,
                    "error": str(error),
                }

    passed = (
        process["passed"]
        and len(comparisons) == len(case.outputs)
        and all(comparison["passed"] for comparison in comparisons.values())
    )
    record = {
        "variant": variant,
        "run_number": run_number,
        "binary": str(binary),
        "binary_sha256": _sha256(binary),
        "process": process,
        "comparisons": comparisons,
        "generated_outputs_sha256": {
            name: _sha256(path) for name, path in generated_outputs.items()
        },
        "golden_outputs_sha256": {
            output.filename: _sha256(case.directory / output.filename) for output in case.outputs
        },
        "passed": passed,
    }
    return record, generated_outputs


def _compare_runs(outputs_by_run: Sequence[dict[str, Path]], case: CaseSpec) -> dict[str, Any]:
    if len(outputs_by_run) < 2:
        return {"assessed": False, "deterministic": None, "comparisons": []}
    if any(len(outputs) != len(case.outputs) for outputs in outputs_by_run):
        return {
            "assessed": False,
            "deterministic": None,
            "comparisons": [],
            "reason": "at least one run did not produce every output",
        }

    comparisons: list[dict[str, Any]] = []
    baseline = outputs_by_run[0]
    for run_index, outputs in enumerate(outputs_by_run[1:], start=2):
        for output in case.outputs:
            try:
                comparison = compare_outputs(
                    outputs[output.filename],
                    baseline[output.filename],
                    relative_tolerance=0.0,
                    absolute_tolerance=0.0,
                    expected_rows=output.expected_rows,
                )
            except (OSError, OutputFormatError, ValueError) as error:
                comparison = {"passed": False, "error": str(error)}
            comparisons.append(
                {
                    "run": run_index,
                    "output": output.filename,
                    "comparison": comparison,
                }
            )

    return {
        "assessed": True,
        "deterministic": all(item["comparison"]["passed"] for item in comparisons),
        "comparison_tolerance": {"relative": 0.0, "absolute": 0.0},
        "comparisons": comparisons,
    }


def _run_case(
    case: CaseSpec,
    *,
    workspace: Path,
    log_dir: Path,
    timeout_seconds: int,
    corrected_runs: int,
    original_runs: int,
) -> dict[str, Any]:
    corrected_records: list[dict[str, Any]] = []
    corrected_outputs: list[dict[str, Path]] = []
    for run_number in range(1, corrected_runs + 1):
        record, outputs = _run_model(
            CORRECTED_BINARY,
            case,
            variant="corrected",
            run_number=run_number,
            workspace=workspace,
            log_dir=log_dir,
            timeout_seconds=timeout_seconds,
        )
        corrected_records.append(record)
        corrected_outputs.append(outputs)
    corrected_reproducibility = _compare_runs(corrected_outputs, case)
    corrected_passed = (
        all(record["passed"] for record in corrected_records)
        and corrected_reproducibility["assessed"]
        and corrected_reproducibility["deterministic"]
    )

    original_records: list[dict[str, Any]] = []
    original_outputs: list[dict[str, Path]] = []
    for run_number in range(1, original_runs + 1):
        record, outputs = _run_model(
            ORIGINAL_BINARY,
            case,
            variant="original",
            run_number=run_number,
            workspace=workspace,
            log_dir=log_dir,
            timeout_seconds=timeout_seconds,
        )
        original_records.append(record)
        original_outputs.append(outputs)

    reproducibility = _compare_runs(original_outputs, case)
    if original_runs == 0:
        original_assessment = "skipped"
    elif not all(record["process"]["passed"] for record in original_records):
        original_assessment = "execution-failure-observed"
    elif reproducibility["assessed"] and not reproducibility["deterministic"]:
        original_assessment = "nondeterminism-observed"
    elif all(record["passed"] for record in original_records):
        original_assessment = "within-golden-tolerance"
    else:
        original_assessment = "divergence-from-golden-observed"

    print(
        f"[{case.name}] corrected={'PASS' if corrected_passed else 'FAIL'}; "
        f"original baseline={original_assessment}",
        flush=True,
    )
    return {
        "name": case.name,
        "golden_directory": str(case.directory.relative_to(ROOT)),
        "tolerance": {
            "relative": case.relative_tolerance,
            "absolute": case.absolute_tolerance,
            "basis": case.tolerance_basis,
            "absolute_basis": ABSOLUTE_TOLERANCE_BASIS,
        },
        "case_files_sha256": {
            str(path.relative_to(case.directory)): _sha256(path)
            for path in sorted(case.directory.rglob("*"))
            if path.is_file()
        },
        "corrected": {
            "required_runs": corrected_runs,
            "runs": corrected_records,
            "reproducibility": corrected_reproducibility,
            "passed": corrected_passed,
        },
        "original": {
            "required_for_pass": False,
            "assessment": original_assessment,
            "runs": original_records,
            "reproducibility": reproducibility,
        },
        "passed": corrected_passed,
    }


def _copy_pipeline_logs(source: Path, destination: Path) -> None:
    for path in source.rglob("*"):
        if path.is_file() and (path.suffix == ".log" or path.name.endswith(".manifest.json")):
            relative = path.relative_to(source)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _run_full_pipeline(
    workspace: Path, log_dir: Path, artifact_dir: Path, timeout_seconds: int
) -> dict[str, Any]:
    canonical_directory = workspace / "full-pipeline" / "Caso_Pipeline"
    shutil.copytree(ROOT / "Caso_Pipeline", canonical_directory)
    common_environment = _clean_environment(
        BIN_AERMET=str(ROOT / "build" / "aermet" / "aermet"),
        BIN_AERMOD=str(ROOT / "build" / "aermod" / "aermod"),
        BIN_RLINE=str(CORRECTED_BINARY),
    )
    for timeout_variable in (
        "PIPELINE_STEP_TIMEOUT_SECONDS",
        "ALL_CASES_STEP_TIMEOUT_SECONDS",
        "CASE_STEP_TIMEOUT_SECONDS",
        "RLINE_TIMEOUT_SECONDS",
    ):
        common_environment[timeout_variable] = os.environ.get(
            timeout_variable, str(timeout_seconds)
        )
    common_environment["MAX_PARALLEL_CASES"] = os.environ.get(
        "MAX_PARALLEL_CASES", str(min(4, os.cpu_count() or 1))
    )
    canonical_environment = common_environment.copy()
    canonical_environment["PIPELINE_CASE_DIR"] = str(canonical_directory)
    print("[full-pipeline] running canonical preprocessing and processing", flush=True)
    canonical_result = _run_logged_command(
        ["bash", str(ROOT / "scripts" / "run_pipeline.sh")],
        cwd=ROOT,
        log_path=log_dir / "canonical-pipeline.log",
        timeout_seconds=timeout_seconds,
        environment=canonical_environment,
    )

    cases_directory = workspace / "full-pipeline" / "casos"
    configs = sorted((ROOT / "casos").glob("*/config.json"))
    for config in configs:
        destination = cases_directory / config.parent.name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config, destination / "config.json")

    environment = common_environment.copy()
    environment.update(
        {
            "CASES_DIR": str(cases_directory),
            "DIR_DADOS_AERMET": str(canonical_directory / "dados_aermet"),
        }
    )
    configured_case_names = tuple(config.parent.name for config in configs)
    configured_case_set_matches = configured_case_names == EXPECTED_CONFIGURED_CASES
    canonical_result["required_stages"] = [
        "AERMET Stage 1",
        "AERMET Stage 2",
        "AERMOD",
        "RLINE corrected",
        "post-processing",
    ]
    if canonical_result["passed"]:
        print("[full-pipeline] running all four configured AERMOD/RLINE cases", flush=True)
        cases_result = _run_logged_command(
            ["bash", str(ROOT / "scripts" / "run_todos_casos.sh")],
            cwd=ROOT,
            log_path=log_dir / "full-pipeline.log",
            timeout_seconds=timeout_seconds,
            environment=environment,
        )
    else:
        cases_result = {
            "passed": False,
            "status": "skipped",
            "error": "canonical pipeline failed",
        }
    cases_result["configured_cases"] = list(configured_case_names)
    cases_result["configured_case_set_matches"] = configured_case_set_matches
    _copy_pipeline_logs(cases_directory, artifact_dir / "full-pipeline-logs")
    _copy_pipeline_logs(canonical_directory, artifact_dir / "canonical-pipeline-logs")
    return {
        "requested": True,
        "canonical": canonical_result,
        "configured_cases": cases_result,
        "passed": (
            canonical_result["passed"] and cases_result["passed"] and configured_case_set_matches
        ),
    }


def _environment_flag(name: str) -> bool:
    value = os.environ.get(name, "0").strip().lower()
    if value in {"", "0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    raise ValueError(f"{name} must be 0 or 1, got {value!r}")


def _git_state() -> dict[str, Any]:
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    try:
        dirty = bool(
            subprocess.check_output(
                ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        dirty = None
    return {"revision": revision, "dirty": dirty}


def _write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary_name = stream.name
            stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def _parse_positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _parse_reproducibility_runs(value: str) -> int:
    parsed = int(value)
    if parsed < 2:
        raise argparse.ArgumentTypeError("value must be at least 2")
    return parsed


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run isolated RLINE scientific regressions without replacing golden files."
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=[case.name for case in CASES],
        dest="case_names",
        help="run only the selected EPA case (repeatable)",
    )
    parser.add_argument(
        "--model-timeout",
        type=_parse_positive_integer,
        default=int(os.environ.get("SCIENTIFIC_MODEL_TIMEOUT_SECONDS", "7200")),
    )
    parser.add_argument(
        "--corrected-runs",
        type=_parse_reproducibility_runs,
        default=int(os.environ.get("CORRECTED_REGRESSION_RUNS", "2")),
        help="number of corrected-source runs required to prove deterministic output",
    )
    parser.add_argument(
        "--original-runs",
        type=_parse_positive_integer,
        default=int(os.environ.get("ORIGINAL_REGRESSION_RUNS", "2")),
        help="number of original-source runs used to expose output nondeterminism",
    )
    parser.add_argument(
        "--skip-original",
        action="store_true",
        help="skip the diagnostic original-source baseline runs",
    )
    parser.add_argument(
        "--skip-project-checks",
        action="store_true",
        help="skip pytest and validation of the four versioned configured cases",
    )
    parser.add_argument(
        "--run-full-pipeline",
        action="store_true",
        default=_environment_flag("RUN_FULL_PIPELINE"),
        help="run all four configured AERMOD/RLINE cases in temporary directories",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = parse_args(arguments)
    selected_cases = [case for case in CASES if not args.case_names or case.name in args.case_names]
    original_runs = 0 if args.skip_original else args.original_runs
    artifact_dir = (
        Path(os.environ.get("REGRESSION_ARTIFACT_DIR", ROOT / "build" / "scientific-regression"))
        .expanduser()
        .resolve()
    )
    log_dir = artifact_dir / "logs"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifact_dir / "scientific-regression-report.json"
    lock_stream = (artifact_dir / ".scientific-regression.lock").open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"Another scientific regression is using {artifact_dir}", file=sys.stderr)
        lock_stream.close()
        return 75

    missing_binaries = [
        str(binary)
        for binary in (CORRECTED_BINARY, ORIGINAL_BINARY)
        if not binary.is_file() or not os.access(binary, os.X_OK)
    ]
    if args.skip_original:
        missing_binaries = [path for path in missing_binaries if path != str(ORIGINAL_BINARY)]
    if missing_binaries:
        message = "Missing model binaries; run `make models` first: " + ", ".join(missing_binaries)
        (log_dir / "preflight.log").write_text(message + "\n", encoding="utf-8")
        _write_report(
            {
                "schema_version": 2,
                "status": "failed",
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "repository": str(ROOT),
                "git": _git_state(),
                "missing_binaries": missing_binaries,
                "error": message,
                "passed": False,
            },
            report_path,
        )
        print(message, file=sys.stderr)
        print(f"Scientific regression report: {report_path}", file=sys.stderr)
        lock_stream.close()
        return 2

    report: dict[str, Any] = {
        "schema_version": 2,
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "repository": str(ROOT),
        "git": _git_state(),
        "platform": platform.platform(),
        "python": sys.version,
        "artifact_directory": str(artifact_dir),
        "workspace_policy": "model executions use a temporary directory; golden files are read-only",
        "project_checks": {},
        "epa_cases": [],
        "full_pipeline": {"requested": args.run_full_pipeline, "passed": True},
        "passed": False,
    }
    _write_report(report, report_path)

    with tempfile.TemporaryDirectory(prefix="rline-scientific-regression-") as temporary:
        workspace = Path(temporary)

        if not args.skip_project_checks:
            print("[checks] running the existing non-scientific pytest suite", flush=True)
            report["project_checks"]["pytest"] = _run_logged_command(
                [sys.executable, "-m", "pytest", "-m", "not scientific"],
                cwd=ROOT,
                log_path=log_dir / "pytest.log",
                timeout_seconds=1800,
                environment=_clean_environment(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"),
            )
            print("[checks] validating all versioned configured case results", flush=True)
            report["project_checks"]["versioned_cases"] = _run_logged_command(
                [sys.executable, str(ROOT / "scripts" / "teste_casos.py")],
                cwd=ROOT,
                log_path=log_dir / "versioned-cases.log",
                timeout_seconds=900,
                environment=_clean_environment(),
            )

        for case in selected_cases:
            report["epa_cases"].append(
                _run_case(
                    case,
                    workspace=workspace,
                    log_dir=log_dir,
                    timeout_seconds=args.model_timeout,
                    corrected_runs=args.corrected_runs,
                    original_runs=original_runs,
                )
            )

        if args.run_full_pipeline:
            full_timeout = int(os.environ.get("FULL_PIPELINE_TIMEOUT_SECONDS", "21600"))
            report["full_pipeline"] = _run_full_pipeline(
                workspace,
                log_dir,
                artifact_dir,
                full_timeout,
            )
            report["full_pipeline"]["requested"] = True

    project_checks_pass = all(check["passed"] for check in report["project_checks"].values())
    epa_cases_pass = len(report["epa_cases"]) == len(selected_cases) and all(
        case["passed"] for case in report["epa_cases"]
    )
    report["passed"] = project_checks_pass and epa_cases_pass and report["full_pipeline"]["passed"]
    report["finished_at"] = datetime.now(UTC).isoformat()
    report["status"] = "passed" if report["passed"] else "failed"
    _write_report(report, report_path)

    print(f"Scientific regression report: {report_path}", flush=True)
    print(f"Scientific regression: {'PASS' if report['passed'] else 'FAIL'}", flush=True)
    exit_code = 0 if report["passed"] else 1
    lock_stream.close()
    return exit_code


if __name__ == "__main__":

    def _terminate_regression(signum: int, _frame: Any) -> None:
        raise InterruptedError(f"received signal {signum}")

    signal.signal(signal.SIGTERM, _terminate_regression)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except InterruptedError:
        raise SystemExit(143) from None
