from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import streamlit as st

from utils.export import results_to_pdf_bytes, scenario_to_excel_bytes
from utils.session import ensure_current_results, init_state
from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Export Results",
    subtitle="Download a PDF summary report or Excel data tables",
    icon="📥",
)

current = ensure_current_results()
a = st.session_state.results_A
b = st.session_state.results_B

available_sections = ["Summary", "Economics", "Yields", "Population", "Tables"]
selected_sections = st.multiselect(
    "Select sections to include",
    available_sections,
    default=["Summary", "Economics", "Tables"],
)

stamp = datetime.now().strftime("%Y-%m-%d_%H%M")

text_blocks = []
if "Summary" in selected_sections:
    s = current["summary"]
    text_blocks.append(
        "\n".join(
            [
                "Current Strategy Summary",
                f"Average gross margin: ${s['avg_gross_margin']:.1f}/ha",
                f"Nominal annuity: ${s['nominal_annuity']:.1f}/ha",
                f"Average weed control cost: ${s['avg_weed_control_cost']:.1f}/ha",
                f"Ending seed bank: {s['ending_seed_bank']:.1f} seeds/m²",
            ]
        )
    )

if "Economics" in selected_sections:
    text_blocks.append("Economics: annual gross margin, weed control cost, and income breakdown are available in the Results pages.")
if "Yields" in selected_sections:
    text_blocks.append("Yields: potential vs actual yields and ryegrass penalties are available in the Yields page.")
if "Population" in selected_sections:
    text_blocks.append("Population: ryegrass plants and seed bank dynamics are available in the Population page.")

pdf_bytes = results_to_pdf_bytes("RIM Export", text_blocks)
st.download_button("Download PDF report", data=pdf_bytes, file_name=f"RIM_{stamp}.pdf", mime="application/pdf")

results = {"Current": current["yearly"]}
if a is not None:
    results["Strategy A"] = a["yearly"]
if b is not None:
    results["Strategy B"] = b["yearly"]

st.download_button(
    "Download scenario as Excel",
    data=scenario_to_excel_bytes(
        strategy_rows=st.session_state.strategy_current,
        profile=st.session_state.profile_current,
        prices=st.session_state.prices_current,
        options=st.session_state.options_current,
        results=results,
    ),
    file_name=f"RIM_{stamp}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="One workbook: the ten-year plan, the paddock profile, prices and "
         "options, then the yearly results for each held strategy.",
)
st.caption(
    "The workbook carries the inputs as well as the results, so a colleague can "
    "see what was asked for and not just what came out. To move a scenario "
    "*back* into RIM Online, use the .rim.json file from **Keep this work** on "
    "the Strategy or Paddock profile page — Excel is for reading, JSON round-trips."
)

if a is None or b is None:
    st.info("For full A/B exports, freeze both scenarios from the Strategy page.")
