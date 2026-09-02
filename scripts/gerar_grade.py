#!/usr/bin/env python3
"""Gera receptores e fonte RLINE usando a grade decimal do modulo central."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    SCHEMA_VERSION,
    CaseConfig,
    GridConfig,
    PipelineValidationError,
    validate_case_config,
)
from rline_pipeline.generation import (  # noqa: E402
    build_receptor_file,
    build_source_file,
)
from rline_pipeline._io import publish_file_set  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera grade de receptores e fonte RLINE")
    parser.add_argument("--saida", type=Path, default=Path("Caso_Pipeline/rodada_rline"))
    parser.add_argument("--xini", type=float, default=0.0)
    parser.add_argument("--xn", type=int, default=26)
    parser.add_argument("--xdelta", type=float, default=40.0)
    parser.add_argument("--yini", type=float, default=-300.0)
    parser.add_argument("--yn", type=int, default=31)
    parser.add_argument("--ydelta", type=float, default=20.0)
    parser.add_argument("--comprimento", type=float, default=1000.0)
    parser.add_argument("--qs", type=float, default=0.001)
    parser.add_argument("--width", type=float, default=20.0)
    parser.add_argument("--emis", type=float, default=None)
    return parser


def _config_from_args(args: argparse.Namespace) -> CaseConfig:
    grid = GridConfig(
        xini=args.xini,
        xn=args.xn,
        xdelta=args.xdelta,
        yini=args.yini,
        yn=args.yn,
        ydelta=args.ydelta,
    )
    overlap_start = max(0.0, grid.xini)
    overlap_end = min(args.comprimento, grid.xmax)
    transect = (overlap_start + overlap_end) / 2.0
    config = CaseConfig(
        schema_version=SCHEMA_VERSION,
        nome="grade_avulsa",
        descricao="Grade avulsa gerada pela interface de linha de comando",
        comprimento=args.comprimento,
        y_rodovia=0.0,
        qs=args.qs,
        width=args.width,
        grid=grid,
        transecto_x=transect,
        periodos_esperados=120,
        emis_fator=args.emis,
    )
    validate_case_config(config)
    return config


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _config_from_args(args)
    except PipelineValidationError as error:
        print(f"ERRO: parametros invalidos: {error}", file=sys.stderr)
        return 2

    output_dir = args.saida.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    receptor_path = output_dir / "Receptor_Road.txt"
    source_path = output_dir / "Source_Road.txt"
    with tempfile.TemporaryDirectory(prefix="rline-grid-") as temporary:
        staging = Path(temporary)
        staged_receptors = staging / receptor_path.name
        staged_source = staging / source_path.name
        staged_receptors.write_text(build_receptor_file(config), encoding="utf-8", newline="\n")
        staged_source.write_text(build_source_file(config), encoding="utf-8", newline="\n")
        publish_file_set(((staged_receptors, receptor_path), (staged_source, source_path)))

    print(f"Receptores gerados: {config.numero_receptores}")
    print(f"Arquivo de receptores: {receptor_path}")
    print(f"Arquivo de fontes   : {source_path}")
    print(f"Emis (g/s/m): {config.emissao_rline:g} | comprimento (m): {config.comprimento:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
