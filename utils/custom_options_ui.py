"""Loading, showing and clearing a user's own option definitions.

This panel lives on the **Strategy** page, beside the editor whose *Other*
dropdowns it fills. The pack itself is stored in the options bundle, so it saves
inside the same ``.rim.json`` as everything else and reaches the command-line
runner -- but where the data lives and where the control lives are separate
questions, and the control belongs with the thing it changes.

RIM's spreadsheet keeps four such options because ``1.Profile`` C32:C35 is four
cells. There is no such limit here; see :mod:`rim.custom_options`.

The pack never becomes process-wide state: one Streamlit server serves many
browsers, and one user's options must not appear in another's session.
"""
from __future__ import annotations

import json

import streamlit as st

from rim import custom_options as custom
from utils.session import reset_editor_widgets

EXAMPLE = {
    "format": custom.FORMAT,
    "version": custom.FORMAT_VERSION,
    "options": [
        {
            "for": "spring",
            "name": "Spring grazing crash",
            "control": {"default": 0.55, "Canola": 0.0},
            "cost_per_ha": {"default": 12.0},
        },
        {
            "for": "spring",
            "name": "Steam weeding",
            "control": {"default": 0.80},
            "cost_per_ha": {"default": 90.0},
        },
        {
            "for": "harvest",
            "name": "Weed seed impact mill",
            "control": {"default": 0.95},
            "cost_per_ha": {"default": 30.0, "Legume crop": 26.0},
        },
    ],
}


def custom_options_controls(key: str = "custom_options") -> None:
    """Upload, inspect and clear a user's own spring and harvest options."""
    st.caption(
        "Describe your own spring and harvest operations in a JSON file and "
        "load it here. They appear in the **Other** dropdowns above, priced and "
        "rated the way you set them. RIM's spreadsheet keeps two of each; there "
        "is no such limit here, so define as many as you need. The file travels "
        "with the scenario, so saving your work keeps it — and the same file "
        "works with the command-line runner."
    )

    loaded = st.session_state.options_current.get("custom_options")
    if loaded:
        described = custom.describe(loaded)
        st.success(f"Loaded {len(described)} option(s):\n\n" + "\n\n".join(
            f"- {line}" for line in described
        ))
        if len(described) > custom.MANY_OPTIONS:
            st.warning(
                f"{len(described)} options is a long dropdown to scroll. Nothing "
                "stops you, but at this scale a tool that builds and compares "
                "packs would serve you better than a list."
            )
        if st.button("Clear these", key=f"{key}_clear"):
            st.session_state.options_current.pop("custom_options", None)
            st.session_state.results_current = None
            reset_editor_widgets()
            st.toast("Your own options were cleared")
            st.rerun()
    else:
        st.info("None loaded — the **Other** dropdowns hold RIM's own two "
                "spring and two harvest placeholders.")

    uploaded = st.file_uploader(
        "Load an options file",
        type=["json"],
        key=f"{key}_upload",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        try:
            payload = json.loads(uploaded.getvalue().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            st.error("That file is not readable JSON.")
        else:
            try:
                parsed = custom.parse(payload)
            except custom.CustomOptionError as problem:
                # The message names the slot and the field, so it is worth
                # showing verbatim rather than replacing with "invalid file".
                st.error(str(problem))
            else:
                st.session_state.options_current["custom_options"] = parsed
                st.session_state.results_current = None
                reset_editor_widgets()
                st.toast(f"Loaded {sum(len(v) for v in parsed.values())} "
                         f"option(s) of your own")
                st.rerun()

    st.download_button(
        "Download an example to edit",
        data=json.dumps(EXAMPLE, indent=2).encode("utf-8"),
        file_name="rim-custom-options.json",
        mime="application/json",
        key=f"{key}_example",
    )
    st.caption(
        "Each option needs `for` (`spring` or `harvest`), a `name`, a `control` "
        "and a `cost_per_ha`. `control` is the share of ryegrass it kills, 0 to "
        "1; `cost_per_ha` is dollars per hectare. Both take a `default` plus any "
        "per-crop exceptions. A control of 0 for a crop means the option does "
        "nothing there, so it stops being offered for that crop. Loading any "
        "spring options replaces RIM's two spring placeholders, and likewise "
        "for harvest."
    )
