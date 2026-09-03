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

from rim.herbicides import NONE as HERBICIDE_NONE

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
    "Stage timing is lost: Calcs!C75:C83 applies each control at a named "
    "seasonal stage, whereas Python applies one combined annual fraction.",
)


def _present(value: Any) -> bool:
    """Excel treats a blank cell as 'option not selected' (Calcs!C7:C27)."""
    return value is not None and str(value).strip() != ""


# 2.Strategy's dropdown (P70:P95) abbreviates one name that the control table
# (Calcs!B55:B97) spells out. Everything else matches, so only the exception is
# listed; an unrecognised label is passed through rather than silently dropped.
STRATEGY_PRODUCT_LABELS: dict[str, str] = {
    "Triflur+Tria": "Triflur+Triallate",
    "DoubleK": "Glyphosate/Paraquat",
    "Green man.": "Green M.",
    "Brown man.": "Brown M",
    "Hay": "Hay+Spray",
    "Silage": "Sil.+Spray",
    "Mowing": "Mow+Spray",
    "Burn": "B.all",
}


def _product(value: Any) -> str:
    """A herbicide cell on 2.Strategy, as the app names the product."""
    if not _present(value):
        return HERBICIDE_NONE
    text = str(value).strip()
    return STRATEGY_PRODUCT_LABELS.get(text, text)


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
        "knockdown": _product(excel_row.get("knock_down")),
        "pre_emergent": _product(excel_row.get("pre_emergent")),
        **{f"post_emergent_{i}": _product(excel_row.get(f"post_emergent_{i}"))
           for i in (1, 2, 3)},
        "spring_option": _product(spring_raw),
        "spring_swathe": _product(excel_row.get("spring_swathe")),
        "spring_others": _product(excel_row.get("spring_others")),
        "harvest_others": _product(excel_row.get("harvest_others")),
        "grazing_intensity": str(excel_row.get("grazing_intensity") or "None").strip(),
        "harvest_option": (
            _product(excel_row.get("harvest_crops"))
            if _present(excel_row.get("harvest_crops")) else "Standard"
        ),
    }


def translate_strategy(excel_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map a full 10-year Excel strategy grid."""
    return [translate_year(row) for row in excel_rows]
