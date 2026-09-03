"""The herbicide view of :mod:`rim.control_options`, and the schema migration.

Herbicides were the first decisions to get their real names, so this module is
where the rest of the app reaches for them. The table it reads is now the
general one -- every weed-control decision, control and cost together -- and
lives in :mod:`rim.control_options`.

It also carries :func:`upgrade_row`, which brings a strategy row written by an
earlier version up to the current schema. There have been three:

    1  ``pre_emergent`` / ``post_emergent`` held "Yes" or "No"; the knock-down
       was "Single knock-down" / "Double knock-down"; spring and harvest used
       names of our own ("Green manuring", "Narrow windrow burn").
    2  Herbicides named as the workbook names them, and ``post_emergent`` split
       into the three slots the workbook has.
    3  Every weed-control decision uses the workbook's own vocabulary, and the
       three decisions RIM has that the app lacked -- spring swathe, spring
       others, harvest others -- exist.

A row already at the current schema passes through untouched, so upgrading is
safe to apply to anything.
"""
from __future__ import annotations

from rim import control_options
from rim.control_options import NONE, ControlOption

# The herbicide-facing names for what are now generic option rows.
Herbicide = ControlOption
DATA_PATH = control_options.SURVIVAL_PATH

KNOCKDOWN_ROWS = control_options.FIELD_ROWS["knockdown"]
PRE_EMERGENT_ROWS = control_options.FIELD_ROWS["pre_emergent"]
POST_EMERGENT_ROWS = control_options.FIELD_ROWS["post_emergent_1"]

POST_EMERGENT_FIELDS: tuple[str, ...] = (
    "post_emergent_1", "post_emergent_2", "post_emergent_3",
)

# The herbicide slots, and the strategy field each one reads.
_SLOT_FIELD = {
    "knockdown": "knockdown",
    "pre": "pre_emergent",
    "post": "post_emergent_1",
}


def _field(slot: str) -> str:
    return _SLOT_FIELD[slot]


def knockdowns() -> tuple[Herbicide, ...]:
    """Calcs rows 55-57 — Glyphosate, Paraquat, and the double knock."""
    return control_options.options_for("knockdown")


def pre_emergents() -> tuple[Herbicide, ...]:
    """Calcs rows 58-62, in workbook order."""
    return control_options.options_for("pre_emergent")


def post_emergents() -> tuple[Herbicide, ...]:
    """Calcs rows 71-75, in workbook order."""
    return control_options.options_for("post_emergent_1")


def knockdown_names() -> list[str]:
    return control_options.names("knockdown")


def pre_emergent_names() -> list[str]:
    return control_options.names("pre_emergent")


def post_emergent_names() -> list[str]:
    return control_options.names("post_emergent_1")


def find(name: object, *, slot: str) -> Herbicide | None:
    """The named product in ``slot``, or None for "not sprayed"/unknown."""
    return control_options.find(_field(slot), name)


def control(name: object, crop_code: int, *, slot: str) -> float:
    """Proportion of germinated ryegrass this product kills in this crop."""
    return control_options.control(_field(slot), name, crop_code)


def works_on(name: object, crop_code: int, *, slot: str) -> bool:
    """Would this selection have any effect in this crop?"""
    return control_options.works_on(_field(slot), name, crop_code)


def first_that_works(crop_code: int, *, slot: str) -> str:
    """The first product in workbook order that does anything in this crop.

    Used to carry a plan forward from a schema that recorded only "Yes".
    Returns ``NONE`` when nothing in this slot works on the crop, which is the
    honest answer for a pasture with no pre-emergent.
    """
    for product in control_options.options_for(_field(slot)):
        if product.works_on(crop_code):
            return product.name
    return NONE


# ── Carrying older plans forward ──────────────────────────────────────────────

# Version 1 named the knock-down by how many passes it was, which the workbook
# never does. A single knock becomes the first single product it lists; the
# double becomes the row that *is* the double.
LEGACY_KNOCKDOWN = {
    "Single knock-down": "Glyphosate",
    "Double knock-down": "Glyphosate/Paraquat",
}

# Version 1 spring and harvest names, against the workbook rows they meant.
LEGACY_SPRING = {
    "Green manuring": "Green M.",
    "Brown manuring": "Brown M",
    "Mowing": "Mow+Spray",
    "Hay & Silage": "Hay+Spray",
    "Topping": "Topping",
}
LEGACY_HARVEST = {
    "Narrow windrow burn": "Narr+B.",
    "Chaff-tramlining": "Tram.",
    "Chaff cart+dumps": "Cart+B.",
    "HSD": "HSD",
    "BDS": "BDS+E.",
}

# Two version-1 choices sat in the wrong column: the workbook keeps burning
# everything on the harvest-others row, and swathing on a row of its own.
LEGACY_MOVED = {
    ("harvest_option", "Whole paddock burn"): ("harvest_others", "B.all"),
    ("spring_option", "Swathing"): ("spring_swathe", "W/o Spray"),
}


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def upgrade_row(row: dict) -> dict:
    """Bring one strategy row up to the current schema. Idempotent."""
    from rim.rotation import app_crop_code

    out = dict(row)
    code = app_crop_code(out.get("crop", "Wheat"))

    # A bare "Yes" does not say which product, and none can be inferred from it,
    # so it becomes the first the workbook lists that works on this crop -- a
    # rule rather than a guess at intent.
    def resolve(value: object, slot: str) -> str:
        text = _text(value)
        if text == "Yes":
            return first_that_works(code, slot=slot)
        return NONE if text in ("No", "") else text

    if _text(out.get("pre_emergent")) in ("Yes", "No", ""):
        out["pre_emergent"] = resolve(out.get("pre_emergent"), "pre")

    if "post_emergent" in out:
        legacy = out.pop("post_emergent")
        if _text(out.get("post_emergent_1")) in (NONE, ""):
            out["post_emergent_1"] = resolve(legacy, "post")

    for field in POST_EMERGENT_FIELDS:
        if _text(out.get(field)) in ("", "No", "Yes"):
            out[field] = resolve(out.get(field, NONE), "post")

    for field, legacy_names in (("knockdown", LEGACY_KNOCKDOWN),
                                ("spring_option", LEGACY_SPRING),
                                ("harvest_option", LEGACY_HARVEST)):
        current = _text(out.get(field))
        out[field] = legacy_names.get(
            current, current or control_options.INERT[field]
        )

    for (field, old), (target, new) in LEGACY_MOVED.items():
        if _text(out.get(field)) == old:
            out[field] = control_options.INERT[field]
            if _text(out.get(target)) in (NONE, ""):
                out[target] = new

    for field in control_options.FIELDS:
        out.setdefault(field, control_options.INERT[field])

    return out


def upgrade_strategy(rows: list[dict]) -> list[dict]:
    """:func:`upgrade_row` across a whole plan."""
    return [upgrade_row(row) for row in rows]
