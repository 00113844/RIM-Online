from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.export import tables_to_excel_bytes
from utils.session import custom_options, ensure_current_results, init_state
from utils.validation import held_results_notice, problems
from utils.theme import (
    inject_uwa_theme,
    section,
    uwa_footer,
    uwa_page_header,
    uwa_sidebar_logo,
)

st.set_page_config(page_title="Data tables | RIM Online", page_icon="🌾", layout="wide")

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 3 — Data tables",
    subtitle="Every number behind the charts, year by year.",
)

# Plain-language headers and the units each column is in. The model's own field
# names stay in the download; on screen they are named for the reader.
COLUMNS = {
    "year": ("Year", None, "%d"),
    "crop": ("Crop or pasture", None, None),
    "gross_margin": ("Gross margin", "$/ha", "%.2f"),
    "weed_control_cost": ("Weed control", "$/ha", "%.2f"),
    "income_grain": ("Grain income", "$/ha", "%.2f"),
    "income_pasture": ("Pasture income", "$/ha", "%.2f"),
    "income_livestock": ("Livestock income", "$/ha", "%.2f"),
    "yield_potential_t_ha": ("Potential yield", "t/ha", "%.2f"),
    "yield_t_ha": ("Harvested yield", "t/ha", "%.2f"),
    "ryegrass_penalty_fraction": ("Yield lost", "fraction", "%.3f"),
    "ryegrass_plants_m2": ("Ryegrass", "plants/m²", "%.1f"),
    "seed_bank_start": ("Seed bank, start", "seeds/m²", "%.1f"),
    "seed_bank_end": ("Seed bank, end", "seeds/m²", "%.1f"),
    "new_seed_added": ("New seed set", "seeds/m²", "%.1f"),
    "control_fraction": ("Ryegrass controlled", "fraction", "%.3f"),
    "stocking_dse": ("Stocking rate", "DSE/ha", "%.1f"),
}


def column_config(frame) -> dict:
    config = {}
    for field, (label, unit, fmt) in COLUMNS.items():
        if field not in frame.columns:
            continue
        heading = f"{label} ({unit})" if unit else label
        if fmt is None:
            config[field] = st.column_config.TextColumn(heading)
        else:
            config[field] = st.column_config.NumberColumn(heading, format=fmt)
    return config


def show(frame) -> None:
    ordered = [c for c in COLUMNS if c in frame.columns]
    ordered += [c for c in frame.columns if c not in ordered]
    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        height=430,
        column_order=ordered,
        column_config=column_config(frame),
    )


found = problems(st.session_state.strategy_current, custom_options())
if found and st.session_state.get("results_A") is None:
    held_results_notice(found)
    uwa_footer()
    st.stop()

current = ensure_current_results()
a = st.session_state.get("results_A")
b = st.session_state.get("results_B")

current_tab, a_tab, b_tab = st.tabs(["Current plan", "Strategy A", "Strategy B"])
with current_tab:
    show(current["yearly"])
with a_tab:
    if a is None:
        st.info("Nothing held as A yet. Use **Hold as A** on the Strategy page.")
    else:
        show(a["yearly"])
with b_tab:
    if b is None:
        st.info("Nothing held as B yet. Use **Hold as B** on the Strategy page.")
    else:
        show(b["yearly"])

section("Take it away")

tables = {"Current": current["yearly"]}
if a is not None:
    tables["Strategy_A"] = a["yearly"]
if b is not None:
    tables["Strategy_B"] = b["yearly"]

left, right = st.columns([1, 3])
with left:
    st.download_button(
        "Download as Excel",
        data=tables_to_excel_bytes(tables),
        file_name="RIM_tables.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
with right:
    sheets = ", ".join(tables)
    st.caption(f"One sheet per strategy: {sheets}. Columns keep the model's field names.")

uwa_footer()
