from __future__ import annotations

import hashlib
import math
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rline-minimal"
MANIFEST = ROOT / "patches" / "rline-v1.2" / "UPSTREAM_SHA256.txt"
RELEASE_BINARY = ROOT / "build" / "rline-patched" / "RLINEv1_2_patched.x"
DEBUG_BINARY = ROOT / "build" / "rline-patched-debug" / "RLINEv1_2_patched_debug.x"


@pytest.fixture(scope="session")
def binaries() -> tuple[Path, Path]:
    subprocess.run(
        ["make", "rline-release", "rline-debug"],
        cwd=ROOT,
        check=True,
        text=True,
        timeout=180,
    )
    assert RELEASE_BINARY.is_file()
    assert DEBUG_BINARY.is_file()
    return RELEASE_BINARY, DEBUG_BINARY


def copy_case(tmp_path: Path, name: str = "case") -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURE, destination)
    return destination


def run_model(binary: Path, case: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary)],
        cwd=case,
        capture_output=True,
        text=True,
        timeout=60,
    )


def output_values(
    case: Path, output_name: str = "output.csv"
) -> dict[tuple[float, float, float], float]:
    lines = (case / output_name).read_text(encoding="ascii").splitlines()
    header = next(index for index, line in enumerate(lines) if "Year, Julian_Day" in line)
    values: dict[tuple[float, float, float], float] = {}
    for line in lines[header + 1 :]:
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 7 or not fields[0]:
            continue
        coordinates = (float(fields[3]), float(fields[4]), float(fields[5]))
        values[coordinates] = float(fields[6])
    return values


def set_control_option(case: Path, label: str, value: str) -> None:
    control = case / "Line_Source_Inputs.txt"
    lines = control.read_text(encoding="ascii").splitlines()
    label_index = next(index for index, line in enumerate(lines) if label in line)
    lines[label_index + 1] = f"'{value}'"
    control.write_text("\n".join(lines) + "\n", encoding="ascii")


def source_fields(case: Path) -> list[str]:
    lines = (case / "sources.txt").read_text(encoding="ascii").splitlines()
    return lines[3].split()


def set_source_fields(case: Path, fields: list[str]) -> None:
    source = case / "sources.txt"
    lines = source.read_text(encoding="ascii").splitlines()
    lines[3] = " ".join(fields)
    source.write_text("\n".join(lines) + "\n", encoding="ascii")


def test_upstream_snapshot_matches_manifest() -> None:
    checked = 0
    for line in MANIFEST.read_text(encoding="ascii").splitlines():
        if not line or line.startswith("#"):
            continue
        expected, relative_path = line.split(maxsplit=1)
        actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert actual == expected, relative_path
        checked += 1
    assert checked == 30


def test_release_debug_and_patch_stage(binaries: tuple[Path, Path]) -> None:
    release, debug = binaries
    assert release.stat().st_mode & 0o111
    assert debug.stat().st_mode & 0o111
    assert not list((ROOT / "build").glob("rline-patched*/**/*.rej"))

    release_info = (release.parent / "BUILD-INFO.txt").read_text(encoding="utf-8")
    debug_info = (debug.parent / "BUILD-INFO.txt").read_text(encoding="utf-8")
    assert "variant=release" in release_info
    assert "variant=debug" in debug_info
    assert "-fcheck=all" in debug_info
    assert "-finit-real=snan" in debug_info
    assert "-ffpe-trap=invalid,zero,overflow" in debug_info


def test_changed_interfaces_are_explicit(binaries: tuple[Path, Path]) -> None:
    del binaries
    staged = ROOT / "build" / "rline-patched" / "src"
    depressed = (staged / "Depressed_Displacement.f90").read_text(encoding="ascii")
    translated = (staged / "Translate_Rotate.f90").read_text(encoding="ascii")
    numerical = (staged / "Numerical_Line_Source.f90").read_text(encoding="ascii")
    main = (staged / "RLINE_Main.f90").read_text(encoding="ascii")

    assert "Depressed_Displacement(theta_line, source_index)" in depressed
    assert "Source(indq)" not in depressed
    assert "Interface\n        Function Depressed_Displacement" in translated
    assert "Err,Converged" in numerical
    assert "Subroutine Numerical_Line_Source(im,ir,Conc_Num,Err,Converged)" in main
    assert "deallocate(h,Conc,Stat=AllocError)" in numerical


def test_aermet_pbl_dependency_is_explicit() -> None:
    makefile = (ROOT / "aermet_and_aermod" / "aermet_source" / "Makefile").read_text(
        encoding="utf-8"
    )
    dependency = next(line for line in makefile.splitlines() if line.startswith("mod_pbl.o:"))
    assert "mod_upperair.o" in dependency


@pytest.mark.parametrize("binary_index", [0, 1], ids=["release", "debug"])
def test_parallel_wind_is_finite(
    binaries: tuple[Path, Path], tmp_path: Path, binary_index: int
) -> None:
    case = copy_case(tmp_path, f"parallel-{binary_index}")
    result = run_model(binaries[binary_index], case)
    assert result.returncode == 0, result.stdout + result.stderr
    values = output_values(case)
    assert len(values) == 2
    assert all(math.isfinite(value) and value >= 0.0 for value in values.values())


def test_receptor_order_does_not_change_results(
    binaries: tuple[Path, Path], tmp_path: Path
) -> None:
    first = copy_case(tmp_path, "original-order")
    second = copy_case(tmp_path, "reversed-order")
    receptor_file = second / "receptors.txt"
    receptor_lines = receptor_file.read_text(encoding="ascii").splitlines()
    receptor_lines[3:] = reversed(receptor_lines[3:])
    receptor_file.write_text("\n".join(receptor_lines) + "\n", encoding="ascii")

    first_result = run_model(binaries[0], first)
    second_result = run_model(binaries[0], second)
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr

    first_values = output_values(first)
    second_values = output_values(second)
    assert first_values.keys() == second_values.keys()
    for coordinates, first_value in first_values.items():
        assert math.isclose(first_value, second_values[coordinates], rel_tol=1e-12, abs_tol=1e-15)


def test_analytical_xwd_zero_limit_is_initialized(
    binaries: tuple[Path, Path], tmp_path: Path
) -> None:
    case = copy_case(tmp_path, "analytical-limit")
    fields = source_fields(case)
    fields[4:7] = ["0.0", "10.0", "1.0"]
    set_source_fields(case, fields)
    (case / "receptors.txt").write_text(
        "Receptor input file\n"
        "X_coordinate Y_coordinate Z_coordinate\n"
        "--------------------------------------------------\n"
        "0.0 20.0 1.5\n",
        encoding="ascii",
    )
    set_control_option(case, "Use analytical solution", "Y")

    result = run_model(binaries[0], case)
    assert result.returncode == 0, result.stdout + result.stderr
    values = output_values(case)
    assert len(values) == 1
    assert all(math.isfinite(value) and value >= 0.0 for value in values.values())


def test_zero_length_source_is_rejected(binaries: tuple[Path, Path], tmp_path: Path) -> None:
    case = copy_case(tmp_path, "zero-length")
    fields = source_fields(case)
    fields[4:7] = fields[1:4]
    set_source_fields(case, fields)

    result = run_model(binaries[0], case)
    assert result.returncode != 0
    assert "zero-length source" in (result.stdout + result.stderr).lower()


def test_second_barrier_is_rejected(binaries: tuple[Path, Path], tmp_path: Path) -> None:
    case = copy_case(tmp_path, "second-barrier")
    fields = source_fields(case)
    fields[13] = "2.0"
    set_source_fields(case, fields)

    result = run_model(binaries[0], case)
    assert result.returncode != 0
    assert "second barrier" in (result.stdout + result.stderr).lower()


def test_invalid_meteorology_is_marked_missing(
    binaries: tuple[Path, Path], tmp_path: Path
) -> None:
    case = copy_case(tmp_path, "invalid-met")
    met_file = case / "met.sfc"
    lines = met_file.read_text(encoding="ascii").splitlines()
    fields = lines[1].split()
    fields[12] = "-999.0"
    lines[1] = " ".join(fields)
    met_file.write_text("\n".join(lines) + "\n", encoding="ascii")

    result = run_model(binaries[0], case)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "roughness length must be positive" in (result.stdout + result.stderr)
    assert set(output_values(case).values()) == {-99.0}


def test_aermet_stable_wstar_sentinel_is_accepted(
    binaries: tuple[Path, Path], tmp_path: Path
) -> None:
    case = copy_case(tmp_path, "stable-wstar-sentinel")
    met_file = case / "met.sfc"
    lines = met_file.read_text(encoding="ascii").splitlines()
    fields = lines[1].split()
    fields[7] = "-9.0"
    lines[1] = " ".join(fields)
    met_file.write_text("\n".join(lines) + "\n", encoding="ascii")

    result = run_model(binaries[0], case)

    assert result.returncode == 0, result.stdout + result.stderr
    assert all(value >= 0.0 for value in output_values(case).values())


def test_long_input_and_output_names_are_not_truncated(
    binaries: tuple[Path, Path], tmp_path: Path
) -> None:
    case = copy_case(tmp_path, "long-paths")
    source_name = "source_" + "s" * 64 + ".txt"
    receptor_name = "receptors_" + "r" * 64 + ".txt"
    met_name = "meteorology_" + "m" * 64 + ".sfc"
    output_name = "output_" + "o" * 64 + ".csv"

    (case / "sources.txt").rename(case / source_name)
    (case / "receptors.txt").rename(case / receptor_name)
    (case / "met.sfc").rename(case / met_name)
    control = case / "Line_Source_Inputs.txt"
    contents = control.read_text(encoding="ascii")
    contents = contents.replace("'sources.txt'", f"'{source_name}'")
    contents = contents.replace("'receptors.txt'", f"'{receptor_name}'")
    contents = contents.replace("'met.sfc'", f"'{met_name}'")
    contents = contents.replace("'output.csv'", f"'{output_name}'")
    control.write_text(contents, encoding="ascii")

    result = run_model(binaries[0], case)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (case / output_name).is_file()
    assert len(output_values(case, output_name)) == 2
