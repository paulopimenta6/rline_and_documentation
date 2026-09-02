#!/usr/bin/env python3
"""Wrapper historico para o grafico comparativo central."""

from __future__ import annotations

from _pipeline_common import BASE, REFERENCE_CONFIG, load_reference
from rline_pipeline.plotting import render_comparison_plot


def main() -> int:
    _config, _aermod, _rline, _period, merged = load_reference()
    output = render_comparison_plot(
        merged,
        REFERENCE_CONFIG,
        BASE / "graficos" / "conc_aermod_vs_rline.png",
    )
    print(f"Figura salva em {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
