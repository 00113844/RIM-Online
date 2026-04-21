from __future__ import annotations

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
    reset_strategy_current,
    save_strategy_slot,
)


from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 2 — Strategy Builder",
    subtitle="Define year-by-year management actions for up to 10 years",
    icon="📋",
)

left, right = st.columns([2, 1])
with left:
    st.session_state.strategy_scale_mode = st.radio(
        "Scale mode",
        ["Auto", "Fixed"],
        index=0 if st.session_state.strategy_scale_mode == "Auto" else 1,
        horizontal=True,
    )
with right:
    st.session_state.strategy_graph_mode = st.selectbox(
        "Graph visibility",
        options=[0, 1, 2],
        format_func=lambda x: {0: "Hide graphs", 1: "Show first", 2: "Show all"}[x],
        index=int(st.session_state.strategy_graph_mode),
    )

slot_cols = st.columns(7)
with slot_cols[0]:
    if st.button("Load S0"):
        if load_strategy_slot(0):
            st.success("Loaded default strategy")
            st.rerun()
for slot in range(1, 7):
    with slot_cols[slot]:
        if st.button(f"Save S{slot}"):
            save_strategy_slot(slot)
            st.success(f"Saved S{slot}")
        if st.button(f"Load S{slot}"):
            if load_strategy_slot(slot):
                st.success(f"Loaded S{slot}")
                st.rerun()
            else:
                st.warning("Empty")

action_cols = st.columns(4)
with action_cols[0]:
    if st.button("Reset Current Strategy"):
        reset_strategy_current()
        st.rerun()
with action_cols[1]:
    if st.button("Compare A"):
        freeze_results("A")
        st.success("Current results frozen to A")
with action_cols[2]:
    if st.button("Compare B"):
        freeze_results("B")
        st.success("Current results frozen to B")
with action_cols[3]:
    if st.button("Clear A/B"):
        st.session_state.results_A = None
        st.session_state.results_B = None
        st.success("A/B comparison cleared")

strategy_df = pd.DataFrame(st.session_state.strategy_current)

edited = st.data_editor(
    strategy_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "year": st.column_config.NumberColumn("Year", min_value=1, max_value=50, step=1),
        "crop": st.column_config.SelectboxColumn("Crop/Pasture", options=CROP_OPTIONS),
        "seeding_timing": st.column_config.SelectboxColumn("Seeding timing", options=SEEDING_TIMING_OPTIONS),
        "seeding_technique": st.column_config.SelectboxColumn("Seeding technique", options=SEEDING_TECHNIQUE_OPTIONS),
        "seeding_rate": st.column_config.SelectboxColumn("Seeding rate", options=SEEDING_RATE_OPTIONS),
        "pre_tillage": st.column_config.SelectboxColumn("Pre-tillage", options=PRE_TILLAGE_OPTIONS),
        "knockdown": st.column_config.SelectboxColumn("Knock-down", options=KNOCKDOWN_OPTIONS),
        "pre_emergent": st.column_config.SelectboxColumn("Pre-emergent", options=YES_NO_OPTIONS),
        "post_emergent": st.column_config.SelectboxColumn("Post-emergent", options=YES_NO_OPTIONS),
        "spring_option": st.column_config.SelectboxColumn("Spring option", options=SPRING_OPTIONS),
        "grazing_intensity": st.column_config.SelectboxColumn("Grazing", options=GRAZING_OPTIONS),
        "harvest_option": st.column_config.SelectboxColumn("Harvest option", options=HARVEST_OPTIONS),
    },
    key="strategy_editor",
)

st.session_state.strategy_current = edited.to_dict("records")
result = compute_current_results()
yearly = result["yearly"]
summary = result["summary"]

mx1, mx2, mx3, mx4 = st.columns(4)
mx1.metric("Average gross margin", f"${summary['avg_gross_margin']:.1f}/ha")
mx2.metric("Nominal annuity", f"${summary['nominal_annuity']:.1f}/ha")
mx3.metric("Average weed control cost", f"${summary['avg_weed_control_cost']:.1f}/ha")
mx4.metric("Ending seed bank", f"{summary['ending_seed_bank']:.1f} seeds/m²")

fixed = st.session_state.strategy_scale_mode == "Fixed"
if st.session_state.strategy_graph_mode >= 1:
    st.plotly_chart(gross_margin_and_ryegrass_chart(yearly, "Gross Margin and Ryegrass", fixed_scale=fixed), use_container_width=True)
if st.session_state.strategy_graph_mode >= 2:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(weed_cost_chart(yearly, "Weed Control Cost", fixed_scale=fixed), use_container_width=True)
    with c2:
        st.plotly_chart(income_breakdown_chart(yearly, "Income Breakdown", fixed_scale=fixed), use_container_width=True)
