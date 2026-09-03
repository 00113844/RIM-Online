from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.graph_objects as go
import streamlit as st

from utils.charts import _base, yield_comparison_chart
from utils.results_view import panel_key, comparison_note, views
from utils.session import init_state
from utils.theme import (
    RYE,
    inject_uwa_theme,
    metric_row,
    section,
    uwa_footer,
    uwa_page_header,
    uwa_sidebar_logo,
)

st.set_page_config(page_title="Yields | RIM Online", page_icon="🌾", layout="wide")

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Yield and competition",
    subtitle="What the crop could have yielded, and how much of it the ryegrass took.",
)


def penalty_chart(df):
    """Yield lost to ryegrass, as a share of potential."""
    fig = go.Figure()
    fig.add_scatter(
        x=df["year"],
        y=df["ryegrass_penalty_fraction"] * 100.0,
        mode="lines+markers",
        name="Yield lost",
        line=dict(color=RYE, width=2),
        marker=dict(size=5, color=RYE),
        fill="tozeroy",
        fillcolor="rgba(168,68,42,0.10)",
        hovertemplate="Year %{x}<br>%{y:.1f}% of potential lost<extra></extra>",
    )
    _base(fig, height=280, legend=False)
    fig.update_yaxes(title="% of potential", rangemode="tozero")
    return fig


comparison_note()
panels = views()

for label, result in panels:
    yearly = result["yearly"]
    if len(panels) > 1:
        section(label)
    potential = float(yearly["yield_potential_t_ha"].sum())
    actual = float(yearly["yield_t_ha"].sum())
    lost = max(0.0, potential - actual)
    share = (lost / potential * 100.0) if potential else 0.0
    metric_row([
        {"label": "Harvested over ten years", "value": f"{actual:,.1f}", "unit": "t/ha",
         "accent": "margin"},
        {"label": "Lost to ryegrass", "value": f"{lost:,.1f}", "unit": "t/ha",
         "accent": "rye", "note": f"{share:.0f}% of potential"},
        {"label": "Worst year", "value": f"{yearly['ryegrass_penalty_fraction'].max() * 100:,.0f}",
         "unit": "% lost", "accent": "rye"},
    ])

section("Year by year")

yield_tab, penalty_tab = st.tabs(["Harvested and lost", "Share lost to ryegrass"])
with yield_tab:
    columns = st.columns(len(panels))
    for column, (label, result) in zip(columns, panels):
        with column:
            if len(panels) > 1:
                st.caption(label)
            st.plotly_chart(yield_comparison_chart(result["yearly"]),
                            width="stretch", key=panel_key("yield", label))
    st.caption(
        "The loss is stacked on top of what was harvested, so the pale band is the "
        "yield the ryegrass took rather than a gap you have to measure."
    )
with penalty_tab:
    columns = st.columns(len(panels))
    for column, (label, result) in zip(columns, panels):
        with column:
            if len(panels) > 1:
                st.caption(label)
            st.plotly_chart(penalty_chart(result["yearly"]),
                            width="stretch", key=panel_key("penalty", label))

uwa_footer()
