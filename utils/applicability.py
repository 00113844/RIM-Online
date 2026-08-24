"""Which decisions the workbook can act on in a given year, and which it cannot.

Excel never refuses an impossible selection — it accepts it and drops it from
the calculation. On screen that is indistinguishable from an option that worked,
which is how someone ends up believing they are controlling ryegrass when they
are not.

This module is the single source of truth for that. :func:`gates` decides, for
one year, which decisions are inert and why; everything else is built on it:

* the detailed year editor disables those controls outright, so the choice
  cannot be made in the first place;
* :func:`neutralise` clears anything a bulk grid edit still holds, so the plan
  can never sit in a state the model would silently ignore;
* :func:`ineffective_choices` reports what was cleared, with the cell that
  decided it.

Every rule is structural — it depends only on the crop and the workbook's own
gates, not on which engine computes the numbers.
"""
from __future__ import annotations

from typing import Any, Iterable

from rim.activation import is_sown
from rim.excel_inputs import CROP_LABELS
from rim.rotation import CROP_CODE

# The app's crop labels back to the workbook's crop codes.
_APP_LABEL_TO_CODE = {
    app_label: CROP_CODE[workbook_label]
    for workbook_label, app_label in CROP_LABELS.items()
}

FIRST_PASTURE_CROP_CODE = 4

# 2.Strategy!D65 closes the knock-down gate for these sowing times.
NO_GAP_SOWING = {"Dry", "Wet"}

# What each decision falls back to when it cannot apply — the value the model
# already reads as "nothing selected". A field mapped to None has no meaningful
# "off": the model simply does not read it, so it is left as it is.
INERT_VALUE: dict[str, str | None] = {
    "knockdown": "None",
    "pre_emergent": "No",
    "post_emergent": "No",
    "grazing_intensity": "None",
    "harvest_option": "Standard",
    "seeding_technique": None,
    "seeding_rate": None,
    "seeding_timing": None,
}

FIELD_LABEL = {
    "crop": "Crop",
    "seeding_timing": "Sowing time",
    "seeding_technique": "Sowing system",
    "seeding_rate": "Sowing rate",
    "pre_tillage": "Tillage",
    "knockdown": "Knock-down",
    "pre_emergent": "Pre-emergent",
    "post_emergent": "Post-emergent",
    "spring_option": "Spring option",
    "grazing_intensity": "Grazing",
    "harvest_option": "Harvest control",
}

SOURCE = {
    "knockdown": "2.Strategy!D65",
    "pre_emergent": "2.Strategy!D66",
    "seeding_technique": "2.Strategy!D66",
    "seeding_rate": "2.Strategy!D66",
    "seeding_timing": "2.Strategy!D66",
    "grazing_intensity": "Calcs Table 8, grazing and stocking columns",
    "harvest_option": "Calcs rows 89-94",
}


def _chosen(field: str, value: Any) -> bool:
    """Is this an active selection, rather than the field's inert value?"""
    if value in ("", None):
        return False
    text = str(value).strip()
    if field == "harvest_option":
        return text != "Standard"
    return text not in ("None", "No")


def crop_code(label: Any) -> int:
    return _APP_LABEL_TO_CODE.get(str(label).strip(), 0)


def gates(strategy_rows: Iterable[dict]) -> list[dict[str, str]]:
    """For each year, the decisions the model cannot act on, and why.

    Returns one dict per year mapping a field name to a plain-language reason.
    A field absent from the dict is live.
    """
    rows = list(strategy_rows)
    codes = [crop_code(row.get("crop")) for row in rows]
    out: list[dict[str, str]] = []

    for index, row in enumerate(rows):
        code = codes[index]
        previous = codes[index - 1] if index >= 1 else 0
        before = codes[index - 2] if index >= 2 else 0
        sown = is_sown(code, previous, before)
        blocked: dict[str, str] = {}

        # 2.Strategy!D65 — with dry or wet sowing there is no gap between
        # spraying and seeding, so a knock-down would kill the cohort the
        # seeding operation already accounts for.
        timing = str(row.get("seeding_timing", "")).strip()
        if sown and timing in NO_GAP_SOWING:
            blocked["knockdown"] = (
                f"No gap between spraying and {timing.lower()} sowing — the "
                "seeding operation already accounts for this cohort. Sow "
                "delayed to make a knock-down count."
            )

        # 2.Strategy!D66 — a paddock that regenerates is never sown, so there is
        # no seeding pass and no soil-applied herbicide.
        if not sown:
            reason = (
                "This pasture regenerates rather than being sown, so there is no "
                "seeding pass to carry it."
            )
            for field in ("pre_emergent", "seeding_technique", "seeding_rate",
                          "seeding_timing"):
                blocked[field] = reason

        # Table 8 holds 0 for both grazing and both stocking columns on every
        # crop key: grazing a crop changes neither ryegrass nor income.
        if code < FIRST_PASTURE_CROP_CODE:
            blocked["grazing_intensity"] = (
                "A crop is not grazed — this changes neither ryegrass nor "
                "livestock income."
            )

        # Calcs rows 89-94 carry no value for crop codes 4-6: harvest weed seed
        # control needs a header going through the paddock.
        if code >= FIRST_PASTURE_CROP_CODE:
            blocked["harvest_option"] = (
                "Pasture is not harvested, so there is no chaff for weed seed "
                "control to treat."
            )

        out.append(blocked)

    return out


def neutralise(strategy_rows: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    """Clear any selection the model cannot act on.

    Returns ``(rows, changes)``, where ``changes`` describes each clearing so
    the interface can say what happened rather than silently rewriting input.
    """
    rows = [dict(row) for row in strategy_rows]
    changes: list[dict] = []

    for index, (row, blocked) in enumerate(zip(rows, gates(rows))):
        for field, reason in blocked.items():
            inert = INERT_VALUE.get(field)
            if inert is None or not _chosen(field, row.get(field)):
                continue
            changes.append({
                "year": int(row.get("year", index + 1)),
                "field": FIELD_LABEL.get(field, field),
                "choice": row.get(field),
                "reason": reason,
                "source": SOURCE.get(field, ""),
            })
            row[field] = inert

    return rows, changes


def ineffective_choices(strategy_rows: Iterable[dict]) -> list[dict]:
    """Selections the model would ignore, without changing them."""
    return neutralise(strategy_rows)[1]


def summarise(findings: list[dict]) -> str:
    """One line describing the distinct problems, not the row count."""
    if not findings:
        return ""
    distinct = {(f["field"], str(f["choice"]), f["reason"]) for f in findings}
    years = sorted({f["year"] for f in findings})
    subject = "One choice was" if len(distinct) == 1 else f"{len(distinct)} choices were"
    span = f"year {years[0]}" if len(years) == 1 else f"{len(years)} of the years"
    return f"{subject} cleared, across {span} — the model cannot act on them."
