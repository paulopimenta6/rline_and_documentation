"""Parsers estritos para saidas AERMOD e RLINE."""

from __future__ import annotations

import csv
from datetime import date
from itertools import product
import math
from pathlib import Path
import re
from typing import Collection, Sequence

import numpy as np
import pandas as pd

from .errors import PipelineValidationError

AERMOD_COLUMNS = [
    "X",
    "Y",
    "conc",
    "ZELEV",
    "ZHILL",
    "ZFLAG",
    "AVE",
    "GRP",
    "NHRS",
    "NETID",
]
RLINE_COLUMNS = ["Year", "JD", "Hour", "X", "Y", "Z", "C"]
RLINE_HEADER = [
    "Year",
    "Julian_Day",
    "Hour",
    "X-Coordinate",
    "Y-Coordinate",
    "Z-Coordinate",
    "C_HWY",
]
Period = tuple[int, int, int]
ExpectedPeriods = int | Collection[Period]


def _read_header(path: Path, line_count: int) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", errors="strict") as source:
            lines = []
            for _ in range(line_count):
                line = source.readline()
                if line == "":
                    break
                lines.append(line.rstrip("\n"))
    except OSError as error:
        raise PipelineValidationError(f"nao foi possivel ler {path}: {error}") from error
    if len(lines) != line_count:
        raise PipelineValidationError(
            f"{path}: cabecalho incompleto; esperadas {line_count} linhas, encontradas {len(lines)}"
        )
    return lines


def _require_file(path: str | Path, label: str) -> Path:
    source = Path(path)
    if not source.is_file():
        raise PipelineValidationError(f"{label} nao encontrado: {source}")
    if source.stat().st_size == 0:
        raise PipelineValidationError(f"{label} vazio: {source}")
    return source


def _convert_numeric(frame: pd.DataFrame, columns: Sequence[str], source: Path) -> None:
    for column in columns:
        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except (TypeError, ValueError) as error:
            raise PipelineValidationError(
                f"{source}: coluna {column} contem valor nao numerico: {error}"
            ) from error
    values = frame[list(columns)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        bad_rows = np.flatnonzero(~np.isfinite(values).all(axis=1))[:5] + 1
        raise PipelineValidationError(
            f"{source}: valores nao finitos nas linhas de dados {bad_rows.tolist()}"
        )


def _convert_integer(frame: pd.DataFrame, columns: Sequence[str], source: Path) -> None:
    for column in columns:
        values = frame[column].to_numpy(dtype=float)
        if not np.equal(values, np.floor(values)).all():
            raise PipelineValidationError(f"{source}: coluna {column} deve conter apenas inteiros")
        frame[column] = frame[column].astype("int64")


def _coordinate_columns(left: pd.DataFrame, right: pd.DataFrame) -> list[str]:
    columns = ["X", "Y"]
    if "Z" in left.columns and "Z" in right.columns:
        columns.append("Z")
    return columns


def _validate_unique_coordinates(
    frame: pd.DataFrame, source: str, columns: Sequence[str] = ("X", "Y")
) -> None:
    duplicates = frame.duplicated(list(columns), keep=False)
    if duplicates.any():
        examples = frame.loc[duplicates, list(columns)].head(5).to_dict("records")
        joined = "/".join(columns)
        raise PipelineValidationError(
            f"{source}: coordenadas {joined} duplicadas; exemplos: {examples}"
        )


def coordinate_mapping(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    tolerance: float | None,
    labels: tuple[str, str] = ("resultado", "referencia"),
) -> np.ndarray:
    """Mapeia cada coordenada de ``left`` para uma unica linha de ``right``."""

    if len(left) != len(right):
        raise PipelineValidationError(
            f"cardinalidade de coordenadas difere: {labels[0]}={len(left)}, "
            f"{labels[1]}={len(right)}"
        )
    columns = _coordinate_columns(left, right)
    _validate_unique_coordinates(left, labels[0], columns)
    _validate_unique_coordinates(right, labels[1], columns)

    left_index = pd.MultiIndex.from_frame(left[columns])
    right_index = pd.MultiIndex.from_frame(right[columns])
    exact = right_index.get_indexer(left_index)
    if (exact >= 0).all() and len(np.unique(exact)) == len(exact):
        return exact

    if tolerance is None:
        missing = left.loc[exact < 0, columns].head(5).to_dict("records")
        raise PipelineValidationError(
            f"coordenadas sem correspondencia exata entre {labels[0]} e {labels[1]}; "
            f"exemplos: {missing}"
        )
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise PipelineValidationError("tolerancia de coordenadas deve ser finita e positiva")

    left_values = left[columns].to_numpy(dtype=float)
    right_values = right[columns].to_numpy(dtype=float)
    if not np.isfinite(left_values).all() or not np.isfinite(right_values).all():
        raise PipelineValidationError(
            f"coordenadas nao finitas entre {labels[0]} e {labels[1]}"
        )

    # A matriz cartesiana N x N usada anteriormente tornava o fallback por
    # tolerancia inviavel para grades grandes. Um indice espacial por celulas
    # de lado igual a tolerancia limita a busca a 3**dim celulas vizinhas sem
    # alterar o criterio componente-a-componente usado pela API.
    buckets: dict[tuple[int, ...], list[int]] = {}
    for right_index_value, values in enumerate(right_values):
        key = tuple(math.floor(float(value) / tolerance) for value in values)
        buckets.setdefault(key, []).append(right_index_value)

    offsets = tuple(product((-1, 0, 1), repeat=len(columns)))
    mapping = np.full(len(left_values), -1, dtype=np.int64)
    used_right: set[int] = set()
    bad_left: list[int] = []
    for left_index_value, values in enumerate(left_values):
        key = tuple(math.floor(float(value) / tolerance) for value in values)
        matches: list[int] = []
        for offset in offsets:
            neighbour = tuple(cell + delta for cell, delta in zip(key, offset, strict=True))
            for right_index_value in buckets.get(neighbour, ()):
                if np.all(np.abs(values - right_values[right_index_value]) <= tolerance):
                    matches.append(right_index_value)
                    if len(matches) > 1:
                        break
            if len(matches) > 1:
                break
        if len(matches) != 1 or matches[0] in used_right:
            bad_left.append(left_index_value)
            if len(bad_left) >= 5:
                break
            continue
        mapping[left_index_value] = matches[0]
        used_right.add(matches[0])

    if bad_left or len(used_right) != len(right_values):
        bad_right = [index for index in range(len(right_values)) if index not in used_right][:5]
        raise PipelineValidationError(
            f"correspondencia por tolerancia {tolerance:g} nao e bijetiva entre "
            f"{labels[0]} e {labels[1]}; indices ambiguos/ausentes: "
            f"{labels[0]}={bad_left}, {labels[1]}={bad_right}"
        )
    return mapping


def _validate_expected_coordinates(
    actual: pd.DataFrame,
    expected: pd.DataFrame | None,
    source: Path,
    tolerance: float | None,
) -> None:
    if expected is None:
        return
    actual_coordinates = actual
    if "Z" not in actual_coordinates.columns and "ZFLAG" in actual_coordinates.columns:
        actual_coordinates = actual_coordinates.rename(columns={"ZFLAG": "Z"})
    columns = _coordinate_columns(actual_coordinates, expected)
    coordinate_mapping(
        actual_coordinates[columns],
        expected[columns],
        tolerance=tolerance,
        labels=(str(source), "grade esperada"),
    )


def parse_aermod(
    path: str | Path,
    *,
    expected_receptors: int | None = None,
    expected_periods: int | None = None,
    expected_coordinates: pd.DataFrame | None = None,
    coordinate_tolerance: float | None = None,
    expected_group: str | None = None,
    expected_netid: str | None = None,
) -> pd.DataFrame:
    """Le ``CONC_PLOT.PLT`` e valida estrutura, finitude e cardinalidade."""

    source = _require_file(path, "saida AERMOD")
    header = _read_header(source, 8)
    required_header_labels = (
        "X",
        "Y",
        "AVERAGE CONC",
        "ZELEV",
        "ZHILL",
        "ZFLAG",
        "AVE",
        "GRP",
        "NUM HRS",
        "NET ID",
    )
    if not all(label in header[6] for label in required_header_labels):
        raise PipelineValidationError(
            f"{source}: cabecalho de colunas AERMOD inesperado: {header[6].strip()}"
        )

    try:
        frame = pd.read_csv(source, sep=r"\s+", skiprows=8, header=None)
    except (OSError, pd.errors.ParserError) as error:
        raise PipelineValidationError(f"falha ao parsear {source}: {error}") from error
    if frame.shape[1] != len(AERMOD_COLUMNS):
        raise PipelineValidationError(
            f"{source}: esperadas {len(AERMOD_COLUMNS)} colunas AERMOD, "
            f"encontradas {frame.shape[1]}"
        )
    if frame.empty:
        raise PipelineValidationError(f"{source}: nenhuma linha de receptor")
    frame.columns = AERMOD_COLUMNS
    if frame.isna().any().any():
        raise PipelineValidationError(f"{source}: ha campos ausentes na tabela AERMOD")

    numeric_columns = ["X", "Y", "conc", "ZELEV", "ZHILL", "ZFLAG", "NHRS"]
    _convert_numeric(frame, numeric_columns, source)
    _convert_integer(frame, ["NHRS"], source)
    _validate_unique_coordinates(frame, str(source))

    declared_match = re.search(r"FOR A TOTAL OF\s+(\d+)\s+RECEPTORS", header[4], re.IGNORECASE)
    if not declared_match:
        raise PipelineValidationError(f"{source}: total declarado de receptores ausente")
    if int(declared_match.group(1)) != len(frame):
        raise PipelineValidationError(
            f"{source}: cabecalho declara {declared_match.group(1)} receptores, "
            f"mas os dados contem {len(frame)}"
        )

    if (frame["conc"] < 0).any():
        raise PipelineValidationError(f"{source}: concentracao AERMOD negativa")
    if not frame["AVE"].eq("PERIOD").all():
        values = sorted(frame["AVE"].astype(str).unique().tolist())
        raise PipelineValidationError(
            f"{source}: AVE deve ser PERIOD em todas as linhas; encontrado: {values}"
        )
    if expected_receptors is not None and len(frame) != expected_receptors:
        raise PipelineValidationError(
            f"{source}: receptores AERMOD={len(frame)}, esperado={expected_receptors}"
        )
    if expected_periods is not None and not frame["NHRS"].eq(expected_periods).all():
        counts = sorted(frame["NHRS"].unique().tolist())
        raise PipelineValidationError(
            f"{source}: NHRS={counts}, esperado={expected_periods} em cada receptor"
        )
    for column, expected in (("GRP", expected_group), ("NETID", expected_netid)):
        if expected is not None and not frame[column].eq(expected).all():
            values = sorted(frame[column].astype(str).unique().tolist())
            raise PipelineValidationError(
                f"{source}: {column}={values}, esperado={expected!r} em cada receptor"
            )
    _validate_expected_coordinates(frame, expected_coordinates, source, coordinate_tolerance)
    return frame


def _normalise_rline_header(line: str) -> list[str]:
    columns = next(csv.reader([line]))
    return [column.strip() for column in columns if column.strip()]


def _expected_period_set(expected_periods: ExpectedPeriods) -> set[Period] | None:
    if isinstance(expected_periods, int):
        if isinstance(expected_periods, bool) or expected_periods <= 0:
            raise PipelineValidationError("numero esperado de periodos deve ser positivo")
        return None
    raw_periods = list(expected_periods)
    if not raw_periods:
        raise PipelineValidationError("conjunto esperado de periodos nao pode ser vazio")
    periods: set[Period] = set()
    for period in raw_periods:
        if not isinstance(period, (tuple, list)) or len(period) != 3:
            raise PipelineValidationError(
                "cada periodo esperado deve ser uma tupla (Year, JD, Hour)"
            )
        if any(not isinstance(value, int) or isinstance(value, bool) for value in period):
            raise PipelineValidationError("Year, JD e Hour esperados devem ser inteiros")
        year, julian_day, hour = period
        if year < 1 or not 1 <= julian_day <= 366 or not 1 <= hour <= 24:
            raise PipelineValidationError(f"periodo esperado invalido: {tuple(period)}")
        periods.add((year, julian_day, hour))
    if len(periods) != len(raw_periods):
        raise PipelineValidationError("conjunto esperado de periodos contem duplicatas")
    return periods


def parse_rline(
    path: str | Path,
    *,
    expected_receptors: int | None = None,
    expected_periods: ExpectedPeriods = 120,
    expected_coordinates: pd.DataFrame | None = None,
    coordinate_tolerance: float | None = None,
) -> pd.DataFrame:
    """Le todas as linhas RLINE, inclusive a ultima, e valida cada periodo."""

    source = _require_file(path, "saida RLINE")
    header = _read_header(source, 12)
    columns = _normalise_rline_header(header[11])
    if columns != RLINE_HEADER:
        raise PipelineValidationError(
            f"{source}: colunas RLINE inesperadas; esperado={RLINE_HEADER}, encontrado={columns}"
        )

    try:
        raw = pd.read_csv(source, skiprows=12, header=None, skip_blank_lines=True)
    except (OSError, pd.errors.ParserError) as error:
        raise PipelineValidationError(f"falha ao parsear {source}: {error}") from error
    if raw.empty:
        raise PipelineValidationError(f"{source}: nenhuma linha de concentracao")
    if raw.shape[1] not in (7, 8):
        raise PipelineValidationError(
            f"{source}: esperadas 7 colunas e uma virgula final opcional; "
            f"encontradas {raw.shape[1]} colunas"
        )
    if raw.shape[1] == 8:
        trailing_values = raw.iloc[:, 7].fillna("").astype(str).str.strip()
        if trailing_values.ne("").any():
            raise PipelineValidationError(f"{source}: oitava coluna RLINE deve estar vazia")

    frame = raw.iloc[:, :7].copy()
    frame.columns = RLINE_COLUMNS
    if frame.isna().any().any():
        bad = (frame.isna().any(axis=1).to_numpy().nonzero()[0][:5] + 1).tolist()
        raise PipelineValidationError(f"{source}: linhas RLINE com campos ausentes: {bad}")
    _convert_numeric(frame, RLINE_COLUMNS, source)
    _convert_integer(frame, ["Year", "JD", "Hour"], source)

    if not frame["JD"].between(1, 366).all():
        raise PipelineValidationError(f"{source}: Julian Day deve estar entre 1 e 366")
    if not frame["Hour"].between(1, 24).all():
        raise PipelineValidationError(f"{source}: Hour deve estar entre 1 e 24")
    if (frame["C"] < 0).any():
        raise PipelineValidationError(
            f"{source}: concentracao RLINE negativa ou sentinela de dado ausente"
        )

    duplicate_keys = ["Year", "JD", "Hour", "X", "Y"]
    duplicated = frame.duplicated(duplicate_keys, keep=False)
    if duplicated.any():
        examples = frame.loc[duplicated, duplicate_keys].head(5).to_dict("records")
        raise PipelineValidationError(
            f"{source}: periodos duplicados por receptor; exemplos: {examples}"
        )

    receptors = frame[["X", "Y", "Z"]].drop_duplicates().reset_index(drop=True)
    z_per_xy = frame.groupby(["X", "Y"], sort=False)["Z"].nunique()
    if not z_per_xy.eq(1).all():
        raise PipelineValidationError(f"{source}: um receptor X/Y possui mais de um Z")
    if expected_receptors is not None and len(receptors) != expected_receptors:
        raise PipelineValidationError(
            f"{source}: receptores RLINE={len(receptors)}, esperado={expected_receptors}"
        )

    declared_match = re.search(r"\((\d+)\s+Receptors\)", header[2], re.IGNORECASE)
    if declared_match and int(declared_match.group(1)) != len(receptors):
        raise PipelineValidationError(
            f"{source}: cabecalho declara {declared_match.group(1)} receptores, "
            f"mas os dados contem {len(receptors)}"
        )

    observed_periods = {
        (int(year), int(day), int(hour))
        for year, day, hour in frame[["Year", "JD", "Hour"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    }
    explicit_periods = _expected_period_set(expected_periods)
    expected_count = (
        expected_periods if isinstance(expected_periods, int) else len(explicit_periods or ())
    )
    if explicit_periods is not None and observed_periods != explicit_periods:
        missing = sorted(explicit_periods - observed_periods)[:5]
        extra = sorted(observed_periods - explicit_periods)[:5]
        raise PipelineValidationError(
            f"{source}: conjunto global de periodos difere do esperado; "
            f"faltantes={missing}, extras={extra}"
        )
    if len(observed_periods) != expected_count:
        raise PipelineValidationError(
            f"{source}: periodos globais={len(observed_periods)}, esperado={expected_count}"
        )

    counts = frame.groupby(["X", "Y"], sort=False).size()
    invalid_counts = counts[counts != expected_count]
    if not invalid_counts.empty:
        examples = [
            {"X": index[0], "Y": index[1], "periodos": int(count)}
            for index, count in invalid_counts.head(5).items()
        ]
        raise PipelineValidationError(
            f"{source}: cada receptor deve possuir exatamente {expected_count} periodos; "
            f"receptores invalidos={len(invalid_counts)}, exemplos={examples}"
        )

    expected_rows = len(receptors) * expected_count
    if len(frame) != expected_rows:
        raise PipelineValidationError(
            f"{source}: linhas={len(frame)}, esperado={expected_rows} (receptores x periodos)"
        )
    _validate_expected_coordinates(receptors, expected_coordinates, source, coordinate_tolerance)
    return frame


def validate_aermod_completion(path: str | Path, expected_periods: int) -> None:
    """Exige termino bem-sucedido, zero erros fatais e o total de horas esperado."""

    source = _require_file(path, "log AERMOD")
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise PipelineValidationError(f"nao foi possivel ler {source}: {error}") from error

    if not re.search(r"AERMOD\s+Finishes\s+Successfully", text, re.IGNORECASE):
        raise PipelineValidationError(f"{source}: marcador 'AERMOD Finishes Successfully' ausente")
    fatal_counts = [
        int(value)
        for value in re.findall(r"A Total of\s+(\d+)\s+Fatal Error Message", text, re.IGNORECASE)
    ]
    if not fatal_counts or any(fatal_counts):
        raise PipelineValidationError(
            f"{source}: contagem de erros fatais invalida: {fatal_counts or 'ausente'}"
        )
    hours = [
        int(value)
        for value in re.findall(r"A Total of\s+(\d+)\s+Hours Were Processed", text, re.IGNORECASE)
    ]
    if not hours or hours[-1] != expected_periods:
        raise PipelineValidationError(
            f"{source}: horas processadas={hours[-1] if hours else 'ausente'}, "
            f"esperado={expected_periods}"
        )
    for label in ("Calm", "Missing"):
        counts = [
            int(value)
            for value in re.findall(
                rf"A Total of\s+(\d+)\s+{label} Hours Identified", text, re.IGNORECASE
            )
        ]
        if counts and any(counts):
            raise PipelineValidationError(
                f"{source}: horas {label.lower()} devem ser zero; encontrado={counts}"
            )


def parse_rline_meteorology_periods(path: str | Path) -> set[Period]:
    """Read and validate calendar periods from an AERMET surface file."""

    source = _require_file(path, "meteorologia RLINE")
    try:
        lines = source.read_text(encoding="ascii").splitlines()[1:]
    except (OSError, UnicodeError) as error:
        raise PipelineValidationError(f"falha ao ler {source}: {error}") from error

    periods: set[Period] = set()
    for line_number, line in enumerate(lines, start=2):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) < 5:
            raise PipelineValidationError(f"{source}:{line_number}: registro incompleto")
        try:
            year, month, day, julian_day, hour = (int(value) for value in fields[:5])
            calendar_day = date(year, month, day)
        except (ValueError, OverflowError) as error:
            raise PipelineValidationError(
                f"{source}:{line_number}: periodo meteorologico invalido"
            ) from error
        actual_julian_day = calendar_day.timetuple().tm_yday
        if julian_day != actual_julian_day or not 1 <= hour <= 24:
            raise PipelineValidationError(
                f"{source}:{line_number}: calendario/JD/hora inconsistentes"
            )
        period = (year, julian_day, hour)
        if period in periods:
            raise PipelineValidationError(
                f"{source}:{line_number}: periodo meteorologico duplicado {period}"
            )
        periods.add(period)
    if not periods:
        raise PipelineValidationError(f"{source}: nenhum periodo meteorologico")
    return periods


def validate_rline_output(
    output_path: str | Path,
    receptor_path: str | Path,
    meteorology_path: str | Path,
    *,
    coordinate_tolerance: float = 1.0e-3,
) -> None:
    """Valida estruturalmente um output RLINE standalone, inclusive multiplos grupos."""

    output = _require_file(output_path, "saida RLINE")
    receptors_source = _require_file(receptor_path, "receptores RLINE")
    meteorology_source = _require_file(meteorology_path, "meteorologia RLINE")

    try:
        receptor_lines = receptors_source.read_text(encoding="ascii").splitlines()[3:]
    except (OSError, UnicodeError) as error:
        raise PipelineValidationError(f"falha ao ler inputs RLINE: {error}") from error

    receptor_values: list[tuple[float, float, float]] = []
    for line_number, line in enumerate(receptor_lines, start=4):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) < 3:
            raise PipelineValidationError(f"{receptors_source}:{line_number}: receptor incompleto")
        try:
            receptor_values.append(tuple(float(value) for value in fields[:3]))
        except ValueError as error:
            raise PipelineValidationError(
                f"{receptors_source}:{line_number}: receptor nao numerico"
            ) from error
    expected_receptors = pd.DataFrame(receptor_values, columns=["X", "Y", "Z"])
    if expected_receptors.empty:
        raise PipelineValidationError(f"{receptors_source}: nenhum receptor")
    if not np.isfinite(expected_receptors.to_numpy()).all():
        raise PipelineValidationError(f"{receptors_source}: receptor nao finito")
    _validate_unique_coordinates(expected_receptors, str(receptors_source), ["X", "Y", "Z"])

    expected_periods = parse_rline_meteorology_periods(meteorology_source)

    try:
        with output.open(encoding="ascii", newline="") as stream:
            rows = list(csv.reader(stream))
    except (OSError, UnicodeError, csv.Error) as error:
        raise PipelineValidationError(f"falha ao ler {output}: {error}") from error
    header_index = next(
        (index for index, row in enumerate(rows) if row and row[0].strip() == "Year"),
        None,
    )
    if header_index is None:
        raise PipelineValidationError(f"{output}: cabecalho tabular RLINE ausente")
    columns = [field.strip() for field in rows[header_index] if field.strip()]
    expected_prefix = RLINE_HEADER[:6]
    if columns[:6] != expected_prefix or len(columns) < 7:
        raise PipelineValidationError(f"{output}: chaves de colunas RLINE inesperadas")
    if not all(column.startswith("C_") for column in columns[6:]):
        raise PipelineValidationError(f"{output}: colunas de concentracao RLINE inesperadas")

    data_rows: list[list[str]] = []
    for row in rows[header_index + 1 :]:
        fields = [field.strip() for field in row]
        while fields and not fields[-1]:
            fields.pop()
        if not fields:
            continue
        if len(fields) != len(columns):
            raise PipelineValidationError(
                f"{output}: linha com {len(fields)} campos; esperado={len(columns)}"
            )
        data_rows.append(fields)
    if not data_rows:
        raise PipelineValidationError(f"{output}: nenhuma concentracao")

    frame = pd.DataFrame(data_rows, columns=columns)
    _convert_numeric(frame, columns, output)
    _convert_integer(frame, columns[:3], output)
    concentrations = frame[columns[6:]].to_numpy(dtype=float)
    if (concentrations < 0.0).any():
        raise PipelineValidationError(
            f"{output}: concentracao negativa ou sentinela de dado ausente"
        )

    actual_periods = {
        tuple(period) for period in frame[columns[:3]].itertuples(index=False, name=None)
    }
    if actual_periods != expected_periods:
        raise PipelineValidationError(f"{output}: periodos diferem da meteorologia informada")
    actual_receptors = frame[columns[3:6]].drop_duplicates().reset_index(drop=True)
    actual_receptors.columns = ["X", "Y", "Z"]
    coordinate_mapping(
        actual_receptors,
        expected_receptors,
        tolerance=coordinate_tolerance,
        labels=(str(output), str(receptors_source)),
    )
    key_columns = columns[:6]
    if frame.duplicated(key_columns).any():
        raise PipelineValidationError(f"{output}: chave receptor-periodo duplicada")
    expected_rows = len(expected_receptors) * len(expected_periods)
    if len(frame) != expected_rows:
        raise PipelineValidationError(
            f"{output}: linhas={len(frame)}, esperado={expected_rows} (receptores x periodos)"
        )
