"""Carregamento, validacao e grade dos casos RLINE/AERMOD."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from importlib.resources import files
import json
import math
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
import pandas as pd

from .errors import ConfigValidationError

SCHEMA_VERSION = 1
SCHEMA_FILENAME = "case-config-v1.schema.json"


@dataclass(frozen=True)
class GridConfig:
    """Parametros de uma grade cartesiana regular."""

    xini: float
    xn: int
    xdelta: float
    yini: float
    yn: int
    ydelta: float

    @property
    def numero_receptores(self) -> int:
        return self.xn * self.yn

    @property
    def xmax(self) -> float:
        return self.xini + (self.xn - 1) * self.xdelta

    @property
    def ymax(self) -> float:
        return self.yini + (self.yn - 1) * self.ydelta


@dataclass(frozen=True)
class CaseConfig:
    """Configuracao validada e imutavel de um caso."""

    schema_version: int
    nome: str
    descricao: str
    comprimento: float
    y_rodovia: float
    qs: float
    width: float
    grid: GridConfig
    transecto_x: float
    periodos_esperados: int
    emis_fator: float | None = None

    @property
    def emissao_rline(self) -> float:
        if self.emis_fator is not None:
            return self.emis_fator
        return self.qs * self.width

    @property
    def numero_receptores(self) -> int:
        return self.grid.numero_receptores

    @property
    def inicio_rodovia(self) -> tuple[float, float]:
        return (0.0, self.y_rodovia)

    @property
    def fim_rodovia(self) -> tuple[float, float]:
        return (self.comprimento, self.y_rodovia)


def _reject_json_constant(value: str) -> None:
    raise ConfigValidationError(f"constante JSON nao finita nao permitida: {value}")


def _load_schema() -> Mapping[str, Any]:
    schema_resource = files("rline_pipeline.schemas").joinpath(SCHEMA_FILENAME)
    with schema_resource.open("r", encoding="utf-8") as schema_file:
        return json.load(schema_file)


def _format_schema_error(error: Any) -> str:
    location = ".".join(str(part) for part in error.absolute_path)
    if not location:
        location = "config"
    return f"{location}: {error.message}"


def _validate_finite_values(value: Any, location: str = "config") -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ConfigValidationError(f"{location}: numero deve ser finito")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_finite_values(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_finite_values(item, f"{location}[{index}]")


def validate_case_config(config: CaseConfig) -> None:
    """Valida restricoes semanticas que o JSON Schema nao expressa."""

    numeric_values = {
        "comprimento": config.comprimento,
        "y_rodovia": config.y_rodovia,
        "qs": config.qs,
        "width": config.width,
        "transecto_x": config.transecto_x,
        "grid.xini": config.grid.xini,
        "grid.xdelta": config.grid.xdelta,
        "grid.yini": config.grid.yini,
        "grid.ydelta": config.grid.ydelta,
        "emis_fator": config.emis_fator,
    }
    for name, value in numeric_values.items():
        if value is not None and not math.isfinite(value):
            raise ConfigValidationError(f"{name}: numero deve ser finito")

    if config.comprimento <= 0:
        raise ConfigValidationError("comprimento deve ser maior que zero")
    if config.qs <= 0:
        raise ConfigValidationError("qs deve ser maior que zero")
    if config.width <= 0:
        raise ConfigValidationError("width deve ser maior que zero")
    if config.emissao_rline <= 0 or not math.isfinite(config.emissao_rline):
        raise ConfigValidationError("emissao RLINE deve ser finita e maior que zero")
    if config.grid.xn < 2 or config.grid.yn < 2:
        raise ConfigValidationError("dimensoes xn e yn devem ser pelo menos 2 para gerar mapas")
    if config.grid.xdelta <= 0 or config.grid.ydelta <= 0:
        raise ConfigValidationError("deltas xdelta e ydelta devem ser maiores que zero")
    if config.periodos_esperados <= 0:
        raise ConfigValidationError("periodos_esperados deve ser positivo")

    if config.numero_receptores > 1_000_000:
        raise ConfigValidationError("grade excede o limite operacional de 1000000 receptores")
    for axis_name, start, delta, count in (
        ("X", config.grid.xini, config.grid.xdelta, config.grid.xn),
        ("Y", config.grid.yini, config.grid.ydelta, config.grid.yn),
    ):
        decimal_start = Decimal(str(start))
        decimal_delta = Decimal(str(delta))
        float_axis = tuple(
            float(decimal_start + index * decimal_delta)
            for index in (0, 1, count - 2, count - 1)
        )
        if not all(math.isfinite(value) for value in float_axis):
            raise ConfigValidationError(f"extensao {axis_name} da grade deve ser finita")
        if float_axis[0] == float_axis[1] or float_axis[2] == float_axis[3]:
            raise ConfigValidationError(
                f"coordenadas {axis_name} da grade perdem unicidade em ponto flutuante"
            )

    road_grid_start = max(0.0, config.grid.xini)
    road_grid_end = min(config.comprimento, config.grid.xmax)
    if road_grid_start > road_grid_end:
        raise ConfigValidationError("a rodovia nao intercepta a extensao X da grade")
    if not road_grid_start <= config.transecto_x <= road_grid_end:
        raise ConfigValidationError(
            "transecto_x deve estar simultaneamente sobre a rodovia e dentro da grade "
            f"([{road_grid_start:g}, {road_grid_end:g}])"
        )
    if not config.grid.yini <= config.y_rodovia <= config.grid.ymax:
        raise ConfigValidationError(
            "y_rodovia deve estar dentro da extensao Y da grade "
            f"([{config.grid.yini:g}, {config.grid.ymax:g}])"
        )


def load_case_config(path: str | Path) -> CaseConfig:
    """Carrega um JSON v1, valida seu schema e retorna uma configuracao tipada."""

    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigValidationError(f"config nao encontrado: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            raw = json.load(config_file, parse_constant=_reject_json_constant)
    except json.JSONDecodeError as error:
        raise ConfigValidationError(
            f"JSON invalido em {config_path}: linha {error.lineno}, coluna {error.colno}: "
            f"{error.msg}"
        ) from error
    except OSError as error:
        raise ConfigValidationError(f"nao foi possivel ler {config_path}: {error}") from error

    if not isinstance(raw, dict):
        raise ConfigValidationError("config: o documento raiz deve ser um objeto JSON")
    _validate_finite_values(raw)

    version = raw.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version != SCHEMA_VERSION:
        raise ConfigValidationError(
            f"schema_version deve ser {SCHEMA_VERSION}; recebido: {version!r}"
        )

    errors = sorted(
        Draft202012Validator(_load_schema()).iter_errors(raw),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        details = "; ".join(_format_schema_error(error) for error in errors)
        raise ConfigValidationError(f"config invalido: {details}")

    grid_data = raw["grid"]
    config = CaseConfig(
        schema_version=int(raw["schema_version"]),
        nome=raw["nome"],
        descricao=raw["descricao"],
        comprimento=float(raw["comprimento"]),
        y_rodovia=float(raw["y_rodovia"]),
        qs=float(raw["qs"]),
        width=float(raw["width"]),
        grid=GridConfig(
            xini=float(grid_data["xini"]),
            xn=int(grid_data["xn"]),
            xdelta=float(grid_data["xdelta"]),
            yini=float(grid_data["yini"]),
            yn=int(grid_data["yn"]),
            ydelta=float(grid_data["ydelta"]),
        ),
        transecto_x=float(raw["transecto_x"]),
        periodos_esperados=int(raw["periodos_esperados"]),
        emis_fator=(None if raw.get("emis_fator") is None else float(raw["emis_fator"])),
    )
    validate_case_config(config)
    return config


def decimal_grid_axes(grid: GridConfig) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    """Gera eixos por aritmetica decimal, sem arredondamento cumulativo."""

    x_start = Decimal(str(grid.xini))
    x_delta = Decimal(str(grid.xdelta))
    y_start = Decimal(str(grid.yini))
    y_delta = Decimal(str(grid.ydelta))
    xs = tuple(x_start + index * x_delta for index in range(grid.xn))
    ys = tuple(y_start + index * y_delta for index in range(grid.yn))
    return xs, ys


def generate_grid(grid: GridConfig) -> pd.DataFrame:
    """Retorna a grade na ordem GRIDCART/RLINE: X varia primeiro, depois Y."""

    xs, ys = decimal_grid_axes(grid)
    rows = ((float(x), float(y), 0.0) for y in ys for x in xs)
    return pd.DataFrame(rows, columns=["X", "Y", "Z"])
