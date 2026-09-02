"""Deterministic, synthetic meteorology for safe demonstrations and smoke tests."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any


@dataclass(frozen=True)
class ExampleScenario:
    """Parameters that define one explicitly synthetic meteorological scenario."""

    name: str
    description: str
    days: tuple[int, ...]
    wind_direction: float
    direction_jitter: float
    stability: str

    @property
    def periods(self) -> int:
        return len(self.days) * 24


SCENARIOS: dict[str, ExampleScenario] = {
    "smoke-crosswind": ExampleScenario(
        name="smoke-crosswind",
        description="24 h, vento aproximadamente transversal a rodovia leste-oeste",
        days=(1,),
        wind_direction=180.0,
        direction_jitter=3.0,
        stability="mixed",
    ),
    "smoke-near-parallel": ExampleScenario(
        name="smoke-near-parallel",
        description="24 h, vento quase paralelo a rodovia para exercitar geometria adversa",
        days=(1,),
        wind_direction=270.0,
        direction_jitter=1.0,
        stability="stable",
    ),
    "mixed-diurnal": ExampleScenario(
        name="mixed-diurnal",
        description="120 h com ciclo diurno sintetico convectivo/estavel",
        days=(1, 2, 3, 4, 5),
        wind_direction=265.0,
        direction_jitter=8.0,
        stability="mixed",
    ),
}

ALTITUDES = (10.0, 50.0, 100.0)
VEERING = (0.0, 6.0, 12.0)


def get_example_scenario(name: str) -> ExampleScenario:
    """Return a named scenario, rejecting implicit fallback behavior."""

    try:
        return SCENARIOS[name]
    except KeyError as error:
        choices = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"cenario desconhecido {name!r}; opcoes: {choices}") from error


def _range(values: list[float]) -> dict[str, float]:
    return {"min": min(values), "max": max(values)}


def generate_onsite_text(
    scenario_name: str = "mixed-diurnal", *, seed: int = 42
) -> tuple[str, dict[str, Any]]:
    """Generate AERMET ONSITE free-format records and a compact QA summary.

    The function has no file-system or process-wide random state side effects.
    Values are illustrative and must not be represented as observations.
    """

    scenario = get_example_scenario(scenario_name)
    generator = random.Random(seed)
    lines: list[str] = []
    wind_speeds: list[float] = []
    wind_directions: list[float] = []
    temperatures: list[float] = []
    mixing_heights: list[float] = []
    cloud_covers: list[float] = []

    for day in scenario.days:
        for hour in range(1, 25):
            diurnal = (
                max(0.0, math.sin(math.pi * (hour - 6.0) / 16.0))
                if 7 <= hour <= 22
                else 0.0
            )
            convection = 0.0 if scenario.stability == "stable" else diurnal

            ws10 = 3.5 * (0.55 + 0.45 * convection) + generator.uniform(-0.4, 0.4)
            ws10 = max(0.8, ws10)
            tt10 = (
                8.0
                + 7.0 * math.sin(math.pi * (hour - 7.0) / 14.0)
                + generator.uniform(-0.5, 0.5)
            )
            tskc = generator.choice((0, 0, 1, 2, 3, 4, 4, 5, 6))
            if convection > 0.02:
                mhgt = 300.0 + convection * 1200.0 + generator.uniform(-80.0, 80.0)
            else:
                mhgt = 150.0 + 250.0 * generator.random()
            mhgt = max(100.0, mhgt)
            wd10 = (
                scenario.wind_direction
                + generator.uniform(-scenario.direction_jitter, scenario.direction_jitter)
            ) % 360.0
            sa10 = 5.0 + 40.0 * (1.0 - convection) + generator.uniform(-3.0, 3.0)
            sa10 = max(2.0, min(85.0, sa10))
            sw10 = max(0.02, 0.06 + 0.70 * convection + generator.uniform(-0.05, 0.05))

            wind_speed_profile: list[float] = []
            wind_direction_profile: list[float] = []
            temperature_profile: list[float] = []
            sigma_direction_profile: list[float] = []
            sigma_vertical_profile: list[float] = []
            for index, altitude in enumerate(ALTITUDES):
                wind_speed_profile.append(ws10 * (altitude / 10.0) ** 0.20)
                wind_direction_profile.append((wd10 + VEERING[index]) % 360.0)
                if convection > 0.05:
                    temperature_profile.append(tt10 - 0.3 * index)
                else:
                    temperature_profile.append(tt10 + 0.8 * (index + 1))
                sigma_direction_profile.append(sa10 * (0.85 + 0.15 * index))
                sigma_vertical_profile.append(sw10 * (0.85 + 0.15 * index))

            lines.append(
                f"{day:d} 3 88 {hour:d} {ALTITUDES[0]:5.1f} "
                f"{sigma_direction_profile[0]:5.1f} {sigma_vertical_profile[0]:6.3f} "
                f"{temperature_profile[0]:6.2f} {wind_direction_profile[0]:7.2f} "
                f"{wind_speed_profile[0]:6.2f} {mhgt:7.1f} {tskc:2d}"
            )
            for index in (1, 2):
                lines.append(
                    f"{ALTITUDES[index]:5.1f} {sigma_direction_profile[index]:5.1f} "
                    f"{sigma_vertical_profile[index]:6.3f} "
                    f"{temperature_profile[index]:6.2f} "
                    f"{wind_direction_profile[index]:7.2f} "
                    f"{wind_speed_profile[index]:6.2f}"
                )

            wind_speeds.append(wind_speed_profile[0])
            wind_directions.append(wind_direction_profile[0])
            temperatures.append(temperature_profile[0])
            mixing_heights.append(mhgt)
            cloud_covers.append(float(tskc))

    qa: dict[str, Any] = {
        "synthetic": True,
        "scenario": scenario.name,
        "description": scenario.description,
        "seed": seed,
        "periods": scenario.periods,
        "levels": list(ALTITUDES),
        "ranges_at_10m": {
            "wind_speed_m_s": _range(wind_speeds),
            "wind_direction_deg": _range(wind_directions),
            "temperature_c": _range(temperatures),
            "mixing_height_m": _range(mixing_heights),
            "cloud_cover_tenths": _range(cloud_covers),
        },
        "limitations": [
            "Dados gerados para teste de software; nao sao observacoes meteorologicas.",
            "Nao usar para demonstracao de conformidade regulatoria ou validade externa.",
        ],
    }
    return "\n".join(lines) + "\n", qa
