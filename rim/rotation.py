"""Rotation coding: a direct port of Calcs rows 184-189.

The workbook turns the ten enterprise labels on ``2.Strategy!D4:M4`` into a
single integer per year -- the key that Table 8 (``Calcs!C193:M291``) is looked
up by for weed-free yield, ryegrass control and stocking rates.

It does this with five stacked rows, each reading the column to its left, so the
key for a year depends on the whole rotation history before it. The columns run
``C``, ``D`` (paddock history: two years ago, one year ago) then ``E``..``N``
for simulation years 1..10.

Row-by-row, using ``Calcs!E184`` etc. as the reference column:

===== ================== =========================================================
Row   Name               Meaning
===== ================== =========================================================
184   ``crop_code``      Enterprise label -> 0..6 (Wheat=0 ... Cadiz=6)
185   ``phase_code``     Crops keep their code; pastures count their run length
186   ``pasture_carry``  Carries a finished pasture phase forward, +11 per year
187   ``barley_code``    Barley-only offset (+22, or 1 when there is no carry)
188   ``break_since_canola``  Years since the last canola, capped at 3
189   ``rotation_key``   The Table 8 VLOOKUP key
===== ================== =========================================================

Nothing here is inferred. Every branch mirrors a formula, and the module is
tested against the workbook's own cached values for rows 184-189.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

# Calcs!E184 -- the enterprise labels the workbook matches against, in code order.
CROP_CODE: dict[str, int] = {
    "Wheat": 0,
    "Barley": 1,
    "Canola": 2,
    "Legume": 3,
    "Volunt.": 4,
    "Clover": 5,
    "Cadiz": 6,
}

# Calcs!C184/D184 -- paddock history uses single letters, not full labels.
HISTORY_CODE: dict[str, int] = {
    "w": 0, "b": 1, "c": 2, "l": 3, "v": 4, "s": 5, "z": 6,
}

# Calcs!C185 -- for each pasture crop code, the phase codes for the first,
# second and third-or-later consecutive year of that pasture.
_PASTURE_PHASES: dict[int, tuple[int, int, int]] = {
    4: (4, 5, 6),    # Volunteer
    5: (7, 8, 9),    # Sub-clover
    6: (10, 11, 12),  # Cadiz
}

# Calcs!C188 is a literal 3: the paddock starts with a full canola break behind it.
INITIAL_BREAK_SINCE_CANOLA = 3

BARLEY = 1
CANOLA = 2
BLANK_KEY = -1


@dataclass(frozen=True)
class YearCodes:
    """One column of the Calcs 184-189 cascade."""

    crop_code: int
    phase_code: int
    pasture_carry: int
    barley_code: int
    break_since_canola: int
    rotation_key: int
    year: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "crop_code": self.crop_code,
            "phase_code": self.phase_code,
            "pasture_carry": self.pasture_carry,
            "barley_code": self.barley_code,
            "break_since_canola": self.break_since_canola,
            "rotation_key": self.rotation_key,
        }


def _phase_code(crop_code: int, prev: YearCodes | None) -> int:
    """Calcs!E185 -- crops keep their code; pastures count consecutive years."""
    if crop_code < 4:
        return crop_code

    first, second, later = _PASTURE_PHASES[crop_code]
    if prev is None or prev.crop_code != crop_code:
        return first
    return second if prev.phase_code == first else later


def _pasture_carry(phase_code: int, prev: YearCodes | None) -> int:
    """Calcs!E186 -- once a pasture phase ends, carry it forward, +11 a year.

    The carry stops at 24, which is how the workbook bounds "how long ago the
    pasture was" before it stops mattering.
    """
    if phase_code > 1:
        return phase_code
    if prev is not None and 1 < prev.pasture_carry < 24:
        return prev.pasture_carry + 11
    return 0


def _barley_code(crop_code: int, pasture_carry: int) -> int:
    """Calcs!E187 -- barley gets its own band of keys; every other crop passes through."""
    if crop_code != BARLEY:
        return pasture_carry
    return 1 if pasture_carry == 0 else pasture_carry + 22


def _break_since_canola(prev: YearCodes | None) -> int:
    """Calcs!E188 -- reset the year after canola, otherwise count up to 3."""
    if prev is None:
        return INITIAL_BREAK_SINCE_CANOLA
    if prev.barley_code == CANOLA:
        return 0
    return prev.break_since_canola + 1 if prev.break_since_canola < 3 else prev.break_since_canola


def _rotation_key(
    barley_code: int,
    break_since_canola: int,
    prev: YearCodes | None,
    enterprise_present: bool,
) -> int:
    """Calcs!E189 -- the Table 8 lookup key.

    Canola is the special case: its key encodes how long the break was and what
    the previous phase was, because canola's yield depends on both.
    """
    if not enterprise_present:
        return BLANK_KEY
    if barley_code != CANOLA:
        return barley_code

    prev_carry = prev.pasture_carry if prev else 0
    prev_phase = prev.phase_code if prev else 0
    if prev_carry == 14:
        return 96 if break_since_canola == 2 else 97
    return 44 + 13 * break_since_canola + prev_phase


def _advance(crop_code: int, prev: YearCodes | None, *, enterprise_present: bool = True,
             year: int | None = None) -> YearCodes:
    """Compute one column of the cascade from the column to its left."""
    phase_code = _phase_code(crop_code, prev)
    pasture_carry = _pasture_carry(phase_code, prev)
    barley_code = _barley_code(crop_code, pasture_carry)
    break_since_canola = _break_since_canola(prev)
    rotation_key = _rotation_key(barley_code, break_since_canola, prev, enterprise_present)
    return YearCodes(
        crop_code=crop_code,
        phase_code=phase_code,
        pasture_carry=pasture_carry,
        barley_code=barley_code,
        break_since_canola=break_since_canola,
        rotation_key=rotation_key,
        year=year,
    )


def history_columns(one_year_ago: str = "w", two_years_ago: str = "w") -> list[YearCodes]:
    """Seed the cascade with Calcs columns C and D (the paddock's prior two years)."""
    two = _advance(HISTORY_CODE.get(str(two_years_ago).strip().lower(), 0), None)
    one = _advance(HISTORY_CODE.get(str(one_year_ago).strip().lower(), 0), two)
    return [two, one]


def rotation_codes(
    enterprises: Iterable[str | None],
    *,
    one_year_ago: str = "w",
    two_years_ago: str = "w",
) -> list[YearCodes]:
    """Run the Calcs 184-189 cascade over a strategy's enterprise labels.

    ``enterprises`` holds the ``2.Strategy`` row-4 labels in year order. A blank
    or unrecognised entry yields ``rotation_key == -1``, matching the workbook's
    handling of an incomplete strategy.
    """
    columns = history_columns(one_year_ago=one_year_ago, two_years_ago=two_years_ago)
    out: list[YearCodes] = []
    for index, label in enumerate(enterprises, start=1):
        text = str(label).strip() if label is not None else ""
        present = text != ""
        codes = _advance(
            CROP_CODE.get(text, 0),
            columns[-1],
            enterprise_present=present,
            year=index,
        )
        columns.append(codes)
        out.append(codes)
    return out
