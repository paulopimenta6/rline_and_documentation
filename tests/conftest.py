from __future__ import annotations

from pathlib import Path

import pytest

from rline_pipeline import load_case_results

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def case_paths() -> dict[str, Path]:
    return {
        path.parent.name: path.parent for path in sorted((ROOT / "casos").glob("*/config.json"))
    }


@pytest.fixture(scope="session")
def real_results(case_paths: dict[str, Path]) -> dict[str, tuple]:
    return {name: load_case_results(path) for name, path in case_paths.items()}
