from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.charts import seedbank_population_chart
from utils.results_view import comparison_note, scale_toggle, views
from utils.session import init_state
from utils.theme import (
    inject_uwa_theme, metric_row, seedbank_spine, section, uwa_footer,
    uwa_page_header, uwa_sidebar_logo,
)

st.set_page_config(page_title="Population | RIM Online", page_icon="🌾", layout="wide")

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Ryegrass population",
    subtitle="The stand you see each year, and the seed bank underneath it that decides the next one.",
)

comparison_note()
panels = views()

for label, result in panels:
    yearly = result["yearly"]
    if len(panels) > 1:
        section(label)
    seedbank_spine(
        years=yearly["year"].tolist(),
        crops=yearly["crop"].tolist(),
        seed_bank=yearly["seed_bank_end"].tolist(),
    )
    start = float(yearly["seed_bank_start"].iloc[0])
    end = float(yearly["seed_bank_end"].iloc[-1])
    last_year = int(yearly["year"].iloc[-1])
    if start > 0:
        change = (end - start) / start * 100.0
        note = f"{abs(change):,.0f}% {'lower' if change < 0 else 'higher'} than the start"
    else:
        note = "no seed bank to start from"
    metric_row([
        {"label": "Seed bank at the start", "value": f"{start:,.1f}", "unit": "seeds/m²",
         "accent": "rye", "note": "What year 1 inherited"},
        {"label": f"Seed bank after year {last_year}", "value": f"{end:,.1f}",
         "unit": "seeds/m²", "accent": "rye", "note": note},
        {"label": "Peak ryegrass", "value": f"{yearly['ryegrass_plants_m2'].max():,.1f}",
         "unit": "plants/m²", "accent": "rye", "note": "Worst year of the run"},
        {"label": "Ryegrass in the final year", "value": f"{yearly['ryegrass_plants_m2'].iloc[-1]:,.1f}",
         "unit": "plants/m²", "accent": "rye"},
    ])

section("Year by year")
fixed = scale_toggle()

columns = st.columns(len(panels))
for column, (label, result) in zip(columns, panels):
    with column:
        if len(panels) > 1:
            st.caption(label)
        st.plotly_chart(
            seedbank_population_chart(result["yearly"], fixed_scale=fixed),
            use_container_width=True,
        )

st.caption(
    "The seed bank is drawn as a filled area because it is a stock that carries "
    "between years; the plant count is a line because it is a single reading each spring."
)

uwa_footer()
