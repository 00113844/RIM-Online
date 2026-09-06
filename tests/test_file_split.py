"""A paddock and a plan are separate files, and either uploader takes any.

They answer different questions. A course hands out one paddock and collects
thirty plans against it; a consultant carries one paddock between plans. With a
single combined file neither is possible without hand-editing JSON.

So there are three files and two uploaders:

* ``.profile.json``  — profile, prices, options, profile slots
* ``.strategy.json`` — the plan, the strategy slots and their names
* ``.rim.json``      — both, which is what every earlier save was

Each page downloads the half it owns and the Export page writes the pair. Either
uploader accepts any of the three, so a file dropped in the wrong box still does
the right thing and nothing saved before the split is stranded.
"""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

import utils.session as session
from rim import scenario as scenarios
from rim.defaults import (
    DEFAULT_OPTIONS,
    DEFAULT_PRICES,
    DEFAULT_PROFILE,
    build_default_strategy,
)
from tools import run_scenario


class FakeState(dict):
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
        profile_current={**deepcopy(DEFAULT_PROFILE), "paddock_name": "North Block"},
        prices_current=deepcopy(DEFAULT_PRICES),
        options_current=deepcopy(DEFAULT_OPTIONS),
        strategy_current=build_default_strategy(10),
        profile_slots={1: None, 2: None, 3: None, 4: None},
        strategy_slots={n: None for n in range(7)},
        strategy_slot_names={},
        results_current="stale",
    )
    monkeypatch.setattr(session.st, "session_state", fake)
    return fake


# -- What each file carries ---------------------------------------------------


def test_the_paddock_file_holds_the_paddock_and_no_plan(state) -> None:
    payload = session.export_profile_bundle()

    assert payload["format"] == scenarios.PROFILE_FORMAT
    assert set(payload) == {"format", "version", *scenarios.PROFILE_SECTIONS}
    assert "strategy" not in payload


def test_the_plan_file_holds_the_plan_and_no_paddock(state) -> None:
    payload = session.export_strategy_bundle()

    assert payload["format"] == scenarios.STRATEGY_FORMAT
    assert set(payload) == {"format", "version", *scenarios.STRATEGY_SECTIONS}
    assert "profile" not in payload and "prices" not in payload


def test_the_plan_file_carries_the_saved_slots(state) -> None:
    """Asked for explicitly: a submission brings the alternatives tried."""
    session.save_strategy_slot(1, "No glyphosate")

    payload = session.export_strategy_bundle()

    assert payload["strategy_slots"][1] is not None
    assert payload["strategy_slot_names"][1] == "No glyphosate"


def test_the_combined_file_holds_both(state) -> None:
    payload = session.export_bundle()

    assert payload["format"] == scenarios.SAVE_FORMAT
    assert set(payload) == {
        "format", "version",
        *scenarios.PROFILE_SECTIONS, *scenarios.STRATEGY_SECTIONS,
    }


def test_the_three_downloads_are_all_offered(state) -> None:
    for kind in (scenarios.PROFILE_FORMAT, scenarios.STRATEGY_FORMAT,
                 scenarios.SAVE_FORMAT):
        payload = json.loads(session.export_bytes(kind))
        assert scenarios.kind_of(payload) == kind


# -- Either uploader takes any of them ----------------------------------------


def test_a_paddock_file_replaces_the_paddock_and_leaves_the_plan(state) -> None:
    state.strategy_current[0]["crop"] = "Canola"
    incoming = session.export_profile_bundle()
    incoming["profile"] = {**incoming["profile"], "paddock_name": "River Block"}

    ok, message = session.import_bundle(incoming)

    assert ok
    assert "paddock" in message.lower()
    assert state.profile_current["paddock_name"] == "River Block"
    assert state.strategy_current[0]["crop"] == "Canola", "the plan was untouched"


def test_a_plan_file_replaces_the_plan_and_leaves_the_paddock(state) -> None:
    incoming = session.export_strategy_bundle()
    incoming["strategy"] = [dict(row, crop="Barley") for row in incoming["strategy"]]

    ok, message = session.import_bundle(incoming)

    assert ok
    assert "strategy" in message.lower()
    assert state.strategy_current[0]["crop"] == "Barley"
    assert state.profile_current["paddock_name"] == "North Block", "paddock untouched"


def test_a_combined_file_replaces_both(state) -> None:
    incoming = session.export_bundle()
    incoming["profile"] = {**incoming["profile"], "paddock_name": "River Block"}
    incoming["strategy"] = [dict(row, crop="Barley") for row in incoming["strategy"]]

    ok, _ = session.import_bundle(incoming)

    assert ok
    assert state.profile_current["paddock_name"] == "River Block"
    assert state.strategy_current[0]["crop"] == "Barley"


def test_a_plan_file_does_not_forget_the_slot_names(state) -> None:
    """Loading a paddock must not wipe what the plan side was holding."""
    session.save_strategy_slot(1, "No glyphosate")

    session.import_bundle(session.export_profile_bundle())

    assert session.strategy_slot_name(1) == "No glyphosate"


def test_every_earlier_save_still_loads(state) -> None:
    """A .rim.json written before the split, at the format of the day."""
    ok, _ = session.import_bundle({
        "format": scenarios.SAVE_FORMAT,
        "version": 1,
        "profile": dict(DEFAULT_PROFILE),
        "prices": dict(DEFAULT_PRICES),
        "options": dict(DEFAULT_OPTIONS),
        "strategy": [{"crop": "Wheat", "pre_emergent": "Yes",
                      "post_emergent": "Yes", "knockdown": "Single knock-down"}],
    })

    assert ok
    assert state.strategy_current[0]["pre_emergent"] == "Trifluralin + triallate"


def test_something_else_entirely_is_refused(state) -> None:
    ok, message = session.import_bundle({"format": "not-ours", "version": 1})

    assert not ok
    assert "not a RIM Online file" in message


# -- Reading the halves without Streamlit -------------------------------------


def test_a_plan_alone_runs_on_the_default_paddock() -> None:
    plan = scenarios.default().as_strategy_payload()

    scenario = scenarios.from_payload(plan, name="smith-j")

    assert scenario.years == 10
    assert scenario.profile["seed_bank_start"] == DEFAULT_PROFILE["seed_bank_start"]


def test_a_paddock_alone_runs_on_the_default_plan() -> None:
    paddock = scenarios.default().as_profile_payload()

    scenario = scenarios.from_payload(paddock, name="north")

    assert scenario.years == 10


def test_pairing_takes_the_paddock_from_one_and_the_plan_from_the_other() -> None:
    base = scenarios.default()
    paddock = base.as_profile_payload()
    paddock["profile"] = {**paddock["profile"], "seed_bank_start": 100}
    plan = base.as_strategy_payload()
    plan["strategy"] = [dict(row, crop="Barley") for row in plan["strategy"]]

    scenario = scenarios.from_payload(scenarios.merge_payloads(plan, paddock))

    assert scenario.profile["seed_bank_start"] == 100
    assert scenario.strategy[0]["crop"] == "Barley"


@pytest.mark.parametrize("name, expected", [
    ("smith-j.strategy.json", "smith-j"),
    ("north.profile.json", "north"),
    ("broomehill.rim.json", "broomehill"),
])
def test_a_file_names_its_scenario_without_its_suffix(name, expected) -> None:
    """`.strategy.json` must not be left as `smith-j.strategy`."""
    assert scenarios.name_for(name) == expected


# -- One paddock, many plans --------------------------------------------------


@pytest.fixture
def marking(tmp_path):
    """A paddock handed out, and three plans handed back."""
    base = scenarios.default()
    paddock = base.as_profile_payload()
    paddock["profile"] = {**paddock["profile"], "seed_bank_start": 100}
    (tmp_path / "north.profile.json").write_text(json.dumps(paddock), encoding="utf-8")

    for who, overrides in (
        ("smith-j", {"pre_emergent": "None", "post_emergent_1": "None"}),
        ("nguyen-t", {"post_emergent_1": "Hussar", "post_emergent_2": "Topik"}),
        ("patel-r", {"post_emergent_1": "Topik"}),
    ):
        plan = base.as_strategy_payload()
        plan["strategy"] = [dict(row, **overrides) for row in plan["strategy"]]
        (tmp_path / f"{who}.strategy.json").write_text(json.dumps(plan), encoding="utf-8")
    return tmp_path


def test_one_paddock_is_applied_to_every_plan(marking) -> None:
    plans = sorted(str(p) for p in marking.glob("*.strategy.json"))

    loaded = run_scenario.load_all(
        plans, None, str(marking / "north.profile.json")
    )

    assert len(loaded) == 3
    assert {s.name for s in loaded} == {"smith-j", "nguyen-t", "patel-r"}
    for scenario in loaded:
        assert scenario.profile["seed_bank_start"] == 100, "the shared paddock"


def test_the_plans_still_differ_from_each_other(marking) -> None:
    """Sharing a paddock must not flatten the thing being compared."""
    plans = sorted(str(p) for p in marking.glob("*.strategy.json"))

    results = {
        s.name: run_scenario.simulate(s)
        for s in run_scenario.load_all(plans, None,
                                       str(marking / "north.profile.json"))
    }
    ending = {
        name: float(r["yearly"]["seed_bank_end"].iloc[-1])
        for name, r in results.items()
    }

    assert ending["smith-j"] > ending["nguyen-t"], "spraying nothing leaves more"
    # Two sprays draw the bank down to nothing worth counting. Stated as an
    # agronomic threshold rather than an epsilon: the claim is "gone", and one
    # seed per hundred square metres is gone.
    assert ending["nguyen-t"] < 0.01
    assert ending["smith-j"] > 1.0, "and no control lets it run away"


def test_the_runner_marks_a_whole_set_in_one_command(marking, capsys) -> None:
    plans = sorted(str(p) for p in marking.glob("*.strategy.json"))

    code = run_scenario.main(
        ["--paddock", str(marking / "north.profile.json"), *plans]
    )

    assert code == 0
    printed = capsys.readouterr().out
    for who in ("smith-j", "nguyen-t", "patel-r"):
        assert who in printed


def test_a_plan_passed_as_the_paddock_says_so(marking) -> None:
    """The mistake someone will make, named rather than half-applied."""
    with pytest.raises(scenarios.ScenarioError, match="is a strategy file"):
        run_scenario.load_all(
            [], None, str(marking / "smith-j.strategy.json")
        )


def test_without_a_paddock_each_plan_keeps_its_own(marking) -> None:
    loaded = run_scenario.load_all(
        [str(marking / "smith-j.strategy.json")], None, None
    )

    assert loaded[0].profile["seed_bank_start"] == DEFAULT_PROFILE["seed_bank_start"]
