from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.session import (
    init_state,
    load_profile_slot,
    profile_completeness,
    reset_profile_bundle,
    save_profile_slot,
)
from utils.save_load import save_load_controls
from utils.theme import (
    inject_uwa_theme,
    metric_row,
    section,
    uwa_footer,
    uwa_page_header,
    uwa_sidebar_logo,
)


st.set_page_config(page_title="Paddock profile | RIM Online", page_icon="🌾", layout="wide")

init_state()
inject_uwa_theme()
uwa_sidebar_logo()

uwa_page_header(
    title="Step 1 — Paddock profile",
    subtitle="Describe the paddock once: yields, prices and the parameters every "
             "strategy is measured against.",
)

slot_col, load_col, save_col, reset_col, clear_col, _ = st.columns([2, 1, 1, 1.3, 1.5, 3])
_spacer = '<div style="height:1.62rem"></div>'

with slot_col:
    profile_slot = st.selectbox(
        "Profile slot",
        options=[1, 2, 3, 4],
        format_func=lambda s: f"Slot {s}",
        key="profile_slot_pick",
    )
with load_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    if st.button("Load", use_container_width=True):
        if load_profile_slot(profile_slot):
            st.toast(f"Loaded slot {profile_slot}")
            st.rerun()
        else:
            st.toast(f"Slot {profile_slot} is empty — save a profile to it first")
with save_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    if st.button("Save", use_container_width=True):
        save_profile_slot(profile_slot)
        st.toast(f"Saved to slot {profile_slot}")
with reset_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    if st.button("Reset all", use_container_width=True):
        reset_profile_bundle()
        st.toast("Profile, prices and options reset to defaults")
        st.rerun()
with clear_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    if st.button("Clear names", use_container_width=True):
        st.session_state.confirm_clear_profile = True

st.caption(
    "Slots keep a full profile — paddock details, prices and options together — "
    "for this browser session only. Reset all does not touch them."
)

with st.expander("Keep this work"):
    save_load_controls("profile")
    st.page_link("pages/4_How_RIM_Works.py", label="How saving and loading works")

if st.session_state.get("confirm_clear_profile"):
    st.warning(
        "Clear the farm and paddock names and reset the starting seed bank? "
        "Your saved slots are not touched."
    )
    if st.button("Clear names", key="confirm_clear_profile_btn", type="primary"):
        p = st.session_state.profile_current
        p["farm_name"] = ""
        p["paddock_name"] = ""
        p["seed_bank_start"] = 20
        st.session_state.confirm_clear_profile = False
        st.toast("Names cleared")
        st.rerun()

p = st.session_state.profile_current
prices = st.session_state.prices_current
options = st.session_state.options_current

with st.form("profile_form"):
    section("Core paddock parameters")
    col_a, col_b, col_c = st.columns(3)
    farm_name = col_a.text_input("Farm name", value=p["farm_name"])
    paddock_name = col_b.text_input("Paddock name", value=p["paddock_name"])
    farm_size_ha = col_c.number_input("Farm size (ha)", min_value=1.0, value=float(p["farm_size_ha"]), step=10.0)

    col1, col2, col3, col4 = st.columns(4)
    y_wheat = col1.number_input("Base yield Wheat (t/ha)", min_value=0.0, value=float(p["base_yields"]["Wheat"]), step=0.1)
    y_barley = col2.number_input("Base yield Barley (t/ha)", min_value=0.0, value=float(p["base_yields"]["Barley"]), step=0.1)
    y_canola = col3.number_input("Base yield Canola (t/ha)", min_value=0.0, value=float(p["base_yields"]["Canola"]), step=0.1)
    y_legume = col4.number_input("Base yield Legume crop (t/ha)", min_value=0.0, value=float(p["base_yields"]["Legume crop"]), step=0.1)

    col5, col6, col7, col8 = st.columns(4)
    sheep_gm = col5.number_input("Sheep gross margin ($/DSE)", min_value=0.0, value=float(p["sheep_gm_per_dse"]), step=1.0)
    seed_bank_start = col6.select_slider("Starting ryegrass seed bank", options=[2, 20, 100], value=int(p["seed_bank_start"]))
    interest = col7.number_input("Interest rate (%)", min_value=0.0, value=float(p["interest_rate_pct"]), step=0.1)
    inflation = col8.number_input("Inflation rate (%)", min_value=0.0, value=float(p["inflation_rate_pct"]), step=0.1)

    col9, col10, col11 = st.columns(3)
    tax = col9.number_input("Tax rate (%)", min_value=0.0, max_value=60.0, value=float(p["tax_rate_pct"]), step=0.5)
    farm_area_ha = col10.number_input("Farm area for machinery repayment (ha)", min_value=1.0, value=float(p["farm_area_ha"]), step=10.0)
    cereal_share = col11.number_input("Rotation share - cereal", min_value=0.0, max_value=1.0, value=float(p["rotation_shares"]["cereal"]), step=0.05)

    col12, col13 = st.columns(2)
    canola_share = col12.number_input("Rotation share - canola", min_value=0.0, max_value=1.0, value=float(p["rotation_shares"]["canola"]), step=0.05)
    legume_share = col13.number_input("Rotation share - legume", min_value=0.0, max_value=1.0, value=float(p["rotation_shares"]["legume"]), step=0.05)

    submitted_profile = st.form_submit_button("Update Core Profile")

if submitted_profile:
    p["farm_name"] = farm_name
    p["paddock_name"] = paddock_name
    p["farm_size_ha"] = farm_size_ha
    p["farm_area_ha"] = farm_area_ha
    p["base_yields"]["Wheat"] = y_wheat
    p["base_yields"]["Barley"] = y_barley
    p["base_yields"]["Canola"] = y_canola
    p["base_yields"]["Legume crop"] = y_legume
    p["sheep_gm_per_dse"] = sheep_gm
    p["seed_bank_start"] = seed_bank_start
    p["interest_rate_pct"] = interest
    p["inflation_rate_pct"] = inflation
    p["tax_rate_pct"] = tax
    p["rotation_shares"]["cereal"] = cereal_share
    p["rotation_shares"]["canola"] = canola_share
    p["rotation_shares"]["legume"] = legume_share
    st.success("Core profile updated")

with st.form("prices_form"):
    section("Prices")
    cp1, cp2, cp3, cp4 = st.columns(4)
    prices["Wheat"] = cp1.number_input("Wheat price ($/t)", min_value=0.0, value=float(prices["Wheat"]), step=5.0)
    prices["Barley"] = cp2.number_input("Barley price ($/t)", min_value=0.0, value=float(prices["Barley"]), step=5.0)
    prices["Canola"] = cp3.number_input("Canola price ($/t)", min_value=0.0, value=float(prices["Canola"]), step=5.0)
    prices["Legume crop"] = cp4.number_input("Legume price ($/t)", min_value=0.0, value=float(prices["Legume crop"]), step=5.0)

    cc1, cc2, cc3, cc4 = st.columns(4)
    prices["cost_no_till"] = cc1.number_input("No-till cost ($/ha)", min_value=0.0, value=float(prices["cost_no_till"]), step=1.0)
    prices["cost_full_cut_extra"] = cc2.number_input("Full-cut extra cost ($/ha)", min_value=0.0, value=float(prices["cost_full_cut_extra"]), step=1.0)
    prices["cost_tickle"] = cc3.number_input("Tickle cost ($/ha)", min_value=0.0, value=float(prices["cost_tickle"]), step=1.0)
    prices["cost_high_seeding_rate_extra"] = cc4.number_input("High seeding rate extra ($/ha)", min_value=0.0, value=float(prices["cost_high_seeding_rate_extra"]), step=1.0)

    submit_prices = st.form_submit_button("Update Prices")
if submit_prices:
    st.success("Prices updated")

with st.form("options_form"):
    section("Options")
    co1, co2, co3 = st.columns(3)
    options["germination_rate"]["default"] = co1.slider("Germination no-till", 0.50, 0.95, float(options["germination_rate"]["default"]), 0.01)
    options["germination_rate"]["tickle"] = co2.slider("Germination with tickle", 0.50, 0.99, float(options["germination_rate"]["tickle"]), 0.01)
    options["natural_seed_mortality"] = co3.slider("Natural seed mortality", 0.05, 0.50, float(options["natural_seed_mortality"]), 0.01)

    cx1, cx2 = st.columns(2)
    options["stocking_rate"]["standard"] = cx1.number_input("Volunteer pasture stocking (DSE/ha)", min_value=0.0, value=float(options["stocking_rate"]["standard"]), step=0.1)
    options["stocking_rate"]["high"] = cx2.number_input("High intensity stocking (DSE/ha)", min_value=0.0, value=float(options["stocking_rate"]["high"]), step=0.1)

    submit_options = st.form_submit_button("Update Options")
if submit_options:
    st.success("Options updated")

section("Is this profile ready?")

scores = profile_completeness()
rotation_sum = (
    p["rotation_shares"]["cereal"]
    + p["rotation_shares"]["canola"]
    + p["rotation_shares"]["legume"]
)

targets = (("Paddock", scores["profile"], 7), ("Prices", scores["prices"], 10),
           ("Options", scores["options"], 8))
metric_row([
    {"label": f"{name} fields set", "value": f"{filled}",
     "unit": f"of {target} needed",
     "accent": "margin" if filled >= target else "rye",
     "note": "Ready" if filled >= target else f"{target - filled} still to fill in"}
    for name, filled, target in targets
] + [
    {"label": "Rotation shares", "value": f"{rotation_sum:.2f}",
     "accent": "margin" if rotation_sum >= 1.0 else "rye",
     "note": "Adds to 1.00" if rotation_sum >= 1.0 else "Should add to at least 1.00"},
])

if rotation_sum < 1.0:
    st.warning(
        f"Cereal, canola and legume shares add to {rotation_sum:.2f}. "
        "Raise them to at least 1.00 so the rotation accounts for the whole paddock."
    )

st.page_link("pages/2_Strategy.py", label="Continue to the strategy builder")

uwa_footer()
