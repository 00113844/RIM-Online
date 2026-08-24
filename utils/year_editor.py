"""Edit one year with the impossible decisions actually switched off.

The grid is fast for bulk work but Streamlit's data editor can only disable a
whole column, never one cell — so it cannot express "grazing is available in
year 4 but not year 3". This panel can: every control is a real widget, and the
ones the model cannot act on are disabled outright, with the reason under them.

Selection is prevented here rather than corrected afterwards, which is the
difference between a tool that teaches the model and one that merely records
what you typed.
"""
from __future__ import annotations

import streamlit as st

from rim.options import (
    CROP_OPTIONS,
    GRAZING_OPTIONS,
    HARVEST_OPTIONS,
    KNOCKDOWN_OPTIONS,
    PRE_TILLAGE_OPTIONS,
    SEEDING_RATE_OPTIONS,
    SEEDING_TECHNIQUE_OPTIONS,
    SEEDING_TIMING_OPTIONS,
    SPRING_OPTIONS,
    YES_NO_OPTIONS,
)
from utils.applicability import INERT_VALUE, gates

# Grouped the way the season runs, not the way the columns happen to sit.
GROUPS: tuple[tuple[str, tuple[tuple[str, str, list], ...]], ...] = (
    ("Establishment", (
        ("seeding_timing", "Sowing time", SEEDING_TIMING_OPTIONS),
        ("seeding_technique", "Sowing system", SEEDING_TECHNIQUE_OPTIONS),
        ("seeding_rate", "Sowing rate", SEEDING_RATE_OPTIONS),
        ("pre_tillage", "Tillage", PRE_TILLAGE_OPTIONS),
    )),
    ("Weed control", (
        ("knockdown", "Knock-down", KNOCKDOWN_OPTIONS),
        ("pre_emergent", "Pre-emergent", YES_NO_OPTIONS),
        ("post_emergent", "Post-emergent", YES_NO_OPTIONS),
    )),
    ("Spring and harvest", (
        ("spring_option", "Spring option", SPRING_OPTIONS),
        ("grazing_intensity", "Grazing", GRAZING_OPTIONS),
        ("harvest_option", "Harvest control", HARVEST_OPTIONS),
    )),
)


def _index(options: list, value, fallback: int = 0) -> int:
    try:
        return options.index(value)
    except ValueError:
        return fallback


def year_editor(rows: list[dict], key: str = "year_editor") -> list[dict]:
    """Render the panel and return the (possibly edited) strategy rows."""
    if not rows:
        return rows

    labels = [
        f"Year {row.get('year', n + 1)} — {row.get('crop', 'Wheat')}"
        for n, row in enumerate(rows)
    ]
    picked = st.selectbox(
        "Year to edit",
        options=list(range(len(rows))),
        format_func=lambda i: labels[i],
        key=f"{key}_pick",
    )

    rows = [dict(row) for row in rows]
    row = rows[picked]
    blocked = gates(rows)[picked]

    crop_col, _ = st.columns([1, 3])
    with crop_col:
        row["crop"] = st.selectbox(
            "Crop or pasture",
            options=CROP_OPTIONS,
            index=_index(CROP_OPTIONS, row.get("crop")),
            key=f"{key}_crop_{picked}",
            help="What you grow decides which of the choices below the model can act on.",
        )

    # The crop may have just changed, so re-derive the gates before drawing.
    rows[picked] = row
    blocked = gates(rows)[picked]

    for group, fields in GROUPS:
        st.markdown(
            f'<div class="rim-section" style="margin-top:1.1rem">{group}</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(len(fields))
        for column, (field, label, options) in zip(columns, fields):
            reason = blocked.get(field)
            with column:
                if reason:
                    inert = INERT_VALUE.get(field)
                    shown = inert if inert is not None else row.get(field)
                    st.selectbox(
                        label,
                        options=[shown],
                        index=0,
                        disabled=True,
                        key=f"{key}_{field}_{picked}_off",
                    )
                    st.markdown(
                        f'<div class="rim-blocked">{reason}</div>',
                        unsafe_allow_html=True,
                    )
                    if inert is not None:
                        row[field] = inert
                else:
                    row[field] = st.selectbox(
                        label,
                        options=options,
                        index=_index(options, row.get(field)),
                        key=f"{key}_{field}_{picked}",
                    )

    rows[picked] = row
    return rows
