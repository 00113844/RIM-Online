from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.session import init_state
from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Welcome to RIM Online",
    subtitle="Ryegrass Integrated Management — Whole-farm bioeconomic simulation",
    icon="🌾",
)

col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown("#### What is RIM Online?")
    st.write(
        "RIM Online simulates the long-term interaction between ryegrass populations "
        "and management decisions across a crop rotation. Define a paddock, choose "
        "year-by-year actions, and compare economics, yield and weed dynamics."
    )
    st.markdown("#### Getting started")
    steps = [
        ("1", "Paddock Profile",  "Enter farm details, base yields, grain prices and rotation shares."),
        ("2", "Strategy Builder", "Set management actions year-by-year over a 10-year horizon."),
        ("3", "Results",          "Explore economics, yield penalties and ryegrass population charts."),
        ("4", "Compare A / B",    "Freeze two strategies and view them side-by-side."),
        ("5", "Export",           "Download a PDF summary or full Excel data tables."),
    ]
    for num, label, desc in steps:
        st.markdown(
            f"""
            <div class="uwa-section-card" style="display:flex;align-items:flex-start;gap:0.9rem;margin-bottom:0.5rem;">
              <div class="uwa-step-badge">{num}</div>
              <div>
                <strong style="color:var(--uwa-navy);">{label}</strong>
                <div style="color:var(--uwa-text-m);font-size:0.87rem;margin-top:0.1rem;">{desc}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with col_r:
    st.markdown("#### Navigate to")
    st.page_link("pages/1_Paddock_Profile.py",   label="→  Step 1: Paddock Profile")
    st.page_link("pages/2_Strategy.py",           label="→  Step 2: Strategy Builder")
    st.page_link("pages/3_Results_Economics.py",  label="→  Step 3: Economics")
    st.page_link("pages/3_Results_Yields.py",     label="→  Step 3: Yields")
    st.page_link("pages/3_Results_Population.py", label="→  Step 3: Population")
    st.page_link("pages/4_Export.py",             label="→  Export")

    guided = st.checkbox("Enable guided mode", value=True)
    if guided:
        st.info(
            "**Guided mode:** Complete Paddock Profile first, then Strategy. "
            "Use **Compare A** and **Compare B** to freeze scenarios before viewing Results."
        )

uwa_footer()
