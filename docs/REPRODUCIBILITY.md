# Reproducibility

This repository compares AERMOD with original and locally corrected RLINE
implementations. A result is reproducible only when its source variant, inputs,
environment, command, and comparison rule are identified.

## Result Classes

- **Upstream original:** the unmodified RLINE v1.2 snapshot under
  `RLINE_v1_2.Source/v1_2/`.
- **Locally corrected:** the upstream snapshot plus the eight ordered patches
  under `patches/rline-v1.2/`, applied only to a temporary build tree.
- **Golden:** a maintainer-reviewed numerical baseline that tests read but do
  not replace.
- **Generated:** disposable output from one execution. A generated or tracked
  file is not automatically a golden.

Always distinguish AERMOD, original RLINE, and corrected RLINE outputs.
Cross-model agreement is evidence for review, not regulatory approval.

## Environment

The supported Python contract is 3.11 or newer. Runtime and development
dependencies are declared in `pyproject.toml`:

```bash
python3 -m venv .venv
. .venv/bin/activate
bash .github/scripts/install-python-deps.sh
```

The repository helper pins `uv==0.12.2`, exports the development resolution
from `uv.lock` with `--frozen`, installs the exported dependencies, and then
installs the project editable with `--no-deps`. Direct
`python -m pip install -e '.[dev]'` remains an unlocked convenience for
exploratory development; it is not the release or CI contract.

Model builds require GNU Make, GNU Fortran, and `patch`. Transactional wrappers
also require `flock` and `setsid`.

For a publication or release candidate, start from a clean revision and use a
disposable worktree:

```bash
git worktree add --detach /tmp/rline-regression HEAD
cd /tmp/rline-regression
bash .github/scripts/install-python-deps.sh
bash .github/scripts/build-models.sh all
RUN_FULL_PIPELINE=1 bash .github/scripts/run-scientific-regression.sh
```

Generated files then remain outside the contributor's primary checkout. The
scientific workflow also checks that versioned model results are unchanged.

## Build Contract

The top-level `Makefile` is authoritative. It copies source files into isolated
directories under `build/`; it does not place objects, modules, or new binaries
in source trees.

| Target | Output |
|---|---|
| `make aermet` | `build/aermet/aermet` |
| `make aermod` | `build/aermod/aermod` |
| `make rline-original` | `build/rline-original/RLINEv1_2_gfortran.x` |
| `make rline-release` | `build/rline-patched/RLINEv1_2_patched.x` |
| `make rline-debug` | `build/rline-patched-debug/RLINEv1_2_patched_debug.x` |
| `make models` | AERMET, AERMOD, original RLINE, and corrected release RLINE |

`make models` first checks the three local source snapshots. AERMET and AERMOD
are checked against the manifests under `provenance/`; these manifests establish
local identity but do not, without a recorded official ZIP hash, prove official
download equivalence. RLINE is checked against
`patches/rline-v1.2/UPSTREAM_SHA256.txt`. The corrected build then normalizes
line endings in its copied tree and applies all eight patches with zero fuzz.

The four historical comparisons under `casos/` have a
`baseline-manifest.json`. It verifies their controls, outputs and exact shared
meteorology before analysis, so a clean checkout does not depend on ignored
per-case meteorology copies.

Each corrected build writes `BUILD-INFO.txt` with the variant, compiler flags,
compiler version, executable checksum, and patch checksums. The debug target
adds runtime checks, sentinel initialization, backtraces, and IEEE traps. The
upstream tree remains untouched.

The CI helper performs clean builds, includes the corrected debug target, checks
every expected executable, and verifies that the Git worktree state did not
change:

```bash
bash .github/scripts/build-models.sh all
```

## Fast Verification

The ordinary local contract is:

```bash
make test
make quality
```

`make test` runs `pytest -m "not scientific"`; 72 tests are collected in the
repository state dated 2026-08-27. They cover configuration, deterministic
generation, strict parsing, real versioned cases, plots, wrapper failure modes,
RLINE release/debug behavior, and regression comparison logic.

`make quality` runs Ruff and validates Bash syntax. These targets do not update
goldens.

## Transactional Execution

The default wrapper executables are:

- `build/aermet/aermet`;
- `build/aermod/aermod`;
- `build/rline-patched/RLINEv1_2_patched.x`.

Historical tracked binaries are not wrapper defaults. An explicit `BIN_AERMET`,
`BIN_AERMOD`, or `BIN_RLINE` override is required to use another executable.

The wrappers acquire non-blocking destination locks, reject symlinked runtime
paths, stage inputs in exclusive workspaces, remove stale outputs there, and run
models in separate process groups. Timeout or interruption sends `TERM` and
then `KILL` to the whole process group and waits for cleanup.

After validation, every output is copied to a temporary file adjacent to its
target and each replacement is atomic on the target filesystem. Backups remain
available until the run manifest succeeds, and handled publication or manifest
failures roll the installed set back. Multiple target paths are not exposed as
one atomic snapshot: an unlocked reader can observe intermediate replacements,
and abrupt `SIGKILL` or power loss is not covered by a durable journal.

Each wrapper creates a unique log and adjacent `*.manifest.json` under the
destination's `logs/` directory. Manifest schema v1 records timestamps,
duration, Git revision and dirty state, executable/input/output/log checksums,
command exit codes, timeout status, and kill grace period. Build flags and
compiler details remain in the corrected build's `BUILD-INFO.txt`.

## Data Contracts

Case configurations use JSON Schema v1 from
`rline_pipeline/schemas/case-config-v1.schema.json`. Unknown fields, invalid
physical ranges, non-finite values, and inconsistent road/grid/transect geometry
are rejected before generation. Each axis requires at least two distinct
coordinates after conversion to `float`, and a grid may contain at most
1,000,000 receptors. Regeneration invalidates prior derived outputs when any
effective model input changes.

The central parsers require:

- the expected AERMOD header, ten columns, `PERIOD` averaging, finite
  non-negative values, unique coordinates, expected receptor count, declared
  total count, and the exact expected meteorological periods;
- the expected 12-line RLINE header, seven data columns plus an optional empty
  trailing field, finite non-negative values, unique receptor-period keys, and
  exactly every expected period for every receptor;
- valid meteorological year, Julian day, and hour fields, including leap-year
  calendars, with calm or missing AERMOD hours represented by zero;
- a bijective coordinate match to the declared grid;
- a one-to-one AERMOD/RLINE merge without coordinate rounding.

The RLINE parser retains the final data row; it does not use `skipfooter`.
Plots use a validated Y-by-X pivot, the configured road endpoints, and the
configured perpendicular transect.

## Scientific Regression

Run the isolated EPA and project regression with:

```bash
make scientific-regression
```

The target builds the model variants, runs the non-scientific pytest suite,
validates exactly the four versioned configured cases, and executes the Example
Case, CALTRANS, Idaho Falls, and Raleigh in temporary directories. Every ordered
key and every concentration column is compared against its golden. Corrected
and original RLINE are each run twice by default; every corrected run must be
deterministic and within tolerance, while the original result is diagnostic.

The corrected-variant limits and observed maximum relative differences are:

| Case | Observed maximum | Limit |
|---|---:|---:|
| Example Case | 1.789152% | 1.9% |
| CALTRANS | 0.523329% | 0.55% |
| Idaho Falls | 0.088408% | 0.095% |
| Raleigh | 0.314472% | 0.33% |

All four observations are within their documented limits. The absolute
tolerance is `1e-6` output units and is used only near a zero golden value; the
per-case rationale is encoded in `scripts/scientific_regression.py` and emitted
in the JSON report.

Set `RUN_FULL_PIPELINE=1` to add model execution from generated inputs:

```bash
RUN_FULL_PIPELINE=1 make scientific-regression
```

The full-pipeline branch first runs the canonical pipeline with AERMET Stages 1
and 2, AERMOD, corrected RLINE, and post-processing. It then regenerates and
runs all four configured cases. Work is performed under temporary directories;
logs and manifests are copied to `REGRESSION_ARTIFACT_DIR`.

`FULL_PIPELINE_TIMEOUT_SECONDS` defaults to 21,600 seconds locally and is also
used as the default budget for nested pipeline, case, and RLINE wrappers. An
explicit wrapper-specific timeout environment variable still takes precedence.
The four independent configured cases run with bounded parallelism, limited to
the available CPU count and at most four workers. Set `MAX_PARALLEL_CASES=1`
to force sequential execution.

By default, the report is
`build/scientific-regression/scientific-regression-report.json`. Override its
root with `REGRESSION_ARTIFACT_DIR`. The schema-v2 report is written atomically
under an exclusive artifact-directory lock and records Git state plus hashes of
case inputs, golden files, executables, and generated outputs.

## CI Separation

`.github/workflows/ci.yml` runs on pushes, pull requests, and manual requests.
It installs Python 3.11 dependencies, validates tracked Shell syntax, runs the
fast tests, and clean-builds AERMET, AERMOD, original RLINE, corrected release
RLINE, and corrected debug RLINE.

`.github/workflows/scientific-regression.yml` runs weekly and manually. It
creates an isolated worktree, rebuilds all variants, sets
`RUN_FULL_PIPELINE=1`, runs the complete regression, rejects changes to
versioned results, and uploads logs, manifests, the report, and environment
metadata. It never updates or publishes golden files.

## Minimum Run Record

For a result used in review or publication, retain:

- Git revision and whether the source worktree was clean;
- model name, upstream version, and original or corrected variant;
- patch identifiers and `BUILD-INFO.txt` for a corrected build;
- operating system, architecture, compiler version, and compiler flags;
- Python version and resolved dependency versions;
- exact command, effective configuration, inputs, exit status, and duration;
- comparison tolerance and differences from the selected golden;
- wrapper log and manifest, when a wrapper produced the result.

The checksum manifest establishes the identity of the RLINE source snapshot.
It does not make a licensing determination. Preserve upstream notices and
consult the terms supplied with each third-party component.
