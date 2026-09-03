"""Named herbicides, and what each one controls on each crop.

RIM does not ask whether you sprayed. It asks *what* you sprayed, because a
product's effect depends on the crop it is sprayed into: Topik takes 90% of the
ryegrass in wheat and nothing at all in canola, while Clethodim is the other way
round. A yes/no answer cannot express that, and the flat control rate it implies
is wrong for every product.

The numbers live in ``Calcs!N54:T97`` -- one row per control option, one column
per crop code -- and are already generated into
``data/calcs_survival_table.json`` by ``tools/extract_params.py``. Nothing here
is typed; this module only names the rows and reads them.

    Pre-emergent   Calcs rows 58-62   Triflur+Triallate .. Triazine
    Post-emergent  Calcs rows 71-75   Topik .. Paraquat

**A zero is a statement, not a gap.** Where the table holds 0 for a crop the
product does nothing there, and the workbook means it: Topik and Hussar are
grass-selective cereal herbicides, so they read 0 on canola, legume and every
pasture. :func:`works_on` is that reading, and ``utils/applicability.py`` turns
it into a disabled control rather than a silent no-op.

The workbook offers three post-emergent slots (``2.Strategy`` rows 11-13), so a
year can carry up to three applications. They are independent rows in the same
table; nothing here privileges one slot over another.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "calcs_survival_table.json"

# Calcs!N54:T97 row numbers. The order is the workbook's own, and it is the
# order the dropdowns show, so the app reads like 1.Profile does.
PRE_EMERGENT_ROWS: tuple[int, ...] = (58, 59, 60, 61, 62)
POST_EMERGENT_ROWS: tuple[int, ...] = (71, 72, 73, 74, 75)

# The three post-emergent decisions, 2.Strategy rows 11, 12 and 13.
POST_EMERGENT_FIELDS: tuple[str, ...] = (
    "post_emergent_1",
    "post_emergent_2",
    "post_emergent_3",
)

# What "nothing sprayed" reads as in a strategy row.
NONE = "None"


@dataclass(frozen=True)
class Herbicide:
    """One row of the control table, under the name 1.Profile gives it."""

    row: int                      # Calcs row, for citation
    name: str                     # "Sakura"
    control: dict[int, float]     # crop code -> proportion of ryegrass killed

    def works_on(self, crop_code: int) -> bool:
        """Does this product do anything at all to ryegrass in this crop?"""
        return self.control.get(crop_code, 0.0) > 0.0

    @property
    def crops_it_works_on(self) -> tuple[int, ...]:
        return tuple(code for code, value in sorted(self.control.items()) if value > 0.0)


@lru_cache(maxsize=1)
def _table() -> dict:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"{DATA_PATH} is missing. Regenerate it with:\n"
            r"    .venv\Scripts\python -m tools.extract_params"
        )
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _read(rows: tuple[int, ...]) -> tuple[Herbicide, ...]:
    options = _table()["options"]
    out = []
    for row in rows:
        entry = options[str(row)]
        # Labels arrive as "Pre-E: Sakura" / "Post-E: Topik"; the prefix says
        # which slot, which the row number already tells us.
        name = entry["label"].split(":", 1)[-1].strip()
        out.append(Herbicide(
            row=row,
            name=name,
            control={int(code): float(value)
                     for code, value in entry["by_crop_code"].items()},
        ))
    return tuple(out)


@lru_cache(maxsize=1)
def pre_emergents() -> tuple[Herbicide, ...]:
    """Calcs rows 58-62, in workbook order."""
    return _read(PRE_EMERGENT_ROWS)


@lru_cache(maxsize=1)
def post_emergents() -> tuple[Herbicide, ...]:
    """Calcs rows 71-75, in workbook order."""
    return _read(POST_EMERGENT_ROWS)


def _by_name(products: tuple[Herbicide, ...]) -> dict[str, Herbicide]:
    return {product.name: product for product in products}


def pre_emergent_names() -> list[str]:
    """The pre-emergent dropdown: no spray, then the workbook's five."""
    return [NONE] + [product.name for product in pre_emergents()]


def post_emergent_names() -> list[str]:
    """One post-emergent slot's dropdown: no spray, then the workbook's five."""
    return [NONE] + [product.name for product in post_emergents()]


def find(name: object, *, slot: str) -> Herbicide | None:
    """The named product in ``slot`` ("pre" or "post"), or None.

    Returns None for "None", for a blank, and for a name this build does not
    know -- a strategy saved by a later version, say. A caller that treats None
    as "nothing sprayed" degrades safely.
    """
    if name in (None, "", NONE):
        return None
    products = pre_emergents() if slot == "pre" else post_emergents()
    return _by_name(products).get(str(name).strip())


def control(name: object, crop_code: int, *, slot: str) -> float:
    """Proportion of germinated ryegrass this product kills in this crop.

    Zero when nothing is sprayed, and zero when the product does nothing to
    this crop -- which is the workbook's own value, not a fallback.
    """
    product = find(name, slot=slot)
    return 0.0 if product is None else product.control.get(crop_code, 0.0)


def works_on(name: object, crop_code: int, *, slot: str) -> bool:
    """Would this selection have any effect in this crop?"""
    return control(name, crop_code, slot=slot) > 0.0


def first_that_works(crop_code: int, *, slot: str) -> str:
    """The first product in workbook order that does anything in this crop.

    Used only to carry forward a plan saved before products existed, where the
    decision recorded was the bare "Yes". Returns ``NONE`` when no product in
    this slot works on the crop, which is the honest answer for a pasture with
    no pre-emergent.
    """
    products = pre_emergents() if slot == "pre" else post_emergents()
    for product in products:
        if product.works_on(crop_code):
            return product.name
    return NONE


def upgrade_row(row: dict) -> dict:
    """Carry a strategy row written before herbicides had names.

    Version 1 of the strategy schema asked only whether you sprayed:
    ``pre_emergent`` and ``post_emergent`` held "Yes" or "No". A bare "Yes"
    does not say which product, and no product can be inferred from it, so it
    becomes the first one the workbook lists that works on that year's crop --
    a deterministic rule, not a guess at intent. "No" becomes ``NONE``.

    Rows already using product names pass through untouched, so this is safe to
    apply to anything.
    """
    from rim.rotation import app_crop_code

    out = dict(row)
    code = app_crop_code(out.get("crop", "Wheat"))

    def resolve(value: object, slot: str) -> str:
        text = str(value).strip()
        if text == "Yes":
            return first_that_works(code, slot=slot)
        if text in ("No", ""):
            return NONE
        return text

    if str(out.get("pre_emergent", "")).strip() in ("Yes", "No", ""):
        out["pre_emergent"] = resolve(out.get("pre_emergent"), "pre")

    # The single old slot becomes the first of the workbook's three.
    if "post_emergent" in out:
        legacy = out.pop("post_emergent")
        if str(out.get("post_emergent_1", NONE)).strip() in (NONE, ""):
            out["post_emergent_1"] = resolve(legacy, "post")

    for field in POST_EMERGENT_FIELDS:
        if str(out.get(field, "")).strip() in ("", "No", "Yes"):
            out[field] = resolve(out.get(field, NONE), "post")
        out.setdefault(field, NONE)

    return out


def upgrade_strategy(rows: list[dict]) -> list[dict]:
    """:func:`upgrade_row` across a whole plan."""
    return [upgrade_row(row) for row in rows]
