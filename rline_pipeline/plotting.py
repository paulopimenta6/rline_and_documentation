"""Graficos e pos-processamento validados dos casos."""

from __future__ import annotations

import math
from pathlib import Path
import os
import tempfile
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ._io import atomic_write_text, publish_file_set
from .analysis import DEFAULT_COORDINATE_TOLERANCE, calculate_metrics, load_case_results
from .config import CaseConfig
from .errors import PipelineValidationError


def concentration_pivot(frame: pd.DataFrame, value_column: str = "conc") -> pd.DataFrame:
    """Organiza concentracoes por Y/X, sem depender da ordem das linhas."""

    missing = sorted({"X", "Y", value_column} - set(frame.columns))
    if missing:
        raise PipelineValidationError(f"dados sem colunas para pivot: {missing}")
    try:
        pivot = frame.pivot(index="Y", columns="X", values=value_column)
    except ValueError as error:
        raise PipelineValidationError(f"nao foi possivel criar pivot X/Y: {error}") from error
    pivot = pivot.sort_index(axis=0).sort_index(axis=1)
    if pivot.empty or pivot.isna().any().any():
        missing_cells = int(pivot.isna().sum().sum())
        raise PipelineValidationError(
            f"grade X/Y incompleta para grafico: {missing_cells} celulas ausentes"
        )
    values = pivot.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise PipelineValidationError("grade de concentracao contem valor nao finito")
    return pivot


def select_transect(
    merged: pd.DataFrame, config: CaseConfig, requested_x: float | None = None
) -> tuple[float, pd.DataFrame]:
    """Seleciona o X de grade mais proximo de um transecto valido da rodovia."""

    target = config.transecto_x if requested_x is None else requested_x
    if not np.isfinite(target):
        raise PipelineValidationError("coordenada do transecto deve ser finita")
    grid_start = config.grid.xini
    grid_end = config.grid.xmax
    valid_start = max(0.0, grid_start)
    valid_end = min(config.comprimento, grid_end)
    if not valid_start <= target <= valid_end:
        raise PipelineValidationError(
            f"transecto {target:g} fora da intersecao rodovia/grade "
            f"[{valid_start:g}, {valid_end:g}]"
        )
    available = np.sort(merged["X"].unique().astype(float))
    available = available[
        (available >= valid_start - DEFAULT_COORDINATE_TOLERANCE)
        & (available <= valid_end + DEFAULT_COORDINATE_TOLERANCE)
    ]
    if available.size == 0:
        raise PipelineValidationError("nenhuma coordenada X disponivel para transecto")
    selected = float(available[np.argmin(np.abs(available - target))])
    transect = merged.loc[merged["X"].eq(selected)].sort_values("Y", kind="stable")
    if len(transect) != config.grid.yn:
        raise PipelineValidationError(
            f"transecto X={selected:g} incompleto: {len(transect)}/{config.grid.yn} receptores"
        )
    return selected, transect


def _contour_levels(values: np.ndarray) -> np.ndarray:
    upper = float(np.max(values))
    if not np.isfinite(upper) or upper <= 0:
        raise PipelineValidationError("concentracoes invalidas para mapa de contorno")
    return np.linspace(0.0, upper, 40)


def _save_figure(figure: plt.Figure, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.stem}.plot.",
        suffix=destination.suffix,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        figure.savefig(temporary, dpi=150)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def render_concentration_plot(
    aermod: pd.DataFrame,
    merged: pd.DataFrame,
    config: CaseConfig,
    output_path: str | Path,
    *,
    transect_x: float | None = None,
) -> Path:
    """Gera mapa AERMOD e perfil transversal AERMOD/RLINE."""

    pivot = concentration_pivot(aermod, "conc")
    selected_x, transect = select_transect(merged, config, transect_x)
    xs = pivot.columns.to_numpy(dtype=float)
    ys = pivot.index.to_numpy(dtype=float)
    values = pivot.to_numpy(dtype=float)
    mesh_x, mesh_y = np.meshgrid(xs, ys)

    figure, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    contour = axes[0].contourf(
        mesh_x,
        mesh_y,
        values,
        levels=_contour_levels(values),
        cmap="inferno",
    )
    colorbar = figure.colorbar(contour, ax=axes[0])
    colorbar.set_label("Conc. PERIOD (ug/m3)")
    axes[0].plot(
        [0.0, config.comprimento],
        [config.y_rodovia, config.y_rodovia],
        color="cyan",
        linewidth=3,
        label="Rodovia",
    )
    axes[0].axvline(
        selected_x,
        color="white",
        linestyle="--",
        linewidth=1,
        label=f"Transecto X={selected_x:g} m",
    )
    axes[0].set_title(f"{config.nome} - concentracao PERIOD AERMOD")
    axes[0].set_xlabel("X (m)")
    axes[0].set_ylabel("Y (m)")
    axes[0].set_aspect("equal")
    axes[0].grid(alpha=0.25)
    axes[0].legend(loc="upper right")

    axes[1].plot(
        transect["Y"],
        transect["conc"],
        "o-",
        markersize=3,
        linewidth=1.5,
        color="firebrick",
        label="AERMOD (PERIOD)",
    )
    axes[1].plot(
        transect["Y"],
        transect["C"],
        "s-",
        markersize=3,
        linewidth=1.2,
        color="royalblue",
        label=f"RLINE (media {config.periodos_esperados} h)",
    )
    axes[1].axvline(
        config.y_rodovia,
        color="black",
        linestyle="--",
        linewidth=0.8,
        label=f"Eixo da rodovia Y={config.y_rodovia:g} m",
    )
    axes[1].set_xlabel("Y transversal (m)")
    axes[1].set_ylabel("Concentracao (ug/m3)")
    axes[1].set_title(f"Transecto perpendicular em X={selected_x:g} m")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    destination = Path(output_path)
    figure.tight_layout()
    try:
        _save_figure(figure, destination)
    finally:
        plt.close(figure)
    return destination


def render_comparison_plot(
    merged: pd.DataFrame,
    config: CaseConfig,
    output_path: str | Path,
    *,
    transect_x: float | None = None,
) -> Path:
    """Gera transecto, scatter log-log e razao AERMOD/RLINE."""

    metrics = calculate_metrics(merged, config)
    selected_x, transect = select_transect(merged, config, transect_x)
    ordered = merged.sort_values(["Y", "X"], kind="stable")

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    axes[0].plot(transect["Y"], transect["conc"], "-o", markersize=3, label="AERMOD (PERIOD)")
    axes[0].plot(
        transect["Y"],
        transect["C"],
        "-s",
        markersize=3,
        label=f"RLINE (media {config.periodos_esperados} h)",
    )
    axes[0].axvline(config.y_rodovia, color="black", linestyle="--", linewidth=0.8)
    axes[0].set_xlabel(f"Y transversal (m), X={selected_x:g} m")
    axes[0].set_ylabel("Concentracao (ug/m3)")
    axes[0].set_title(f"Transecto em X={selected_x:g} m")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].loglog(ordered["C"], ordered["conc"], ".", markersize=4, alpha=0.6)
    limits = (
        float(ordered[["C", "conc"]].min().min()),
        float(ordered[["C", "conc"]].max().max()),
    )
    axes[1].plot(limits, limits, "k--", linewidth=0.8, label="1:1")
    axes[1].set_xlabel("RLINE standalone (ug/m3)")
    axes[1].set_ylabel("AERMOD RLINE (ug/m3)")
    axes[1].set_title(
        f"Scatter log-log ({int(metrics['n'])} receptores)\n"
        f"R2 global={metrics['r2_global']:.3f}; "
        f"R2 trecho={metrics['r2_trecho']:.3f}"
    )
    axes[1].legend()
    axes[1].grid(alpha=0.3, which="both")

    axes[2].plot(transect["Y"], transect["ratio"], "-o", markersize=4, label=f"X={selected_x:g} m")
    axes[2].axhline(1.0, color="black", linestyle="--", linewidth=0.8)
    axes[2].set_xlabel("Y transversal (m)")
    axes[2].set_ylabel("Razao AERMOD / RLINE")
    axes[2].set_title("Razao de concentracoes")
    axes[2].legend()
    axes[2].grid(alpha=0.3)

    figure.suptitle(f"Comparacao AERMOD vs RLINE standalone - {config.nome}", fontsize=11)
    destination = Path(output_path)
    figure.tight_layout()
    try:
        _save_figure(figure, destination)
    finally:
        plt.close(figure)
    return destination


def write_case_summary(
    output_path: str | Path,
    config: CaseConfig,
    metrics: dict[str, float | int],
) -> Path:
    """Grava as metricas calculadas sobre o conjunto integral validado."""

    content = "".join(
        [
            f"Caso: {config.nome}\n",
            f"Receptores comparados: {int(metrics['n'])}\n",
            "AERMOD PERIOD max: "
            f"{metrics['max_aermod']:.1f} | RLINE media max: {metrics['max_rline']:.1f}\n",
            "Media AERMOD: "
            f"{metrics['media_aermod']:.1f} | Media RLINE: {metrics['media_rline']:.1f}\n",
            "Ratio AERMOD/RLINE: "
            f"media {metrics['ratio_media']:.3f} mediana {metrics['ratio_mediana']:.3f}\n",
            f"Correlacao(log-log) global : {metrics['correlacao_log']:.4f}\n",
            f"R2(log-log) global : {metrics['r2_global']:.4f}\n",
            "R2(log-log) trecho "
            f"(0..{config.comprimento:g} m): {metrics['r2_trecho']:.4f}  "
            f"[n={int(metrics['n_trecho'])}]\n",
        ]
    )
    destination = Path(output_path)
    return atomic_write_text(destination, content)


def process_case(
    case_dir: str | Path,
    *,
    transect_x: float | None = None,
    output_dir: str | Path | None = None,
    summary_path: str | Path | None = None,
) -> tuple[dict[str, float | int], tuple[Path, Path, Path]]:
    """Valida o caso inteiro e somente entao gera graficos e resumo."""

    directory = Path(case_dir)
    config, aermod, _rline, _period, merged = load_case_results(directory)
    metrics = calculate_metrics(merged, config)
    graphics = Path(output_dir) if output_dir is not None else directory / "graficos"
    summary = Path(summary_path) if summary_path is not None else directory / "resumo.txt"
    concentration_path = graphics / "conc_periodo_rline.png"
    comparison_path = graphics / "conc_aermod_vs_rline.png"
    with tempfile.TemporaryDirectory(prefix="rline-postprocess-") as temporary:
        staging = Path(temporary)
        staged_concentration = render_concentration_plot(
            aermod,
            merged,
            config,
            staging / "conc_periodo_rline.png",
            transect_x=transect_x,
        )
        staged_comparison = render_comparison_plot(
            merged,
            config,
            staging / "conc_aermod_vs_rline.png",
            transect_x=transect_x,
        )
        staged_summary = write_case_summary(staging / "resumo.txt", config, metrics)
        publish_file_set(
            (
                (staged_concentration, concentration_path),
                (staged_comparison, comparison_path),
                (staged_summary, summary),
            )
        )
    return metrics, (concentration_path, comparison_path, summary)


def plot_cases_summary(
    case_dirs: Iterable[str | Path], output_path: str | Path
) -> list[dict[str, object]]:
    """Gera comparativo somente se todos os casos configurados estiverem completos."""

    records: list[dict[str, object]] = []
    for case_dir in case_dirs:
        config, aermod, _rline, _period, merged = load_case_results(case_dir)
        records.append(
            {
                "config": config,
                "aermod": aermod,
                "metrics": calculate_metrics(merged, config),
            }
        )
    if not records:
        raise PipelineValidationError("nenhum caso configurado para o comparativo")

    column_count = min(2, len(records))
    map_rows = math.ceil(len(records) / column_count)
    figure = plt.figure(figsize=(13, 3.8 * map_rows + 3.2))
    grid_spec = figure.add_gridspec(
        map_rows + 1,
        column_count,
        height_ratios=[3] * map_rows + [2],
    )

    for index, record in enumerate(records):
        config = record["config"]
        aermod = record["aermod"]
        metrics = record["metrics"]
        assert isinstance(config, CaseConfig)
        assert isinstance(aermod, pd.DataFrame)
        assert isinstance(metrics, dict)
        axis = figure.add_subplot(grid_spec[index // column_count, index % column_count])
        pivot = concentration_pivot(aermod, "conc")
        xs = pivot.columns.to_numpy(dtype=float)
        ys = pivot.index.to_numpy(dtype=float)
        mesh_x, mesh_y = np.meshgrid(xs, ys)
        values = pivot.to_numpy(dtype=float)
        axis.contourf(
            mesh_x,
            mesh_y,
            values,
            levels=_contour_levels(values),
            cmap="inferno",
        )
        axis.plot(
            [0.0, config.comprimento],
            [config.y_rodovia, config.y_rodovia],
            color="cyan",
            linewidth=3,
        )
        axis.set_title(f"{config.nome}\nR2(trecho)={metrics['r2_trecho']:.3f}", fontsize=9)
        axis.set_xlabel("X (m)")
        axis.set_ylabel("Y (m)")
        axis.set_aspect("equal")
        axis.tick_params(labelsize=7)

    bar_axis = figure.add_subplot(grid_spec[map_rows, :])
    names = [record["config"].nome for record in records]  # type: ignore[union-attr]
    positions = np.arange(len(names))
    width = 0.38
    aermod_max = [float(record["metrics"]["max_aermod"]) for record in records]  # type: ignore[index]
    rline_max = [float(record["metrics"]["max_rline"]) for record in records]  # type: ignore[index]
    bar_axis.bar(
        positions - width / 2,
        aermod_max,
        width,
        label="AERMOD RLINE (PERIOD)",
        color="#d1495b",
    )
    bar_axis.bar(
        positions + width / 2,
        rline_max,
        width,
        label="RLINE standalone (media)",
        color="#247ba0",
    )
    bar_axis.set_yscale("log")
    bar_axis.set_xticks(positions, names, rotation=15, ha="right", fontsize=8)
    bar_axis.set_ylabel("Concentracao maxima (ug/m3, log)")
    bar_axis.set_title("Concentracao maxima por caso")
    bar_axis.legend(fontsize=8)
    bar_axis.grid(alpha=0.3, axis="y")

    figure.suptitle("Resultados AERMOD/RLINE por caso configurado", fontsize=12)
    destination = Path(output_path)
    figure.tight_layout()
    try:
        _save_figure(figure, destination)
    finally:
        plt.close(figure)
    return records
