"""A strategy slot should say which plan it holds.

Profile slots read "Slot 2 — Broomehill · North Paddock", derived from the farm
and paddock the user typed. A ten-year plan has no such field, so the name is
typed instead: "No glyphosate" says why the plan exists in a way "Canola-Wheat
x5" never could.

The name is kept beside the slot rather than inside it. Both
``utils.session.import_bundle`` and ``rim.scenario`` put a slot's value through
``upgrade_strategy``, which expects a list of years; burying a name in there
would have to be unpicked in two places.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

import utils.session as session
from rim.defaults import (
    DEFAULT_OPTIONS,
    DEFAULT_PRICES,
    DEFAULT_PROFILE,
    build_default_strategy,
)


class FakeState(dict):
    """``st.session_state`` supports both attribute and item access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def state(monkeypatch) -> FakeState:
    fake = FakeState(
        profile_current=deepcopy(DEFAULT_PROFILE),
        prices_current=deepcopy(DEFAULT_PRICES),
        options_current=deepcopy(DEFAULT_OPTIONS),
        profile_slots={1: None, 2: None, 3: None, 4: None},
        strategy_current=build_default_strategy(10),
        strategy_slots={n: None for n in range(7)},
        strategy_slot_names={},
    )
    fake["strategy_slots"][0] = build_default_strategy(10)
    monkeypatch.setattr(session.st, "session_state", fake)
    return fake


# ── Naming ────────────────────────────────────────────────────────────────────


def test_a_saved_slot_carries_the_name_it_was_given(state) -> None:
    session.save_strategy_slot(2, "No glyphosate")

    assert session.strategy_slot_name(2) == "No glyphosate"
    assert session.strategy_slot_label(2) == "Slot 2 — No glyphosate"


def test_an_unnamed_slot_keeps_its_number(state) -> None:
    """Naming is optional; it should not force a placeholder on anyone."""
    session.save_strategy_slot(3)

    assert session.strategy_slot_label(3) == "Slot 3"


def test_a_blank_name_is_not_a_name(state) -> None:
    session.save_strategy_slot(3, "   ")

    assert session.strategy_slot_name(3) == ""
    assert session.strategy_slot_label(3) == "Slot 3"


def test_a_name_is_tidied_but_not_mangled(state) -> None:
    session.save_strategy_slot(2, "  No   glyphosate  ")

    assert session.strategy_slot_name(2) == "No glyphosate"


def test_renaming_replaces_the_old_name(state) -> None:
    session.save_strategy_slot(2, "First idea")
    session.save_strategy_slot(2, "Second idea")

    assert session.strategy_slot_label(2) == "Slot 2 — Second idea"


def test_clearing_the_name_leaves_the_slot_numbered(state) -> None:
    session.save_strategy_slot(2, "No glyphosate")
    session.save_strategy_slot(2, "")

    assert session.strategy_slot_label(2) == "Slot 2"


def test_an_empty_slot_says_so(state) -> None:
    assert session.strategy_slot_label(4) == "Slot 4 — empty"


def test_the_default_slot_is_named_for_what_it_is(state) -> None:
    """Slot 0 is the read-only starting point and is never saved over."""
    assert session.strategy_slot_label(session.DEFAULT_STRATEGY_SLOT) == "Default strategy"


def test_every_slot_gets_a_label(state) -> None:
    session.save_strategy_slot(1, "Wheat every year")

    labels = session.strategy_slot_labels()

    assert labels[0] == "Default strategy"
    assert labels[1] == "Slot 1 — Wheat every year"
    assert labels[2] == "Slot 2 — empty"
    assert set(labels) == set(state.strategy_slots)


# ── The plan itself still behaves ─────────────────────────────────────────────


def test_saving_keeps_the_plan_not_a_reference_to_it(state) -> None:
    session.save_strategy_slot(1, "Wheat every year")

    state.strategy_current[0]["crop"] = "Canola"

    assert state.strategy_slots[1][0]["crop"] == "Wheat"


def test_loading_a_named_slot_restores_the_plan(state) -> None:
    state.strategy_current[0]["crop"] = "Canola"
    session.save_strategy_slot(1, "Canola first")
    state.strategy_current[0]["crop"] = "Barley"

    assert session.load_strategy_slot(1) is True
    assert state.strategy_current[0]["crop"] == "Canola"


def test_loading_an_empty_slot_changes_nothing(state) -> None:
    before = deepcopy(state.strategy_current)

    assert session.load_strategy_slot(5) is False
    assert state.strategy_current == before


# ── Names travel with the file ────────────────────────────────────────────────


def test_names_survive_a_save_file(state) -> None:
    session.save_strategy_slot(1, "Wheat every year")
    session.save_strategy_slot(2, "No glyphosate")

    payload = session.export_bundle()

    fresh = FakeState(
        profile_current={}, prices_current={}, options_current={},
        profile_slots={}, strategy_slots={}, strategy_slot_names={},
        strategy_current=[], results_current="stale",
    )
    session.st.session_state = fresh
    ok, _ = session.import_bundle(payload)

    assert ok
    assert session.strategy_slot_label(1) == "Slot 1 — Wheat every year"
    assert session.strategy_slot_label(2) == "Slot 2 — No glyphosate"


def test_a_file_saved_before_names_existed_still_loads(state) -> None:
    """Older saves simply have unnamed slots."""
    payload = session.export_bundle()
    payload.pop("strategy_slot_names")
    payload["version"] = 4

    ok, _ = session.import_bundle(payload)

    assert ok
    assert session.strategy_slot_name(1) == ""


def test_the_runner_reads_the_names_too() -> None:
    """rim.scenario carries them, so a scenario is not silently thinned."""
    from rim import scenario as scenarios

    payload = scenarios.default().as_save_payload()
    payload["strategy_slot_names"] = {"1": "Wheat every year"}

    assert scenarios.from_payload(payload).strategy_slot_names == {
        "1": "Wheat every year"
    }


def test_both_ends_write_the_same_format_version() -> None:
    from rim import scenario as scenarios

    assert session.SAVE_FORMAT_VERSION == scenarios.SAVE_FORMAT_VERSION


# ── The page renders them ─────────────────────────────────────────────────────

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402


def strategy_page() -> AppTest:
    """The strategy page, reached the way a user reaches it."""
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.switch_page("pages/2_Strategy.py").run()
    assert not at.exception, at.exception
    return at


def test_the_picker_names_the_plan_in_each_slot() -> None:
    at = strategy_page()

    at.text_input(key="strategy_slot_name").set_value("No glyphosate")
    at.selectbox(key="strategy_slot_pick").set_value(2).run()
    [b for b in at.button if b.label == "Save"][0].click().run()

    labels = at.selectbox(key="strategy_slot_pick").options
    assert "Slot 2 — No glyphosate" in labels
    assert "Default strategy" in labels
    assert "Slot 3 — empty" in labels


def test_the_default_slot_cannot_be_saved_over() -> None:
    at = strategy_page()

    save = [b for b in at.button if b.label == "Save"][0]
    assert save.disabled, "slot 0 is the read-only starting point"
