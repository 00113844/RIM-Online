"""Shared furniture for the three results pages.

All three answer the same question in different currencies — what did this
decade do? — so they share one shape: what you are looking at, the headline
figures, then the detail. The A/B mechanic works identically on each.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from utils.session import ensure_current_results
from utils.validation import held_results_notice, problems


def scale_toggle(key: str = "results_scale_mode") -> bool:
    """Auto or the workbook's fixed axis limits. Returns True when fixed."""
    left, _ = st.columns([1, 3])
    with left:
        current = st.session_state.get(key, "Auto")
        st.session_state[key] = st.radio(
            "Chart scale",
            ["Auto", "Fixed"],
            index=1 if current == "Fixed" else 0,
            horizontal=True,
            key=f"{key}_widget",
            help="Fixed uses the same axis limits as the Excel workbook, so runs "
                 "can be compared by eye.",
        )
    return st.session_state[key] == "Fixed"


def views() -> list[tuple[str, dict[str, Any]]]:
    """What to render: A and B when both are held, otherwise the current plan.

    Held strategies were valid when they were held, so they always show. The
    current plan only shows once it is consistent — otherwise the page stops
    with a notice, because numbers from a plan the model half-ignores answer a
    different question from the one asked.
    """
    a = st.session_state.get("results_A")
    b = st.session_state.get("results_B")
    if a is not None and b is not None:
        return [("Strategy A", a), ("Strategy B", b)]

    found = problems(st.session_state.strategy_current)
    if found:
        held_results_notice(found)
        st.stop()

    return [("Current plan", ensure_current_results())]


def comparison_note() -> None:
    """Say plainly which strategies are on screen, and how to get two."""
    a = st.session_state.get("results_A") is not None
    b = st.session_state.get("results_B") is not None
    if a and b:
        st.caption("Comparing the two strategies you held on the Strategy page.")
    elif a or b:
        held = "A" if a else "B"
        missing = "B" if a else "A"
        st.caption(
            f"Showing your current plan. You are holding {held} — hold {missing} "
            "on the Strategy page to compare them side by side."
        )
    else:
        st.caption(
            "Showing your current plan. Hold two strategies as A and B on the "
            "Strategy page to compare them side by side."
        )
