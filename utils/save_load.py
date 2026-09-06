"""Save-to-file and load-from-file controls.

Slots live in ``st.session_state``, which is per browser session and held in the
server's memory: close the tab or restart the server and they are gone. A file
is the only way to keep work, move it between machines, or send it to someone.

**Three files, two uploaders.** A paddock and a plan answer different questions,
and separating them is what lets one paddock be handed out and thirty plans come
back against it. So each page offers a download of the thing it owns, the Export
page offers the two together, and either uploader accepts any of the three --
a file dropped into the wrong box still does the right thing, and every
``.rim.json`` written before the split still loads.
"""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from rim import scenario
from utils.session import export_bytes, import_bundle, strategy_slot_name
from utils.uploads import is_new_upload, mark_handled

# What the page calls the panel. "Keep this work" said only half of it -- you
# can load here too, and the box that does it is the one people were missing.
PANEL_TITLES: dict[str, str] = {
    scenario.PROFILE_FORMAT: "Save or load a paddock",
    scenario.STRATEGY_FORMAT: "Save or load a plan",
    scenario.SAVE_FORMAT: "Save or load everything",
}

# Per file: the button, what it writes, and what it says it holds.
_DOWNLOADS: dict[str, dict[str, str]] = {
    scenario.PROFILE_FORMAT: {
        "label": "Download this paddock",
        "help": "The paddock profile, prices and options — everything except the "
                "plan. Hand this out to have several plans built against one "
                "paddock.",
    },
    scenario.STRATEGY_FORMAT: {
        "label": "Download this plan",
        "help": "The ten-year plan and your saved strategy slots — no paddock. "
                "This is the half to send back.",
    },
    scenario.SAVE_FORMAT: {
        "label": "Download everything",
        "help": "The paddock and the plan in one file, with every filled slot. "
                "This is what to keep if you are keeping one file.",
    },
}


def _stem(kind: str) -> str:
    """What to call the file, from whatever the user has already named."""
    if kind == scenario.STRATEGY_FORMAT:
        chosen = st.session_state.get("strategy_slot_pick")
        named = strategy_slot_name(chosen) if chosen is not None else ""
    else:
        named = ""
    if not named:
        named = str(st.session_state.profile_current.get("paddock_name") or "").strip()
    cleaned = "".join(c if c.isalnum() else "-" for c in named).strip("-")
    return cleaned or "RIM"


def download_button(kind: str, *, key: str) -> None:
    """One of the three files, offered for download."""
    spec = _DOWNLOADS[kind]
    st.download_button(
        spec["label"],
        data=export_bytes(kind),
        file_name=f"{_stem(kind)}-{datetime.now():%Y-%m-%d}{scenario.SUFFIXES[kind]}",
        mime="application/json",
        width="stretch",
        key=f"{key}_download_{kind}",
        help=spec["help"],
    )


def upload_control(key: str) -> None:
    """One uploader, taking any of the three files."""
    # Labelled, not collapsed. An unlabelled drop zone is why nobody could tell
    # this panel loaded anything, let alone that it takes all three files.
    uploaded = st.file_uploader(
        "Load a paddock, a plan, or both",
        type=["json"],
        key=f"{key}_upload",
        help="Takes any RIM file — a .profile.json, a .strategy.json, or a "
             "full .rim.json — and loads whichever parts it holds.",
    )
    # Once per file, not once per run: the uploader keeps handing the same file
    # back, and rerunning on it would never stop. See utils/uploads.py.
    if not is_new_upload(uploaded, key=key):
        return

    try:
        payload = json.loads(uploaded.getvalue().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        st.error("That file is not readable JSON.")
        return

    ok, message = import_bundle(payload)
    if not ok:
        st.error(message)
        return

    mark_handled(uploaded, key=key)
    st.toast(message)
    st.rerun()


def save_load_controls(key: str, kind: str = scenario.SAVE_FORMAT) -> None:
    """The panel a page shows: its own file to download, and one uploader.

    ``kind`` is the file this page owns. The uploader is not restricted to it --
    dropping a full scenario onto the Strategy page loads the paddock too, which
    is what someone doing that meant.
    """
    save_col, load_col = st.columns(2)
    with save_col:
        download_button(kind, key=key)
    with load_col:
        upload_control(key)

    if kind == scenario.PROFILE_FORMAT:
        saves = ("**Download** writes the paddock on its own — profile, prices "
                 "and options. The plan is saved from the Strategy page.")
    elif kind == scenario.STRATEGY_FORMAT:
        saves = ("**Download** writes the plan on its own, with your saved "
                 "slots. The paddock is saved from the Paddock profile page.")
    else:
        saves = "**Download** writes the paddock and the plan together."

    st.caption(
        f"{saves} **Load** takes any of the three — paddock, plan, or both — "
        "so it does not matter which page you are on. The Export page writes "
        "the pair in one file."
    )

    st.caption(
        "Slots live in this browser session only. Closing the tab clears them; "
        "a file is the only thing that keeps them."
    )
