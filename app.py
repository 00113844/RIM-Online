from __future__ import annotations

import os
import sys

# Ensure the project root is on sys.path (needed on some Streamlit Cloud configurations)
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from utils.session import init_state
from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


st.set_page_config(
    page_title="RIM Online | UWA",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_uwa_theme()
init_state()
uwa_sidebar_logo()

uwa_page_header(
    title="Ryegrass Integrated Management",
    subtitle="Whole-farm bioeconomic simulation · University of Western Australia",
    icon="🌾",
)

col_l, col_r = st.columns([2, 1])

with col_l:
    st.markdown("### How to use RIM Online")
    steps = [
        ("1", "Paddock Profile", "Enter your farm name, base yields, grain prices and rotation details."),
        ("2", "Strategy Builder", "Set year-by-year management actions across a 10-year horizon."),
        ("3", "Results", "View economics, yield impacts and ryegrass population trajectories."),
        ("4", "Compare A / B", "Freeze two strategies to compare side-by-side in the Results pages."),
        ("5", "Export", "Download results as Excel or a PDF summary report."),
    ]
    for num, label, desc in steps:
        st.markdown(
            f"""
            <div class="uwa-section-card" style="display:flex;align-items:flex-start;gap:0.9rem;margin-bottom:0.6rem;">
              <div class="uwa-step-badge">{num}</div>
              <div>
                <strong style="color:var(--uwa-navy);">{label}</strong>
                <div style="color:var(--uwa-text-m);font-size:0.88rem;margin-top:0.15rem;">{desc}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with col_r:
    st.markdown("### Quick Navigation")
    st.page_link("pages/1_Paddock_Profile.py", label="→  Step 1: Paddock Profile")
    st.page_link("pages/2_Strategy.py",         label="→  Step 2: Strategy Builder")
    st.page_link("pages/3_Results_Economics.py",label="→  Step 3: Economics Results")
    st.page_link("pages/3_Results_Yields.py",   label="→  Step 3: Yield Results")
    st.page_link("pages/3_Results_Population.py",label="→  Step 3: Population Results")
    st.page_link("pages/4_Export.py",            label="→  Export")

    st.info("**Tip:** Use 'Compare A' and 'Compare B' in the Strategy page to lock two scenarios before viewing Results.")

uwa_footer()
