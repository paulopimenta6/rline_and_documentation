# Contributing

This repository combines locally authored automation with third-party
scientific models, data, binaries, and documentation. Contributions must
preserve that distinction and make every numerical change independently
reviewable.

## Scope Changes Carefully

Use a short-lived branch and keep each pull request focused on one logical
change. Do not mix numerical corrections, golden updates, dependency changes,
generated outputs, and broad formatting.

Never commit secrets, machine-specific paths, local environments, build
products, execution workspaces, or transient logs. Run expensive scientific
models in a disposable worktree rather than over versioned inputs and results.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) in this form:

```text
<type>[optional scope]: <imperative summary>
```

Common types are `feat`, `fix`, `docs`, `test`, `build`, `ci`, `refactor`, and
`chore`. Mark incompatible behavior with `!` and explain it in a
`BREAKING CHANGE:` footer. Keep commits atomic; a numerical fix should include
its focused test and rationale.

Examples:

```text
fix(rline): initialize effective wind before dispersion
test(regression): cover the CALTRANS reference case
docs: align wrapper commands with isolated builds
```

## Third-Party Sources and Patches

Treat the distributed AERMET, AERMOD, and RLINE source snapshots as upstream
material. Preserve original headers and notices. In particular, do not apply a
local RLINE correction directly to `RLINE_v1_2.Source/v1_2/`.

Store RLINE corrections as small ordered patches under
`patches/rline-v1.2/`. A patch must:

- identify the defect, scientific impact, and intended behavior;
- apply non-interactively with zero fuzz to a temporary copy of the checksummed
  upstream snapshot;
- include a focused test that fails before and passes after the correction;
- avoid unrelated reformatting;
- preserve original and corrected builds and outputs as distinct variants;
- update `UPSTREAM_SHA256.txt` only for a separately reviewed provenance
  change, never to conceal an unintended source modification.

If upstream publishes a new version, add it as an explicit provenance update.
Do not silently rewrite an existing snapshot or regenerate patches against an
unidentified source.

## Local Setup

Use Python 3.11 or newer and install the declared development dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
bash .github/scripts/install-python-deps.sh
```

The helper pins `uv==0.12.2`, exports `uv.lock` with `--frozen`, installs those
resolved dependencies, and then installs the project editable without resolving
again. Direct `python -m pip install -e '.[dev]'` is allowed for exploratory
development but is not the reproducible environment contract.

Model builds require GNU Make, GNU Fortran, and `patch`. Wrapper tests and model
execution also require `flock` and `setsid`.

## Local Checks

For ordinary code and documentation changes, run the relevant subset of:

```bash
make quality
make test
make models
make rline-debug
git diff --check
```

The top-level `Makefile` writes all build products below ignored `build/` paths.
`make models` produces AERMET, AERMOD, original RLINE, and corrected release
RLINE; `make rline-debug` adds the diagnostic corrected build. Do not use or
refresh historical binaries in source or case directories as part of normal
verification.

The helper below performs the same clean model build used by CI and verifies
that the Git worktree state is unchanged:

```bash
bash .github/scripts/build-models.sh all
```

In the pull request, list exact commands run, operating system, compiler
version, and every skipped check. A passing historical output is not a
substitute for a fresh test execution.

## Scientific Regression

The standard scientific target runs fast project checks, validates versioned
cases, and compares corrected and diagnostic original RLINE runs with the four
EPA goldens:

```bash
make scientific-regression
```

To also regenerate and execute the canonical AERMET/AERMOD/RLINE pipeline and
all four configured cases:

```bash
RUN_FULL_PIPELINE=1 make scientific-regression
```

Run this expensive form only in a disposable worktree. The full-pipeline branch
runs the canonical AERMET Stages 1/2, AERMOD, corrected RLINE, and
post-processing before the four configured cases. Set
`REGRESSION_ARTIFACT_DIR` when reports, logs, and manifests must be retained.

The original RLINE runs are diagnostic and may expose upstream nondeterminism;
the corrected variant and documented tolerances determine regression success.
See `docs/REPRODUCIBILITY.md` for the exact contract.

## Golden Files

Golden files are reviewed scientific baselines, not ordinary generated output.
Tests must read them without modifying them and must write candidate output to
a temporary or ignored directory.

Do not update a golden merely to make a failing test pass. An intentional
update requires a dedicated pull request or clearly isolated commit containing:

- the scientific reason for the change;
- the exact generation command and model variant;
- compiler, flags, Python, dependency, and platform versions;
- the old-versus-new numerical comparison and justified tolerances;
- review by a maintainer familiar with the affected model and data.

Normal test and regression targets must never overwrite baselines. Preserve the
prior baseline in Git history; do not rewrite history to hide a numerical
change.

## Scientific Claims

Label outputs by model, version, and variant. A local corrected RLINE result is
experimental unless an applicable regulatory process establishes otherwise.
Do not describe repository CI, cross-model correlation, or agreement with a
golden as regulatory approval or EPA endorsement.

Preserve third-party notices and consult the terms supplied with each upstream
distribution. Repository documentation does not assign or infer a license for
third-party material.
