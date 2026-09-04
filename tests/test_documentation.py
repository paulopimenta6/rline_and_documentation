"""Checks for the beginner-facing documentation entry points."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
ENTRY_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "PRIMEIROS_PASSOS.md",
    ROOT / "docs" / "GUIA_PROJETO.md",
    ROOT / "docs" / "FORMATOS_DE_ENTRADA.md",
)
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def test_documentation_entry_points_have_no_broken_local_links() -> None:
    broken: list[str] = []

    for document in ENTRY_DOCUMENTS:
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>")
            parsed = urlparse(target)
            if parsed.scheme or target.startswith("#"):
                continue

            relative_path = unquote(parsed.path)
            if not relative_path:
                continue

            destination = (document.parent / relative_path).resolve()
            if not destination.exists():
                broken.append(
                    f"{document.relative_to(ROOT)} -> {raw_target}"
                )

    assert not broken, "Links locais quebrados:\n" + "\n".join(broken)


def test_beginner_guide_keeps_the_complete_safe_path() -> None:
    guide = (ROOT / "docs" / "PRIMEIROS_PASSOS.md").read_text(encoding="utf-8")
    required_steps = (
        "bash scripts/verificar_ambiente.sh",
        "python3 -m venv .venv",
        "bash .github/scripts/install-python-deps.sh",
        "make models",
        "python scripts/gerar_dados_exemplo.py --name meu-primeiro-teste",
        "bash scripts/run_aermet.sh",
        "bash scripts/run_caso.sh",
        "python scripts/teste_casos.py",
    )

    missing = [step for step in required_steps if step not in guide]
    assert not missing, "Etapas essenciais ausentes do guia: " + ", ".join(missing)


def test_beginner_guide_warns_that_example_data_are_not_real() -> None:
    guide = (ROOT / "docs" / "PRIMEIROS_PASSOS.md").read_text(encoding="utf-8")
    normalized = guide.casefold()

    assert "dados sintéticos" in normalized
    assert "regulatóri" in normalized
