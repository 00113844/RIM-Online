"""The plan has to make sense before it is worth simulating.

Results computed from a plan the model half-ignores are worse than no results:
they look authoritative and quietly answer a different question from the one
asked. So the simulation is gated. While anything in the plan is inconsistent
the numbers are not produced at all, and the panel says what to fix.

Why not disable the cells instead? ``st.data_editor`` can disable a whole
column but never one cell, so it cannot express "grazing is available in year 4
but not year 3". Rebuilding the grid out of individual widgets would mean about
110 of them re-rendering on every keystroke, which is the one change here that
really would be slow. The grid stays; the gate and the guided year editor carry
the logic instead.
"""
from __future__ import annotations

import streamlit as st

from utils.applicability import FIELD_LABEL, neutralise

# What to do about each kind of problem, in the user's terms.
REMEDY = {
    "Knock-down": "set it to None, or sow delayed so the knock-down has something to catch",
    "Pre-emergent": "set it to No — there is no seeding pass to carry it",
    "Grazing": "set it to None, or change the year to a pasture",
    "Harvest control": "set it to Standard, or change the year to a crop",
    "Post-emergent": "set it to No",
    "Sowing rate": "leave it — the model does not read it in this year",
    "Sowing system": "leave it — the model does not read it in this year",
}


def problems(strategy_rows, custom=None) -> list[dict]:
    """Every decision in the plan the model cannot act on.

    ``custom`` carries a user's own option definitions when they have loaded
    any, so their names are recognised rather than reported as impossible. It
    is a parameter rather than a session lookup so this stays callable outside
    Streamlit -- the command-line runner checks a plan the same way.
    """
    return neutralise(strategy_rows, custom)[1]


def problem_panel(found: list[dict], *, on_fix_key: str) -> bool:
    """Render the blocking panel. Returns True if the caller should apply the fix.

    Each problem names the year, the choice, why it cannot work, and what to do
    about it. Grouping is by the decision rather than by year, so one mistake
    repeated across a decade reads as one thing to fix.
    """
    if not found:
        return False

    grouped: dict[tuple, list[int]] = {}
    for item in found:
        key = (item["field"], str(item["choice"]), item["reason"], item["source"])
        grouped.setdefault(key, []).append(item["year"])

    count = len(grouped)
    st.markdown(
        f'<div class="rim-gate">'
        f'<div class="rim-gate-head">'
        f'<span class="rim-gate-count">{count}</span>'
        f"<span>{'This decision cannot' if count == 1 else 'These decisions cannot'} "
        "be simulated</span></div>"
        "<p class=\"rim-gate-lede\">The model would ignore "
        f"{'it' if count == 1 else 'them'} and still produce numbers, which would "
        "answer a different question from the one you asked. Resolve "
        f"{'it' if count == 1 else 'them'} to see results.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    rows = []
    for (field, choice, reason, source), years in sorted(
        grouped.items(), key=lambda kv: min(kv[1])
    ):
        when = (
            f"Year {years[0]}" if len(years) == 1
            else f"Years {', '.join(str(y) for y in sorted(years))}"
        )
        remedy = REMEDY.get(field, "change it to the inert option")
        rows.append(
            '<div class="rim-problem">'
            f'<div class="rim-problem-when">{when}</div>'
            "<div class=\"rim-problem-body\">"
            f'<div class="rim-problem-what"><b>{field}: {choice}</b></div>'
            f'<div class="rim-problem-why">{reason}</div>'
            f'<div class="rim-problem-fix">Fix: {remedy}</div>'
            f'<div class="rim-problem-src">{source}</div>'
            "</div></div>"
        )
    st.markdown(f'<div class="rim-problems">{"".join(rows)}</div>', unsafe_allow_html=True)

    fix_col, hint_col = st.columns([1, 3])
    with fix_col:
        pressed = st.button(
            f"Clear {'it' if count == 1 else 'all ' + str(count)} and run",
            type="primary",
            use_container_width=True,
            key=on_fix_key,
        )
    with hint_col:
        st.markdown(
            '<div style="padding-top:0.45rem;font-size:0.82rem;color:var(--muted)">'
            "Or edit the plan yourself — in the grid above, or year by year below "
            "where the impossible choices are switched off."
            "</div>",
            unsafe_allow_html=True,
        )
    return pressed


def held_results_notice(found: list[dict]) -> None:
    """Stand in for results on a page that cannot show them."""
    count = len({(f["field"], str(f["choice"])) for f in found})
    years = sorted({f["year"] for f in found})
    st.markdown(
        '<div class="rim-gate rim-gate-quiet">'
        '<div class="rim-gate-head">'
        f'<span class="rim-gate-count">{count}</span>'
        "<span>No results yet</span></div>"
        '<p class="rim-gate-lede">The plan has '
        f"{count} decision{'s' if count != 1 else ''} the model cannot act on, in "
        f"year{'s' if len(years) != 1 else ''} {', '.join(str(y) for y in years)}. "
        "Resolve them on the Strategy page and the results appear here.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Strategy.py", label="Go to the strategy builder")
