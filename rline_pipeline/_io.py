"""Atomic file publication helpers used by generation and plotting."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterable

from .errors import PipelineValidationError


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_text(path: str | Path, content: str) -> Path:
    """Write UTF-8 text through a same-directory temporary file."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.write.",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        _sync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def publish_file_set(mappings: Iterable[tuple[str | Path, str | Path]]) -> None:
    """Publish regular files with same-filesystem replacement and rollback."""

    prepared: list[tuple[Path, Path, Path | None]] = []
    targets: set[Path] = set()
    installed = 0
    preserve_backups = False
    try:
        for raw_source, raw_target in mappings:
            source = Path(raw_source)
            target = Path(raw_target).absolute()
            if target in targets:
                raise PipelineValidationError(f"destino de publicacao duplicado: {target}")
            targets.add(target)
            if not source.is_file() or source.is_symlink():
                raise PipelineValidationError(
                    f"artefato de publicacao deve ser arquivo regular: {source}"
                )
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise PipelineValidationError(
                    f"destino de publicacao deve ser arquivo regular: {target}"
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            staged_fd, staged_name = tempfile.mkstemp(
                dir=target.parent,
                prefix=f".{target.name}.publish.",
            )
            os.close(staged_fd)
            staged = Path(staged_name)
            shutil.copy2(source, staged)
            with staged.open("rb") as stream:
                os.fsync(stream.fileno())

            backup: Path | None = None
            if target.exists():
                backup_fd, backup_name = tempfile.mkstemp(
                    dir=target.parent,
                    prefix=f".{target.name}.backup.",
                )
                os.close(backup_fd)
                backup = Path(backup_name)
                shutil.copy2(target, backup)
                with backup.open("rb") as stream:
                    os.fsync(stream.fileno())
            prepared.append((target, staged, backup))

        for target, staged, _backup in prepared:
            os.replace(staged, target)
            _sync_directory(target.parent)
            installed += 1
    except Exception as error:
        rollback_errors: list[str] = []
        for target, _staged, backup in reversed(prepared[:installed]):
            try:
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(backup, target)
                _sync_directory(target.parent)
            except OSError as rollback_error:
                rollback_errors.append(f"{target}: {rollback_error}")
        if rollback_errors:
            preserve_backups = True
            details = "; ".join(rollback_errors)
            raise PipelineValidationError(
                f"falha de publicacao ({error}); rollback incompleto: {details}"
            ) from error
        raise
    finally:
        for _target, staged, backup in prepared:
            staged.unlink(missing_ok=True)
            if backup is not None and not preserve_backups:
                backup.unlink(missing_ok=True)
