"""Compatibilidade dos scripts historicos com a API central."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rline_pipeline import (  # noqa: E402
    SCHEMA_VERSION,
    CaseConfig,
    GridConfig,
    load_case_results,
)

REFERENCE_CONFIG = CaseConfig(
    schema_version=SCHEMA_VERSION,
    nome="Caso_Pipeline",
    descricao="Caso historico de referencia",
    comprimento=1000.0,
    y_rodovia=0.0,
    qs=0.001,
    width=20.0,
    grid=GridConfig(
        xini=0.0,
        xn=26,
        xdelta=40.0,
        yini=-300.0,
        yn=31,
        ydelta=20.0,
    ),
    transecto_x=600.0,
    periodos_esperados=120,
)
REFERENCE_AERMOD_TITLE = "TESTE RLINE COM DADOS ONSITE SINTETICOS"
REFERENCE_RLINE_METEOROLOGY_PATH = "../dados_aermet/ONSITE.SFC"


def load_reference() -> tuple[CaseConfig, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return load_case_results(
        BASE,
        config=REFERENCE_CONFIG,
        expected_aermod_title=REFERENCE_AERMOD_TITLE,
        expected_rline_meteorology_path=REFERENCE_RLINE_METEOROLOGY_PATH,
    )
