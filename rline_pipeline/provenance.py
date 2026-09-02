"""Verification helpers for immutable, versioned result baselines."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .errors import PipelineValidationError

BASELINE_MANIFEST_FILENAME = "baseline-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise PipelineValidationError(f"nao foi possivel calcular hash de {path}: {error}") from error
    return digest.hexdigest()


def _repository_root(case_dir: Path) -> Path:
    for candidate in (case_dir, *case_dir.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "Caso_Pipeline").is_dir():
            return candidate
    raise PipelineValidationError(f"raiz do repositorio nao encontrada a partir de {case_dir}")


def _safe_resolve(root: Path, relative: str, *, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise PipelineValidationError(f"{label} escapa da raiz permitida: {relative}") from error
    return candidate


def _load_manifest(path: Path) -> Mapping[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineValidationError(f"manifesto de baseline invalido em {path}: {error}") from error
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise PipelineValidationError(f"{path}: schema_version de baseline deve ser 1")
    if raw.get("evidence_class") != "legacy-baseline":
        raise PipelineValidationError(f"{path}: evidence_class deve ser legacy-baseline")
    return raw


def verify_baseline_manifest(case_dir: str | Path) -> dict[str, Path]:
    """Verify every declared file and return resolved shared inputs by name."""

    directory = Path(case_dir).resolve()
    manifest_path = directory / BASELINE_MANIFEST_FILENAME
    manifest = _load_manifest(manifest_path)
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise PipelineValidationError(f"{manifest_path}: files deve ser um objeto nao vazio")
    for relative, expected_hash in files.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise PipelineValidationError(f"{manifest_path}: entrada de arquivo invalida")
        path = _safe_resolve(directory, relative, label="arquivo da baseline")
        if not path.is_file():
            raise PipelineValidationError(f"arquivo da baseline ausente: {path}")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise PipelineValidationError(
                f"hash da baseline diverge para {path}: esperado={expected_hash}, atual={actual_hash}"
            )

    repository = _repository_root(directory)
    shared = manifest.get("shared_inputs")
    if not isinstance(shared, dict) or not shared:
        raise PipelineValidationError(f"{manifest_path}: shared_inputs deve ser um objeto nao vazio")
    resolved: dict[str, Path] = {}
    for name, description in shared.items():
        if not isinstance(name, str) or not isinstance(description, dict):
            raise PipelineValidationError(f"{manifest_path}: shared_input invalido")
        relative = description.get("path")
        expected_hash = description.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise PipelineValidationError(f"{manifest_path}: shared_input {name} incompleto")
        path = _safe_resolve(repository, relative, label="input compartilhado")
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise PipelineValidationError(f"input compartilhado ausente ou divergente: {path}")
        resolved[name] = path
    return resolved
