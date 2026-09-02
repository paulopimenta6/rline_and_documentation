from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_AERMET = REPO_ROOT / "scripts" / "run_aermet.sh"
RUN_AERMOD = REPO_ROOT / "scripts" / "run_aermod.sh"
RUN_RLINE = REPO_ROOT / "scripts" / "run_rline.sh"
RUN_COMMON = REPO_ROOT / "scripts" / "lib" / "run_common.sh"

VALID_RLINE_OUTPUT = """RLINEv1_2
SOURCE FILE: Source_Road.txt
RECEPTOR FILE: Receptor_Road.txt
SURFACE FILE: ONSITE.SFC
Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_HWY,
1988, 61, 1, 0.0, 0.0, 0.0, 1.0,
"""


def write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nset -u\n" + body, encoding="utf-8")
    path.chmod(0o755)


def prepare_rline_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "Source_Road.txt").write_text("source input\n", encoding="utf-8")
    (path / "Receptor_Road.txt").write_text(
        "receptor input\nX Y Z\n---\n0.0 0.0 0.0\n", encoding="utf-8"
    )
    (path / "ONSITE.SFC").write_text(
        "meteorology input\n"
        "1988 3 1 61 1 -10.0 0.2 -9.0 -9.0 -999.0 100.0 -100.0 "
        "0.1 1.0 0.2 3.0 270.0 10.0 290.0 2.0\n",
        encoding="utf-8",
    )
    (path / "Line_Source_Inputs.txt").write_text(
        """User control file for RLINEv1_2
Source File Name
'Source_Road.txt'
Receptor File Name
'Receptor_Road.txt'
Input Met File
'./ONSITE.SFC'
Receptor Output File
'Output_Road_Numerical.csv'
""",
        encoding="utf-8",
    )


def run_script(
    script: Path, *arguments: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        RUN_TIMEOUT_SECONDS="3",
        RUN_KILL_GRACE_SECONDS="0.2",
        LC_ALL="C",
    )
    if extra_env:
        environment.update(extra_env)
    return subprocess.run(
        ["bash", str(script), *arguments],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=12,
        check=False,
    )


def manifests(run_directory: Path, component: str) -> list[Path]:
    return sorted((run_directory / "logs").glob(f"{component}-*.manifest.json"))


class WrapperTests(unittest.TestCase):
    def test_publish_stages_replacements_on_target_filesystem(self) -> None:
        shared_memory = Path("/dev/shm")
        if not shared_memory.is_dir():
            self.skipTest("/dev/shm is unavailable")
        with tempfile.TemporaryDirectory(prefix="publish-source-") as source_temporary:
            source_root = Path(source_temporary)
            if source_root.stat().st_dev == shared_memory.stat().st_dev:
                self.skipTest("temporary source and /dev/shm use the same filesystem")
            with tempfile.TemporaryDirectory(
                prefix="publish-target-", dir=shared_memory
            ) as target_temporary:
                target_root = Path(target_temporary)
                source = source_root / "new-output"
                target = target_root / "output"
                source.write_text("new\n", encoding="utf-8")
                target.write_text("old\n", encoding="utf-8")

                command = f"""
set -u
RAIZ={str(REPO_ROOT)!r}
source {str(RUN_COMMON)!r}
RUN_LOG={str(source_root / "publish.log")!r}
RUN_WORKSPACE={str(source_root)!r}
RUN_ID=test-filesystem
RUN_PUBLISH_DIR=''
RUN_PUBLISH_TARGETS=()
RUN_PUBLISH_BACKUPS=()
mv() {{
    source_path="${{@: -2:1}}"
    target_path="${{@: -1}}"
    source_device="$(stat -c %d -- "$(dirname -- "$source_path")")"
    target_device="$(stat -c %d -- "$(dirname -- "$target_path")")"
    [[ "$source_device" == "$target_device" ]] || return 89
    command mv "$@"
}}
publish_mapped_files {str(source)!r} {str(target)!r}
_commit_publish
"""
                result = subprocess.run(
                    ["bash", "-c", command],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_publish_set_rolls_back_if_a_later_target_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="publish-rollback-") as temporary:
            root = Path(temporary)
            source_one = root / "new-one"
            source_two = root / "new-two"
            destination_one = root / "destination-one"
            destination_two = root / "destination-two"
            source_one.write_text("new one\n", encoding="utf-8")
            source_two.write_text("new two\n", encoding="utf-8")
            destination_one.write_text("old one\n", encoding="utf-8")
            destination_two.write_text("old two\n", encoding="utf-8")

            command = f"""
set -u
RAIZ={str(REPO_ROOT)!r}
source {str(RUN_COMMON)!r}
RUN_LOG={str(root / "publish.log")!r}
RUN_WORKSPACE={str(root)!r}
RUN_ID=test-publish
RUN_PUBLISH_DIR=''
RUN_PUBLISH_TARGETS=()
RUN_PUBLISH_BACKUPS=()
move_count=0
mv() {{
    move_count=$((move_count + 1))
    if (( move_count == 2 )); then
        return 1
    fi
    command mv "$@"
}}
if publish_mapped_files \
    {str(source_one)!r} {str(destination_one)!r} \
    {str(source_two)!r} {str(destination_two)!r}; then
    exit 99
fi
"""
            result = subprocess.run(
                ["bash", "-c", command],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(destination_one.read_text(encoding="utf-8"), "old one\n")
            self.assertEqual(destination_two.read_text(encoding="utf-8"), "old two\n")
            self.assertEqual(list(root.glob(".*.publish.*")), [])
            self.assertEqual(list(root.glob(".*.backup.*")), [])

    def test_manifest_failure_rolls_back_published_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-manifest-failure-") as temporary:
            root = Path(temporary)
            run_directory = root / "run"
            executable = root / "fake-rline"
            prepare_rline_directory(run_directory)
            output = run_directory / "Output_Road_Numerical.csv"
            stale = VALID_RLINE_OUTPUT + "STALE\n"
            output.write_text(stale, encoding="utf-8")
            write_executable(
                executable,
                """printf '%s\n' \\
'RLINEv1_2' \\
'SOURCE FILE: Source_Road.txt' \\
'RECEPTOR FILE: Receptor_Road.txt' \\
'SURFACE FILE: ONSITE.SFC' \\
'Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_HWY,' \\
'1988, 61, 1, 0.0, 0.0, 0.0, 2.0,' > Output_Road_Numerical.csv
""",
            )

            result = run_script(
                RUN_RLINE,
                str(run_directory),
                str(executable),
                extra_env={"RUN_MANIFEST_WRITER": str(root / "missing-writer.py")},
            )

            self.assertEqual(result.returncode, 70, result.stderr + result.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), stale)

    def test_model_does_not_inherit_wrapper_lock_descriptor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-lock-fd-") as temporary:
            root = Path(temporary)
            run_directory = root / "run"
            executable = root / "fake-rline"
            prepare_rline_directory(run_directory)
            write_executable(
                executable,
                """for descriptor in /proc/self/fd/*; do
    target="$(readlink "$descriptor" 2>/dev/null || true)"
    case "$target" in
        *.rline.lock) exit 88 ;;
    esac
done
printf '%s\n' \\
'RLINEv1_2' \\
'SOURCE FILE: Source_Road.txt' \\
'RECEPTOR FILE: Receptor_Road.txt' \\
'SURFACE FILE: ONSITE.SFC' \\
'Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_HWY,' \\
'1988, 61, 1, 0.0, 0.0, 0.0, 2.0,' > Output_Road_Numerical.csv
""",
            )

            result = run_script(RUN_RLINE, str(run_directory), str(executable))

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_parent_waits_for_child_cleanup_on_signal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-child-signal-") as temporary:
            root = Path(temporary)
            destination = root / "destination"
            child = root / "child-wrapper"
            ready = root / "ready"
            cleaned = root / "cleaned"
            write_executable(
                child,
                """trap 'printf cleaned > "$CLEANED_FILE"; exit 143' TERM
printf ready > "$READY_FILE"
while :; do sleep 0.1; done
""",
            )
            command = f"""
set -euo pipefail
RAIZ={str(REPO_ROOT)!r}
source {str(RUN_COMMON)!r}
run_init parent {str(destination)!r} {str(child)!r}
if run_child_command {str(root)!r} 30 child {str(child)!r}; then
    :
else
    status=$?
    run_fail_command child "$status"
fi
run_mark_success
"""
            environment = os.environ.copy()
            environment.update(READY_FILE=str(ready), CLEANED_FILE=str(cleaned))
            process = subprocess.Popen(
                ["bash", "-c", command],
                cwd=REPO_ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(ready.exists(), "child wrapper did not start")

            process.terminate()
            stdout, stderr = process.communicate(timeout=10)

            self.assertEqual(process.returncode, 143, stderr + stdout)
            self.assertTrue(cleaned.exists(), "parent removed staging before child cleanup")
            self.assertEqual(list(root.glob(".parent-workspace.*")), [])

    def test_rline_accepts_double_quoted_control_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-double-quotes-") as temporary:
            root = Path(temporary)
            run_directory = root / "run"
            executable = root / "fake-rline"
            prepare_rline_directory(run_directory)
            control = run_directory / "Line_Source_Inputs.txt"
            control.write_text(
                control.read_text(encoding="utf-8").replace("'", '"'),
                encoding="utf-8",
            )
            write_executable(
                executable,
                """printf '%s\n' \\
'RLINEv1_2' \\
'SOURCE FILE: Source_Road.txt' \\
'RECEPTOR FILE: Receptor_Road.txt' \\
'SURFACE FILE: ONSITE.SFC' \\
'Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_HWY,' \\
'1988, 61, 1, 0.0, 0.0, 0.0, 2.0,' > Output_Road_Numerical.csv
""",
            )

            result = run_script(RUN_RLINE, str(run_directory), str(executable))

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((run_directory / "Output_Road_Numerical.csv").is_file())

    def test_rline_stages_referenced_inputs_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-external-inputs-") as temporary:
            root = Path(temporary)
            run_directory = root / "run"
            shared = root / "shared"
            executable = root / "fake-rline"
            prepare_rline_directory(run_directory)
            shared.mkdir()
            for name in ("Source_Road.txt", "Receptor_Road.txt", "ONSITE.SFC"):
                (run_directory / name).rename(shared / name)
            control = run_directory / "Line_Source_Inputs.txt"
            contents = control.read_text(encoding="utf-8")
            contents = contents.replace("'Source_Road.txt'", "'../shared/Source_Road.txt'")
            contents = contents.replace("'Receptor_Road.txt'", f"'{shared / 'Receptor_Road.txt'}'")
            contents = contents.replace("'./ONSITE.SFC'", "'../shared/ONSITE.SFC'")
            control.write_text(contents, encoding="utf-8")
            write_executable(
                executable,
                """grep -q "'./wrapper_source_input.txt'" Line_Source_Inputs.txt
grep -q "'./wrapper_receptor_input.txt'" Line_Source_Inputs.txt
grep -q "'./ONSITE.SFC'" Line_Source_Inputs.txt
test -s wrapper_source_input.txt
test -s wrapper_receptor_input.txt
test -s ONSITE.SFC
printf '%s\n' \
'RLINEv1_2' \
'SOURCE FILE: wrapper_source_input.txt' \
'RECEPTOR FILE: wrapper_receptor_input.txt' \
'SURFACE FILE: ONSITE.SFC' \
'Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_HWY,' \
'1988, 61, 1, 0.0, 0.0, 0.0, 2.0,' > Output_Road_Numerical.csv
""",
            )

            result = run_script(RUN_RLINE, str(run_directory), str(executable))

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((run_directory / "Output_Road_Numerical.csv").is_file())

    def test_rline_success_with_relative_paths_spaces_and_unique_logs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper paths with spaces ") as temporary:
            root = Path(temporary)
            run_directory = root / "case with spaces" / "rline run"
            executable = root / "fake binaries" / "fake rline success"
            prepare_rline_directory(run_directory)
            (run_directory / "Output_Road_Numerical.csv").write_text(
                VALID_RLINE_OUTPUT + "STALE\n", encoding="utf-8"
            )
            write_executable(
                executable,
                """printf '%s\n' \\
'RLINEv1_2' \\
'SOURCE FILE: Source_Road.txt' \\
'RECEPTOR FILE: Receptor_Road.txt' \\
'SURFACE FILE: ONSITE.SFC' \\
'Year, Julian_Day, Hour, X-Coordinate, Y-Coordinate, Z-Coordinate, C_HWY,' \\
'1988, 61, 1, 0.0, 0.0, 0.0, 2.0,' > Output_Road_Numerical.csv
""",
            )
            relative_run = os.path.relpath(run_directory, REPO_ROOT)
            relative_executable = os.path.relpath(executable, REPO_ROOT)

            first = run_script(RUN_RLINE, relative_run, relative_executable)
            second = run_script(RUN_RLINE, relative_run, relative_executable)

            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            output = (run_directory / "Output_Road_Numerical.csv").read_text(encoding="utf-8")
            self.assertNotIn("STALE", output)
            self.assertIn("2.0", output)
            manifest_paths = manifests(run_directory, "rline")
            self.assertEqual(len(manifest_paths), 2)
            log_paths = list((run_directory / "logs").glob("rline-*.log"))
            self.assertEqual(len(log_paths), 2)
            manifest = json.loads(manifest_paths[-1].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["exit_code"], 0)
            self.assertTrue(manifest["git"]["commit"])
            self.assertIn("dirty", manifest["git"])
            self.assertRegex(manifest["executable"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(manifest["outputs"][0]["sha256"], r"^[0-9a-f]{64}$")
            command_cwd = Path(manifest["commands"][0]["cwd"])
            self.assertEqual(command_cwd.name, "rodada_rline")
            self.assertIn(".rline-workspace.", command_cwd.parent.name)
            self.assertIn("fake\\ rline\\ success", manifest["commands"][0]["command"])
            self.assertEqual(manifest["commands"][0]["timeout_seconds"], 3.0)

    def test_rline_preserves_nonzero_exit_and_does_not_publish(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-exit-") as temporary:
            root = Path(temporary)
            run_directory = root / "run"
            executable = root / "fake-exit"
            prepare_rline_directory(run_directory)
            stale = VALID_RLINE_OUTPUT + "STALE-CONTENT\n"
            (run_directory / "Output_Road_Numerical.csv").write_text(stale, encoding="utf-8")
            write_executable(
                executable,
                """printf '%s\n' 'RLINEv1_2' 'Year, Julian_Day, X-Coordinate' > Output_Road_Numerical.csv
exit 37
""",
            )

            result = run_script(RUN_RLINE, str(run_directory), str(executable))

            self.assertEqual(result.returncode, 37, result.stderr + result.stdout)
            self.assertEqual(
                (run_directory / "Output_Road_Numerical.csv").read_text(encoding="utf-8"),
                stale,
            )
            manifest = json.loads(manifests(run_directory, "rline")[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["exit_code"], 37)
            self.assertEqual(manifest["commands"][0]["exit_code"], 37)

    def test_rline_does_not_accept_old_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-stale-") as temporary:
            root = Path(temporary)
            run_directory = root / "run"
            executable = root / "fake-no-output"
            prepare_rline_directory(run_directory)
            stale = VALID_RLINE_OUTPUT + "VALID-BUT-STALE\n"
            output_path = run_directory / "Output_Road_Numerical.csv"
            output_path.write_text(stale, encoding="utf-8")
            write_executable(executable, "exit 0\n")

            result = run_script(RUN_RLINE, str(run_directory), str(executable))

            self.assertNotEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(output_path.read_text(encoding="utf-8"), stale)
            self.assertIn("nao gerou output novo", result.stderr)

    def test_timeout_kills_process_group_without_active_orphan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wrapper-timeout-") as temporary:
            root = Path(temporary)
            run_directory = root / "run"
            executable = root / "fake-hang"
            orphan_pid_file = root / "descendant.pid"
            prepare_rline_directory(run_directory)
            write_executable(
                executable,
                """(
    trap '' TERM
    while :; do sleep 1; done
) &
descendant=$!
printf '%s\n' "$descendant" > "$ORPHAN_PID_FILE"
trap '' TERM
wait "$descendant"
""",
            )

            started = time.monotonic()
            result = run_script(
                RUN_RLINE,
                str(run_directory),
                str(executable),
                extra_env={
                    "RUN_TIMEOUT_SECONDS": "0.3",
                    "RUN_KILL_GRACE_SECONDS": "0.2",
                    "ORPHAN_PID_FILE": str(orphan_pid_file),
                },
            )
            elapsed = time.monotonic() - started

            self.assertEqual(result.returncode, 124, result.stderr + result.stdout)
            self.assertLess(elapsed, 4)
            descendant_pid = int(orphan_pid_file.read_text(encoding="utf-8").strip())
            deadline = time.monotonic() + 2
            while Path(f"/proc/{descendant_pid}").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertFalse(
                Path(f"/proc/{descendant_pid}").exists(), "descendant survived timeout"
            )
            log_path = next((run_directory / "logs").glob("rline-*.log"))
            self.assertIn("KILL", log_path.read_text(encoding="utf-8"))
            self.assertEqual(list(root.glob(".rline-workspace.*")), [])
            manifest = json.loads(manifests(run_directory, "rline")[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "timeout")
            self.assertEqual(manifest["exit_code"], 124)
            self.assertTrue(manifest["commands"][0]["timed_out"])

    def test_aermod_success_validates_and_publishes_from_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aermod paths with spaces ") as temporary:
            root = Path(temporary)
            run_directory = root / "case" / "aermod run"
            met_directory = root / "met data"
            control = root / "controls" / "control file.INP"
            executable = root / "fake bins" / "fake aermod"
            run_directory.mkdir(parents=True)
            met_directory.mkdir(parents=True)
            control.parent.mkdir(parents=True)
            control.write_text("CO STARTING\n", encoding="utf-8")
            (met_directory / "ONSITE.SFC").write_text("surface\n", encoding="utf-8")
            (met_directory / "ONSITE.PFL").write_text("profile\n", encoding="utf-8")
            (run_directory / "CONC_PLOT.PLT").write_text("STALE\n", encoding="utf-8")
            write_executable(
                executable,
                """control="$1"
stem="${control%.*}"
printf '%s\n' \
    'A Total of 0 Fatal Error Message(s)' \
    'A Total of 1 Hours Were Processed' \
    '*** AERMOD Finishes Successfully ***' > "$stem.out"
printf '%s\n' \
    '* AERMOD' \
    '* AERMET' \
    '* MODELING OPTIONS USED' \
    '* PLOT FILE OF PERIOD VALUES' \
    '* FOR A TOTAL OF 1 RECEPTORS.' \
    '* FORMAT' \
    '* X Y AVERAGE CONC ZELEV ZHILL ZFLAG AVE GRP NUM HRS NET ID' \
    '* ____________' \
    '0.0 0.0 1.0 0.0 0.0 0.0 PERIOD ALL 00000001 GRID' > CONC_PLOT.PLT
""",
            )

            result = run_script(
                RUN_AERMOD,
                str(run_directory),
                str(executable),
                str(control),
                str(met_directory),
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("00000001", (run_directory / "CONC_PLOT.PLT").read_text(encoding="utf-8"))
            self.assertTrue((run_directory / "control file.out").is_file())
            self.assertTrue((run_directory / "ONSITE.SFC").is_file())
            self.assertEqual(len(manifests(run_directory, "aermod")), 1)

    def test_aermet_two_stages_publish_only_after_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aermet-") as temporary:
            root = Path(temporary)
            data_directory = root / "met data"
            executable = root / "fake aermet"
            data_directory.mkdir(parents=True)
            (data_directory / "ONSITE_S1.INP").write_text("stage 1\n", encoding="utf-8")
            (data_directory / "ONSITE_S2.INP").write_text("stage 2\n", encoding="utf-8")
            (data_directory / "ONSITE.MET").write_text("1 3 88 1 data\n", encoding="utf-8")
            (data_directory / "ONSITE.SFC").write_text("STALE\n", encoding="utf-8")
            write_executable(
                executable,
                """case "$1" in
    ONSITE_S1.INP)
        printf '%s\n' 'AERMET FINISHED SUCCESSFULLY' > ONSITE_S1_REPORT.TXT
        printf '%s\n' 'qa output' > ONSITE_QAOUT.TXT
        ;;
    ONSITE_S2.INP)
        printf '%s\n' 'AERMET FINISHED SUCCESSFULLY' > ONSITE_S2_REPORT.RPT
        printf '%s\n' 'HEADER VERSION: 26135' 'new surface' > ONSITE.SFC
        printf '%s\n' '1988 3 1 1 10.0 profile' > ONSITE.PFL
        ;;
    *) exit 9 ;;
esac
""",
            )

            result = run_script(RUN_AERMET, str(data_directory), str(executable))

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn(
                "new surface", (data_directory / "ONSITE.SFC").read_text(encoding="utf-8")
            )
            self.assertTrue((data_directory / "ONSITE.PFL").is_file())
            manifest = json.loads(
                manifests(data_directory, "aermet")[0].read_text(encoding="utf-8")
            )
            self.assertEqual(len(manifest["commands"]), 2)
            self.assertEqual(manifest["status"], "success")


if __name__ == "__main__":
    unittest.main()
