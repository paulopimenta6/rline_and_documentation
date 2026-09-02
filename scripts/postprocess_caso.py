#!/usr/bin/env python3
"""Interface de linha de comando para o pos-processamento central."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    PipelineValidationError,
    load_case_config,
    load_case_results,
    process_case,
)


def carregar(
    caso_dir: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Mantem a API historica e retorna AERMOD, media RLINE e merge validado."""

    _config, aermod, _rline, rline_period, merged = load_case_results(caso_dir)
    return aermod, rline_period, merged


def comprimento_rodovia(caso_dir: str | Path) -> float:
    return load_case_config(Path(caso_dir) / "config.json").comprimento


def gerar_graficos(
    caso_dir: str | Path, transecto_x: float | None = None
) -> dict[str, float | int]:
    metrics, paths = process_case(caso_dir, transect_x=transecto_x)
    print(f"Figuras salvas em {paths[0].parent}/")
    print(f"Resumo em {paths[2]}")
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pos-processamento de um caso")
    parser.add_argument("caso_dir", type=Path, help="pasta que contem config.json")
    parser.add_argument(
        "--transecto",
        type=float,
        default=None,
        help="X desejado; por padrao usa transecto_x do config",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        gerar_graficos(args.caso_dir, args.transecto)
    except PipelineValidationError as error:
        print(f"ERRO: caso incompleto ou invalido: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
