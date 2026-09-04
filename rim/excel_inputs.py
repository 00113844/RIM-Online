"""Translate the workbook's native strategy labels into the current Python schema.

This adapter is **deliberately and documentedly lossy**. The Excel model makes
product-specific decisions at named seasonal stages; the current Python engine
takes generic ``Yes``/``No`` decisions once per year. Nothing here invents
model behaviour -- it only maps vocabulary so that a captured Excel scenario can
be fed to ``simulate_strategy()`` and the resulting gap measured.

Every lossy mapping is recorded in :data:`TRANSLATION_LOSSES` so a parity report
can state plainly which part of a discrepancy is a genuine model error and which
is an artefact of the translation. As the engine port lands (see
``.claude/memory/engine-port-status.md``) entries here should disappear, not grow.
"""
from __future__ import annotations

from typing import Any

from rim import control_options

# 2.Strategy row 4 label -> the crop name rim/options.py uses.
CROP_LABELS: dict[str, str] = {
    "Wheat": "Wheat",
    "Barley": "Barley",
    "Canola": "Canola",
    "Legume": "Legume crop",
    "Volunt.": "Volunteer pasture",
    "Clover": "Sub-Clover pasture",
    "Cadiz": "Cadiz pasture",
}

# 2.Strategy row 5.
SOWING_LABELS: dict[str, str] = {
    "Dry": "Dry",
    "Wet": "Wet",
    "Delayed": "Delayed (1-2 wks)",
    "+Delayed": "+Delayed (3 wks)",
}

# 2.Strategy row 6. Blank means no pre-seeding tillage.
SOIL_PREP_LABELS: dict[str, str] = {
    "Tickle": "Tickle",
    "Mouldboard": "Mouldboard plough",
    "Mouldb.": "Mouldboard plough",
}


# 2.Strategy row 9.
ESTABLISHMENT_LABELS: dict[str, str] = {
    "No-till": "No-till",
    "Full-cut": "Full-cut (wide points)",
}


TRANSLATION_LOSSES: tuple[str, ...] = (
    # An earlier version of this entry said Calcs!C75:C83 "applies each control
    # at a named seasonal stage". Those cells do no such thing -- they are
    # survival factors for post-emergent Paraquat, the two grazing intensities
    # and the spring options, looked up like every other row. The claim was
    # right in substance and wrong in its citation, which is worse than saying
    # nothing: it sends the next reader to cells that do not support it.
    "Stage timing is lost. Calcs rows 55-97 turn each active option into a "
    "survival factor by HLOOKUP into the control table at Calcs!N54:T97, and "
    "the cascade applies each one where it belongs in the season -- Calcs!C168 "
    "combines the three post-emergent slots, and Calcs!C177 carries the result "
    "into the plant and seed-set model. Python multiplies one combined annual "
    "fraction instead, so both the ordering and which cohorts a control can "
    "still reach are lost.",
)


def _present(value: Any) -> bool:
    """Excel treats a blank cell as 'option not selected' (Calcs!C7:C27)."""
    return value is not None and str(value).strip() != ""


def _option(field: str, value: Any) -> str:
    """A weed-control cell on 2.Strategy, as the app names that option.

    The strategy sheet's dropdowns abbreviate differently from the control table
    -- "Triflur+Tria" against "Triflur+Triallate", "Green man." against
    "Green M." -- and both are aliases in rim.control_options, so resolving is
    the same lookup the app uses everywhere else rather than a table kept here.
    """
    if not _present(value):
        return control_options.INERT[field]
    return control_options.canonical(field, value)


def translate_year(excel_row: dict[str, Any]) -> dict[str, Any]:
    """Map one Excel strategy year onto a ``simulate_strategy`` decision dict."""
    crop_raw = str(excel_row.get("enterprise") or "Wheat").strip()
    spring_raw = str(excel_row.get("spring_option") or "").strip()

    return {
        "year": excel_row.get("year"),
        "crop": CROP_LABELS.get(crop_raw, crop_raw),
        "seeding_timing": SOWING_LABELS.get(
            str(excel_row.get("time_of_sowing") or "Dry").strip(), "Dry"
        ),
        "seeding_technique": ESTABLISHMENT_LABELS.get(
            str(excel_row.get("establishment_system") or "No-till").strip(), "No-till"
        ),
        "seeding_rate": str(excel_row.get("crop_seeding_rate") or "Standard").strip(),
        "pre_tillage": SOIL_PREP_LABELS.get(
            str(excel_row.get("soil_preparation") or "").strip(), "None"
        ),
        # Every weed-control decision now uses the workbook's own vocabulary,
        # rated and priced per crop, so these carry across as they are rather
        # than collapsing into names of ours. 2.Strategy rows 7, 8, 11-13,
        # 15-19.
        "knockdown": _option("knockdown", excel_row.get("knock_down")),
        "pre_emergent": _option("pre_emergent", excel_row.get("pre_emergent")),
        **{f"post_emergent_{i}": _option(f"post_emergent_{i}",
                                         excel_row.get(f"post_emergent_{i}"))
           for i in (1, 2, 3)},
        "spring_option": _option("spring_option", spring_raw),
        "spring_swathe": _option("spring_swathe", excel_row.get("spring_swathe")),
        "spring_others": _option("spring_others", excel_row.get("spring_others")),
        "harvest_others": _option("harvest_others", excel_row.get("harvest_others")),
        "grazing_intensity": str(excel_row.get("grazing_intensity") or "None").strip(),
        "harvest_option": _option("harvest_option", excel_row.get("harvest_crops")),
    }


def translate_strategy(excel_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a full 10-year Excel strategy grid."""
    return [translate_year(row) for row in excel_rows]
