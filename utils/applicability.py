"""Which choices the workbook quietly ignores, and why.

The Excel model does not stop you selecting an option that cannot do anything —
it just gates it out of the calculation. On screen that is indistinguishable
from an option that worked, which is how a user ends up believing they are
controlling ryegrass when they are not.

Every rule below is structural: it depends only on the crop and the workbook's
own gates, not on which engine computes the numbers. Each cites the cell it
comes from.
"""
from __future__ import annotations

from typing import Any, Iterable

from rim.activation import is_sown
from rim.rotation import CROP_CODE
from rim.excel_inputs import CROP_LABELS

# The app's crop labels back to the workbook's crop codes.
_APP_LABEL_TO_CODE = {
    app_label: CROP_CODE[workbook_label]
    for workbook_label, app_label in CROP_LABELS.items()
}

FIRST_PASTURE_CROP_CODE = 4
VOLUNTEER_CROP_CODE = 4

# 2.Strategy!D65 closes the knock-down gate for these sowing times.
NO_GAP_SOWING = {"Dry", "Wet"}

_NOTHING = ("None", "No", "", None)


def _chosen(value: Any) -> bool:
    return value not in _NOTHING


def crop_code(label: Any) -> int:
    return _APP_LABEL_TO_CODE.get(str(label).strip(), 0)


def ineffective_choices(strategy_rows: Iterable[dict]) -> list[dict]:
    """Find selections that will have no effect on ryegrass.

    Returns one entry per finding: ``{year, field, choice, reason, source}``.
    """
    rows = list(strategy_rows)
    codes = [crop_code(row.get("crop")) for row in rows]
    findings: list[dict] = []

    for index, row in enumerate(rows):
        year = int(row.get("year", index + 1))
        code = codes[index]
        previous = codes[index - 1] if index >= 1 else 0
        before = codes[index - 2] if index >= 2 else 0
        sown = is_sown(code, previous, before)

        # 2.Strategy!D65 — with dry or wet sowing there is no gap between
        # spraying and seeding, so the knock-down would kill the cohort the
        # seeding operation already accounts for.
        timing = str(row.get("seeding_timing", "")).strip()
        if _chosen(row.get("knockdown")) and sown and timing in NO_GAP_SOWING:
            findings.append({
                "year": year,
                "field": "Knock-down",
                "choice": row.get("knockdown"),
                "reason": f"no gap before {timing.lower()} sowing, so it is not counted twice",
                "source": "2.Strategy!D65",
            })

        # 2.Strategy!D66 — a paddock that is not sown gets no seeding operation
        # and no soil-applied herbicide.
        if not sown:
            for field, label in (
                ("pre_emergent", "Pre-emergent"),
                ("seeding_technique", "Sowing system"),
                ("seeding_rate", "Sowing rate"),
            ):
                if _chosen(row.get(field)):
                    findings.append({
                        "year": year,
                        "field": label,
                        "choice": row.get(field),
                        "reason": "this pasture regenerates rather than being sown",
                        "source": "2.Strategy!D66",
                    })

        # Table 8 (Calcs!C193:M291) holds 0 for both grazing columns and both
        # stocking columns on every crop key. Grazing a crop changes neither
        # ryegrass nor livestock income.
        if code < FIRST_PASTURE_CROP_CODE and _chosen(row.get("grazing_intensity")):
            findings.append({
                "year": year,
                "field": "Grazing",
                "choice": row.get("grazing_intensity"),
                "reason": "a crop is not grazed, so there is no ryegrass control "
                          "and no livestock income",
                "source": "Calcs Table 8, grazing and stocking columns",
            })

        # Calcs rows 89-94 carry no value for crop codes 4-6: harvest weed seed
        # control needs a header going through the paddock.
        if code >= FIRST_PASTURE_CROP_CODE and _chosen(row.get("harvest_option")):
            if str(row.get("harvest_option")).strip() != "Standard":
                findings.append({
                    "year": year,
                    "field": "Harvest control",
                    "choice": row.get("harvest_option"),
                    "reason": "pasture is not harvested, so there is no chaff to treat",
                    "source": "Calcs rows 89-94",
                })

    return findings


def summarise(findings: list[dict]) -> str:
    """One line describing the distinct problems, not the row count."""
    if not findings:
        return ""
    distinct = {(f["field"], str(f["choice"]), f["reason"]) for f in findings}
    years = sorted({f["year"] for f in findings})
    if len(distinct) == 1:
        subject = "One choice below has"
    else:
        subject = f"{len(distinct)} choices below have"
    span = f"year {years[0]}" if len(years) == 1 else f"{len(years)} of the years"
    return f"{subject} no effect, across {span}."
