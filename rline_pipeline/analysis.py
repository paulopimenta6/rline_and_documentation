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
from .provenance import BASELINE_MANIFEST_FILENAME, verify_baseline_manifest

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
    rline_values = merged["C"].to_numpy(dtype=float)
    merged["ratio"] = np.divide(
        merged["conc"].to_numpy(dtype=float),
        rline_values,
        out=np.full(len(merged), np.nan, dtype=float),
        where=rline_values > 0.0,
    )
    return merged


def _positive_log_correlation(
    frame: pd.DataFrame, *, label: str
) -> tuple[float | None, float | None, int]:
    values = frame[["conc", "C"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise PipelineValidationError(f"{label}: concentracoes devem ser finitas")
    if (values < 0).any():
        raise PipelineValidationError(f"{label}: concentracoes nao podem ser negativas")
    positive = values[(values > 0).all(axis=1)]
    if len(positive) < 3:
        return None, None, len(positive)
    logs = np.log10(positive)
    correlation = float(np.corrcoef(logs[:, 0], logs[:, 1])[0, 1])
    if not np.isfinite(correlation):
        return None, None, len(positive)
    return correlation, correlation**2, len(positive)


def _fractional_bias(left: np.ndarray, right: np.ndarray) -> float | None:
    denominator = float(left.mean() + right.mean())
    if denominator == 0.0:
        return 0.0 if np.array_equal(left, right) else None
    return float(2.0 * (left.mean() - right.mean()) / denominator)


def _agreement_metrics(frame: pd.DataFrame) -> dict[str, float | int | None]:
    left = frame["conc"].to_numpy(dtype=float)
    right = frame["C"].to_numpy(dtype=float)
    sums = left + right
    pair_fractional_error = np.divide(
        2.0 * np.abs(left - right),
        sums,
        out=np.zeros_like(sums),
        where=sums > 0.0,
    )
    denominator = float(left.mean() * right.mean())
    if denominator > 0.0:
        nmse: float | None = float(np.mean((left - right) ** 2) / denominator)
    elif np.array_equal(left, right):
        nmse = 0.0
    else:
        nmse = None

    positive_mask = (left > 0.0) & (right > 0.0)
    positive_left = left[positive_mask]
    positive_right = right[positive_mask]
    if len(positive_left):
        ratios = positive_left / positive_right
        log_errors = np.abs(np.log10(ratios))
        fac2: float | None = float(np.mean((ratios >= 0.5) & (ratios <= 2.0)))
        median_log_error: float | None = float(np.median(log_errors))
        p95_log_error: float | None = float(np.quantile(log_errors, 0.95))
    else:
        fac2 = None
        median_log_error = None
        p95_log_error = None

    peak_count = min(25, len(frame))
    peak_left = np.sort(left)[-peak_count:]
    peak_right = np.sort(right)[-peak_count:]
    return {
        "fractional_bias": _fractional_bias(left, right),
        "absolute_fractional_bias": float(pair_fractional_error.mean()),
        "nmse": nmse,
        "fac2": fac2,
        "median_abs_log10_error": median_log_error,
        "p95_abs_log10_error": p95_log_error,
        "peak25_fractional_bias": _fractional_bias(peak_left, peak_right),
        "positive_pair_count": int(positive_mask.sum()),
        "zero_agreement_count": int(((left == 0.0) & (right == 0.0)).sum()),
        "zero_mismatch_count": int(((left == 0.0) ^ (right == 0.0)).sum()),
    }


def road_segment_mask(frame: pd.DataFrame, config: CaseConfig) -> pd.Series:
    """Seleciona receptores cuja projecao X pertence ao segmento real da rodovia."""

    tolerance = DEFAULT_COORDINATE_TOLERANCE
    return frame["X"].between(-tolerance, config.comprimento + tolerance)


def calculate_metrics(
    merged: pd.DataFrame, config: CaseConfig
) -> dict[str, float | int | None]:
    """Calcula metricas globais e no trecho real da rodovia."""

    required = {"X", "Y", "conc", "C"}
    missing = sorted(required - set(merged.columns))
    if missing:
        raise PipelineValidationError(f"merge sem colunas para metricas: {missing}")
    if merged.empty:
        raise PipelineValidationError("merge vazio; metricas nao podem ser calculadas")

    values = merged[["conc", "C"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise PipelineValidationError("concentracoes devem ser finitas")
    if (values < 0.0).any():
        raise PipelineValidationError("concentracoes nao podem ser negativas")

    correlation, r2_global, positive_global = _positive_log_correlation(merged, label="global")
    segment = merged.loc[road_segment_mask(merged, config)]
    segment_correlation, r2_segment, positive_segment = _positive_log_correlation(
        segment, label="trecho da rodovia"
    )
    ratios = merged.loc[merged["C"] > 0.0, "conc"] / merged.loc[merged["C"] > 0.0, "C"]

    return {
        "n": len(merged),
        "n_trecho": len(segment),
        "max_aermod": float(merged["conc"].max()),
        "max_rline": float(merged["C"].max()),
        "media_aermod": float(merged["conc"].mean()),
        "media_rline": float(merged["C"].mean()),
        "ratio_media": float(ratios.mean()) if len(ratios) else None,
        "ratio_mediana": float(ratios.median()) if len(ratios) else None,
        "correlacao_log": correlation,
        "r2_global": r2_global,
        "n_positivo_global": positive_global,
        "correlacao_log_trecho": segment_correlation,
        "r2_trecho": r2_segment,
        "n_positivo_trecho": positive_segment,
        **_agreement_metrics(merged),
    }


def load_case_results(
    case_dir: str | Path,
    *,
    config: CaseConfig | None = None,
    coordinate_tolerance: float | None = DEFAULT_COORDINATE_TOLERANCE,
    expected_aermod_title: str | None = None,
    expected_rline_meteorology_path: str = "./ONSITE.SFC",
    evidence_mode: str = "auto",
) -> tuple[CaseConfig, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega e valida um caso completo antes de devolver seus resultados."""

    directory = Path(case_dir)
    if not directory.is_dir():
        raise PipelineValidationError(f"diretorio de caso nao encontrado: {directory}")
    case_config = config or load_case_config(directory / "config.json")
    expected_grid = generate_grid(case_config.grid)
    if evidence_mode not in {"auto", "legacy-baseline", "off"}:
        raise PipelineValidationError(
            "evidence_mode deve ser auto, legacy-baseline ou off"
        )

    baseline_path = directory / BASELINE_MANIFEST_FILENAME
    shared_inputs: dict[str, Path] = {}
    if evidence_mode == "legacy-baseline" or (
        evidence_mode == "auto" and baseline_path.is_file()
    ):
        shared_inputs = verify_baseline_manifest(directory)

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
    baseline_meteorology = shared_inputs.get("meteorology_sfc")
    if baseline_meteorology is not None:
        for local_meteorology in (aermod_meteorology, rline_meteorology):
            if (
                local_meteorology.is_file()
                and local_meteorology.read_bytes() != baseline_meteorology.read_bytes()
            ):
                raise PipelineValidationError(
                    f"meteorologia local diverge da baseline declarada: {local_meteorology}"
                )
        aermod_meteorology = baseline_meteorology
        rline_meteorology = baseline_meteorology
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
        expected_group="ALL",
        expected_netid="RCART",
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
