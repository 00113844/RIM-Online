from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from utils.session import (
    commit_profile_widgets,
    init_state,
    load_profile_slot,
    profile_completeness,
    profile_slot_label,
    profile_slot_labels,
    profile_widget_key,
    reset_profile_widgets,
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


# These run as `on_click` callbacks rather than in the script body, because the
# picker's labels name the farm in each slot and so have to be right the moment
# it draws. A button handled in the body acts *after* the picker has already
# rendered; Streamlit then shows the label from before the save, and only
# catches up on the next interaction. Callbacks run before the body, so the
# labels below are computed from a session state that already reflects the click.
def _save_slot() -> None:
    slot = st.session_state.profile_slot_pick
    save_profile_slot(slot)
    st.session_state.profile_slot_message = f"Saved to {profile_slot_label(slot)}"


def _load_slot() -> None:
    slot = st.session_state.profile_slot_pick
    st.session_state.profile_slot_message = (
        f"Loaded {profile_slot_label(slot)}"
        if load_profile_slot(slot)
        else f"Slot {slot} is empty — save a profile to it first"
    )


def _reset_all() -> None:
    reset_profile_bundle()
    st.session_state.profile_slot_message = "Profile, prices and options reset to defaults"


slot_labels = profile_slot_labels()

with slot_col:
    profile_slot = st.selectbox(
        "Profile slot",
        options=list(slot_labels),
        format_func=slot_labels.__getitem__,
        key="profile_slot_pick",
    )
with load_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    st.button("Load", width="stretch", on_click=_load_slot)
with save_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    st.button("Save", width="stretch", on_click=_save_slot)
with reset_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    st.button("Reset all", width="stretch", on_click=_reset_all)
with clear_col:
    st.markdown(_spacer, unsafe_allow_html=True)
    if st.button("Clear names", width="stretch"):
        st.session_state.confirm_clear_profile = True

_message = st.session_state.pop("profile_slot_message", None)
if _message:
    st.toast(_message)

# What every slot holds, spelled out. The picker's dropdown carries the same
# labels, but Streamlit keeps a keyed widget's *rendered* label when only its
# option strings change, so the closed box can still read "empty" for a moment
# after a save. This line is plain markdown and is right on every run.
st.caption(" · ".join(slot_labels.values()))

st.caption(
    "Slots keep a full profile — paddock details, prices and options together — "
    "for this browser session only. Changes apply as you make them and Save "
    "captures the page as it stands. Reset all returns the page to defaults "
    "without touching your slots."
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
        reset_profile_widgets()
        st.session_state.confirm_clear_profile = False
        st.toast("Names cleared")
        st.rerun()

p = st.session_state.profile_current
prices = st.session_state.prices_current
options = st.session_state.options_current

# No st.form here, deliberately. A form withholds its widgets' values from
# session state until its submit button is pressed, and the slot toolbar sits
# above these fields -- so Save captured the last submitted values rather than
# what was on screen, and a farm renamed but not "updated" was saved under its
# old name. Every widget below writes as it changes, so the page and the bundle
# cannot disagree.
section("Core paddock parameters")
col_a, col_b, col_c = st.columns(3)
col_a.text_input("Farm name", value=p["farm_name"], key=profile_widget_key("pf_farm_name"))
col_b.text_input("Paddock name", value=p["paddock_name"], key=profile_widget_key("pf_paddock_name"))
col_c.number_input("Farm size (ha)", min_value=1.0, value=float(p["farm_size_ha"]), step=10.0, key=profile_widget_key("pf_farm_size_ha"))

col1, col2, col3, col4 = st.columns(4)
col1.number_input("Base yield Wheat (t/ha)", min_value=0.0, value=float(p["base_yields"]["Wheat"]), step=0.1, key=profile_widget_key("pf_y_wheat"))
col2.number_input("Base yield Barley (t/ha)", min_value=0.0, value=float(p["base_yields"]["Barley"]), step=0.1, key=profile_widget_key("pf_y_barley"))
col3.number_input("Base yield Canola (t/ha)", min_value=0.0, value=float(p["base_yields"]["Canola"]), step=0.1, key=profile_widget_key("pf_y_canola"))
col4.number_input("Base yield Legume crop (t/ha)", min_value=0.0, value=float(p["base_yields"]["Legume crop"]), step=0.1, key=profile_widget_key("pf_y_legume"))

col5, col6, col7, col8 = st.columns(4)
col5.number_input("Sheep gross margin ($/DSE)", min_value=0.0, value=float(p["sheep_gm_per_dse"]), step=1.0, key=profile_widget_key("pf_sheep_gm"))
col6.select_slider("Starting ryegrass seed bank", options=[2, 20, 100], value=int(p["seed_bank_start"]), key=profile_widget_key("pf_seed_bank_start"))
col7.number_input("Interest rate (%)", min_value=0.0, value=float(p["interest_rate_pct"]), step=0.1, key=profile_widget_key("pf_interest"))
col8.number_input("Inflation rate (%)", min_value=0.0, value=float(p["inflation_rate_pct"]), step=0.1, key=profile_widget_key("pf_inflation"))

col9, col10, col11 = st.columns(3)
col9.number_input("Tax rate (%)", min_value=0.0, max_value=60.0, value=float(p["tax_rate_pct"]), step=0.5, key=profile_widget_key("pf_tax"))
col10.number_input("Farm area for machinery repayment (ha)", min_value=1.0, value=float(p["farm_area_ha"]), step=10.0, key=profile_widget_key("pf_farm_area_ha"))
col11.number_input("Rotation share - cereal", min_value=0.0, max_value=1.0, value=float(p["rotation_shares"]["cereal"]), step=0.05, key=profile_widget_key("pf_share_cereal"))

col12, col13 = st.columns(2)
col12.number_input("Rotation share - canola", min_value=0.0, max_value=1.0, value=float(p["rotation_shares"]["canola"]), step=0.05, key=profile_widget_key("pf_share_canola"))
col13.number_input("Rotation share - legume", min_value=0.0, max_value=1.0, value=float(p["rotation_shares"]["legume"]), step=0.05, key=profile_widget_key("pf_share_legume"))

section("Prices")
cp1, cp2, cp3, cp4 = st.columns(4)
cp1.number_input("Wheat price ($/t)", min_value=0.0, value=float(prices["Wheat"]), step=5.0, key=profile_widget_key("px_wheat"))
cp2.number_input("Barley price ($/t)", min_value=0.0, value=float(prices["Barley"]), step=5.0, key=profile_widget_key("px_barley"))
cp3.number_input("Canola price ($/t)", min_value=0.0, value=float(prices["Canola"]), step=5.0, key=profile_widget_key("px_canola"))
cp4.number_input("Legume price ($/t)", min_value=0.0, value=float(prices["Legume crop"]), step=5.0, key=profile_widget_key("px_legume"))

cc1, cc2, cc3, cc4 = st.columns(4)
cc1.number_input("No-till cost ($/ha)", min_value=0.0, value=float(prices["cost_no_till"]), step=1.0, key=profile_widget_key("px_cost_no_till"))
cc2.number_input("Full-cut extra cost ($/ha)", min_value=0.0, value=float(prices["cost_full_cut_extra"]), step=1.0, key=profile_widget_key("px_cost_full_cut_extra"))
cc3.number_input("Tickle cost ($/ha)", min_value=0.0, value=float(prices["cost_tickle"]), step=1.0, key=profile_widget_key("px_cost_tickle"))
cc4.number_input("High seeding rate extra ($/ha)", min_value=0.0, value=float(prices["cost_high_seeding_rate_extra"]), step=1.0, key=profile_widget_key("px_cost_high_seeding_rate_extra"))

section("Options")
co1, co2, co3 = st.columns(3)
co1.slider("Germination no-till", 0.50, 0.95, float(options["germination_rate"]["default"]), 0.01, key=profile_widget_key("op_germ_default"))
co2.slider("Germination with tickle", 0.50, 0.99, float(options["germination_rate"]["tickle"]), 0.01, key=profile_widget_key("op_germ_tickle"))
co3.slider("Natural seed mortality", 0.05, 0.50, float(options["natural_seed_mortality"]), 0.01, key=profile_widget_key("op_seed_mortality"))

cx1, cx2 = st.columns(2)
cx1.number_input("Volunteer pasture stocking (DSE/ha)", min_value=0.0, value=float(options["stocking_rate"]["standard"]), step=0.1, key=profile_widget_key("op_stock_standard"))
cx2.number_input("High intensity stocking (DSE/ha)", min_value=0.0, value=float(options["stocking_rate"]["high"]), step=0.1, key=profile_widget_key("op_stock_high"))

commit_profile_widgets()
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
