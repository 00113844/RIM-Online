"""Loading, showing and clearing a user's own option definitions.

RIM keeps four slots a user can define -- two spring, two harvest. The workbook
takes them typed into ``1.Profile``; this app takes a small JSON file, which is
better than typing into a browser: it can be version-controlled, shared,
reviewed, and replayed by the command-line runner without a browser at all.

The parsed pack lives in the options bundle, so it saves with the scenario in
the same ``.rim.json`` as everything else, and never becomes process-wide state.
"""
from __future__ import annotations

import json

import streamlit as st

from rim import custom_options as custom
from utils.session import reset_editor_widgets

EXAMPLE = {
    "format": custom.FORMAT,
    "version": custom.FORMAT_VERSION,
    "options": {
        "spring_1": {
            "name": "Spring grazing crash",
            "control": {"default": 0.55, "Canola": 0.0},
            "cost_per_ha": {"default": 12.0},
        },
        "harvest_1": {
            "name": "Weed seed impact mill",
            "control": {"default": 0.95},
            "cost_per_ha": {"default": 30.0, "Legume crop": 26.0},
        },
    },
}


def custom_options_controls(key: str = "custom_options") -> None:
    """Upload, inspect and clear the four definable options."""
    st.caption(
        "RIM keeps four slots you can define yourself — two spring, two "
        "harvest. Describe them in a JSON file and load it here; they then "
        "appear in the strategy editor's *Other* dropdowns, priced and rated "
        "the way you set them. The file travels with the scenario, so saving "
        "your work keeps it."
    )

    loaded = st.session_state.options_current.get("custom_options")
    if loaded:
        st.success("Loaded:\n\n" + "\n\n".join(
            f"- {line}" for line in custom.describe(
                {int(row): spec for row, spec in loaded.items()}
            )
        ))
        if st.button("Clear these", key=f"{key}_clear"):
            st.session_state.options_current.pop("custom_options", None)
            st.session_state.results_current = None
            reset_editor_widgets()
            st.toast("Your own options were cleared")
            st.rerun()
    else:
        st.info("No options of your own are loaded — the four slots hold the "
                "workbook's own values.")

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
                st.session_state.options_current["custom_options"] = {
                    str(row): spec for row, spec in parsed.items()
                }
                st.session_state.results_current = None
                reset_editor_widgets()
                st.toast(f"Loaded {len(parsed)} option(s) of your own")
                st.rerun()

    st.download_button(
        "Download an example to edit",
        data=json.dumps(EXAMPLE, indent=2).encode("utf-8"),
        file_name="rim-custom-options.json",
        mime="application/json",
        key=f"{key}_example",
    )
    st.caption(
        "`control` is the share of ryegrass the option kills, 0 to 1. "
        "`cost_per_ha` is dollars per hectare. Both take a `default` plus any "
        "per-crop exceptions. A control of 0 for a crop means the option does "
        "nothing there, and it stops being offered for that crop."
    )
