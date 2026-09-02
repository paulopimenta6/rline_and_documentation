#!/usr/bin/env python3
"""Valida um config.json e gera deterministicamente os insumos do caso."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    CaseConfig,
    PipelineValidationError,
    generate_case,
)


def gerar(config_path: str | Path) -> CaseConfig:
    """Mantem a interface historica, delegando a geracao ao modulo central."""

    return generate_case(config_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera dados de um caso de uso")
    parser.add_argument("config", type=Path, help="caminho do config.json do caso")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = gerar(args.config)
    except PipelineValidationError as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 2

    print(f"Caso gerado: {config.nome}")
    print("  - controles_aermod/RLINE_TEST.INP")
    print("  - rodada_rline/{Source_Road,Receptor_Road,Line_Source_Inputs}.txt")
    print(f"  - {config.numero_receptores} receptores (grid {config.grid.xn}x{config.grid.yn})")
    print(
        f"  - rodovia (0, {config.y_rodovia:g})..({config.comprimento:g}, {config.y_rodovia:g}) m"
    )
    print(f"  - Emis RLINE = {config.emissao_rline:g} g/m/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
