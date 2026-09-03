"""Profile slots must hold the farm the user meant to put in them.

Slots used to lose edits. The page wrapped its fields in ``st.form``, which
withholds a widget's value from session state until the form's own submit button
is pressed, and the slot toolbar sits *above* those forms. So Save read the
last-submitted bundle, not the page: rename the farm, press Save, and the slot
kept the old name. Prices made it worse by being inconsistent -- they were
assigned on every rerun, so an unsubmitted price change *did* land. Fill the page
top to bottom and save, and the slot held new prices under the old farm's name.

The fix has two halves, and both are pinned below:

* the page no longer uses ``st.form``, so every field writes as it changes and
  :func:`utils.session.commit_profile_widgets` can carry the page into the
  bundle on any run;
* loading a slot retires the fields -- their keys carry a generation number that
  is bumped, giving them a new identity -- so they re-seed from what was loaded
  instead of writing their stale values back over it. Deleting the key is not
  enough: the browser still holds a widget with that id and re-sends the old
  value. That half was found in a browser, not here.

The unit tests drive ``utils.session`` against a stand-in for session state. The
integration tests drive the real page through Streamlit's ``AppTest``, which is
the only way to prove the field keys on the page match the map in the module.

``AppTest`` injects widget state directly, so it cannot see either half of what
made this bug: a ``set_value`` on a form widget behaves as though the form were
submitted, and a retired key is simply gone rather than re-sent. Tests here would
pass on a page that is broken in a browser. What they can pin is the structure --
that no form survives on the page, and that loading gives the fields a new
identity. The behaviour itself was verified by hand at
``streamlit run app.py`` -> Paddock profile.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

import utils.session as session
from rim.defaults import DEFAULT_OPTIONS, DEFAULT_PRICES, DEFAULT_PROFILE


# ── Unit: a stand-in for st.session_state ─────────────────────────────────────


class FakeState(dict):
    """``st.session_state`` supports both attribute and item access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def field(name: str) -> str:
    """The session-state key a profile field currently answers to."""
    return session.profile_widget_key(name)


@pytest.fixture
def state(monkeypatch) -> FakeState:
    """A session holding the defaults, with no slots filled."""
    fake = FakeState(
        profile_current=deepcopy(DEFAULT_PROFILE),
        prices_current=deepcopy(DEFAULT_PRICES),
        options_current=deepcopy(DEFAULT_OPTIONS),
        profile_slots={1: None, 2: None, 3: None, 4: None},
    )
    monkeypatch.setattr(session.st, "session_state", fake)
    return fake


def test_every_widget_in_the_map_points_at_something_real(state) -> None:
    """A key that resolves nowhere would drop that field's edits silently."""
    for name, (bundle, path) in session.PROFILE_WIDGETS.items():
        target = state[f"{bundle}_current"]
        for step in path[:-1]:
            assert step in target, f"{name}: no {step!r} in {bundle}"
            target = target[step]
        assert path[-1] in target, f"{name}: no {path[-1]!r} in {bundle}"


def test_committing_carries_the_page_into_the_bundle(state) -> None:
    state[field("pf_farm_name")] = "Wickepin"
    state[field("pf_y_wheat")] = 4.25          # nested one level
    state[field("px_wheat")] = 777.0
    state[field("op_germ_default")] = 0.61     # nested, in a different bundle

    session.commit_profile_widgets()

    assert state.profile_current["farm_name"] == "Wickepin"
    assert state.profile_current["base_yields"]["Wheat"] == 4.25
    assert state.prices_current["Wheat"] == 777.0
    assert state.options_current["germination_rate"]["default"] == 0.61


def test_committing_is_safe_before_the_page_has_rendered(state) -> None:
    """Save can be reached from a file load without the fields ever existing."""
    before = deepcopy(state.profile_current)

    session.commit_profile_widgets()

    assert state.profile_current == before


def test_saving_captures_what_the_page_shows(state) -> None:
    """The reported bug: a renamed farm saved under its old name."""
    state[field("pf_farm_name")] = "Wickepin"
    state[field("px_wheat")] = 777.0

    session.save_profile_slot(1)

    assert state.profile_slots[1]["profile"]["farm_name"] == "Wickepin"
    assert state.profile_slots[1]["prices"]["Wheat"] == 777.0


def test_two_farms_land_in_two_slots(state) -> None:
    state[field("pf_farm_name")] = "Broomehill"
    state[field("px_wheat")] = 999.0
    session.save_profile_slot(1)

    state[field("pf_farm_name")] = "Kojonup"
    state[field("px_wheat")] = 111.0
    session.save_profile_slot(2)

    assert state.profile_slots[1]["profile"]["farm_name"] == "Broomehill"
    assert state.profile_slots[1]["prices"]["Wheat"] == 999.0
    assert state.profile_slots[2]["profile"]["farm_name"] == "Kojonup"
    assert state.profile_slots[2]["prices"]["Wheat"] == 111.0


def test_a_saved_slot_does_not_move_when_the_page_does(state) -> None:
    """Slots are snapshots. Editing on is not editing what was saved."""
    state[field("pf_farm_name")] = "Broomehill"
    session.save_profile_slot(1)

    state[field("pf_farm_name")] = "Kojonup"
    session.commit_profile_widgets()

    assert state.profile_slots[1]["profile"]["farm_name"] == "Broomehill"


def test_loading_retires_the_fields_so_they_reseed(state) -> None:
    """Without this the page writes its stale values back over the load."""
    stale = field("pf_farm_name")
    state[stale] = "Broomehill"
    session.save_profile_slot(1)
    state[stale] = "Kojonup"
    session.commit_profile_widgets()

    assert session.load_profile_slot(1) is True

    assert state.profile_current["farm_name"] == "Broomehill"
    assert stale not in state, "the old field would overwrite the load"
    assert field("pf_farm_name") != stale, (
        "the fields need a new identity, or the browser sends the old value back"
    )


def test_loading_an_empty_slot_changes_nothing(state) -> None:
    state[field("pf_farm_name")] = "Kojonup"
    session.commit_profile_widgets()

    assert session.load_profile_slot(3) is False
    assert state.profile_current["farm_name"] == "Kojonup"


def test_resetting_clears_the_fields_too(state) -> None:
    state[field("pf_farm_name")] = "Kojonup"
    session.commit_profile_widgets()

    stale = field("pf_farm_name")
    session.reset_profile_bundle()

    assert state.profile_current["farm_name"] == DEFAULT_PROFILE["farm_name"]
    assert stale not in state
    assert field("pf_farm_name") != stale


def test_resetting_does_not_touch_the_slots(state) -> None:
    state[field("pf_farm_name")] = "Broomehill"
    session.save_profile_slot(1)

    session.reset_profile_bundle()

    assert state.profile_slots[1]["profile"]["farm_name"] == "Broomehill"


# ── Unit: slot labels ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "profile, expected",
    [
        ({"farm_name": "Broomehill", "paddock_name": "North"}, "Broomehill · North"),
        ({"farm_name": "Broomehill", "paddock_name": ""}, "Broomehill"),
        ({"farm_name": "", "paddock_name": "North"}, "North"),
        ({"farm_name": "  ", "paddock_name": None}, "unnamed"),
        ({}, "unnamed"),
    ],
)
def test_a_profile_describes_itself(profile, expected) -> None:
    assert session.describe_profile(profile) == expected


def test_labels_name_the_farm_in_each_slot(state) -> None:
    state[field("pf_farm_name")] = "Broomehill"
    state[field("pf_paddock_name")] = "North Paddock"
    session.save_profile_slot(2)

    labels = session.profile_slot_labels()

    assert labels[2] == "Slot 2 — Broomehill · North Paddock"
    assert labels[1] == "Slot 1 — empty"


def test_a_renamed_farm_relabels_its_slot(state) -> None:
    """Labels are derived, not stored, so they cannot go stale."""
    state[field("pf_farm_name")] = "Broomehill"
    session.save_profile_slot(1)
    assert session.profile_slot_labels()[1] == "Slot 1 — Broomehill"

    state[field("pf_farm_name")] = "Broomehill South"
    session.save_profile_slot(1)

    assert session.profile_slot_labels()[1] == "Slot 1 — Broomehill South"


# ── Unit: slots survive a round trip through a saved file ─────────────────────


def test_slots_survive_a_save_file(state) -> None:
    state["strategy_current"] = [{"year": 1, "crop": "Wheat"}]
    state["strategy_slots"] = {0: None}
    state["strategy_slot_names"] = {}
    state[field("pf_farm_name")] = "Broomehill"
    session.save_profile_slot(1)
    state[field("pf_farm_name")] = "Kojonup"
    session.save_profile_slot(2)

    payload = session.export_bundle()

    fresh = FakeState(
        profile_current={}, prices_current={}, options_current={},
        profile_slots={}, strategy_slots={}, strategy_slot_names={},
        strategy_current=[], results_current="stale",
    )
    session.st.session_state = fresh
    ok, _ = session.import_bundle(payload)

    assert ok
    assert fresh.profile_slots[1]["profile"]["farm_name"] == "Broomehill"
    assert fresh.profile_slots[2]["profile"]["farm_name"] == "Kojonup"
    assert session.profile_slot_labels()[2] == "Slot 2 — Kojonup"


# ── Integration: the real page, driven through AppTest ────────────────────────

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402


def profile_page() -> AppTest:
    """The profile page, reached the way a user reaches it.

    ``AppTest.from_file`` on a page in ``pages/`` leaves the multipage registry
    unbuilt, and ``st.page_link`` then raises. Entering through ``app.py`` and
    switching gives the page the app it expects.
    """
    at = AppTest.from_file("app.py", default_timeout=120).run()
    at.switch_page("pages/1_Paddock_Profile.py").run()
    assert not at.exception, at.exception
    return at


def click(at: AppTest, label: str) -> AppTest:
    return [b for b in at.button if b.label == label][0].click().run()


def key(at: AppTest, name: str) -> str:
    """A field's key on the running page, at its current generation."""
    # AppTest's session state proxy has no .get, only __contains__/__getitem__.
    generation = (
        at.session_state[session.PROFILE_WIDGET_GENERATION]
        if session.PROFILE_WIDGET_GENERATION in at.session_state
        else 0
    )
    return f"{name}__{generation}"


@pytest.fixture(scope="module")
def page_widget_keys() -> set[str]:
    return {w.key for w in profile_page()._tree if getattr(w, "key", None)}


def test_the_page_renders_every_widget_the_map_names(page_widget_keys) -> None:
    """A key renamed on the page but not in the map would drop that field."""
    at = profile_page()
    missing = {key(at, name) for name in session.PROFILE_WIDGETS} - page_widget_keys
    assert not missing, f"in PROFILE_WIDGETS but not on the page: {sorted(missing)}"


def test_the_page_has_no_forms_left() -> None:
    """A form here would re-open the gap between the page and the bundle."""
    at = profile_page()
    assert not [b for b in at.button if "Update" in b.label], (
        "an Update button means the fields are batched behind a form again"
    )


def test_a_new_farm_saves_to_the_slot_it_was_meant_for() -> None:
    """End to end, the bug as reported: a new farm, straight to Save."""
    at = profile_page()

    at.text_input(key=key(at, "pf_farm_name")).set_value("Wickepin")
    at.text_input(key=key(at, "pf_paddock_name")).set_value("River Block")
    at.number_input(key=key(at, "px_wheat")).set_value(777.0)
    at.selectbox(key="profile_slot_pick").set_value(3).run()
    at = click(at, "Save")

    slot = at.session_state.profile_slots[3]
    assert slot["profile"]["farm_name"] == "Wickepin"
    assert slot["profile"]["paddock_name"] == "River Block"
    assert slot["prices"]["Wheat"] == 777.0


def test_two_farms_round_trip_through_two_slots() -> None:
    at = profile_page()

    at.text_input(key=key(at, "pf_farm_name")).set_value("Broomehill")
    at.number_input(key=key(at, "px_wheat")).set_value(999.0)
    at = click(at, "Save")                                   # slot 1 by default

    at.text_input(key=key(at, "pf_farm_name")).set_value("Kojonup")
    at.number_input(key=key(at, "px_wheat")).set_value(111.0)
    at.selectbox(key="profile_slot_pick").set_value(2).run()
    at = click(at, "Save")

    at.selectbox(key="profile_slot_pick").set_value(1).run()
    at = click(at, "Load")

    assert at.session_state.profile_current["farm_name"] == "Broomehill"
    assert at.session_state.prices_current["Wheat"] == 999.0
    assert at.text_input(key=key(at, "pf_farm_name")).value == "Broomehill"
    assert at.number_input(key=key(at, "px_wheat")).value == 999.0

    # And the other slot is untouched by the round trip.
    assert at.session_state.profile_slots[2]["profile"]["farm_name"] == "Kojonup"
    assert at.session_state.profile_slots[2]["prices"]["Wheat"] == 111.0


def test_the_picker_names_the_farm_in_each_slot() -> None:
    at = profile_page()

    at.text_input(key=key(at, "pf_farm_name")).set_value("Broomehill")
    at.text_input(key=key(at, "pf_paddock_name")).set_value("North Paddock")
    at = click(at, "Save")

    labels = at.selectbox(key="profile_slot_pick").options
    assert "Slot 1 — Broomehill · North Paddock" in labels
    assert "Slot 2 — empty" in labels


def test_saving_over_a_slot_replaces_it() -> None:
    at = profile_page()

    at.text_input(key=key(at, "pf_farm_name")).set_value("Broomehill")
    at = click(at, "Save")
    at.text_input(key=key(at, "pf_farm_name")).set_value("Broomehill South")
    at = click(at, "Save")

    assert at.session_state.profile_slots[1]["profile"]["farm_name"] == "Broomehill South"
    assert "Slot 1 — Broomehill South" in at.selectbox(key="profile_slot_pick").options


def test_loading_an_empty_slot_leaves_the_page_alone() -> None:
    at = profile_page()

    at.text_input(key=key(at, "pf_farm_name")).set_value("Kojonup")
    at.selectbox(key="profile_slot_pick").set_value(4).run()
    at = click(at, "Load")

    assert at.session_state.profile_current["farm_name"] == "Kojonup"
    assert at.session_state.profile_slots[4] is None


def test_reset_returns_the_page_to_defaults_but_keeps_the_slots() -> None:
    at = profile_page()

    at.text_input(key=key(at, "pf_farm_name")).set_value("Broomehill")
    at.number_input(key=key(at, "px_wheat")).set_value(999.0)
    at = click(at, "Save")

    at.text_input(key=key(at, "pf_farm_name")).set_value("Kojonup")
    at = click(at, "Reset all")

    assert at.text_input(key=key(at, "pf_farm_name")).value == DEFAULT_PROFILE["farm_name"]
    assert at.number_input(key=key(at, "px_wheat")).value == DEFAULT_PRICES["Wheat"]
    assert at.session_state.profile_slots[1]["profile"]["farm_name"] == "Broomehill"
    assert at.session_state.profile_slots[1]["prices"]["Wheat"] == 999.0
