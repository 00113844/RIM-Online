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

# 2.Strategy row 7. Excel names the product; Python knows only single/double.
KNOCKDOWN_LABELS: dict[str, str] = {
    "Glyphosate": "Single knock-down",
    "Paraquat": "Single knock-down",
    "DoubleK": "Double knock-down",
}

# 2.Strategy row 9.
ESTABLISHMENT_LABELS: dict[str, str] = {
    "No-till": "No-till",
    "Full-cut": "Full-cut (wide points)",
}

# 2.Strategy row 15.
SPRING_LABELS: dict[str, str] = {
    "Green man.": "Green manuring",
    "Brown man.": "Brown manuring",
    "Mowing": "Mowing",
    "Hay": "Hay & Silage",
    "Silage": "Hay & Silage",
    "Topping": "Topping",
    "Swathing": "Swathing",
}

# 2.Strategy row 18.
HARVEST_LABELS: dict[str, str] = {
    "Standard": "Standard",
    "Burn": "Whole paddock burn",
    "Narr+B.": "Narrow windrow burn",
    "Tramline": "Chaff-tramlining",
    "Cart+B.": "Chaff cart+dumps",
    "HSD": "HSD",
    "BDS": "BDS",
}

TRANSLATION_LOSSES: tuple[str, ...] = (
    "Herbicide products collapse to Yes/No: Excel prices and rates each product "
    "separately from 1.Profile (e.g. E20/H20 Triflur+Triallate $22/ha, 80% control).",
    "Three post-emergent slots (2.Strategy rows 11-13) collapse to one boolean.",
    "Knock-down products collapse to Single/Double; Excel distinguishes "
    "Glyphosate from Paraquat in both cost and control.",
    "Spring sub-options (rows 16 'Swathe' and 17 'Others', e.g. 'With Spray') "
    "are dropped; Excel treats them as separate priced operations.",
    "Harvest-options-others (row 19) is dropped; only the crops row is mapped.",
    "Stage timing is lost: Calcs!C75:C83 applies each control at a named "
    "seasonal stage, whereas Python applies one combined annual fraction.",
)


def _present(value: Any) -> bool:
    """Excel treats a blank cell as 'option not selected' (Calcs!C7:C27)."""
    return value is not None and str(value).strip() != ""


def translate_year(excel_row: dict[str, Any]) -> dict[str, Any]:
    """Map one Excel strategy year onto a ``simulate_strategy`` decision dict."""
    crop_raw = str(excel_row.get("enterprise") or "Wheat").strip()
    spring_raw = str(excel_row.get("spring_option") or "").strip()

    post_em_selected = any(
        _present(excel_row.get(f"post_emergent_{i}")) for i in (1, 2, 3)
    )

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
        "knockdown": KNOCKDOWN_LABELS.get(
            str(excel_row.get("knock_down") or "").strip(), "None"
        ),
        "pre_emergent": "Yes" if _present(excel_row.get("pre_emergent")) else "No",
        "post_emergent": "Yes" if post_em_selected else "No",
        "spring_option": SPRING_LABELS.get(spring_raw, "None"),
        "grazing_intensity": str(excel_row.get("grazing_intensity") or "None").strip(),
        "harvest_option": HARVEST_LABELS.get(
            str(excel_row.get("harvest_crops") or "Standard").strip(), "Standard"
        ),
    }


def translate_strategy(excel_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a full 10-year Excel strategy grid."""
    return [translate_year(row) for row in excel_rows]
