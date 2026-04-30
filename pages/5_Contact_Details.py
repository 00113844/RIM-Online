from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.theme import inject_uwa_theme, uwa_page_header, uwa_footer, uwa_sidebar_logo


inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Contact Details",
    subtitle="Get in touch with the RIM team at AHRI",
    icon="📬",
)

st.markdown("### Contact")
st.markdown(
    "For queries on RIM, please contact "
    "[lisa.mayer@uwa.edu.au](mailto:lisa.mayer@uwa.edu.au)."
)

st.markdown("### More Information")
st.markdown(
    "For more information on how RIM can be used as a decision-support tool please visit "
    "[AHRI – RIM: Ryegrass Integrated Management]"
    "(https://www.ahri.uwa.edu.au/herbicide-resistance/our-research/wim-weed-management-models/"
    "rim-ryegrass-integrated-management/)."
)

st.markdown("### Citation Guidance")
st.write(
    "Please refer to the original publication and associated peer-reviewed publications on "
    "www.ahri.uwa.edu.au."
)
st.markdown("[www.ahri.uwa.edu.au](https://www.ahri.uwa.edu.au)")

st.markdown("### About RIM")
st.write(
    "RIM was developed and updated by the AHRI team."
)

uwa_footer()
