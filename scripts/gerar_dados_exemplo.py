#!/usr/bin/env python3
"""Create a deterministic example bundle below build/examples, then publish atomically."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline.example_data import (  # noqa: E402
    SCENARIOS,
    generate_onsite_text,
    get_example_scenario,
)
from rline_pipeline.generation import generate_case  # noqa: E402

EXAMPLES_ROOT = ROOT / "build" / "examples"
GENERATOR_ID = "rline-safe-example-v1"
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _resolve_destination(output: Path | None, name: str) -> Path:
    allowed = EXAMPLES_ROOT.resolve()
    candidate = allowed / name if output is None else output
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    destination = candidate.resolve()
    try:
        destination.relative_to(allowed)
    except ValueError as error:
        raise ValueError(f"destino deve permanecer dentro de {allowed}") from error
    if destination == allowed:
        raise ValueError("destino deve ser uma subpasta nomeada de build/examples")
    return destination


def _adapt_control(content: str, last_day: int) -> str:
    expected = "1988/3/1 TO 1988/3/5"
    if expected not in content:
        raise ValueError("template AERMET nao contem o intervalo de datas esperado")
    return content.replace(expected, f"1988/3/1 TO 1988/3/{last_day}")


def _case_config(name: str, periods: int, scenario: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "nome": name,
        "descricao": f"Exemplo sintetico seguro {scenario}: rodovia de 200 m e grade 5x5",
        "comprimento": 200.0,
        "y_rodovia": 0.0,
        "qs": 0.001,
        "width": 20.0,
        "grid": {
            "xini": 0.0,
            "xn": 5,
            "xdelta": 50.0,
            "yini": -100.0,
            "yn": 5,
            "ydelta": 50.0,
        },
        "transecto_x": 100.0,
        "periodos_esperados": periods,
    }


def _execution_guide(name: str) -> str:
    relative = f"build/examples/{name}"
    return f"""# Execução segura do exemplo `{name}`

Este pacote contém dados **sintéticos**, destinados exclusivamente a testes de
software. Ele não demonstra conformidade regulatória nem validade científica.

```bash
make models
bash scripts/run_aermet.sh {relative}/meteorology
DIR_DADOS_AERMET={relative}/meteorology \\
  bash scripts/run_caso.sh {relative}/case
python scripts/teste_casos.py {relative}/case
```

Os wrappers usam staging, locks, timeouts, validação e manifests de execução. Os
resultados só são publicados após a conclusão das verificações estruturais.
"""


def _manifest_files(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): _sha256(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "example-manifest.json"
    }


def _verify_replace_target(destination: Path) -> None:
    manifest_path = destination / "example-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"recusa de sobrescrita: {destination} nao possui manifesto valido"
        ) from error
    if manifest.get("generator") != GENERATOR_ID or not isinstance(manifest.get("files"), dict):
        raise ValueError("recusa de sobrescrita: destino nao foi criado por este gerador")
    expected_files = manifest["files"]
    actual_paths = {
        str(path.relative_to(destination))
        for path in destination.rglob("*")
        if path.is_file() and path.name != "example-manifest.json"
    }
    if actual_paths != set(expected_files):
        raise ValueError("recusa de sobrescrita: destino contem arquivos novos ou ausentes")
    for relative, expected_hash in expected_files.items():
        if _sha256(destination / relative) != expected_hash:
            raise ValueError(f"recusa de sobrescrita: arquivo foi alterado: {relative}")


def _publish(staging: Path, destination: Path, *, replace_generated: bool) -> None:
    if not destination.exists():
        os.replace(staging, destination)
        return
    if not replace_generated:
        raise ValueError(
            f"destino ja existe: {destination}; use --replace-generated apenas se estiver intacto"
        )
    if not destination.is_dir() or destination.is_symlink():
        raise ValueError("recusa de sobrescrita: destino nao e uma pasta regular")
    _verify_replace_target(destination)
    backup = destination.with_name(f".{destination.name}.previous")
    if backup.exists():
        raise ValueError(f"backup de publicacao ja existe: {backup}")
    os.replace(destination, backup)
    try:
        os.replace(staging, destination)
    except OSError:
        os.replace(backup, destination)
        raise
    shutil.rmtree(backup)


def create_example_bundle(
    *,
    scenario_name: str,
    seed: int,
    name: str,
    output: Path | None = None,
    replace_generated: bool = False,
) -> Path:
    """Build and atomically publish one safe example bundle."""

    if not NAME_PATTERN.fullmatch(name):
        raise ValueError("nome deve conter somente letras, numeros, '_' ou '-'")
    scenario = get_example_scenario(scenario_name)
    destination = _resolve_destination(output, name)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f".{name}.", dir=destination.parent) as temporary:
        staging = Path(temporary) / "bundle"
        case_dir = staging / "case"
        met_dir = staging / "meteorology"
        case_dir.mkdir(parents=True)
        met_dir.mkdir(parents=True)

        config = _case_config(name, scenario.periods, scenario.name)
        config_path = case_dir / "config.json"
        config_path.write_text(_json_text(config), encoding="utf-8", newline="\n")
        generate_case(config_path, output_dir=case_dir)

        onsite_text, qa = generate_onsite_text(scenario.name, seed=seed)
        (met_dir / "ONSITE.MET").write_text(onsite_text, encoding="utf-8", newline="\n")
        (met_dir / "synthetic-data-qa.json").write_text(
            _json_text(qa), encoding="utf-8", newline="\n"
        )
        for control_name in ("ONSITE_S1.INP", "ONSITE_S2.INP"):
            template = ROOT / "Caso_Pipeline" / "dados_aermet" / control_name
            adapted = _adapt_control(template.read_text(encoding="utf-8"), scenario.days[-1])
            (met_dir / control_name).write_text(adapted, encoding="utf-8", newline="\n")

        (staging / "EXECUCAO.md").write_text(
            _execution_guide(name), encoding="utf-8", newline="\n"
        )
        manifest = {
            "schema_version": 1,
            "generator": GENERATOR_ID,
            "evidence_class": "software-regression",
            "synthetic": True,
            "scenario": scenario.name,
            "seed": seed,
            "periods": scenario.periods,
            "files": _manifest_files(staging),
        }
        (staging / "example-manifest.json").write_text(
            _json_text(manifest), encoding="utf-8", newline="\n"
        )
        _publish(staging, destination, replace_generated=replace_generated)
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="smoke-crosswind")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--name", help="nome da subpasta; padrao: nome do cenario")
    parser.add_argument("--output", type=Path, help="destino dentro de build/examples")
    parser.add_argument(
        "--replace-generated",
        action="store_true",
        help="substitui somente um pacote intacto criado por este gerador",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    name = args.name or args.scenario
    try:
        destination = create_example_bundle(
            scenario_name=args.scenario,
            seed=args.seed,
            name=name,
            output=args.output,
            replace_generated=args.replace_generated,
        )
    except (OSError, ValueError) as error:
        print(f"ERRO: {error}")
        return 2
    print(f"Exemplo sintetico publicado em: {destination}")
    print(f"Instrucoes: {destination / 'EXECUCAO.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
