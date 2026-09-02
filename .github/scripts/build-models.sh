#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
JOBS="${JOBS:-2}"
MODE="${1:-all}"

if [[ ! "$JOBS" =~ ^[1-9][0-9]*$ ]]; then
    printf 'JOBS must be a positive integer, got: %s\n' "$JOBS" >&2
    exit 2
fi

case "$MODE" in
    all | aermet | aermod | rline-original | rline-corrected | rline-patched)
        ;;
    *)
        printf 'Usage: %s [all|aermet|aermod|rline-original|rline-corrected]\n' \
            "$0" >&2
        exit 2
        ;;
esac

STATE_DIR="$(mktemp -d)"
trap 'rm -rf -- "$STATE_DIR"' EXIT

record_git_state() {
    local prefix="$1"
    git -C "$ROOT" status --porcelain=v1 --untracked-files=all > "$STATE_DIR/$prefix.status"
    git -C "$ROOT" diff --binary HEAD > "$STATE_DIR/$prefix.diff"
}

verify_git_state() {
    record_git_state after
    if cmp -s "$STATE_DIR/before.status" "$STATE_DIR/after.status" && \
        cmp -s "$STATE_DIR/before.diff" "$STATE_DIR/after.diff"; then
        printf '==> Build left the Git worktree unchanged\n'
        return 0
    fi

    printf 'Build modified files outside the ignored build tree:\n' >&2
    git -C "$ROOT" status --short --untracked-files=all >&2
    return 1
}

record_git_state before

case "$MODE" in
    all)
        printf '==> Clean-building all model variants under build/\n'
        make --no-print-directory -C "$ROOT" clean
        make --no-print-directory -C "$ROOT" -j "$JOBS" models rline-debug
        ;;
    aermet)
        make --no-print-directory -C "$ROOT" clean-aermet
        make --no-print-directory -C "$ROOT" -j "$JOBS" aermet
        ;;
    aermod)
        make --no-print-directory -C "$ROOT" clean-aermod
        make --no-print-directory -C "$ROOT" -j "$JOBS" aermod
        ;;
    rline-original)
        make --no-print-directory -C "$ROOT" clean-rline-original
        make --no-print-directory -C "$ROOT" -j "$JOBS" rline-original
        ;;
    rline-corrected | rline-patched)
        make --no-print-directory -C "$ROOT" rline-clean
        make --no-print-directory -C "$ROOT" -j "$JOBS" rline-release rline-debug
        ;;
esac

case "$MODE" in
    all)
        test -x "$ROOT/build/aermet/aermet"
        test -x "$ROOT/build/aermod/aermod"
        test -x "$ROOT/build/rline-original/RLINEv1_2_gfortran.x"
        test -x "$ROOT/build/rline-patched/RLINEv1_2_patched.x"
        test -x "$ROOT/build/rline-patched-debug/RLINEv1_2_patched_debug.x"
        ;;
    aermet)
        test -x "$ROOT/build/aermet/aermet"
        ;;
    aermod)
        test -x "$ROOT/build/aermod/aermod"
        ;;
    rline-original)
        test -x "$ROOT/build/rline-original/RLINEv1_2_gfortran.x"
        ;;
    rline-corrected | rline-patched)
        test -x "$ROOT/build/rline-patched/RLINEv1_2_patched.x"
        test -x "$ROOT/build/rline-patched-debug/RLINEv1_2_patched_debug.x"
        ;;
esac

verify_git_state
