"""Option activation: a direct port of Calcs!C7:C49.

Turns one year of the strategy grid into the activation cells the rest of the
model reads. Almost every cell has the same shape, using ``Calcs!C10`` as the
reference::

    IF(AND('2.Strategy'!D8='2.Strategy'!$P$81,      <- the chosen label matches
           '1.Profile'!$C$20<>"",                    <- the profile stocks it
           '2.Strategy'!D$66="yes"),                 <- the gate is open
       E$184, "")                                    <- the crop code, else blank

The value written is the **crop code**, which is why a single cell can say both
*whether* an option applies and *which column* of the control table to read
(see ``rim/survival.py``). Blank means not selected.

Two gates sit on ``2.Strategy`` rows 65 and 66:

``D66`` -- "is the paddock sown this year?" True for any crop, and for the first
year of a clover or Cadiz phase, which has to be re-sown. It suppresses seeding
and herbicide options on a regenerating pasture.

``D65`` -- "does a knock-down get its own effect?" With dry or wet sowing there
is no gap between spraying and seeding, so the knockdown would kill the cohort
the seeding operation already accounts for; Excel suppresses it rather than
double-count. Only delayed sowing, or an unsown pasture, opens it.

Both gates need the previous two years' crop codes, so this block depends on
``rim/rotation.py``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "strategy_vocabulary.json"

# 2.Strategy rows 65/66 -- the two gates.
GATE_SOWN = "D66"
GATE_KNOCKDOWN = "D65"

# Crop codes: anything below 4 is a crop; 5 is clover and 6 is Cadiz, the two
# pastures that must be re-sown at the start of a phase (Calcs!P46/P47).
FIRST_PASTURE_CROP_CODE = 4
CLOVER_CROP_CODE = 5
CADIZ_CROP_CODE = 6

# 2.Strategy!D78/D79 -- the sowing times that leave no gap before seeding.
NO_GAP_SOWING_CELLS = ("D78", "D79")

BLANK = None


@dataclass(frozen=True)
class Spec:
    """How one activation cell is decided."""

    field: str                    # the strategy dict key (see tools/cell_map.py)
    label_cell: str | None        # the list cell its value must equal
    gate: str | None = None       # "D65", "D66" or None
    profile_cell: str | None = None  # 1.Profile slot that must be stocked


# Calcs row -> how it activates. Rows 32 and 45 are absent because the workbook
# has no formula there: they are the "empty slot for adding a..." placeholders,
# which is why survival rows 80 and 93 can never be exercised.
SPEC: dict[int, Spec] = {
    # Knock-down / double-knock, gated on D65.
    7: Spec("knock_down", "P75", GATE_KNOCKDOWN),
    8: Spec("knock_down", "P76", GATE_KNOCKDOWN),
    9: Spec("knock_down", "P77", GATE_KNOCKDOWN),
    # Pre-emergent herbicides, gated on D66 and on the profile stocking them.
    # Note C11 checks C22 (Sakura's slot) rather than C21 (Propyzamide's) --
    # see PROFILE_SLOT_QUIRK below.
    10: Spec("pre_emergent", "P81", GATE_SOWN, "C20"),
    11: Spec("pre_emergent", "P82", GATE_SOWN, "C22"),
    12: Spec("pre_emergent", "P83", GATE_SOWN, "C22"),
    13: Spec("pre_emergent", "P84", GATE_SOWN, "C23"),
    14: Spec("pre_emergent", "P85", GATE_SOWN, "C24"),
    # High seeding rate.
    15: Spec("crop_seeding_rate", "D84"),
    # Soil preparation, gated on D65.
    16: Spec("soil_preparation", "D72", GATE_KNOCKDOWN),
    17: Spec("soil_preparation", "D73", GATE_KNOCKDOWN),
    # Establishment system (full-cut), gated on D66.
    18: Spec("establishment_system", "D76", GATE_SOWN),
    # Time of sowing, gated on D66. Row 20 (wet) is the default and is handled
    # separately -- see activation_cells.
    19: Spec("time_of_sowing", "D78", GATE_SOWN),
    21: Spec("time_of_sowing", "D80", GATE_SOWN),
    22: Spec("time_of_sowing", "D81", GATE_SOWN),
    # Post-emergent herbicides: any of the three slots, plus a profile check.
    23: Spec("post_emergent", "P89", None, "C26"),
    24: Spec("post_emergent", "P90", None, "C27"),
    25: Spec("post_emergent", "P91", None, "C28"),
    26: Spec("post_emergent", "P92", None, "C29"),
    27: Spec("post_emergent", "P93", None, "C30"),
    # Grazing intensity.
    28: Spec("grazing_intensity", "D87"),
    29: Spec("grazing_intensity", "D88"),
    # Spring options.
    30: Spec("spring_option", "D96"),
    31: Spec("spring_option", "D92"),
    33: Spec("spring_option", "D93"),
    34: Spec("spring_option", "D91"),
    35: Spec("spring_option", "D95"),
    36: Spec("spring_option", "D94"),
    # Spring - others.
    37: Spec("spring_others", "D104"),
    38: Spec("spring_others", "D105"),
    # Spring - swathe.
    39: Spec("spring_swathe", "D100"),
    40: Spec("spring_swathe", "D101"),
    # Harvest options - crops.
    41: Spec("harvest_crops", "D108"),
    42: Spec("harvest_crops", "D109"),
    43: Spec("harvest_crops", "D110"),
    44: Spec("harvest_crops", "D111"),
    46: Spec("harvest_crops", "D112"),
    # Harvest options - others.
    47: Spec("harvest_others", "D116"),
    48: Spec("harvest_others", "D117"),
    49: Spec("harvest_others", "D118"),
}

# Calcs!C20 -- "seed wet" is the default rather than a label match:
#   IF(AND(C19="",C21="",C22="",D66="yes"), E$184, "")
DEFAULT_SOWING_ROW = 20
OTHER_SOWING_ROWS = (19, 21, 22)

# Calcs!C23:C27 read all three post-emergent slots.
POST_EMERGENT_ROWS = (23, 24, 25, 26, 27)
POST_EMERGENT_FIELDS = ("post_emergent_1", "post_emergent_2", "post_emergent_3")

# Faithfully reproduced workbook quirk: Calcs!C11 activates Propyzamide but
# tests 1.Profile!C22, which holds Sakura. Invisible while both slots are
# stocked, which they are by default.
PROFILE_SLOT_QUIRK = (
    "Calcs!C11 (Propyzamide) checks 1.Profile!C22 (Sakura) rather than C21."
)

ROWS: tuple[int, ...] = tuple(sorted(set(SPEC) | {DEFAULT_SOWING_ROW}))


@lru_cache(maxsize=1)
def load_vocabulary(path: str | None = None) -> dict[str, Any]:
    """Load the generated dropdown labels and profile product slots."""
    target = Path(path) if path else DATA_PATH
    if not target.is_file():
        raise FileNotFoundError(
            f"{target} is missing. Regenerate it with:\n"
            r"    .venv\Scripts\python -m tools.extract_params"
        )
    return json.loads(target.read_text(encoding="utf-8"))


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def is_sown(crop_code: int, prev_crop_code: int, prev2_crop_code: int) -> bool:
    """2.Strategy!D66 -- is the paddock sown this year?

    ``IF(OR(E184<4, (P46+P47)>0), "yes", "no")`` where P46 marks the first year
    of a Cadiz phase and P47 the first year of a clover phase.
    """
    if crop_code < FIRST_PASTURE_CROP_CODE:
        return True
    # Calcs!P46 -- first year of Cadiz.
    if crop_code == CADIZ_CROP_CODE and prev_crop_code != CADIZ_CROP_CODE:
        return True
    # Calcs!P47 -- first year of clover.
    if crop_code == CLOVER_CROP_CODE and CLOVER_CROP_CODE not in (
        prev_crop_code,
        prev2_crop_code,
    ):
        return True
    return False


def knockdown_counts(time_of_sowing: Any, sown: bool, vocabulary: dict[str, Any]) -> bool:
    """2.Strategy!D65 -- does a knock-down get its own control effect?

    ``IF(D66="no","yes", IF(OR(D5="",D5=$D$78,D5=$D$79),"no","yes"))``
    """
    if not sown:
        return True
    categories = vocabulary["categories"]
    chosen = _text(time_of_sowing)
    if not chosen:
        return False
    return chosen not in {categories.get(cell) for cell in NO_GAP_SOWING_CELLS}


def activation_cells(
    strategy: Mapping[str, Any],
    *,
    crop_code: int,
    prev_crop_code: int,
    prev2_crop_code: int,
    vocabulary: dict[str, Any] | None = None,
    profile_products: Mapping[str, Any] | None = None,
) -> dict[int, float | None]:
    """Compute Calcs!C7:C49 for one year.

    ``strategy`` is a year of the grid keyed by the field names in
    ``tools/cell_map.py``. ``crop_code`` and the two previous years' codes come
    from ``rim.rotation``. ``profile_products`` overrides which
    ``1.Profile`` slots are stocked; by default the workbook's own are used.
    """
    vocabulary = vocabulary if vocabulary is not None else load_vocabulary()
    categories = vocabulary["categories"]
    products = vocabulary["products"]
    stocked = (
        profile_products if profile_products is not None else vocabulary["profile_products"]
    )

    sown = is_sown(crop_code, prev_crop_code, prev2_crop_code)
    knockdown_open = knockdown_counts(strategy.get("time_of_sowing"), sown, vocabulary)
    gates = {GATE_SOWN: sown, GATE_KNOCKDOWN: knockdown_open}

    def label_for(cell: str) -> str:
        return _text(categories.get(cell) or products.get(cell))

    cells: dict[int, float | None] = {}

    for row, spec in SPEC.items():
        if spec.gate is not None and not gates[spec.gate]:
            cells[row] = BLANK
            continue
        if spec.profile_cell is not None and not _text(stocked.get(spec.profile_cell)):
            cells[row] = BLANK
            continue

        wanted = label_for(spec.label_cell) if spec.label_cell else ""
        if not wanted:
            cells[row] = BLANK
            continue

        if row in POST_EMERGENT_ROWS:
            chosen = [_text(strategy.get(field)) for field in POST_EMERGENT_FIELDS]
            matched = wanted in chosen
        else:
            matched = _text(strategy.get(spec.field)) == wanted

        cells[row] = float(crop_code) if matched else BLANK

    # Calcs!C20 -- wet sowing is whatever the other three are not.
    cells[DEFAULT_SOWING_ROW] = (
        float(crop_code)
        if sown and all(cells[row] is BLANK for row in OTHER_SOWING_ROWS)
        else BLANK
    )

    return cells
