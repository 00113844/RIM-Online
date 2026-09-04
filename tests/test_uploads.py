"""An uploaded file must be acted on once, not on every run.

``st.file_uploader`` keeps returning the same file for as long as it sits in the
widget, so this shape never terminates::

    uploaded = st.file_uploader(...)
    if uploaded is not None:
        apply(uploaded)
        st.rerun()

Both of this app's uploaders were written that way. Nothing raised: the page
simply re-ran forever, re-simulating the whole ten years each time. It surfaced
as "Playwright loading a 10 year strategy non-stop on a loop", and it took a
Streamlit server down for memory before it was understood.

These pin the guard, and the static test below pins the shape so a third
uploader cannot quietly reintroduce it.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

import utils.uploads as uploads


class FakeState(dict):
    """``st.session_state`` supports attribute and item access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class FakeUpload:
    """What ``st.file_uploader`` hands back, as far as this cares."""

    def __init__(self, file_id: str, name: str = "scenario.rim.json") -> None:
        self.file_id = file_id
        self.name = name


@pytest.fixture
def state(monkeypatch) -> FakeState:
    fake = FakeState()
    monkeypatch.setattr(uploads.st, "session_state", fake)
    return fake


# -- The guard itself ---------------------------------------------------------


def test_a_file_is_new_the_first_time(state) -> None:
    assert uploads.is_new_upload(FakeUpload("abc"), key="profile")


def test_the_same_file_is_not_new_once_handled(state) -> None:
    """The loop, in one assertion."""
    upload = FakeUpload("abc")

    uploads.mark_handled(upload, key="profile")

    assert not uploads.is_new_upload(upload, key="profile")


def test_an_uploader_keeps_returning_the_file_and_that_is_fine(state) -> None:
    """Simulate ten reruns with the file still sitting in the widget."""
    upload = FakeUpload("abc")
    applied = 0

    for _ in range(10):
        if uploads.is_new_upload(upload, key="profile"):
            applied += 1
            uploads.mark_handled(upload, key="profile")

    assert applied == 1, "acting more than once is the infinite loop"


def test_a_different_file_is_new_again(state) -> None:
    uploads.mark_handled(FakeUpload("abc"), key="profile")

    assert uploads.is_new_upload(FakeUpload("def"), key="profile")


def test_two_uploaders_do_not_share_a_marker(state) -> None:
    """The profile panel and the options panel are separate uploaders."""
    upload = FakeUpload("abc")
    uploads.mark_handled(upload, key="profile")

    assert not uploads.is_new_upload(upload, key="profile")
    assert uploads.is_new_upload(upload, key="custom_options")


def test_no_file_is_never_new(state) -> None:
    assert not uploads.is_new_upload(None, key="profile")


def test_a_failed_file_stays_unhandled(state) -> None:
    """So its error keeps rendering while the bad file is still selected.

    It cannot loop: the failure path never reruns. Marking it would make the
    message vanish on the next interaction and leave the user with a file
    loaded and nothing said about it.
    """
    upload = FakeUpload("bad")

    assert uploads.is_new_upload(upload, key="profile")
    assert uploads.is_new_upload(upload, key="profile"), "still reported, run after run"


def test_forgetting_lets_the_same_file_through_again(state) -> None:
    upload = FakeUpload("abc")
    uploads.mark_handled(upload, key="profile")

    uploads.forget_upload(key="profile")

    assert uploads.is_new_upload(upload, key="profile")


# -- The shape, so a third uploader cannot reintroduce it ---------------------


UPLOADER_MODULES = ("utils/save_load.py", "utils/custom_options_ui.py")


@pytest.mark.parametrize("path", UPLOADER_MODULES)
def test_every_uploader_guards_before_it_reruns(path) -> None:
    source = pathlib.Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)

    uses_uploader = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "file_uploader"
        for node in ast.walk(tree)
    )
    assert uses_uploader, f"{path}: no uploader — has this module changed shape?"

    assert "is_new_upload" in source, (
        f"{path}: an uploader that reruns without is_new_upload loops forever"
    )
    assert "mark_handled" in source, (
        f"{path}: nothing marks the file handled, so the guard never closes"
    )


@pytest.mark.parametrize("path", UPLOADER_MODULES)
def test_no_uploader_reruns_on_a_bare_not_none_check(path) -> None:
    """`if uploaded is not None:` around a rerun is the bug, spelled out."""
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = ast.unparse(node.test)
        if "uploaded is not None" not in test:
            continue
        reruns = [
            child for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "rerun"
        ]
        assert not reruns, (
            f"{path} line {node.lineno}: `{test}` guards an st.rerun() — "
            "the uploader will re-apply and rerun on every run, forever"
        )
