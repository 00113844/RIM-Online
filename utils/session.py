from __future__ import annotations

from copy import deepcopy

import streamlit as st

from rim.defaults import DEFAULT_OPTIONS, DEFAULT_PRICES, DEFAULT_PROFILE, build_default_strategy
from rim.engine import simulate_strategy


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


def reset_profile_bundle() -> None:
    st.session_state.profile_current = deepcopy(DEFAULT_PROFILE)
    st.session_state.prices_current = deepcopy(DEFAULT_PRICES)
    st.session_state.options_current = deepcopy(DEFAULT_OPTIONS)


def save_profile_slot(slot: int) -> None:
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
    return True


def reset_strategy_current() -> None:
    st.session_state.strategy_current = build_default_strategy(10)


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

SAVE_FORMAT_VERSION = 1


def export_bundle() -> dict:
    """Everything needed to restore this session's work, as plain JSON."""
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
    st.session_state.strategy_current = deepcopy(data["strategy"])

    # Slot keys come back from JSON as strings.
    if isinstance(data.get("profile_slots"), dict):
        st.session_state.profile_slots = {
            int(k): v for k, v in data["profile_slots"].items()
        }
    if isinstance(data.get("strategy_slots"), dict):
        st.session_state.strategy_slots = {
            int(k): v for k, v in data["strategy_slots"].items()
        }

    st.session_state.results_current = None
    years = len(st.session_state.strategy_current)
    return True, f"Loaded a {years}-year strategy and its paddock profile."
