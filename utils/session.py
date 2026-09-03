from __future__ import annotations

from copy import deepcopy

import streamlit as st

from rim.defaults import DEFAULT_OPTIONS, DEFAULT_PRICES, DEFAULT_PROFILE, build_default_strategy
from rim.engine import simulate_strategy
from rim import control_options
from rim.herbicides import upgrade_strategy


def init_state() -> None:
    if "profile_current" not in st.session_state:
        st.session_state.profile_current = deepcopy(DEFAULT_PROFILE)
    if "prices_current" not in st.session_state:
        st.session_state.prices_current = deepcopy(DEFAULT_PRICES)
    if "options_current" not in st.session_state:
        st.session_state.options_current = deepcopy(DEFAULT_OPTIONS)
    if "strategy_current" not in st.session_state:
        st.session_state.strategy_current = build_default_strategy(10)

    if "profile_slots" not in st.session_state:
        st.session_state.profile_slots = {1: None, 2: None, 3: None, 4: None}

    if "strategy_slots" not in st.session_state:
        st.session_state.strategy_slots = {0: deepcopy(st.session_state.strategy_current), 1: None, 2: None, 3: None, 4: None, 5: None, 6: None}

    if "results_current" not in st.session_state:
        st.session_state.results_current = None
    if "results_A" not in st.session_state:
        st.session_state.results_A = None
    if "results_B" not in st.session_state:
        st.session_state.results_B = None

    if "strategy_scale_mode" not in st.session_state:
        st.session_state.strategy_scale_mode = "Auto"
    if "results_scale_mode" not in st.session_state:
        st.session_state.results_scale_mode = "Auto"
    if "strategy_graph_mode" not in st.session_state:
        st.session_state.strategy_graph_mode = 1


# ── The paddock profile form ──────────────────────────────────────────────────
# Every widget on the profile page, and where its value belongs. Streamlit forms
# hold their widgets' values until the form is submitted, so the page and the
# bundle drift apart between submits: a farm name typed but not submitted is on
# screen and not in state. Saving a slot in that gap captured the *previous*
# farm, which is what made slots look like they saved to the wrong place.
#
# The mapping is the fix and the record of it. Save commits through it, so a slot
# always holds what the page shows; Load clears the keys, so the form re-seeds
# from what was loaded instead of writing its stale values back.
PROFILE_WIDGETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "pf_farm_name": ("profile", ("farm_name",)),
    "pf_paddock_name": ("profile", ("paddock_name",)),
    "pf_farm_size_ha": ("profile", ("farm_size_ha",)),
    "pf_farm_area_ha": ("profile", ("farm_area_ha",)),
    "pf_y_wheat": ("profile", ("base_yields", "Wheat")),
    "pf_y_barley": ("profile", ("base_yields", "Barley")),
    "pf_y_canola": ("profile", ("base_yields", "Canola")),
    "pf_y_legume": ("profile", ("base_yields", "Legume crop")),
    "pf_sheep_gm": ("profile", ("sheep_gm_per_dse",)),
    "pf_seed_bank_start": ("profile", ("seed_bank_start",)),
    "pf_interest": ("profile", ("interest_rate_pct",)),
    "pf_inflation": ("profile", ("inflation_rate_pct",)),
    "pf_tax": ("profile", ("tax_rate_pct",)),
    "pf_share_cereal": ("profile", ("rotation_shares", "cereal")),
    "pf_share_canola": ("profile", ("rotation_shares", "canola")),
    "pf_share_legume": ("profile", ("rotation_shares", "legume")),
    "px_wheat": ("prices", ("Wheat",)),
    "px_barley": ("prices", ("Barley",)),
    "px_canola": ("prices", ("Canola",)),
    "px_legume": ("prices", ("Legume crop",)),
    "px_cost_no_till": ("prices", ("cost_no_till",)),
    "px_cost_full_cut_extra": ("prices", ("cost_full_cut_extra",)),
    "px_cost_tickle": ("prices", ("cost_tickle",)),
    "px_cost_high_seeding_rate_extra": ("prices", ("cost_high_seeding_rate_extra",)),
    "op_germ_default": ("options", ("germination_rate", "default")),
    "op_germ_tickle": ("options", ("germination_rate", "tickle")),
    "op_seed_mortality": ("options", ("natural_seed_mortality",)),
    "op_stock_standard": ("options", ("stocking_rate", "standard")),
    "op_stock_high": ("options", ("stocking_rate", "high")),
}


# A widget's identity is its key. Deleting the key from session state makes the
# *server* forget the value, but the browser still holds a widget with that same
# id and sends its old value straight back -- so a loaded slot appeared not to
# load. Putting a generation number in the key changes the identity instead, and
# the browser draws a genuinely new widget seeded from `value=`.
PROFILE_WIDGET_GENERATION = "profile_widget_generation"


def profile_widget_key(name: str) -> str:
    """The session-state key a profile field currently answers to."""
    return f"{name}__{st.session_state.get(PROFILE_WIDGET_GENERATION, 0)}"


def commit_profile_widgets() -> None:
    """Push what the profile page shows into the current bundle.

    Fields not yet rendered this session are absent from session state and are
    skipped, so this is safe to call before the page has ever been opened.
    """
    for name, (bundle, path) in PROFILE_WIDGETS.items():
        key = profile_widget_key(name)
        if key not in st.session_state:
            continue
        target = st.session_state[f"{bundle}_current"]
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = st.session_state[key]


def reset_profile_widgets() -> None:
    """Retire the profile page's fields so they re-seed from the bundle.

    The counterpart of :func:`utils.session.reset_editor_widgets` for the
    profile page. Call it from anywhere that replaces the bundle from outside
    the fields — loading a slot or a file, or resetting to defaults.
    """
    generation = st.session_state.get(PROFILE_WIDGET_GENERATION, 0)
    for name in PROFILE_WIDGETS:
        st.session_state.pop(f"{name}__{generation}", None)
    st.session_state[PROFILE_WIDGET_GENERATION] = generation + 1


def describe_profile(profile: dict) -> str:
    """How a profile identifies itself in a slot label.

    Derived rather than stored, so renaming the farm cannot leave a slot
    labelled with a name that is no longer anywhere in the profile.
    """
    parts = [
        str(profile.get(field) or "").strip()
        for field in ("farm_name", "paddock_name")
    ]
    named = " · ".join(part for part in parts if part)
    return named or "unnamed"


def profile_slot_label(slot: int) -> str:
    """"Slot 2 — Broomehill · North Paddock", or that it is still empty."""
    bundle = st.session_state.profile_slots.get(slot)
    if not bundle:
        return f"Slot {slot} — empty"
    return f"Slot {slot} — {describe_profile(bundle['profile'])}"


def profile_slot_labels() -> dict[int, str]:
    """Every slot's label, resolved once.

    The picker formats through this mapping rather than calling
    :func:`profile_slot_label` per option, so its ``format_func`` is a plain
    lookup with no hidden read of session state behind it.
    """
    return {slot: profile_slot_label(slot) for slot in st.session_state.profile_slots}


def custom_options() -> dict | None:
    """This session's own option definitions, if a pack has been loaded.

    Kept in the options bundle rather than anywhere module-level: one Streamlit
    server serves many browsers, and one user's definitions must never appear in
    another's session.
    """
    return control_options.custom_from(st.session_state.options_current)


def snapshot_profile_bundle() -> dict:
    return {
        "profile": deepcopy(st.session_state.profile_current),
        "prices": deepcopy(st.session_state.prices_current),
        "options": deepcopy(st.session_state.options_current),
    }


def load_profile_bundle(bundle: dict) -> None:
    st.session_state.profile_current = deepcopy(bundle["profile"])
    st.session_state.prices_current = deepcopy(bundle["prices"])
    st.session_state.options_current = deepcopy(bundle["options"])
    reset_profile_widgets()


def reset_profile_bundle() -> None:
    st.session_state.profile_current = deepcopy(DEFAULT_PROFILE)
    st.session_state.prices_current = deepcopy(DEFAULT_PRICES)
    st.session_state.options_current = deepcopy(DEFAULT_OPTIONS)
    reset_profile_widgets()


def save_profile_slot(slot: int) -> None:
    """Save what the page shows, including edits not yet submitted."""
    commit_profile_widgets()
    st.session_state.profile_slots[slot] = snapshot_profile_bundle()


def load_profile_slot(slot: int) -> bool:
    bundle = st.session_state.profile_slots.get(slot)
    if not bundle:
        return False
    load_profile_bundle(bundle)
    return True


def save_strategy_slot(slot: int) -> None:
    st.session_state.strategy_slots[slot] = deepcopy(st.session_state.strategy_current)


def load_strategy_slot(slot: int) -> bool:
    strategy = st.session_state.strategy_slots.get(slot)
    if strategy is None:
        return False
    st.session_state.strategy_current = deepcopy(strategy)
    reset_editor_widgets()
    return True


def reset_strategy_current() -> None:
    st.session_state.strategy_current = build_default_strategy(10)
    reset_editor_widgets()


# Widget keys owned by the two strategy editors. Streamlit honours a widget's
# initial value only when the widget is first created; after that its stored
# value wins. So an editor that was off screen when the plan changed still holds
# the old values, and re-applies them the moment it renders again.
STRATEGY_GRID_KEY = "strategy_editor"
YEAR_EDITOR_PREFIX = "yr_"
# Which year you happen to be looking at is view state, not plan data. Clearing
# it would throw the user back to year 1 every time the plan changed.
YEAR_EDITOR_KEEP = {"yr_pick", "yr_year_index"}


def reset_editor_widgets() -> None:
    """Forget both editors' widget state so they re-seed from the current plan.

    Call this from anywhere that changes ``strategy_current`` from outside an
    editor — loading a slot or a file, clearing the plan, or the gate's fix
    button. Without it the change appears to be undone as soon as the other
    editor renders.
    """
    stale = [
        key for key in st.session_state
        if key not in YEAR_EDITOR_KEEP
        and (key == STRATEGY_GRID_KEY or str(key).startswith(YEAR_EDITOR_PREFIX))
    ]
    for key in stale:
        del st.session_state[key]


def profile_completeness() -> dict:
    p = st.session_state.profile_current
    prices = st.session_state.prices_current
    options = st.session_state.options_current

    profile_fields = [
        p.get("farm_name", ""),
        p.get("paddock_name", ""),
        p.get("farm_size_ha", 0),
        p.get("farm_area_ha", 0),
        p.get("interest_rate_pct", 0),
        p.get("inflation_rate_pct", 0),
        p.get("tax_rate_pct", 0),
        p.get("seed_bank_start", 0),
        p.get("sheep_gm_per_dse", 0),
    ]
    profile_score = sum(1 for x in profile_fields if x not in ("", None, 0))

    prices_score = sum(1 for _, v in prices.items() if not isinstance(v, dict) and v not in ("", None, 0))
    options_score = sum(1 for _, v in options.items() if v not in (None, ""))

    return {
        "profile": profile_score,
        "prices": prices_score,
        "options": options_score,
    }


def compute_current_results() -> dict:
    result = simulate_strategy(
        profile=st.session_state.profile_current,
        prices=st.session_state.prices_current,
        options=st.session_state.options_current,
        strategy_rows=st.session_state.strategy_current,
    )
    st.session_state.results_current = result
    return result


def ensure_current_results() -> dict:
    if st.session_state.results_current is None:
        return compute_current_results()
    return st.session_state.results_current


def freeze_results(slot: str) -> None:
    result = ensure_current_results()
    if slot == "A":
        st.session_state.results_A = deepcopy(result)
    if slot == "B":
        st.session_state.results_B = deepcopy(result)


# ── Saving to a file ──────────────────────────────────────────────────────────
# Slots live in st.session_state, which is per browser session and held in the
# server's memory: closing the tab or restarting the server loses them. These
# helpers are the only way to keep work beyond a session.

# 2 named the herbicides and split post_emergent into the workbook's three
# slots. 3 added the three decisions RIM has that the app lacked -- spring
# swathe, spring others, harvest others. 4 gave every option a readable name in
# place of the workbook's abbreviation. Older files still load, and always
# will: every name any version used is an alias in rim.control_options, so
# rim.herbicides.upgrade_strategy resolves rather than translates.
SAVE_FORMAT_VERSION = 4


def export_bundle() -> dict:
    """Everything needed to restore this session's work, as plain JSON.

    Commits the profile page's pending edits first, for the same reason
    :func:`save_profile_slot` does: the file should hold what the page shows.
    """
    commit_profile_widgets()
    return {
        "format": "rim-online-save",
        "version": SAVE_FORMAT_VERSION,
        "profile": deepcopy(st.session_state.profile_current),
        "prices": deepcopy(st.session_state.prices_current),
        "options": deepcopy(st.session_state.options_current),
        "strategy": deepcopy(st.session_state.strategy_current),
        "profile_slots": deepcopy(st.session_state.profile_slots),
        "strategy_slots": deepcopy(st.session_state.strategy_slots),
    }


def export_bytes() -> bytes:
    import json
    return json.dumps(export_bundle(), indent=2, default=str).encode("utf-8")


def import_bundle(data: dict) -> tuple[bool, str]:
    """Restore a saved file. Returns (ok, message) for the caller to show."""
    if not isinstance(data, dict) or data.get("format") != "rim-online-save":
        return False, "That is not a RIM Online save file."
    if int(data.get("version", 0)) > SAVE_FORMAT_VERSION:
        return False, (
            f"That file was written by a newer version of RIM Online "
            f"(format {data['version']}, this build reads {SAVE_FORMAT_VERSION})."
        )

    for key in ("profile", "prices", "options", "strategy"):
        if key not in data:
            return False, f"The file is missing its {key} section."

    st.session_state.profile_current = deepcopy(data["profile"])
    st.session_state.prices_current = deepcopy(data["prices"])
    st.session_state.options_current = deepcopy(data["options"])
    st.session_state.strategy_current = upgrade_strategy(
        deepcopy(data["strategy"]),
        control_options.custom_from(st.session_state.options_current),
    )

    # Slot keys come back from JSON as strings.
    if isinstance(data.get("profile_slots"), dict):
        st.session_state.profile_slots = {
            int(k): v for k, v in data["profile_slots"].items()
        }
    if isinstance(data.get("strategy_slots"), dict):
        st.session_state.strategy_slots = {
            int(k): (upgrade_strategy(
                v, control_options.custom_from(st.session_state.options_current))
                if v else v)
            for k, v in data["strategy_slots"].items()
        }

    st.session_state.results_current = None
    reset_editor_widgets()
    reset_profile_widgets()
    years = len(st.session_state.strategy_current)
    message = f"Loaded a {years}-year strategy and its paddock profile."
    if int(data.get("version", 1)) < SAVE_FORMAT_VERSION:
        message += (
            " It was saved against an older vocabulary and has been carried "
            "across to the workbook’s own — check the weed-control columns."
        )
    return True, message
