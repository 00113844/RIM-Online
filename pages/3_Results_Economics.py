from __future__ import annotations

import streamlit as st

from utils.charts import gross_margin_and_ryegrass_chart, income_breakdown_chart, weed_cost_chart
from utils.session import ensure_current_results, init_state
from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Economics & Summary",
    subtitle="Gross margin, weed control costs and income breakdown",
    icon="💰",
)

st.session_state.results_scale_mode = st.radio(
    "Scale mode",
    ["Auto", "Fixed"],
    index=0 if st.session_state.results_scale_mode == "Auto" else 1,
    horizontal=True,
)
fixed = st.session_state.results_scale_mode == "Fixed"

current = ensure_current_results()
a = st.session_state.results_A
b = st.session_state.results_B

if a is not None and b is not None:
    st.subheader("Comparison: Strategy A vs Strategy B")
    ca, cb = st.columns(2)
    with ca:
        st.plotly_chart(gross_margin_and_ryegrass_chart(a["yearly"], "Strategy A", fixed_scale=fixed), use_container_width=True)
        st.plotly_chart(weed_cost_chart(a["yearly"], "Weed Control Cost - A", fixed_scale=fixed), use_container_width=True)
        st.plotly_chart(income_breakdown_chart(a["yearly"], "Income Breakdown - A", fixed_scale=fixed), use_container_width=True)
        st.metric("Nominal annuity A", f"${a['summary']['nominal_annuity']:.1f}/ha")
    with cb:
        st.plotly_chart(gross_margin_and_ryegrass_chart(b["yearly"], "Strategy B", fixed_scale=fixed), use_container_width=True)
        st.plotly_chart(weed_cost_chart(b["yearly"], "Weed Control Cost - B", fixed_scale=fixed), use_container_width=True)
        st.plotly_chart(income_breakdown_chart(b["yearly"], "Income Breakdown - B", fixed_scale=fixed), use_container_width=True)
        st.metric("Nominal annuity B", f"${b['summary']['nominal_annuity']:.1f}/ha")
else:
    st.info("Compare slots A and B are not both set. Showing current strategy.")
    st.plotly_chart(gross_margin_and_ryegrass_chart(current["yearly"], "Current Strategy", fixed_scale=fixed), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(weed_cost_chart(current["yearly"], "Weed Control Cost", fixed_scale=fixed), use_container_width=True)
    with c2:
        st.plotly_chart(income_breakdown_chart(current["yearly"], "Income Breakdown", fixed_scale=fixed), use_container_width=True)

metrics = current["summary"]
m1, m2, m3 = st.columns(3)
m1.metric("Average gross margin", f"${metrics['avg_gross_margin']:.1f}/ha")
m2.metric("Nominal annuity", f"${metrics['nominal_annuity']:.1f}/ha")
m3.metric("Average weed control cost", f"${metrics['avg_weed_control_cost']:.1f}/ha")
