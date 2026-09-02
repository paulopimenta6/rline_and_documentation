#!/usr/bin/env python3
"""Generate the canonical synthetic ONSITE.MET without import-time side effects."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline.example_data import SCENARIOS, generate_onsite_text  # noqa: E402

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "dados_aermet" / "ONSITE.MET"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera meteorologia ONSITE sintetica")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="mixed-diurnal")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    content, qa = generate_onsite_text(args.scenario, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8", newline="\n")
    print(f"Arquivo gerado: {args.output.resolve()}")
    print(f"Numero de observacoes (horas): {qa['periods']}")
    print(f"Numero de linhas: {len(content.splitlines())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
