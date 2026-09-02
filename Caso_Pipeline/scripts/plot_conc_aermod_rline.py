#!/usr/bin/env python3
"""Wrapper historico para o mapa e transecto centrais."""

from __future__ import annotations

from _pipeline_common import BASE, REFERENCE_CONFIG, load_reference
from rline_pipeline.plotting import render_concentration_plot


def main() -> int:
    _config, aermod, _rline, _period, merged = load_reference()
    output = render_concentration_plot(
        aermod,
        merged,
        REFERENCE_CONFIG,
        BASE / "graficos" / "conc_periodo_rline.png",
    )
    print(f"Figura salva em {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
