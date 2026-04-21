from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.graph_objects as go
import streamlit as st

from utils.charts import yield_comparison_chart
from utils.session import ensure_current_results, init_state
from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Yields & Competition",
    subtitle="Potential vs actual yield and ryegrass penalty over the rotation",
    icon="🌾",
)

current = ensure_current_results()
a = st.session_state.results_A
b = st.session_state.results_B


def penalty_chart(df, title: str):
    fig = go.Figure()
    fig.add_scatter(
        x=df["year"],
        y=df["ryegrass_penalty_fraction"] * 100.0,
        mode="lines+markers",
        line=dict(color="#E64A19", width=3),
        name="Yield penalty (%)",
    )
    fig.update_layout(title=title, xaxis_title="Year", yaxis_title="Penalty (%)", margin=dict(t=60, l=40, r=20, b=30))
    return fig


if a is not None and b is not None:
    st.subheader("Comparison: Strategy A vs Strategy B")
    ca, cb = st.columns(2)
    with ca:
        st.plotly_chart(yield_comparison_chart(a["yearly"], "Potential vs Actual Yield - A"), use_container_width=True)
        st.plotly_chart(penalty_chart(a["yearly"], "Ryegrass Yield Penalty - A"), use_container_width=True)
    with cb:
        st.plotly_chart(yield_comparison_chart(b["yearly"], "Potential vs Actual Yield - B"), use_container_width=True)
        st.plotly_chart(penalty_chart(b["yearly"], "Ryegrass Yield Penalty - B"), use_container_width=True)
else:
    st.info("Compare slots A and B are not both set. Showing current strategy.")
    st.plotly_chart(yield_comparison_chart(current["yearly"], "Potential vs Actual Yield"), use_container_width=True)
    st.plotly_chart(penalty_chart(current["yearly"], "Ryegrass Yield Penalty"), use_container_width=True)
