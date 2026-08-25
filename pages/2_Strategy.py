from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
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
from utils.charts import gross_margin_and_ryegrass_chart, income_breakdown_chart, weed_cost_chart
from utils.session import (
    compute_current_results,
    freeze_results,
    init_state,
    load_strategy_slot,
    reset_editor_widgets,
    reset_strategy_current,
    save_strategy_slot,
)
from utils.applicability import neutralise
from utils.validation import problem_panel, problems
from utils.year_editor import year_editor
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

st.set_page_config(page_title="Strategy | RIM Online", page_icon="🌾", layout="wide")

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 2 — Strategy builder",
    subtitle="Set what happens in each of the next ten years, and watch the seed bank respond.",
)

# ── The plan is checked before anything is computed ───────────────────────────
found = problems(st.session_state.strategy_current)

if problem_panel(found, on_fix_key="fix_all_top"):
    st.session_state.strategy_current = neutralise(st.session_state.strategy_current)[0]
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
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        height=420,
        column_order=[
            "year", "crop",
            "seeding_timing", "seeding_technique", "seeding_rate", "pre_tillage",
            "knockdown", "pre_emergent", "post_emergent",
            "spring_option", "grazing_intensity", "harvest_option",
        ],
        column_config={
            "year": st.column_config.NumberColumn("Yr", width="small", disabled=True),
            "crop": st.column_config.SelectboxColumn("Crop", options=CROP_OPTIONS, width="small"),
            "seeding_timing": st.column_config.SelectboxColumn("Sown", options=SEEDING_TIMING_OPTIONS),
            "seeding_technique": st.column_config.SelectboxColumn("System", options=SEEDING_TECHNIQUE_OPTIONS),
            "seeding_rate": st.column_config.SelectboxColumn("Rate", options=SEEDING_RATE_OPTIONS, width="small"),
            "pre_tillage": st.column_config.SelectboxColumn("Tillage", options=PRE_TILLAGE_OPTIONS),
            "knockdown": st.column_config.SelectboxColumn("Knock-down", options=KNOCKDOWN_OPTIONS),
            "pre_emergent": st.column_config.SelectboxColumn("Pre", options=YES_NO_OPTIONS, width="small"),
            "post_emergent": st.column_config.SelectboxColumn("Post", options=YES_NO_OPTIONS, width="small"),
            "spring_option": st.column_config.SelectboxColumn("Spring", options=SPRING_OPTIONS),
            "grazing_intensity": st.column_config.SelectboxColumn("Grazing", options=GRAZING_OPTIONS, width="small"),
            "harvest_option": st.column_config.SelectboxColumn("Harvest", options=HARVEST_OPTIONS, width="small"),
        },
        key="strategy_editor",
    )
    st.session_state.strategy_current = edited.to_dict("records")

# ── Saving and comparing: one row, not thirteen buttons ───────────────────────
tools_left, tools_right = st.columns([3, 2])

with tools_left:
    slot_col, load_col, save_col, reset_col = st.columns([2, 1, 1, 1.2])
    with slot_col:
        slot = st.selectbox(
            "Strategy slot",
            options=list(range(7)),
            format_func=lambda s: "Default strategy" if s == 0 else f"Slot {s}",
            key="strategy_slot_pick",
        )
    with load_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Load", use_container_width=True):
            if load_strategy_slot(slot):
                st.toast(f"Loaded {'default strategy' if slot == 0 else f'slot {slot}'}")
                st.rerun()
            else:
                st.toast(f"Slot {slot} is empty — save a strategy to it first")
    with save_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Save", use_container_width=True, disabled=slot == 0):
            save_strategy_slot(slot)
            st.toast(f"Saved to slot {slot}")
    with reset_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Clear plan", use_container_width=True):
            reset_strategy_current()
            st.rerun()

with tools_right:
    a_col, b_col, clear_col = st.columns(3)
    held_a = st.session_state.get("results_A") is not None
    held_b = st.session_state.get("results_B") is not None
    with a_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Hold as A" if not held_a else "Replace A",
                     use_container_width=True, disabled=bool(found)):
            freeze_results("A")
            st.toast("Held current results as A")
    with b_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Hold as B" if not held_b else "Replace B",
                     use_container_width=True, disabled=bool(found)):
            freeze_results("B")
            st.toast("Held current results as B")
    with clear_col:
        st.markdown('<div style="height:1.62rem"></div>', unsafe_allow_html=True)
        if st.button("Release", use_container_width=True, disabled=not (held_a or held_b)):
            st.session_state.results_A = None
            st.session_state.results_B = None
            st.rerun()

held = ", ".join(name for name, ok in (("A", held_a), ("B", held_b)) if ok)
if found:
    st.caption("Resolve the plan above before holding it for comparison.")
else:
    st.caption(
        f"Holding {held} for side-by-side comparison on the results pages."
        if held else
        "Hold two strategies as A and B to compare them on the results pages."
    )

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
    st.plotly_chart(gross_margin_and_ryegrass_chart(yearly, fixed_scale=fixed), use_container_width=True)
with cost_tab:
    st.plotly_chart(weed_cost_chart(yearly, fixed_scale=fixed), use_container_width=True)
with income_tab:
    st.plotly_chart(income_breakdown_chart(yearly, fixed_scale=fixed), use_container_width=True)

uwa_footer()
