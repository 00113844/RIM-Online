from __future__ import annotations

from io import BytesIO

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def tables_to_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, table in tables.items():
            safe_name = sheet_name[:31]
            table.to_excel(writer, index=False, sheet_name=safe_name)
    buffer.seek(0)
    return buffer.getvalue()


def results_to_pdf_bytes(title: str, blocks: list[str]) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, title)
    y -= 30

    c.setFont("Helvetica", 10)
    for block in blocks:
        for line in block.splitlines():
            if y < 70:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 10)
            c.drawString(50, y, line[:120])
            y -= 14
        y -= 6

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ── Exporting the inputs, not just the results ───────────────────────────────
# A results table says what happened; it does not say what was asked for. To
# hand a colleague a scenario they can read in Excel, the paddock profile,
# prices, options and the ten-year plan have to travel with it.

from utils.applicability import FIELD_LABEL  # noqa: E402  (kept near its use)

# The strategy grid, in the order the editor shows it.
STRATEGY_COLUMNS = (
    "year", "crop", "seeding_timing", "seeding_technique", "seeding_rate",
    "pre_tillage", "knockdown", "pre_emergent",
    "post_emergent_1", "post_emergent_2", "post_emergent_3",
    "spring_option", "grazing_intensity", "harvest_option",
)


def strategy_to_frame(strategy_rows: list[dict]) -> pd.DataFrame:
    """The ten-year plan as a readable table, one row per year."""
    frame = pd.DataFrame(strategy_rows)
    ordered = [c for c in STRATEGY_COLUMNS if c in frame.columns]
    ordered += [c for c in frame.columns if c not in ordered]
    frame = frame[ordered]
    return frame.rename(columns={
        "year": "Year",
        **{field: FIELD_LABEL.get(field, field) for field in frame.columns if field != "year"},
    })


def settings_to_frame(name: str, settings: dict) -> pd.DataFrame:
    """Flatten one settings dict into Group / Setting / Value rows.

    Profiles, prices and options are a mix of scalars and nested dicts (per-crop
    yields, control effects). Flattening keeps one readable shape rather than a
    sheet per nested key, and the group column preserves where each value sat.
    """
    rows: list[dict] = []
    for key, value in settings.items():
        if isinstance(value, dict):
            for inner_key, inner in value.items():
                if isinstance(inner, dict):
                    for leaf_key, leaf in inner.items():
                        rows.append({"Group": f"{key} / {inner_key}",
                                     "Setting": leaf_key, "Value": leaf})
                else:
                    rows.append({"Group": key, "Setting": inner_key, "Value": inner})
        else:
            rows.append({"Group": "", "Setting": key, "Value": value})
    frame = pd.DataFrame(rows, columns=["Group", "Setting", "Value"])
    frame.attrs["name"] = name
    return frame


def scenario_to_excel_bytes(
    *,
    strategy_rows: list[dict],
    profile: dict,
    prices: dict,
    options: dict,
    results: dict[str, pd.DataFrame] | None = None,
) -> bytes:
    """A whole scenario as one workbook: what was asked for, then what happened.

    Inputs come first deliberately — a reader opening this wants to see the plan
    before the numbers it produced.
    """
    sheets: dict[str, pd.DataFrame] = {
        "Strategy": strategy_to_frame(strategy_rows),
        "Paddock profile": settings_to_frame("Paddock profile", profile),
        "Prices": settings_to_frame("Prices", prices),
        "Options": settings_to_frame("Options", options),
    }
    for name, table in (results or {}).items():
        sheets[f"Results {name}"[:31]] = table
    return tables_to_excel_bytes(sheets)
