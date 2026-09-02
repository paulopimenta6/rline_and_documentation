#!/usr/bin/env python3
"""Validacao executavel de todos os casos declarados por config.json."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    PipelineValidationError,
    calculate_metrics,
    load_case_config,
    load_case_results,
)

Check = tuple[str, bool | None]


def _metric(value: float | int | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{float(value):.{digits}f}"


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
    try:
        config, aermod, rline, rline_period, merged = load_case_results(directory, config=config)
    except PipelineValidationError as error:
        checks.append((f"VALIDACAO CANONICA falhou: {error}", False))
        checks.extend(_not_evaluated(1, "caso completo e coerente indisponivel"))
        return name, checks

    checks.append(
        (
            "T1 AERMOD concluido e coerente: "
            f"{len(aermod)}/{config.numero_receptores} receptores, "
            f"{config.periodos_esperados} horas, GRP=ALL, NETID=RCART",
            True,
        )
    )
    observed_receptors = rline[["X", "Y"]].drop_duplicates().shape[0]
    checks.append(
        (
            "T2 RLINE completo e ligado a meteorologia exata: "
            f"{observed_receptors}/{config.numero_receptores} receptores x "
            f"{config.periodos_esperados} periodos = {len(rline)} linhas",
            True,
        )
    )
    checks.append(
        (
            f"T3 merge one-to-one completo: {len(merged)}/{config.numero_receptores} receptores",
            len(merged) == len(rline_period) == config.numero_receptores,
        )
    )

    values = merged[["conc", "C"]].to_numpy(dtype=float)
    finite = bool(np.isfinite(values).all())
    nonnegative = bool((values >= 0).all())
    checks.append(
        (
            f"T4 concentracoes finitas={finite} e nao negativas={nonnegative}",
            finite and nonnegative,
        )
    )

    try:
        metrics = calculate_metrics(merged, config)
    except PipelineValidationError as error:
        checks.extend(_not_evaluated(5, f"metricas invalidas: {error}"))
        return name, checks

    checks.append(
        (
            "T5 INFO intercomparacao: "
            f"r(log)={_metric(metrics['correlacao_log'])}, "
            f"r2(log)={_metric(metrics['r2_global'])}, "
            f"pares positivos={int(metrics['positive_pair_count'])}",
            None,
        )
    )
    checks.append(
        (
            "T6 INFO concordancia: "
            f"FB={_metric(metrics['fractional_bias'])}, "
            f"NMSE={_metric(metrics['nmse'])}, FAC2={_metric(metrics['fac2'])}",
            None,
        )
    )
    checks.append(
        (
            "T7 INFO erro log absoluto: "
            f"mediana={_metric(metrics['median_abs_log10_error'])}, "
            f"p95={_metric(metrics['p95_abs_log10_error'])}",
            None,
        )
    )
    checks.append(
        (
            "T8 INFO picos/zeros: "
            f"FB(top25)={_metric(metrics['peak25_fractional_bias'])}, "
            f"zeros concordantes={int(metrics['zero_agreement_count'])}, "
            f"zeros discordantes={int(metrics['zero_mismatch_count'])}",
            None,
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
            status = "INFO" if passed is None else ("PASS" if passed else "FAIL")
            print(f"  [{status}] {description}")
            if passed is not None:
                all_ok = all_ok and passed

    print()
    print(f"Casos reportados: {reported}/{len(cases)}")
    if all_ok and reported == len(cases):
        print("VALIDACAO ESTRUTURAL APROVADA; INTERCOMPARACAO REPORTADA SEM GATE CIENTIFICO")
        return 0
    print("ALGUNS TESTES FALHARAM")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
