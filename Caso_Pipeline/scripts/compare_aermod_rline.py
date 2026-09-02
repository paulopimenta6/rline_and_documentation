#!/usr/bin/env python3
"""Relatorio textual do caso historico usando o parser central validado."""

from __future__ import annotations

from _pipeline_common import REFERENCE_CONFIG, load_reference
from rline_pipeline import calculate_metrics
from rline_pipeline.plotting import select_transect


def main() -> int:
    _config, _aermod, _rline, _period, merged = load_reference()
    metrics = calculate_metrics(merged, REFERENCE_CONFIG)
    selected_x, transect = select_transect(merged, REFERENCE_CONFIG)

    print(f"Receptores comparados: {int(metrics['n'])}")
    print(f"AERMOD max: {metrics['max_aermod']:.1f}  |  RLINE max: {metrics['max_rline']:.1f}")
    print(
        f"Media AERMOD: {metrics['media_aermod']:.1f}  |  Media RLINE: {metrics['media_rline']:.1f}"
    )
    print(
        f"Ratio AERMOD/RLINE: media {metrics['ratio_media']:.3f}  "
        f"mediana {metrics['ratio_mediana']:.3f}"
    )
    print(
        f"Correlacao log: {metrics['correlacao_log']:.4f}  |  R2(log): {metrics['r2_global']:.4f}"
    )
    print("\nTop 10 receptores por concentracao AERMOD:")
    print(merged.sort_values("conc", ascending=False).head(10).to_string(index=False))
    print(f"\nTransecto X={selected_x:g}:")
    print(transect[["Y", "conc", "C", "ratio"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
