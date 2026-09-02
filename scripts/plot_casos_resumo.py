#!/usr/bin/env python3
"""Gera o comparativo dos casos descobertos por config.json."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    PipelineValidationError,
    calculate_metrics,
    load_case_results,
    plot_cases_summary,
)


def discover_cases(cases_dir: str | Path) -> list[Path]:
    return sorted(path.parent for path in Path(cases_dir).glob("*/config.json"))


def ler_caso(caso_dir: str | Path) -> dict[str, object]:
    config, aermod, _rline, _period, merged = load_case_results(caso_dir)
    metrics = calculate_metrics(merged, config)
    return {
        "nome": config.nome,
        "descricao": config.descricao,
        "config": config,
        "aermod": aermod,
        "m": merged,
        **metrics,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compara todos os casos configurados")
    parser.add_argument("--casos", type=Path, default=ROOT / "casos")
    parser.add_argument("--saida", type=Path, default=ROOT / "casos" / "comparativo_geral.png")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = discover_cases(args.casos)
    if not cases:
        print(f"ERRO: nenhum config.json encontrado em {args.casos}", file=sys.stderr)
        return 1

    try:
        records = plot_cases_summary(cases, args.saida)
    except PipelineValidationError as error:
        print(f"ERRO: comparativo nao gerado; caso incompleto: {error}", file=sys.stderr)
        return 1

    print(f"Casos carregados: {len(records)}")
    print(f"Figura salva em {args.saida}")
    print(f"{'caso':<24} {'max_AERMOD':>12} {'max_RLINE':>12} {'R2_trecho':>11} {'n':>7}")
    for record in records:
        config = record["config"]
        metrics = record["metrics"]
        print(
            f"{config.nome:<24} "
            f"{metrics['max_aermod']:>12.1f} {metrics['max_rline']:>12.1f} "
            f"{metrics['r2_trecho']:>11.3f} {int(metrics['n']):>7d}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
