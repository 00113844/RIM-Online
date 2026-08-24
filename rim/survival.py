"""Stage survival factors: a direct port of Calcs rows 55-97.

Each control option the strategy selects gets one row here holding the fraction
of ryegrass that *survives* it. ``Bio results!D3:D20`` then multiplies these
through the season in stage order, which is why they are survival factors
rather than control fractions -- the workbook stores ``1 - control``.

The generic formula, using ``Calcs!C75`` as the reference::

    IF(C27<>"", 1 - HLOOKUP(C27, $N$54:$T$97, $A75+1), 1)

Three things are going on:

* **The activation cell holds the crop code.** ``Calcs!C7:C49`` write the year's
  crop code (0..6) into a cell when the option is selected and leave it blank
  otherwise. So a single cell says both *whether* the option applies and *which
  column* of the lookup table to read.
* **The offset is the table row.** Column ``A`` holds the ``HLOOKUP`` row offset,
  which is always ``row - 54``. Option ``r``'s control fraction therefore lives
  in table row ``r`` -- the block and the table are aligned.
* **Blank means no effect.** Excel coerces an empty lookup result to 0, giving a
  survival factor of 1. Options that do not apply to a crop (Topik on canola,
  say) are blank rather than zero, and behave identically.

Rows 68-70 (seeding timing) are the exception: they are not crop-indexed. They
read columns ``P`` and ``Q`` instead, which row 67 labels "No-till" and
"Full cut", selected by whether ``Calcs!C18`` (full-cut) is set.

This module takes the activation cells as input. Producing them from the
strategy grid is block 2 (``Calcs!C7:C27``); until that lands, the activation
values captured from Excel drive the tests.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "calcs_survival_table.json"

# Calcs!C68 is fed by two activation cells rather than one.
ROW_68 = 68
ROW_68_SOURCES = (19, 20)

# Calcs!C68:C70 -- seeding timing, keyed on establishment system not crop.
SEEDING_ROWS = (68, 69, 70)

# Calcs!C18 -- non-blank when full-cut (wide points) is the establishment system.
FULL_CUT_CELL = 18

# Calcs!C69/C70 skip crop code 4 (volunteer pasture), which is not sown.
VOLUNTEER_CROP_CODE = 4

# Which activation cell feeds which survival row. Not a uniform offset --
# note 78 <- 31 and 79 <- 30 are transposed relative to their neighbours.
SOURCE: dict[int, int] = {
    55: 7, 56: 8, 57: 9,                      # knock-down / double-knock
    58: 10, 59: 11, 60: 12, 61: 13, 62: 14,   # pre-emergent
    65: 17,                                   # mouldboard plough
    69: 21, 70: 22,                           # seeding timing
    71: 23, 72: 24, 73: 25, 74: 26, 75: 27,   # post-emergent
    78: 31, 79: 30, 80: 32, 81: 33, 82: 34,   # spring options
    83: 35, 84: 36, 85: 37, 86: 38,
    87: 39, 88: 40,                           # swathing
    89: 41, 90: 42, 91: 43, 92: 44, 93: 45,   # harvest
    94: 46, 95: 47, 96: 48, 97: 49,
}

ROWS: tuple[int, ...] = tuple(sorted(set(SOURCE) | {ROW_68}))

NO_EFFECT = 1.0


@lru_cache(maxsize=1)
def load_table(path: str | None = None) -> dict[str, Any]:
    """Load the generated Calcs!N54:T97 control table."""
    target = Path(path) if path else DATA_PATH
    if not target.is_file():
        raise FileNotFoundError(
            f"{target} is missing. Regenerate it with:\n"
            r"    .venv\Scripts\python -m tools.extract_params"
        )
    return json.loads(target.read_text(encoding="utf-8"))["options"]


def _active(value: Any) -> bool:
    """Every downstream formula tests ``<> ""``, not a numeric value."""
    return value is not None and value != ""


def _crop_code(value: Any) -> int:
    return int(float(value))


def _control(table: dict[str, Any], row: int, crop_code: int) -> float:
    entry = table.get(str(row))
    if entry is None:
        return 0.0
    return float(entry["by_crop_code"].get(str(crop_code), 0.0))


def _seeding_control(table: dict[str, Any], row: int, full_cut: bool) -> float:
    """Calcs!C68:C70 read columns P/Q rather than the crop-code columns."""
    entry = table.get(str(row))
    if entry is None:
        return 0.0
    return float(entry["full_cut" if full_cut else "no_till"])


def survival_factors(
    activation: Mapping[int, Any] | Mapping[str, Any],
    *,
    table: dict[str, Any] | None = None,
) -> dict[int, float]:
    """Compute Calcs rows 55-97 from one year's activation cells.

    ``activation`` maps a Calcs row number in 7..49 to that cell's value: the
    crop code when the option is selected, ``None`` when it is not. Keys may be
    ints or strings, since captured fixtures carry them as JSON object keys.

    Returns ``{row: survival_factor}`` for every row the block defines. A factor
    of 1.0 means the option is inactive or has no effect on this crop.
    """
    table = table if table is not None else load_table()
    cells = {int(k): v for k, v in activation.items() if str(k).isdigit()}

    full_cut = _active(cells.get(FULL_CUT_CELL))
    factors: dict[int, float] = {}

    for row in ROWS:
        if row == ROW_68:
            # Calcs!C68: AND(OR(C19<>"",C20<>""), OR(C19<>"",C20<>4))
            c19, c20 = (cells.get(src) for src in ROW_68_SOURCES)
            active = _active(c19) or (
                _active(c20) and _crop_code(c20) != VOLUNTEER_CROP_CODE
            )
            factors[row] = (
                1.0 - _seeding_control(table, row, full_cut) if active else NO_EFFECT
            )
            continue

        value = cells.get(SOURCE[row])
        if not _active(value):
            factors[row] = NO_EFFECT
            continue

        crop_code = _crop_code(value)
        if row in SEEDING_ROWS:
            # Calcs!C69/C70: AND(C21<>"", C21<>4)
            if crop_code == VOLUNTEER_CROP_CODE:
                factors[row] = NO_EFFECT
            else:
                factors[row] = 1.0 - _seeding_control(table, row, full_cut)
            continue

        factors[row] = 1.0 - _control(table, row, crop_code)

    return factors


def option_label(row: int, table: dict[str, Any] | None = None) -> str:
    """The workbook's own label for a survival row, for diagnostics."""
    table = table if table is not None else load_table()
    entry = table.get(str(row))
    return entry["label"] if entry else f"Calcs!C{row}"
