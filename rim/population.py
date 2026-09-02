"""Seasonal population model: a direct port of Bio results!D3:D8 and D11:D16.

This is the core of RIM and the block the original Python engine had no
equivalent of. Ryegrass does not germinate all at once; it comes up in five
cohorts through autumn and winter, and each control option catches whichever
cohorts have emerged by the time it is applied. Two interleaved cascades run
down the season:

**The seed bank** (``Bio results`` rows 11-16) starts at the summer carryover and
is drawn down cohort by cohort::

    D11  end of summer                seed bank carried in
    D12  = D11 * (1 - g1)             what did not germinate in cohort 1
    D13  = D12 * (1 - g2) * C159      ...cohort 2, then ploughing burial
    D14  = D13 * (1 - g3) * C160
    D15  = D14 * (1 - g4)
    D16  = D15 * (1 - g5) * (1 - loss)

**The plants** (rows 3-8) are what germinated, carried forward through each
control and topped up by the next cohort::

    D3  = D11 * g1                    cohort 1 emerges
    D4  = D3 * C164 + D12 * g2 * C167     survivors + cohort 2, both sprayed
    D5  = D4 * C165 + D13 * g3 * C167
    D6  = D5 * C166 + D14 * g4 * C167
    D7  = D6 * C168 + D15 * g5            post-emergent herbicides
    D8  = D7 * C169 * C314                spring options, then grazing

The ``C1xx`` multipliers come from ``rim/stage_multipliers.py``. Note the
asymmetry in rows 4-6: established plants take the stage multiplier while each
newly emerged cohort takes the pre-emergent multiplier ``C167`` instead, because
a pre-emergent is still active in the soil when they come up.

Germination fractions depend on whether the paddock is sown, whether it was
tickled or ploughed, and whether the establishment system is full-cut
(``Calcs!C151:C155``). Ploughing additionally buries seed between cohorts
(``C159``/``C160``), and grazing removes ryegrass before seed set (``C314``).

This module stops at row 16. Seed production (rows 17-20), which closes the
year and hands the seed bank to the next one, is block 5.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
GERMINATION_PATH = DATA_DIR / "germination.json"
TABLE8_PATH = DATA_DIR / "calcs_table8.json"

# Calcs!C16 (tickle), C17 (plough), C18 (full-cut), C22 (+delayed sowing).
TICKLE_CELL = 16
PLOUGH_CELL = 17
FULL_CUT_CELL = 18
PLUS_DELAYED_CELL = 22

# Calcs!C28 (standard grazing), C29 (high grazing).
GRAZING_STANDARD_CELL = 28
GRAZING_HIGH_CELL = 29
# Calcs!C322/C324 -- fodder and manuring options that cancel grazing.
FODDER_CELLS = (34, 35, 36)

COHORTS = 5


@dataclass(frozen=True)
class SeasonState:
    """One year of Bio results rows 3-8 and 11-16."""

    plants: tuple[float, ...]      # D3..D8
    seed_bank: tuple[float, ...]   # D11..D16

    def as_rows(self) -> dict[int, float]:
        rows = {3 + i: value for i, value in enumerate(self.plants)}
        rows.update({11 + i: value for i, value in enumerate(self.seed_bank)})
        return rows


@lru_cache(maxsize=1)
def load_germination(path: str | None = None) -> dict[str, Any]:
    return _load(Path(path) if path else GERMINATION_PATH)


@lru_cache(maxsize=1)
def load_table8(path: str | None = None) -> dict[str, Any]:
    return _load(Path(path) if path else TABLE8_PATH)


def _load(target: Path) -> dict[str, Any]:
    if not target.is_file():
        raise FileNotFoundError(
            f"{target} is missing. Regenerate it with:\n"
            r"    .venv\Scripts\python -m tools.extract_params"
        )
    return json.loads(target.read_text(encoding="utf-8"))


def _active(value: Any) -> bool:
    return value is not None and value != ""


def starting_seed_bank(germination: dict[str, Any] | None = None) -> float:
    """Bio results!D11 for year 1 -- '+Options'!AG96 * AG124."""
    germination = germination if germination is not None else load_germination()
    return float(germination["starting_seed_bank"]["value"])


def germination_fractions(
    activation: Mapping[int, Any],
    *,
    sown: bool,
    germination: dict[str, Any] | None = None,
) -> tuple[float, ...]:
    """Calcs!C151:C155 -- the fraction of the remaining seed bank each cohort emits.

    ``IF(D66="no", IF(OR(C16,C17), AI105, AG105),
        IF(OR(C16,C17), IF(C18, AJ115, AI115), IF(C18, AH115, AG115)))``
    """
    germination = germination if germination is not None else load_germination()
    disturbed = _active(activation.get(TICKLE_CELL)) or _active(activation.get(PLOUGH_CELL))

    if not sown:
        column = "tickle" if disturbed else "no_tickle"
        return tuple(germination["regenerating"][column])

    full_cut = _active(activation.get(FULL_CUT_CELL))
    column = (
        ("tickle_full_cut" if full_cut else "tickle_no_till")
        if disturbed
        else ("no_tickle_full_cut" if full_cut else "no_tickle_no_till")
    )
    return tuple(germination["sown"][column])


def plough_burial(
    activation: Mapping[int, Any],
    germination: dict[str, Any] | None = None,
) -> tuple[float, float]:
    """Calcs!C159 and C160 -- seed buried by ploughing, applied to one cohort.

    Which cohort depends on sowing time: without +delayed sowing the burial hits
    the transition into cohort 3 (C159), with it the transition into cohort 4
    (C160). Only one of the two is ever below 1.
    """
    germination = germination if germination is not None else load_germination()
    if not _active(activation.get(PLOUGH_CELL)):
        return 1.0, 1.0

    survival = 1.0 - float(germination["plough_seed_burial"]["value"])
    plus_delayed = _active(activation.get(PLUS_DELAYED_CELL))
    return (1.0, survival) if plus_delayed else (survival, 1.0)


def grazing_flags(activation: Mapping[int, Any]) -> tuple[int, int, int, int]:
    """Calcs!C310, C312, C322, C324 -- who is grazing this paddock, and how.

    Returned as the workbook's four 0/1 flags so both the ryegrass effect and
    the stocking rate read the same decision:

    * ``C310`` standard grazing, ``C312`` high intensity — the plain cases;
    * ``C322``/``C324`` the same two but where a fodder or manuring option was
      also taken, which the workbook prices differently because the paddock is
      cut as well as grazed.
    """
    fodder = any(_active(activation.get(cell)) for cell in FODDER_CELLS)
    standard = _active(activation.get(GRAZING_STANDARD_CELL))
    high = _active(activation.get(GRAZING_HIGH_CELL))

    c322 = 1 if (fodder and standard) else 0
    c324 = 1 if (fodder and high) else 0
    c310 = 0 if (high or c322 > 0 or c324 > 1) else (1 if standard else 0)
    c312 = 0 if (c322 > 0 or c324 > 0) else (1 if high else 0)
    return c310, c312, c322, c324


def grazing_survival(
    activation: Mapping[int, Any],
    rotation_key: int,
    table8: dict[str, Any] | None = None,
) -> float:
    """Calcs!C314 = 1 - C311 - C313 -- ryegrass left after grazing.

    Standard and high grazing draw different control fractions from Table 8, and
    both are cancelled when a fodder or manuring option is taken, since the
    paddock is cut rather than grazed (``Calcs!C322``/``C324``).
    """
    table8 = table8 if table8 is not None else load_table8()
    entry = table8["by_key"].get(str(int(rotation_key)))
    if entry is None:
        return 1.0

    c310, c312, _c322, _c324 = grazing_flags(activation)

    c311 = float(entry["ryegrass_control_standard_grazing"]) * c310
    c313 = float(entry["ryegrass_control_high_grazing"]) * c312
    return 1.0 - c311 - c313


def run_season(
    seed_bank_start: float,
    germination_by_cohort: Sequence[float],
    multipliers: Mapping[int, float],
    *,
    burial: tuple[float, float] = (1.0, 1.0),
    grazing: float = 1.0,
    seed_loss_pre_harvest: float,
) -> SeasonState:
    """Bio results!D3:D8 and D11:D16 for one year."""
    g = list(germination_by_cohort)
    if len(g) != COHORTS:
        raise ValueError(f"expected {COHORTS} germination fractions, got {len(g)}")

    c159, c160 = burial
    c164, c165, c166 = multipliers[164], multipliers[165], multipliers[166]
    c167, c168, c169 = multipliers[167], multipliers[168], multipliers[169]

    # Seed bank drawn down cohort by cohort (rows 11-16).
    d11 = float(seed_bank_start)
    d12 = d11 * (1.0 - g[0])
    d13 = d12 * (1.0 - g[1]) * c159
    d14 = d13 * (1.0 - g[2]) * c160
    d15 = d14 * (1.0 - g[3])
    d16 = d15 * (1.0 - g[4]) * (1.0 - seed_loss_pre_harvest)

    # Plants: survivors carried through each control, topped up by each new
    # cohort. Newly emerged cohorts take C167 (the pre-emergent still in the
    # soil) rather than the stage multiplier the established plants take.
    d3 = d11 * g[0]
    d4 = d3 * c164 + d12 * g[1] * c167
    d5 = d4 * c165 + d13 * g[2] * c167
    d6 = d5 * c166 + d14 * g[3] * c167
    d7 = d6 * c168 + d15 * g[4]
    d8 = d7 * c169 * grazing

    return SeasonState(
        plants=(d3, d4, d5, d6, d7, d8),
        seed_bank=(d11, d12, d13, d14, d15, d16),
    )
