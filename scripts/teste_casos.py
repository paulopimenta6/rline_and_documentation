#!/usr/bin/env python3
"""Validacao executavel de todos os casos declarados por config.json."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys
from typing import Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    DEFAULT_COORDINATE_TOLERANCE,
    PipelineValidationError,
    aggregate_rline_period,
    calculate_metrics,
    generate_grid,
    load_case_config,
    merge_one_to_one,
    parse_aermod,
    parse_rline,
    validate_aermod_completion,
)

LIM_R2_GLOBAL = 0.85
LIM_R2_GLOBAL_CURTO = 0.65
LIM_R2_TRECHO = 0.95
LIM_RATIO_MIN = 0.30
LIM_RATIO_MAX = 1.20
LIM_FATOR_ESCALA = 20.0

Check = tuple[str, bool]


def discover_cases(cases_dir: str | Path) -> list[Path]:
    """Descobre casos pela fonte de verdade, nao pela existencia de outputs."""

    return sorted(path.parent for path in Path(cases_dir).glob("*/config.json"))


def _not_evaluated(start: int, reason: str) -> list[Check]:
    return [(f"T{number} nao avaliado: {reason}", False) for number in range(start, 9)]


def testar_caso(caso_dir: str | Path) -> tuple[str, list[Check]]:
    directory = Path(caso_dir)
    name = directory.name
    checks: list[Check] = []

    try:
        config = load_case_config(directory / "config.json")
    except PipelineValidationError as error:
        return name, [(f"CONFIG invalido: {error}", False)]

    name = config.nome
    expected_grid = generate_grid(config.grid)
    aermod: pd.DataFrame | None = None
    rline: pd.DataFrame | None = None

    try:
        validate_aermod_completion(
            directory / "rodada_aermod" / "RLINE_TEST.out",
            config.periodos_esperados,
        )
        aermod = parse_aermod(
            directory / "rodada_aermod" / "CONC_PLOT.PLT",
            expected_receptors=config.numero_receptores,
            expected_periods=config.periodos_esperados,
            expected_coordinates=expected_grid,
            coordinate_tolerance=DEFAULT_COORDINATE_TOLERANCE,
        )
        checks.append(
            (
                "T1 AERMOD concluiu com zero fatais: "
                f"{len(aermod)}/{config.numero_receptores} receptores, "
                f"{config.periodos_esperados} horas",
                True,
            )
        )
    except PipelineValidationError as error:
        checks.append((f"T1 AERMOD incompleto: {error}", False))

    try:
        rline = parse_rline(
            directory / "rodada_rline" / "Output_Road_Numerical.csv",
            expected_receptors=config.numero_receptores,
            expected_periods=config.periodos_esperados,
            expected_coordinates=expected_grid,
            coordinate_tolerance=DEFAULT_COORDINATE_TOLERANCE,
        )
        observed_receptors = rline[["X", "Y"]].drop_duplicates().shape[0]
        checks.append(
            (
                "T2 RLINE completo: "
                f"{observed_receptors}/{config.numero_receptores} receptores x "
                f"{config.periodos_esperados} periodos = {len(rline)} linhas",
                True,
            )
        )
    except PipelineValidationError as error:
        checks.append((f"T2 RLINE incompleto: {error}", False))

    if aermod is None or rline is None:
        checks.extend(_not_evaluated(3, "T1 e T2 precisam estar completos"))
        return name, checks

    try:
        rline_period = aggregate_rline_period(rline)
        merged = merge_one_to_one(
            aermod,
            rline_period,
            coordinate_tolerance=DEFAULT_COORDINATE_TOLERANCE,
        )
    except PipelineValidationError as error:
        checks.append((f"T3 merge one-to-one falhou: {error}", False))
        checks.extend(_not_evaluated(4, "merge T3 indisponivel"))
        return name, checks

    merge_ok = len(merged) == config.numero_receptores
    checks.append(
        (
            f"T3 merge one-to-one completo: {len(merged)}/{config.numero_receptores} receptores",
            merge_ok,
        )
    )

    values = merged[["conc", "C"]].to_numpy(dtype=float)
    finite = bool(np.isfinite(values).all())
    positive = bool((values > 0).all())
    checks.append(
        (
            f"T4 concentracoes finitas={finite} e estritamente positivas={positive}",
            finite and positive,
        )
    )

    try:
        metrics = calculate_metrics(merged, config)
    except PipelineValidationError as error:
        checks.extend(_not_evaluated(5, f"metricas invalidas: {error}"))
        return name, checks

    x_extent = config.grid.xmax - config.grid.xini
    overlap = max(
        0.0,
        min(config.grid.xmax, config.comprimento) - max(config.grid.xini, 0.0),
    )
    coverage = min(1.0, overlap / x_extent) if x_extent > 0 else 1.0
    if coverage >= 0.6:
        global_limit = LIM_R2_GLOBAL
        coverage_note = f"rodovia cobre {coverage:.0%} da grade"
    else:
        global_limit = LIM_R2_GLOBAL_CURTO
        coverage_note = f"limiar curto; rodovia cobre {coverage:.0%} da grade"
    global_correlation = float(metrics["correlacao_log"])
    global_r2 = float(metrics["r2_global"])
    global_ok = global_correlation > 0 and global_r2 >= global_limit
    checks.append(
        (
            "T5 correlacao log global positiva "
            f"(r={global_correlation:.4f}) e R2={global_r2:.4f} >= "
            f"{global_limit:.2f} ({coverage_note})",
            global_ok,
        )
    )

    segment_correlation = float(metrics["correlacao_log_trecho"])
    segment_r2 = float(metrics["r2_trecho"])
    segment_ok = segment_correlation > 0 and segment_r2 >= LIM_R2_TRECHO
    checks.append(
        (
            "T6 correlacao no trecho positiva "
            f"(r={segment_correlation:.4f}) e R2={segment_r2:.4f} >= "
            f"{LIM_R2_TRECHO:.2f} [n={int(metrics['n_trecho'])}]",
            segment_ok,
        )
    )

    median_ratio = float(metrics["ratio_mediana"])
    ratio_ok = LIM_RATIO_MIN <= median_ratio <= LIM_RATIO_MAX
    checks.append(
        (
            f"T7 razao mediana={median_ratio:.3f} em [{LIM_RATIO_MIN:.2f}, {LIM_RATIO_MAX:.2f}]",
            ratio_ok,
        )
    )

    maximum_ratio = float(metrics["max_aermod"]) / float(metrics["max_rline"])
    lower_scale = 1.0 / LIM_FATOR_ESCALA
    scale_ok = math.isfinite(maximum_ratio) and lower_scale <= maximum_ratio <= LIM_FATOR_ESCALA
    checks.append(
        (
            "T8 escala bilateral: "
            f"1/{LIM_FATOR_ESCALA:.0f} <= max AERMOD/RLINE={maximum_ratio:.3f} "
            f"<= {LIM_FATOR_ESCALA:.0f}",
            scale_ok,
        )
    )
    return name, checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida resultados dos casos")
    parser.add_argument(
        "casos",
        nargs="*",
        type=Path,
        help="diretorios de caso; sem argumentos, descobre todos por config.json",
    )
    parser.add_argument(
        "--casos-dir",
        type=Path,
        default=ROOT / "casos",
        help="raiz usada na descoberta automatica",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = [path.parent if path.name == "config.json" else path for path in args.casos]
    if not cases:
        cases = discover_cases(args.casos_dir)
    if not cases:
        print(f"ERRO: nenhum config.json encontrado em {args.casos_dir}", file=sys.stderr)
        return 1

    all_ok = True
    reported = 0
    for case in cases:
        try:
            name, checks = testar_caso(case)
        except Exception as error:  # mantem os demais casos visiveis no relatorio
            name = case.name
            checks = [(f"ERRO INTERNO durante validacao: {type(error).__name__}: {error}", False)]
        reported += 1
        print(f"=== {name} ===")
        for description, passed in checks:
            print(f"  [{'PASS' if passed else 'FAIL'}] {description}")
            all_ok = all_ok and passed

    print()
    print(f"Casos reportados: {reported}/{len(cases)}")
    if all_ok and reported == len(cases):
        print("TODOS OS TESTES PASSARAM")
        return 0
    print("ALGUNS TESTES FALHARAM")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
