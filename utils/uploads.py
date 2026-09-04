"""Acting on an uploaded file once, rather than on every run.

``st.file_uploader`` keeps returning the same file for as long as it is in the
widget, so the obvious shape is an infinite loop::

    uploaded = st.file_uploader(...)
    if uploaded is not None:
        apply(uploaded)
        st.rerun()          # next run: still not None, so apply and rerun again

Nothing errors. The page simply re-runs forever, re-simulating the whole ten
years each time, until the browser tab or the server gives out. Both of this
app's uploaders were written that way and both looped.

The fix is to remember which file has been dealt with. ``file_id`` is Streamlit's
own per-upload identifier, so replacing the file is handled and re-running with
the same one is not.

Only mark a file handled once it has actually been applied. A file that fails to
parse stays unhandled on purpose: its error message then renders on every run,
which is what you want while a bad file is still sitting in the uploader, and it
cannot loop because the failure path never reruns.
"""
from __future__ import annotations

from typing import Any

import streamlit as st


def _marker(key: str) -> str:
    return f"{key}__handled_file"


def is_new_upload(uploaded: Any, *, key: str) -> bool:
    """Has this file arrived since the last one this uploader acted on?"""
    if uploaded is None:
        return False
    return st.session_state.get(_marker(key)) != getattr(uploaded, "file_id", None)


def mark_handled(uploaded: Any, *, key: str) -> None:
    """Record that this file has been applied, so the next run leaves it alone.

    Call it immediately before ``st.rerun()``, not after -- the rerun does not
    return.
    """
    if uploaded is not None:
        st.session_state[_marker(key)] = getattr(uploaded, "file_id", None)


def forget_upload(*, key: str) -> None:
    """Let the same file be applied again, if a caller ever needs that."""
    st.session_state.pop(_marker(key), None)
