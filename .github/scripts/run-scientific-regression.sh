#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

printf '==> Running scientific-regression (RUN_FULL_PIPELINE=%s)\n' \
    "${RUN_FULL_PIPELINE:-0}"
make --no-print-directory -C "$ROOT" scientific-regression
