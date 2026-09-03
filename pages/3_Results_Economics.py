from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.charts import gross_margin_and_ryegrass_chart, income_breakdown_chart, weed_cost_chart
from utils.results_view import panel_key, comparison_note, scale_toggle, views
from utils.session import init_state
from utils.theme import (
    inject_uwa_theme, metric_row, section, uwa_footer, uwa_page_header, uwa_sidebar_logo,
)

st.set_page_config(page_title="Economics | RIM Online", page_icon="🌾", layout="wide")

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Economics",
    subtitle="What the decade earned, what the weed control cost, and where the income came from.",
)

comparison_note()
panels = views()

for label, result in panels:
    summary = result["summary"]
    if len(panels) > 1:
        section(label)
    metric_row([
        {"label": "Average gross margin", "value": f"{summary['avg_gross_margin']:,.0f}",
         "unit": "$/ha/yr", "accent": "margin"},
        {"label": "Nominal annuity", "value": f"{summary['nominal_annuity']:,.0f}",
         "unit": "$/ha/yr", "accent": "margin", "note": "After tax, inflation and interest"},
        {"label": "Best year", "value": f"{summary['max_gross_margin']:,.0f}",
         "unit": "$/ha", "accent": "margin"},
        {"label": "Worst year", "value": f"{summary['min_gross_margin']:,.0f}",
         "unit": "$/ha", "accent": "rye"},
        {"label": "Weed control", "value": f"{summary['avg_weed_control_cost']:,.0f}",
         "unit": "$/ha/yr", "accent": "rye", "note": "Average yearly spend"},
    ])

section("Year by year")
fixed = scale_toggle()

margin_tab, cost_tab, income_tab = st.tabs(
    ["Margin and ryegrass", "Weed control cost", "Income sources"]
)
for tab, builder in (
    (margin_tab, gross_margin_and_ryegrass_chart),
    (cost_tab, weed_cost_chart),
    (income_tab, income_breakdown_chart),
):
    with tab:
        columns = st.columns(len(panels))
        for column, (label, result) in zip(columns, panels):
            with column:
                if len(panels) > 1:
                    st.caption(label)
                st.plotly_chart(
                    builder(result["yearly"], fixed_scale=fixed),
                    width="stretch",
                    key=panel_key(builder.__name__, label),
                )

uwa_footer()
