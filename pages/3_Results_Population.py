from __future__ import annotations

import streamlit as st

from utils.charts import seedbank_population_chart
from utils.session import ensure_current_results, init_state
from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Population & Seed Bank",
    subtitle="Ryegrass plant and seed bank dynamics across the simulation",
    icon="🌿",
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
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(seedbank_population_chart(a["yearly"], "Strategy A", fixed_scale=fixed), use_container_width=True)
    with c2:
        st.plotly_chart(seedbank_population_chart(b["yearly"], "Strategy B", fixed_scale=fixed), use_container_width=True)
else:
    st.info("Compare slots A and B are not both set. Showing current strategy.")
    st.plotly_chart(seedbank_population_chart(current["yearly"], "Current Strategy", fixed_scale=fixed), use_container_width=True)
