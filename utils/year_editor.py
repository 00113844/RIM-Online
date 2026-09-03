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

from functools import partial

import streamlit as st

from rim.options import (
    CROP_OPTIONS,
    GRAZING_OPTIONS,
    PRE_TILLAGE_OPTIONS,
    SEEDING_RATE_OPTIONS,
    SEEDING_TECHNIQUE_OPTIONS,
    SEEDING_TIMING_OPTIONS,
)
from rim.herbicides import NONE as NO_SPRAY, POST_EMERGENT_FIELDS
from utils.applicability import (
    INERT_VALUE,
    gates,
    product_mismatches,
    product_options,
)
from utils.session import custom_options

def _for_crop(field: str, row: dict) -> list[str]:
    """The options worth offering for ``field`` in this row's crop."""
    return product_options(field, row.get("crop"), custom_options())


# Grouped the way the season runs, not the way the columns happen to sit.
GROUPS: tuple[tuple[str, tuple[tuple[str, str, list], ...]], ...] = (
    ("Establishment", (
        ("seeding_timing", "Sowing time", SEEDING_TIMING_OPTIONS),
        ("seeding_technique", "Sowing system", SEEDING_TECHNIQUE_OPTIONS),
        ("seeding_rate", "Sowing rate", SEEDING_RATE_OPTIONS),
        ("pre_tillage", "Tillage", PRE_TILLAGE_OPTIONS),
    )),
    # Herbicide choices are given as a function of the row, not a fixed list:
    # which products are worth offering depends on the year's crop, and a
    # product the workbook rates at zero for that crop is left out rather than
    # offered and quietly ignored. See utils.applicability.product_options.
    ("Weed control", (
        ("knockdown", "Knock-down", partial(_for_crop, "knockdown")),
        ("pre_emergent", "Pre-emergent", partial(_for_crop, "pre_emergent")),
    )),
    ("Post-emergent sprays", tuple(
        (field, f"Spray {n}", partial(_for_crop, field))
        for n, field in enumerate(POST_EMERGENT_FIELDS, start=1)
    )),
    ("Spring", (
        ("spring_option", "Spring option", partial(_for_crop, "spring_option")),
        ("spring_swathe", "Swathe", partial(_for_crop, "spring_swathe")),
        ("spring_others", "Other", partial(_for_crop, "spring_others")),
        ("grazing_intensity", "Grazing", GRAZING_OPTIONS),
    )),
    ("Harvest", (
        ("harvest_option", "Harvest control", partial(_for_crop, "harvest_option")),
        ("harvest_others", "Other", partial(_for_crop, "harvest_others")),
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

    # The label is deliberately just the year, with no crop in it. Deriving it
    # from the plan made the label list change between runs, and Streamlit then
    # matched the selection by its formatted string rather than by index — the
    # stored value turned from 3 into "Year 4 - Wheat" and the whole editor
    # reset. The crop is shown in its own control immediately below anyway.
    years = [int(row.get("year", n + 1)) for n, row in enumerate(rows)]

    # Streamlit discards the state of widgets it did not render, so switching to
    # the grid and back loses the selection. Remember it separately and use it to
    # seed the widget when it has to be recreated. `index` is only consulted when
    # the key is absent, so a live widget still wins.
    remembered = int(st.session_state.get(f"{key}_year_index", 0))
    picked = st.selectbox(
        "Year to edit",
        options=list(range(len(rows))),
        index=min(remembered, len(rows) - 1),
        format_func=lambda i: f"Year {years[i]}",
        key=f"{key}_pick",
    )
    st.session_state[f"{key}_year_index"] = picked

    rows = [dict(row) for row in rows]
    row = rows[picked]
    blocked = gates(rows, custom_options())[picked]

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
    blocked = gates(rows, custom_options())[picked]

    for group, fields in GROUPS:
        # Re-derive before each group so a decision gates the ones below it in
        # the same pass. Sowing time sits in Establishment and decides whether
        # the knock-down in Weed control can do anything; computing the gates
        # once up front left that reason a full interaction out of date.
        rows[picked] = row
        blocked = gates(rows, custom_options())[picked]

        # A product that does nothing in this year's crop is dropped and the
        # control left live, its options already narrowed to what works. Change
        # wheat to canola and the post-emergent should offer Clethodim, not go
        # dead because Topik was in the box. The grid cannot do this -- it has
        # one option list for the whole column -- so there the mismatch stays a
        # gate, reported and cleared by utils.validation.
        for field in product_mismatches(rows, custom_options())[picked]:
            row[field] = NO_SPRAY
            blocked.pop(field, None)

        st.markdown(
            f'<div class="rim-section" style="margin-top:1.1rem">{group}</div>',
            unsafe_allow_html=True,
        )
        columns = st.columns(len(fields))
        for column, (field, label, options) in zip(columns, fields):
            choices = options(row) if callable(options) else options
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
                        options=choices,
                        index=_index(choices, row.get(field)),
                        key=f"{key}_{field}_{picked}",
                    )

    rows[picked] = row
    return rows
