"""Yield: a direct port of Bio results!D23:D54.

The bridge between the biology and the money. A crop's weed-free potential is
adjusted by a chain of management effects, then by the ryegrass standing in it,
and what is left is either harvested for grain or cut for hay.

The centre of it is ``Bio results!D38:D41``, which the RIM user guide names as
one of only two equations in the workbook that are not simple arithmetic::

    (1 + b/a) * density / (b + density + competitiveness * ryegrass) * max_loss
        + (1 - max_loss)

That returns the *proportion of weed-free yield retained*. A dense crop pushes
the ratio toward 1; ryegrass in the denominator pushes it down; and ``max_loss``
bounds how much can ever be lost — 60% in wheat, 45% in barley. ``ryegrass`` is
the early-spring stand, ``Bio results!D7``, which ``rim/population.py`` produces.

Two workbook defects are reproduced rather than silently fixed. Both are in
``D29``; see :data:`WORKBOOK_DEFECTS` and ``INCONSISTENCIES.md``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "economics.json"

# Crop codes that grow grain. Pastures (4-6) carry no yield of their own here.
GRAIN_CROP_CODES = (0, 1, 2, 3)

# Activation cells (Calcs!C7:C49) the yield block reads.
CELL_MOULDBOARD = 17          # D27 — benefit for mouldboarding, permanent
CELL_SOWN_DRY = 19            # D28 — early sowing benefit
CELL_SOWN_DELAYED = 21        # D24 — late sowing penalty
CELL_SOWN_PLUS_DELAYED = 22   # D24
CELL_TOPPING = 30             # D26
CELL_SWATHE_ROWS = (39, 40)   # D25 — penalty when neither is set
CELL_SPRING_SACRIFICE = range(31, 37)   # D42:D45 — any of these zeroes the grain
CELL_HAY_SILAGE = (35, 36)    # D46:D49
CELL_BALING = (45, 46)        # D51:D54

# Previous year's spring options that earn a yield benefit this year (D29).
PREV_GREEN_MANURE = 34
PREV_BROWN_MANURE = 31
PREV_MOWING = 33

WORKBOOK_DEFECTS = (
    "Bio results!E29 term 1 reads '+Options'!#REF! for crop code 3 (legume), so a "
    "legume following green manuring returns an Excel error. Reproduced here as 0.0, "
    "matching the formula's own else-branch. Harmless in practice only because no "
    "captured scenario grows a legume after green manuring.",
    "Bio results!E29 term 1 reads '+Options'!$AJ68 for crop code 0 (wheat) where AG68 "
    "is clearly meant. Harmless: row 68 holds 0.1 in all four crop columns, so the "
    "wrong column returns the right number.",
)


@dataclass(frozen=True)
class YieldResult:
    """Bio results rows 23-54 for one year."""

    adjustment: float          # the net (1 - penalties + benefits) multiplier
    weed_free_yield: float     # D30:D33 for the year's crop
    plant_density: float       # D34:D37
    retained_fraction: float   # D38:D41, capped at 1 by D42:D45
    grain_yield: float         # D42:D45
    fodder_yield: float        # D46:D50 — hay or silage
    baled_yield: float         # D51:D54

    @property
    def yield_lost(self) -> float:
        """Weed-free potential minus what was actually harvested."""
        return max(0.0, self.weed_free_yield - self.grain_yield)


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


def _per_crop(parameters: dict[str, Any], name: str, crop_code: int) -> float:
    """A +Options AG/AH/AI/AJ row, indexed by crop code. Pastures read 0."""
    if crop_code not in GRAIN_CROP_CODES:
        return 0.0
    return float(parameters["yield_parameters"][name][str(crop_code)])


def management_adjustment(
    activation: Mapping[int, Any],
    *,
    crop_code: int,
    phase_code: int,
    herbicide_applications: int,
    mouldboard_ever: bool = False,
    previous_activation: Mapping[int, Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> float:
    """Bio results!D23:D29 folded into ``1 - penalties + benefits``.

    The workbook applies it as ``(1 - D23 - D24 - D25 - D26 + D27 + D28 + D29)``.

    ``mouldboard_ever`` is whether the paddock has been ploughed in *any* year up
    to and including this one. The workbook expands the COUNTIF range year on
    year — ``Calcs!$C$17:D17``, ``$C$17:E17`` — so the benefit is permanent once
    earned, which is what the user guide means by a "permanent yield benefit".
    """
    parameters = parameters if parameters is not None else load_parameters()
    previous_activation = previous_activation or {}

    # D23 — phytotoxicity, one dose per herbicide application.
    phytotoxicity = (
        float(parameters["yield_parameters"]["phytotoxicity_per_spray"]["3"])
        * herbicide_applications
    )

    # D24 — late sowing. Delayed and +delayed carry different penalties.
    late = 0.0
    if _active(activation.get(CELL_SOWN_PLUS_DELAYED)):
        late += _per_crop(parameters, "penalty_sowing_plus_delayed", crop_code)
    if _active(activation.get(CELL_SOWN_DELAYED)):
        late += _per_crop(parameters, "penalty_sowing_delayed", crop_code)

    # D25 — a penalty for *not* swathing, so it applies when neither option is set.
    not_swathed = (
        0.0 if any(_active(activation.get(cell)) for cell in CELL_SWATHE_ROWS)
        else _per_crop(parameters, "penalty_not_swathing", crop_code)
    )

    # D26 — crop topping. Keyed on the phase code, not the crop code.
    topping = (
        _per_crop(parameters, "penalty_crop_topping", phase_code)
        if _active(activation.get(CELL_TOPPING)) else 0.0
    )

    # D27 — mouldboard ploughing. Permanent: any year up to and including this.
    ploughed = mouldboard_ever or _active(activation.get(CELL_MOULDBOARD))
    mouldboard = float(parameters["mouldboard_yield_benefit"]) if ploughed else 0.0

    # D28 — early (dry) sowing.
    early = (
        _per_crop(parameters, "benefit_early_sowing", crop_code)
        if _active(activation.get(CELL_SOWN_DRY)) else 0.0
    )

    # D29 — benefit from what was done to the paddock *last* spring. Zero in
    # year 1, where the workbook hard-codes 0 because there is no previous year.
    previous = 0.0
    for cell, name in (
        (PREV_GREEN_MANURE, "benefit_after_green_manure"),
        (PREV_BROWN_MANURE, "benefit_after_brown_manure"),
        (PREV_MOWING, "benefit_after_mowing"),
    ):
        if _active(previous_activation.get(cell)):
            previous += _per_crop(parameters, name, crop_code)

    return 1.0 - phytotoxicity - late - not_swathed - topping + mouldboard + early + previous


def retained_fraction(
    crop_code: int,
    plant_density: float,
    ryegrass_early_spring: float,
    parameters: dict[str, Any] | None = None,
) -> float:
    """Bio results!D38:D41 -- the share of weed-free yield the crop keeps.

    One of the two equations the user guide calls out as more than arithmetic.
    """
    parameters = parameters if parameters is not None else load_parameters()
    if crop_code not in GRAIN_CROP_CODES:
        return 0.0

    a = _per_crop(parameters, "competition_a", crop_code)
    b = _per_crop(parameters, "competition_b", crop_code)
    max_loss = _per_crop(parameters, "max_yield_loss", crop_code)
    competitiveness = float(parameters["ryegrass_competitiveness"][str(crop_code)])

    denominator = b + plant_density + competitiveness * ryegrass_early_spring
    if denominator == 0:
        return 1.0
    return (1.0 + b / a) * plant_density / denominator * max_loss + (1.0 - max_loss)


def compute_yield(
    activation: Mapping[int, Any],
    *,
    crop_code: int,
    phase_code: int,
    weed_free_from_table8: float,
    ryegrass_early_spring: float,
    herbicide_applications: int,
    mouldboard_ever: bool = False,
    previous_crop_code: int | None = None,
    two_years_ago_crop_code: int | None = None,
    previous_activation: Mapping[int, Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> YieldResult:
    """Bio results!D23:D54 for one year.

    ``weed_free_from_table8`` is column 3 of Table 8 at the year's rotation key,
    which ``rim/rotation.py`` and ``data/calcs_table8.json`` already provide.
    """
    parameters = parameters if parameters is not None else load_parameters()

    adjustment = management_adjustment(
        activation,
        crop_code=crop_code,
        phase_code=phase_code,
        herbicide_applications=herbicide_applications,
        mouldboard_ever=mouldboard_ever,
        previous_activation=previous_activation,
        parameters=parameters,
    )

    # D30:D33 — legume is the exception: it reads +Options AJ56 directly rather
    # than Table 8, and loses AJ77 when a legume was also grown two years ago.
    if crop_code == 3:
        base = float(parameters["yield_parameters"]["weed_free_yield"]["3"])
        if two_years_ago_crop_code == 3:
            base *= 1.0 - float(
                parameters["yield_parameters"]["legume_after_legume_penalty"]["3"]
            )
        weed_free = base * adjustment
    elif crop_code in GRAIN_CROP_CODES:
        weed_free = float(weed_free_from_table8) * adjustment
    else:
        weed_free = 0.0

    # D34:D37 — a high seeding rate raises plant density, which is what makes
    # the crop compete (see retained_fraction).
    high_rate = _active(activation.get(15))
    density = _per_crop(
        parameters, "plant_density_high" if high_rate else "plant_density_standard",
        crop_code,
    )

    retained = retained_fraction(crop_code, density, ryegrass_early_spring, parameters)

    # D42:D45 — no grain at all if the crop was sacrificed in spring.
    sacrificed = any(_active(activation.get(cell)) for cell in CELL_SPRING_SACRIFICE)
    grain = 0.0 if sacrificed else weed_free * min(retained, 1.0)

    # D46:D49 — hay or silage, cut from the weed-free potential.
    harvest_index = _per_crop(parameters, "harvest_index", crop_code)
    conversion = _per_crop(parameters, "fodder_conversion", crop_code)
    cut_for_fodder = any(_active(activation.get(cell)) for cell in CELL_HAY_SILAGE)
    fodder = (
        weed_free / harvest_index * conversion
        if cut_for_fodder and harvest_index else 0.0
    )

    # D51:D54 — straw baled behind the header, from the grain actually harvested.
    baling = any(_active(activation.get(cell)) for cell in CELL_BALING)
    baled = (
        grain * (1.0 - harvest_index) / harvest_index * conversion
        if baling and harvest_index else 0.0
    )

    return YieldResult(
        adjustment=adjustment,
        weed_free_yield=weed_free,
        plant_density=density,
        retained_fraction=retained,
        grain_yield=grain,
        fodder_yield=fodder,
        baled_yield=baled,
    )
