"""Seed production: a direct port of Bio results!D17:D20 and Calcs!C174:C177.

This closes the year. Block 4 leaves a stand of mature ryegrass and a depleted
seed bank; this block works out how much seed that stand sets, adds it back, and
hands the total to next autumn -- which is where the next year's ``D11`` comes
from (``Bio results!E11 = D20``).

**Competition is weighted by cohort.** ``Calcs!C174:C177`` re-run the plant
cascade from block 4, but each newly emerged cohort is scaled by how
competitive it actually is. A plant that came up with the crop competes fully;
one that emerged weeks later barely competes at all -- for dry or wet sowing the
weights run 1, 0.3, 0.1, 0.02. ``C177`` is the resulting *effective* ryegrass
density, and it is that, not the raw plant count, that drives seed set.

**Seed per plant falls with crowding** (``Bio results!D17``)::

    max_seed / (density_constant + C177 + crop_competitiveness * plant_density)

so a denser crop suppresses ryegrass seed production directly. Sowing at a high
seeding rate raises ``plant_density`` and lowers ryegrass seed set, which is the
mechanism behind the "high seeding rate" strategy option.

Two phytotoxicity discounts then apply: one if any herbicide was used
(``Calcs!P48``), one if any spring operation involved a spray (``Calcs!P49``).

Finally (``D18:D20``) the new seed is added to what survived in the seed bank,
harvest weed-seed control is applied to the newly set seed only, and what is
left loses a fixed fraction over summer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "seed_set.json"

# Calcs!C15 -- high seeding rate.
HIGH_SEEDING_RATE_CELL = 15

# Calcs!C19/C20 (dry or wet), C21 (delayed), C22 (+delayed) choose the cohort
# competitiveness column in +Options!AG142:AI145.
SOWING_DRY_OR_WET_CELLS = (19, 20)
SOWING_DELAYED_CELL = 21

# Calcs!P48 -- pre-emergent products active, plus post-emergent slot uses.
PRE_EMERGENT_CELLS = range(10, 15)
# Calcs!P49 -- spring operations that involve a spray.
SPRING_SPRAY_CELLS = (40, 35, 36, 30, 31, 32, 33)

FIRST_PASTURE_CROP_CODE = 4


@dataclass(frozen=True)
class YearClose:
    """Bio results rows 17-20."""

    seed_per_plant: float      # D17
    seed_produced: float       # D18
    before_harvest: float      # D19
    next_autumn: float         # D20


@lru_cache(maxsize=1)
def load_parameters(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else DATA_PATH
    if not target.is_file():
        raise FileNotFoundError(
            f"{target} is missing. Regenerate it with:\n"
            r"    .venv\Scripts\python -m tools.extract_params"
        )
    return json.loads(target.read_text(encoding="utf-8"))


def _active(value: Any) -> bool:
    return value is not None and value != ""


def cohort_competitiveness(
    activation: Mapping[int, Any],
    parameters: dict[str, Any] | None = None,
) -> tuple[float, ...]:
    """+Options!AG142:AI145 -- how much each cohort competes, by time of sowing.

    Later sowing gives the later cohorts more standing: they emerge closer to
    the crop rather than long after it.
    """
    parameters = parameters if parameters is not None else load_parameters()
    weights = parameters["cohort_competitiveness"]
    if any(_active(activation.get(cell)) for cell in SOWING_DRY_OR_WET_CELLS):
        return tuple(weights["dry_or_wet"])
    if _active(activation.get(SOWING_DELAYED_CELL)):
        return tuple(weights["delayed"])
    return tuple(weights["plus_delayed"])


def effective_density(
    seed_bank: Sequence[float],
    plants_first: float,
    germination: Sequence[float],
    multipliers: Mapping[int, float],
    weights: Sequence[float],
) -> float:
    """Calcs!C174:C177 -- the competition-weighted ryegrass density.

    Mirrors Bio results!D4:D7 exactly, except that each newly emerged cohort is
    scaled by its competitiveness weight.
    """
    c167 = multipliers[167]
    value = plants_first * multipliers[164] + seed_bank[1] * germination[1] * c167 * weights[0]
    value = value * multipliers[165] + seed_bank[2] * germination[2] * c167 * weights[1]
    value = value * multipliers[166] + seed_bank[3] * germination[3] * c167 * weights[2]
    value = value * multipliers[168] + seed_bank[4] * germination[4] * weights[3]
    return value


def crop_competition(
    crop_code: int,
    high_seeding_rate: bool,
    parameters: dict[str, Any] | None = None,
) -> float:
    """The crop's share of the competition term in Bio results!D17.

    ``competitiveness * plant_density`` for a crop; a flat figure
    (``+Options!AS182``) for any pasture.
    """
    parameters = parameters if parameters is not None else load_parameters()
    if crop_code >= FIRST_PASTURE_CROP_CODE:
        return float(parameters["pasture_competition"])

    key = str(int(crop_code))
    density = parameters[
        "plant_density_high" if high_seeding_rate else "plant_density_standard"
    ][key]
    return float(parameters["crop_competitiveness"][key]) * float(density)


def herbicide_applications(activation: Mapping[int, Any], use_counts: Mapping[int, int]) -> int:
    """Calcs!P48 -- pre-emergent products active, plus post-emergent slot uses."""
    pre = sum(1 for cell in PRE_EMERGENT_CELLS if _active(activation.get(cell)))
    return pre + sum(use_counts.values())


def spring_spray_operations(activation: Mapping[int, Any]) -> int:
    """Calcs!P49 -- spring operations that involve a spray."""
    return sum(1 for cell in SPRING_SPRAY_CELLS if _active(activation.get(cell)))


def close_year(
    *,
    activation: Mapping[int, Any],
    crop_code: int,
    plants_spray_time: float,       # D7
    plants_mature: float,           # D8
    seed_bank_spring: float,        # D16
    weighted_density: float,        # C177
    harvest_multiplier: float,      # C170
    herbicide_count: int,
    spring_spray_count: int,
    summer_seed_loss: float,
    parameters: dict[str, Any] | None = None,
) -> YearClose:
    """Bio results!D17:D20 -- seed set, and the seed bank handed to next autumn."""
    parameters = parameters if parameters is not None else load_parameters()

    if plants_spray_time == 0:
        # Excel would raise #DIV/0!. With no plants at spraying time there is no
        # stand to set seed, so the year closes on the seed bank alone.
        seed_per_plant = 0.0
    else:
        competition = crop_competition(
            crop_code, _active(activation.get(HIGH_SEEDING_RATE_CELL)), parameters
        )
        denominator = (
            float(parameters["density_constant"]) + weighted_density + competition
        )
        seed_per_plant = (
            float(parameters["max_seed_per_m2"]) / denominator
            * weighted_density / plants_spray_time
        )
        if herbicide_count > 0:
            seed_per_plant *= 1.0 - float(
                parameters["phytotoxicity_herbicides"]["value"]
            )
        if spring_spray_count > 0:
            seed_per_plant *= 1.0 - float(
                parameters["phytotoxicity_spring_sprays"]["value"]
            )

    seed_produced = seed_per_plant * plants_mature                       # D18
    before_harvest = seed_produced + seed_bank_spring                    # D19
    # Harvest weed-seed control acts on the newly set seed only: what is already
    # on the ground has been shed and never enters the header.
    next_autumn = (
        seed_bank_spring + seed_produced * harvest_multiplier
    ) * (1.0 - summer_seed_loss)                                         # D20

    return YearClose(
        seed_per_plant=seed_per_plant,
        seed_produced=seed_produced,
        before_harvest=before_harvest,
        next_autumn=next_autumn,
    )
