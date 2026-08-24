"""Stage multipliers: a direct port of Calcs!C99 and C164:C170.

Block 3 (``rim/survival.py``) produces one survival factor per control option.
This module combines them into the seven multipliers that ``Bio results!D3:D20``
actually applies, one per point in the season where ryegrass is knocked back:

===== ================================================================
Cell  What it multiplies
===== ================================================================
C164  Germination-to-first-stage survival (seeding operation)
C165  ...to 10 days after the break
C166  ...to 20 days after the break
C167  Pre-emergent herbicides, applied to each germinating cohort
C168  Post-emergent herbicides
C169  Spring options
C170  Harvest weed-seed control
===== ================================================================

``Calcs!C99`` belongs with them: it is the seed removal a normal harvest
achieves when no spring or harvest option was chosen, and it folds into C170.

Two subtleties are worth stating, because both look like bugs and are not:

* **Zero and blank are different, and Excel's SUM conflates them.** ``Calcs!C165``
  tests ``SUM(C19:C22)=0``. Those cells hold crop codes, and wheat's code *is*
  zero, so the sum is 0 both when nothing is selected and when the crop is
  wheat. Reproducing that means summing numerically rather than counting
  non-blank cells.
* **Post-emergents are applied per slot, not per product.** ``Calcs!C168`` raises
  each product's survival factor to the power of how many of the three
  post-emergent slots hold it (``Calcs!P35:P39``), so naming Topik twice halves
  survival twice.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "calcs_stage_constants.json"

# 2.Strategy!P89:P93 -- the post-emergent products, in the order their
# activation cells (Calcs!C23:C27), survival rows (55+16..55+20) and use-count
# cells (Calcs!P35:P39) are laid out.
POST_EMERGENT_PRODUCTS: tuple[str, ...] = (
    "Topik", "Hussar", "Clethodim", "Glyphosate", "Paraquat",
)
POST_EMERGENT_ACTIVATION = (23, 24, 25, 26, 27)
POST_EMERGENT_SURVIVAL_ROWS = (71, 72, 73, 74, 75)

# Calcs!C165/C166 -- knock-down and double-knock survival rows.
KNOCKDOWN_ROWS = (55, 56, 57)
MOULDBOARD_ROW = 65

# Calcs!C169 -- every spring option, in the workbook's own multiplication order.
SPRING_ROWS = (78, 79, 80, 82, 83, 84, 87, 88, 81, 85, 86)

# Calcs!C170 -- every harvest option, plus C99 (normal-harvest seed removal).
HARVEST_ROWS = (89, 92, 93, 94, 95, 97, 96, 90, 91)
NORMAL_HARVEST_ROW = 99

# Calcs!C99 -- the ranges it scans for "was any spring or harvest option chosen?"
SPRING_ACTIVATION_RANGE = range(31, 39)   # C31:C38
HARVEST_ACTIVATION_RANGE = range(41, 50)  # C41:C49

# Calcs!C99 applies only to crops, not pastures.
FIRST_PASTURE_CROP_CODE = 4

MULTIPLIER_ROWS: tuple[int, ...] = (164, 165, 166, 167, 168, 169, 170)


@lru_cache(maxsize=1)
def load_constants(path: str | None = None) -> dict[str, float]:
    """Load the generated scalars, keyed by name."""
    target = Path(path) if path else DATA_PATH
    if not target.is_file():
        raise FileNotFoundError(
            f"{target} is missing. Regenerate it with:\n"
            r"    .venv\Scripts\python -m tools.extract_params"
        )
    payload = json.loads(target.read_text(encoding="utf-8"))
    return {key: float(entry["value"]) for key, entry in payload.items() if key != "_source"}


def _active(value: Any) -> bool:
    return value is not None and value != ""


def _numeric(value: Any) -> float:
    """Excel's SUM treats a blank as zero -- and so does a wheat crop code."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def post_emergent_use_counts(
    slots: Sequence[Any],
    activation: Mapping[int, Any],
) -> dict[int, int]:
    """Calcs!P35:P39 -- how many of the three post-emergent slots hold each product.

    Zero unless the product's activation cell is set, matching
    ``IF(C23<>"", ...count..., 0)``.
    """
    labels = [str(slot).strip() for slot in slots if slot is not None]
    counts: dict[int, int] = {}
    for index, product in enumerate(POST_EMERGENT_PRODUCTS):
        cell = POST_EMERGENT_ACTIVATION[index]
        counts[cell] = labels.count(product) if _active(activation.get(cell)) else 0
    return counts


def normal_harvest_factor(
    activation: Mapping[int, Any],
    crop_code: int,
    constants: Mapping[str, float] | None = None,
) -> float:
    """Calcs!C99 -- seed a normal harvest removes when nothing else was done.

    ``IF(AND(E184<4, COUNTIF(C31:C38,">=0")=0, COUNTIF(C41:C49,">=0")=0),
    1-'+Options'!$AG$134, 1)``
    """
    constants = constants if constants is not None else load_constants()
    if crop_code >= FIRST_PASTURE_CROP_CODE:
        return 1.0
    any_spring = any(_active(activation.get(row)) for row in SPRING_ACTIVATION_RANGE)
    any_harvest = any(_active(activation.get(row)) for row in HARVEST_ACTIVATION_RANGE)
    if any_spring or any_harvest:
        return 1.0
    return 1.0 - constants["normal_harvest_seed_removal"]


def _product(factors: Mapping[int, float], rows: Sequence[int]) -> float:
    result = 1.0
    for row in rows:
        result *= factors.get(row, 1.0)
    return result


def stage_multipliers(
    activation: Mapping[int, Any] | Mapping[str, Any],
    factors: Mapping[int, float],
    *,
    crop_code: int,
    post_emergent_slots: Sequence[Any] = (),
    pre_emergent_selected: bool = False,
    constants: Mapping[str, float] | None = None,
) -> dict[int, float]:
    """Compute Calcs!C164:C170 for one year.

    ``activation`` is that year's Calcs!C7:C49; ``factors`` is the output of
    ``rim.survival.survival_factors``. ``pre_emergent_selected`` mirrors the
    ``'2.Strategy'!D8<>""`` test inside Calcs!C167.
    """
    constants = constants if constants is not None else load_constants()
    cells = {int(k): v for k, v in activation.items() if str(k).isdigit()}

    c19, c20, c21, c22 = (cells.get(n) for n in (19, 20, 21, 22))
    knockdowns = _product(factors, KNOCKDOWN_ROWS)
    mouldboard = factors.get(MOULDBOARD_ROW, 1.0)

    # Calcs!C164: IF(C19<>"",1,IF(C20<>"",C68,1))
    m164 = 1.0 if _active(c19) else (factors.get(68, 1.0) if _active(c20) else 1.0)

    # Calcs!C165: C69*IF(OR(SUM(C19:C22)=0,C21<>""),C55*C56*C57*C65,1)
    seeding_sum = sum(_numeric(cells.get(n)) for n in (19, 20, 21, 22))
    m165 = factors.get(69, 1.0) * (
        knockdowns * mouldboard if (seeding_sum == 0 or _active(c21)) else 1.0
    )

    # Calcs!C166: C70*C65*IF(C22<>"",C55*C56*C57,1)
    m166 = factors.get(70, 1.0) * mouldboard * (knockdowns if _active(c22) else 1.0)

    # Calcs!C167: C58..C62*(1-AG128) + IF(AND(strategy!D8<>"",C19<>""),N167,0)
    m167 = _product(factors, (58, 59, 60, 61, 62)) * (1.0 - constants["pre_em_extra_control"])
    if pre_emergent_selected and _active(c19):
        m167 += constants["pre_em_survival_floor"]

    # Calcs!C168: each product's factor raised to the number of slots holding it.
    counts = post_emergent_use_counts(post_emergent_slots, cells)
    m168 = 1.0
    for cell, row in zip(POST_EMERGENT_ACTIVATION, POST_EMERGENT_SURVIVAL_ROWS):
        m168 *= factors.get(row, 1.0) ** counts[cell]

    m169 = _product(factors, SPRING_ROWS)

    # Calcs!C170 includes C99, which is not one of the survival rows.
    m170 = _product(factors, HARVEST_ROWS) * normal_harvest_factor(cells, crop_code, constants)

    return {164: m164, 165: m165, 166: m166, 167: m167, 168: m168, 169: m169, 170: m170}
