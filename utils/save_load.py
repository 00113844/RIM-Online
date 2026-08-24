"""Save-to-file and load-from-file controls.

Slots live in ``st.session_state``, which is per browser session and held in the
server's memory: close the tab or restart the server and they are gone. A file
is the only way to keep work, move it between machines, or send it to someone.
"""
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from utils.session import export_bytes, import_bundle


def save_load_controls(key: str) -> None:
    """A download button, an uploader, and an honest description of both."""
    paddock = str(st.session_state.profile_current.get("paddock_name") or "").strip()
    stem = "".join(c if c.isalnum() else "-" for c in paddock).strip("-") or "RIM"
    filename = f"{stem}-{datetime.now():%Y-%m-%d}.rim.json"

    save_col, load_col = st.columns(2)
    with save_col:
        st.download_button(
            "Save to a file",
            data=export_bytes(),
            file_name=filename,
            mime="application/json",
            use_container_width=True,
            key=f"{key}_download",
            help="Downloads the paddock profile, prices, options, the current "
                 "strategy and every filled slot as one file.",
        )
    with load_col:
        uploaded = st.file_uploader(
            "Load a saved file",
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
                ok, message = import_bundle(payload)
                if ok:
                    st.toast(message)
                    st.rerun()
                else:
                    st.error(message)

    st.caption(
        "Slots are kept for this browser session only — closing the tab or "
        "restarting the app clears them. Save to a file to keep your work."
    )
