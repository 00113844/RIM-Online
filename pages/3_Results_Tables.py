from __future__ import annotations

import streamlit as st

from utils.export import tables_to_excel_bytes
from utils.session import ensure_current_results, init_state
from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Data Tables",
    subtitle="Annual simulation results for current strategy and comparisons A/B",
    icon="📊",
)

current = ensure_current_results()
a = st.session_state.results_A
b = st.session_state.results_B

tabs = st.tabs(["Current", "Strategy A", "Strategy B"])
with tabs[0]:
    st.dataframe(current["yearly"], use_container_width=True)
with tabs[1]:
    if a is None:
        st.info("Strategy A is not frozen yet.")
    else:
        st.dataframe(a["yearly"], use_container_width=True)
with tabs[2]:
    if b is None:
        st.info("Strategy B is not frozen yet.")
    else:
        st.dataframe(b["yearly"], use_container_width=True)

tables = {"Current": current["yearly"]}
if a is not None:
    tables["Strategy_A"] = a["yearly"]
if b is not None:
    tables["Strategy_B"] = b["yearly"]

st.download_button(
    "Download tables as Excel",
    data=tables_to_excel_bytes(tables),
    file_name="RIM_tables.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
