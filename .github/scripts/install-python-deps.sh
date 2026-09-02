#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python -m pip install --upgrade pip

manifest_found=false
locked_install=false
if [[ -f uv.lock && -f pyproject.toml ]]; then
    locked_requirements="$(mktemp)"
    trap 'rm -f -- "$locked_requirements"' EXIT
    python -m pip install 'uv==0.12.2'
    uv export --frozen --extra dev --no-emit-project --no-hashes \
        --output-file "$locked_requirements"
    python -m pip install -r "$locked_requirements"
    python -m pip install --no-deps -e .
    manifest_found=true
    locked_install=true
else
    for requirements_file in requirements.txt requirements-dev.txt requirements-test.txt; do
        if [[ -f "$requirements_file" ]]; then
            python -m pip install -r "$requirements_file"
            manifest_found=true
        fi
    done
fi

if [[ "$locked_install" != true && -f pyproject.toml ]]; then
    install_target="."
    if python -c \
        "import tomllib; data=tomllib.load(open('pyproject.toml', 'rb')); raise SystemExit('dev' not in data.get('project', {}).get('optional-dependencies', {}))"; then
        install_target=".[dev]"
    fi
    python -m pip install -e "$install_target"
    manifest_found=true
elif [[ -f setup.py || -f setup.cfg ]]; then
    python -m pip install -e .
    manifest_found=true
fi

if [[ "$manifest_found" != true ]]; then
    printf '%s\n' \
        'No Python dependency manifest found; installing the documented legacy runtime dependencies.'
    python -m pip install \
        'numpy>=1.24' \
        'pandas>=1.5' \
        'matplotlib>=3.6' \
        'jsonschema>=4'
fi

# Keep the test runner available when an unlocked manifest has no development extra.
if [[ "$locked_install" != true ]]; then
    python -m pip install 'pytest>=8,<10'
fi
python -m pip check
