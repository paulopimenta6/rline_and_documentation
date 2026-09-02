"""Agregacao, merge, metricas e validacao integrada dos casos."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import CaseConfig, generate_grid, load_case_config
from .errors import PipelineValidationError
from .generation import validate_generated_case_inputs
from .parsing import (
    coordinate_mapping,
    parse_aermod,
    parse_rline,
    parse_rline_meteorology_periods,
    validate_aermod_completion,
)

DEFAULT_COORDINATE_TOLERANCE = 1.0e-3


def aggregate_rline_period(rline: pd.DataFrame) -> pd.DataFrame:
    """Calcula a media temporal RLINE de cada receptor."""

    required = {"X", "Y", "C"}
    missing = sorted(required - set(rline.columns))
    if missing:
        raise PipelineValidationError(f"RLINE sem colunas necessarias para agregacao: {missing}")
    period = (
        rline.groupby(["X", "Y"], as_index=False, sort=True)["C"]
        .mean()
        .sort_values(["Y", "X"], kind="stable")
        .reset_index(drop=True)
    )
    if period.duplicated(["X", "Y"]).any():
        raise PipelineValidationError("agregacao RLINE produziu coordenadas duplicadas")
    if not np.isfinite(period[["X", "Y", "C"]].to_numpy(dtype=float)).all():
        raise PipelineValidationError("agregacao RLINE produziu valores nao finitos")
    return period


def merge_one_to_one(
    aermod: pd.DataFrame,
    rline_period: pd.DataFrame,
    *,
    coordinate_tolerance: float | None = None,
) -> pd.DataFrame:
    """Faz merge bijetivo sem arredondar coordenadas."""

    for label, frame, concentration in (
        ("AERMOD", aermod, "conc"),
        ("RLINE", rline_period, "C"),
    ):
        missing = sorted({"X", "Y", concentration} - set(frame.columns))
        if missing:
            raise PipelineValidationError(f"{label} sem colunas para merge: {missing}")
        if frame.duplicated(["X", "Y"]).any():
            raise PipelineValidationError(f"{label}: coordenadas duplicadas antes do merge")

    try:
        exact = aermod.merge(
            rline_period,
            on=["X", "Y"],
            how="outer",
            validate="one_to_one",
            indicator=True,
            suffixes=("_AERMOD", "_RLINE"),
            sort=False,
        )
    except pd.errors.MergeError as error:
        raise PipelineValidationError(f"merge AERMOD/RLINE nao e one-to-one: {error}") from error

    if len(exact) == len(aermod) == len(rline_period) and exact["_merge"].eq("both").all():
        merged = exact.drop(columns="_merge")
    else:
        mapping = coordinate_mapping(
            aermod[["X", "Y"]],
            rline_period[["X", "Y"]],
            tolerance=coordinate_tolerance,
            labels=("AERMOD", "RLINE"),
        )
        right = rline_period.iloc[mapping].reset_index(drop=True)
        left = aermod.reset_index(drop=True)
        overlapping = (set(left.columns) & set(right.columns)) - {"X", "Y"}
        right = right.drop(columns=["X", "Y"]).rename(
            columns={column: f"{column}_RLINE" for column in overlapping}
        )
        left = left.rename(columns={column: f"{column}_AERMOD" for column in overlapping})
        merged = pd.concat([left, right], axis=1)

    if len(merged) != len(aermod) or len(merged) != len(rline_period):
        raise PipelineValidationError(
            f"merge incompleto: AERMOD={len(aermod)}, RLINE={len(rline_period)}, "
            f"merge={len(merged)}"
        )
    merged["ratio"] = merged["conc"] / merged["C"]
    return merged


def _positive_log_correlation(frame: pd.DataFrame, *, label: str) -> tuple[float, float]:
    if len(frame) < 3:
        raise PipelineValidationError(f"{label}: ao menos 3 receptores sao necessarios")
    values = frame[["conc", "C"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise PipelineValidationError(f"{label}: concentracoes devem ser finitas")
    if (values <= 0).any():
        raise PipelineValidationError(
            f"{label}: concentracoes devem ser estritamente positivas para metricas log"
        )
    logs = np.log10(values)
    correlation = float(np.corrcoef(logs[:, 0], logs[:, 1])[0, 1])
    if not np.isfinite(correlation):
        raise PipelineValidationError(f"{label}: correlacao logaritmica indefinida")
    return correlation, correlation**2


def road_segment_mask(frame: pd.DataFrame, config: CaseConfig) -> pd.Series:
    """Seleciona receptores cuja projecao X pertence ao segmento real da rodovia."""

    tolerance = DEFAULT_COORDINATE_TOLERANCE
    return frame["X"].between(-tolerance, config.comprimento + tolerance)


def calculate_metrics(merged: pd.DataFrame, config: CaseConfig) -> dict[str, float | int]:
    """Calcula metricas globais e no trecho real da rodovia."""

    required = {"X", "Y", "conc", "C"}
    missing = sorted(required - set(merged.columns))
    if missing:
        raise PipelineValidationError(f"merge sem colunas para metricas: {missing}")

    correlation, r2_global = _positive_log_correlation(merged, label="global")
    segment = merged.loc[road_segment_mask(merged, config)]
    segment_correlation, r2_segment = _positive_log_correlation(segment, label="trecho da rodovia")
    ratios = merged["conc"] / merged["C"]
    if not np.isfinite(ratios.to_numpy(dtype=float)).all():
        raise PipelineValidationError("razao AERMOD/RLINE contem valor nao finito")

    return {
        "n": len(merged),
        "n_trecho": len(segment),
        "max_aermod": float(merged["conc"].max()),
        "max_rline": float(merged["C"].max()),
        "media_aermod": float(merged["conc"].mean()),
        "media_rline": float(merged["C"].mean()),
        "ratio_media": float(ratios.mean()),
        "ratio_mediana": float(ratios.median()),
        "correlacao_log": correlation,
        "r2_global": r2_global,
        "correlacao_log_trecho": segment_correlation,
        "r2_trecho": r2_segment,
    }


def load_case_results(
    case_dir: str | Path,
    *,
    config: CaseConfig | None = None,
    coordinate_tolerance: float | None = DEFAULT_COORDINATE_TOLERANCE,
    expected_aermod_title: str | None = None,
    expected_rline_meteorology_path: str = "./ONSITE.SFC",
) -> tuple[CaseConfig, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega e valida um caso completo antes de devolver seus resultados."""

    directory = Path(case_dir)
    if not directory.is_dir():
        raise PipelineValidationError(f"diretorio de caso nao encontrado: {directory}")
    case_config = config or load_case_config(directory / "config.json")
    expected_grid = generate_grid(case_config.grid)

    validate_aermod_completion(
        directory / "rodada_aermod" / "RLINE_TEST.out",
        case_config.periodos_esperados,
    )
    validate_generated_case_inputs(
        directory,
        case_config,
        aermod_title=expected_aermod_title,
        rline_meteorology_path=expected_rline_meteorology_path,
    )

    aermod_meteorology = directory / "rodada_aermod" / "ONSITE.SFC"
    rline_meteorology = directory / "rodada_rline" / "ONSITE.SFC"
    try:
        if aermod_meteorology.read_bytes() != rline_meteorology.read_bytes():
            raise PipelineValidationError(
                "AERMOD e RLINE nao usam a mesma copia exata de ONSITE.SFC"
            )
    except OSError as error:
        raise PipelineValidationError("meteorologia publicada do caso esta ausente") from error
    expected_periods = parse_rline_meteorology_periods(rline_meteorology)
    if len(expected_periods) != case_config.periodos_esperados:
        raise PipelineValidationError(
            f"meteorologia contem {len(expected_periods)} periodos; "
            f"config espera {case_config.periodos_esperados}"
        )

    aermod = parse_aermod(
        directory / "rodada_aermod" / "CONC_PLOT.PLT",
        expected_receptors=case_config.numero_receptores,
        expected_periods=case_config.periodos_esperados,
        expected_coordinates=expected_grid,
        coordinate_tolerance=coordinate_tolerance,
    )
    rline = parse_rline(
        directory / "rodada_rline" / "Output_Road_Numerical.csv",
        expected_receptors=case_config.numero_receptores,
        expected_periods=expected_periods,
        expected_coordinates=expected_grid,
        coordinate_tolerance=coordinate_tolerance,
    )
    rline_period = aggregate_rline_period(rline)
    merged = merge_one_to_one(
        aermod,
        rline_period,
        coordinate_tolerance=coordinate_tolerance,
    )
    if len(merged) != case_config.numero_receptores:
        raise PipelineValidationError(
            f"caso incompleto: merge={len(merged)}, "
            f"esperado={case_config.numero_receptores} receptores"
        )
    calculate_metrics(merged, case_config)
    return case_config, aermod, rline, rline_period, merged
