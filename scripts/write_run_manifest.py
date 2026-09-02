#!/usr/bin/env python3
"""Write an atomic JSON provenance manifest for one wrapper execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def describe_path(raw_path: str) -> dict[str, object]:
    path = Path(raw_path).absolute()
    record: dict[str, object] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record

    try:
        mode = path.stat().st_mode
        if stat.S_ISREG(mode):
            record.update(
                type="file",
                size_bytes=path.stat().st_size,
                sha256=hash_file(path),
            )
            return record
        if stat.S_ISDIR(mode):
            digest = hashlib.sha256()
            total_size = 0
            file_count = 0
            for child in sorted(
                (entry for entry in path.rglob("*") if entry.is_file()),
                key=lambda entry: os.fsencode(str(entry.relative_to(path))),
            ):
                relative = os.fsencode(str(child.relative_to(path)))
                child_hash = hash_file(child)
                child_size = child.stat().st_size
                digest.update(relative + b"\0" + child_hash.encode("ascii") + b"\0")
                total_size += child_size
                file_count += 1
            record.update(
                type="directory",
                file_count=file_count,
                size_bytes=total_size,
                sha256=digest.hexdigest(),
            )
            return record
        record["type"] = "other"
    except OSError as exc:
        record["error"] = str(exc)
    return record


def parse_command_result(value: str) -> dict[str, object]:
    fields = value.split("\t", 6)
    if len(fields) != 7:
        raise argparse.ArgumentTypeError("invalid command result")
    label, exit_code, timed_out, duration_ns, cwd, timeout_seconds, command = fields
    return {
        "label": label,
        "command": command,
        "cwd": cwd,
        "timeout_seconds": float(timeout_seconds),
        "exit_code": int(exit_code),
        "timed_out": timed_out == "1",
        "duration_seconds": round(int(duration_ns) / 1_000_000_000, 6),
    }


def iso_from_ns(value: int) -> str:
    return datetime.fromtimestamp(value / 1_000_000_000, timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--component", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--started-ns", required=True, type=int)
    parser.add_argument("--finished-ns", required=True, type=int)
    parser.add_argument("--git-commit", default="")
    parser.add_argument("--git-dirty", choices=("true", "false", "unknown"), default="unknown")
    parser.add_argument("--log", required=True)
    parser.add_argument("--kill-grace-seconds", required=True)
    parser.add_argument("--executable")
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--command-result", action="append", default=[], type=parse_command_result)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    dirty = None if args.git_dirty == "unknown" else args.git_dirty == "true"
    duration = max(0, args.finished_ns - args.started_ns) / 1_000_000_000
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "component": args.component,
        "status": args.status,
        "exit_code": args.exit_code,
        "started_at": args.started_at,
        "finished_at": iso_from_ns(args.finished_ns),
        "duration_seconds": round(duration, 6),
        "git": {"commit": args.git_commit or None, "dirty": dirty},
        "executable": describe_path(args.executable) if args.executable else None,
        "inputs": [describe_path(path) for path in args.input],
        "outputs": [describe_path(path) for path in args.output],
        "log": describe_path(args.log),
        "commands": args.command_result,
        "runtime": {"kill_grace_seconds": args.kill_grace_seconds},
        "repo_root": str(Path(args.repo_root).absolute()),
    }

    destination = Path(args.manifest).absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=destination.parent, delete=False
        ) as stream:
            temporary_name = stream.name
            json.dump(manifest, stream, indent=2, sort_keys=True, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


if __name__ == "__main__":
    main()
