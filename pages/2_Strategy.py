from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from rim.control_options import names
from utils.custom_options_ui import custom_options_controls
from utils.session import custom_options
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
    PRE_EMERGENT_OPTIONS,
    POST_EMERGENT_OPTIONS,
    SPRING_SWATHE_OPTIONS,
)
from utils.charts import gross_margin_and_ryegrass_chart, income_breakdown_chart, weed_cost_chart
from utils.session import (
    compute_current_results,
    freeze_results,
    release_results,
    init_state,
    DEFAULT_STRATEGY_SLOT,
    load_strategy_slot,
    reset_editor_widgets,
    reset_strategy_current,
    save_strategy_slot,
    strategy_slot_label,
    strategy_slot_labels,
    strategy_slot_name,
)
from utils.applicability import neutralise
from utils.validation import problem_panel, problems
from utils.year_editor import FIELD_HELP as _YEAR_FIELD_HELP, year_editor
from utils.save_load import save_load_controls
from utils.theme import (
    inject_uwa_theme,
    metric_row,
    seedbank_spine,
    section,
    uwa_footer,
    uwa_page_header,
    uwa_sidebar_logo,
)

# The grid and the year editor explain the three sprays the same way, from one
# string, so they cannot drift apart.
POST_EMERGENT_HELP = _YEAR_FIELD_HELP["post_emergent_1"]

st.set_page_config(page_title="Strategy | RIM Online", page_icon="🌾", layout="wide")

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 2 — Strategy builder",
    subtitle="Set what happens in each of the next ten years, and watch the seed bank respond.",
)

# ── The plan is checked before anything is computed ───────────────────────────
found = problems(st.session_state.strategy_current, custom_options())

if problem_panel(found, on_fix_key="fix_all_top"):
    st.session_state.strategy_current = neutralise(
        st.session_state.strategy_current, custom_options()
    )[0]
    st.session_state.results_current = None
    reset_editor_widgets()
    st.rerun()

result = None
if not found:
    result = compute_current_results()
    yearly = result["yearly"]
    summary = result["summary"]

    seedbank_spine(
        years=yearly["year"].tolist(),
        crops=yearly["crop"].tolist(),
        seed_bank=yearly["seed_bank_end"].tolist(),
    )

    metric_row([
        {"label": "Average gross margin", "value": f"{summary['avg_gross_margin']:,.0f}",
         "unit": "$/ha/yr", "accent": "margin", "note": "Mean across the ten years"},
        {"label": "Nominal annuity", "value": f"{summary['nominal_annuity']:,.0f}",
         "unit": "$/ha/yr", "accent": "margin", "note": "After tax, inflation and interest"},
        {"label": "Weed control", "value": f"{summary['avg_weed_control_cost']:,.0f}",
         "unit": "$/ha/yr", "accent": "rye", "note": "Average yearly spend"},
        {"label": "Seed bank at year 10", "value": f"{summary['ending_seed_bank']:,.0f}",
         "unit": "seeds/m²", "accent": "rye", "note": "What the next decade inherits"},
    ])

# ── The editor ────────────────────────────────────────────────────────────────
section("Year-by-year plan")

# Only one editor renders at a time, and this is not cosmetic. Streamlit runs the
# body of every tab on every script run — switching tabs is purely client-side —
# so with both editors live they both wrote the plan, and the grid's retained
# edit state overwrote whatever the year editor had just set.
BY_YEAR = "Year by year"
ALL_YEARS = "All ten years"

mode = st.radio(
    "Editing",
    [BY_YEAR, ALL_YEARS],
    horizontal=True,
    key="strategy_edit_mode",
    label_visibility="collapsed",
)

# Each editor keeps its own widget state, so the one coming on screen has to
# re-seed from the current plan rather than re-apply what it was last holding.
if st.session_state.get("_strategy_edit_mode_seen") != mode:
    st.session_state._strategy_edit_mode_seen = mode
    reset_editor_widgets()

if mode == BY_YEAR:
    st.caption(
        "Pick a year and set it up. Anything that cannot work in that year — grazing "
        "a crop, a knock-down with no gap before sowing — is switched off, with the "
        "reason shown, so you cannot pick it by mistake."
    )
    # Plain assignment, no st.rerun(): changing any widget already triggers a
    # rerun, and year_editor re-derives the gates after reading the crop, so the
    # greying-out still updates live.
    st.session_state.strategy_current = year_editor(
        st.session_state.strategy_current, key="yr"
    )

else:
    st.caption(
        "Faster for repeating a decision across the run. This view cannot switch "
        "options off, so check the plan afterwards — anything the model cannot use "
        "is listed above the grid."
    )
    edited = st.data_editor(
        pd.DataFrame(st.session_state.strategy_current),
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        height=420,
        column_order=[
            "year", "crop",
            "seeding_timing", "seeding_technique", "seeding_rate", "pre_tillage",
            "knockdown", "pre_emergent",
            "post_emergent_1", "post_emergent_2", "post_emergent_3",
            "spring_option", "spring_swathe", "spring_others",
            "grazing_intensity", "harvest_option", "harvest_others",
        ],
        column_config={
            "year": st.column_config.NumberColumn("Yr", width="small", disabled=True),
            "crop": st.column_config.SelectboxColumn("Crop", options=CROP_OPTIONS, width="small"),
            "seeding_timing": st.column_config.SelectboxColumn("Sown", options=SEEDING_TIMING_OPTIONS),
            "seeding_technique": st.column_config.SelectboxColumn("System", options=SEEDING_TECHNIQUE_OPTIONS),
            "seeding_rate": st.column_config.SelectboxColumn("Rate", options=SEEDING_RATE_OPTIONS, width="small"),
            "pre_tillage": st.column_config.SelectboxColumn("Tillage", options=PRE_TILLAGE_OPTIONS),
            "knockdown": st.column_config.SelectboxColumn("Knock-down", options=KNOCKDOWN_OPTIONS),
            # The grid offers every product, because st.data_editor cannot vary
            # a column's options per row. Anything that does nothing in that
            # year's crop is cleared by utils.applicability.neutralise and
            # reported, rather than left to look effective. The year editor,
            # which can vary per row, never offers it in the first place.
            "pre_emergent": st.column_config.SelectboxColumn("Pre-em", options=PRE_EMERGENT_OPTIONS),
            "post_emergent_1": st.column_config.SelectboxColumn(
                "Post-em 1", options=POST_EMERGENT_OPTIONS, help=POST_EMERGENT_HELP),
            "post_emergent_2": st.column_config.SelectboxColumn(
                "Post-em 2", options=POST_EMERGENT_OPTIONS, help=POST_EMERGENT_HELP),
            "post_emergent_3": st.column_config.SelectboxColumn(
                "Post-em 3", options=POST_EMERGENT_OPTIONS, help=POST_EMERGENT_HELP),
            "spring_option": st.column_config.SelectboxColumn("Spring", options=SPRING_OPTIONS),
            "spring_swathe": st.column_config.SelectboxColumn("Swathe", options=SPRING_SWATHE_OPTIONS),
            "spring_others": st.column_config.SelectboxColumn("Spring other", options=names("spring_others", custom_options())),
            "grazing_intensity": st.column_config.SelectboxColumn("Grazing", options=GRAZING_OPTIONS, width="small"),
            "harvest_option": st.column_config.SelectboxColumn("Harvest", options=HARVEST_OPTIONS, width="small"),
            "harvest_others": st.column_config.SelectboxColumn("Harvest other", options=names("harvest_others", custom_options())),
        },
        key="strategy_editor",
    )
    st.session_state.strategy_current = edited.to_dict("records")

# ── Saving and comparing: one row, not thirteen buttons ───────────────────────
tools_left, tools_right = st.columns([3, 2])

# Handled as `on_click` callbacks, not in the script body: the picker's labels
# carry the names, so they have to be right the moment it draws. A button
# handled below it acts after it has already rendered, and Streamlit then shows
# the label from before the save. See
# .claude/memory/streamlit-widget-state-staleness.md.
def _save_plan_slot() -> None:
    chosen = st.session_state.strategy_slot_pick
    save_strategy_slot(chosen, st.session_state.get("strategy_slot_name", ""))
    st.session_state.strategy_slot_message = f"Saved to {strategy_slot_label(chosen)}"


def _load_plan_slot() -> None:
    chosen = st.session_state.strategy_slot_pick
    label = strategy_slot_label(chosen)
    if load_strategy_slot(chosen):
        st.session_state.strategy_slot_name = strategy_slot_name(chosen)
        st.session_state.strategy_slot_message = f"Loaded {label}"
    else:
        st.session_state.strategy_slot_message = (
            f"Slot {chosen} is empty — save a plan to it first"
        )


with tools_left:
    slot_labels = strategy_slot_labels()
    slot_col, name_col, load_col, save_col, reset_col = st.columns([2, 2, 1, 1, 1.2])
    with slot_col:
        slot = st.selectbox(
            "Strategy slot",
            options=list(slot_labels),
            format_func=slot_labels.__getitem__,
            key="strategy_slot_pick",
        )
    with name_col:
        st.text_input(
            "Name this plan",
            key="strategy_slot_name",
            placeholder="e.g. No glyphosate",
            disabled=slot == DEFAULT_STRATEGY_SLOT,
            help="Shown in the slot list, so you can tell your plans apart. "
                 "Saved with the slot.",
        )
    with load_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        st.button("Load", width="stretch", on_click=_load_plan_slot)
    with save_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        st.button("Save", width="stretch", on_click=_save_plan_slot,
                  disabled=slot == DEFAULT_STRATEGY_SLOT)
    with reset_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Clear plan", width="stretch"):
            reset_strategy_current()
            st.rerun()

with tools_right:
    a_col, b_col, clear_col = st.columns(3)
    held_a = st.session_state.get("results_A") is not None
    held_b = st.session_state.get("results_B") is not None
    with a_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Hold as A" if not held_a else "Replace A",
                     width="stretch", disabled=bool(found)):
            freeze_results("A")
            st.toast("Held current results as A")
    with b_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Hold as B" if not held_b else "Replace B",
                     width="stretch", disabled=bool(found)):
            freeze_results("B")
            st.toast("Held current results as B")
    with clear_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Release", width="stretch", disabled=not (held_a or held_b)):
            release_results()
            st.rerun()

# What each slot holds, spelled out. The picker carries the same names, but
# Streamlit keeps a keyed widget's rendered label when only its options change,
# so the closed box can read a beat behind. This line is plain markdown and is
# right on every run.
st.caption(" · ".join(slot_labels.values()))

_message = st.session_state.pop("strategy_slot_message", None)
if _message:
    st.toast(_message)

held = ", ".join(name for name, ok in (("A", held_a), ("B", held_b)) if ok)
if found:
    st.caption("Resolve the plan above before holding it for comparison.")
else:
    st.caption(
        f"Holding {held} for side-by-side comparison on the results pages."
        if held else
        "Hold two strategies as A and B to compare them on the results pages."
    )

with st.expander("Spring and harvest options of your own"):
    custom_options_controls()

with st.expander("Keep this work"):
    save_load_controls("strategy")
    st.page_link("pages/4_How_RIM_Works.py", label="How saving and loading works")

# ── Charts ────────────────────────────────────────────────────────────────────
if result is None:
    uwa_footer()
    st.stop()

section("How the decade plays out")

fixed = st.session_state.get("strategy_scale_mode") == "Fixed"
scale_col, _ = st.columns([1, 3])
with scale_col:
    st.session_state.strategy_scale_mode = st.radio(
        "Chart scale",
        ["Auto", "Fixed"],
        index=1 if fixed else 0,
        horizontal=True,
        help="Fixed uses the same axis limits as the Excel workbook, so runs can be compared by eye.",
    )
fixed = st.session_state.strategy_scale_mode == "Fixed"

margin_tab, cost_tab, income_tab = st.tabs(["Margin and ryegrass", "Weed control cost", "Income sources"])
with margin_tab:
    st.plotly_chart(gross_margin_and_ryegrass_chart(yearly, fixed_scale=fixed),
                    width="stretch", key="strategy_margin")
with cost_tab:
    st.plotly_chart(weed_cost_chart(yearly, fixed_scale=fixed),
                    width="stretch", key="strategy_weed_cost")
with income_tab:
    st.plotly_chart(income_breakdown_chart(yearly, fixed_scale=fixed),
                    width="stretch", key="strategy_income")

uwa_footer()
