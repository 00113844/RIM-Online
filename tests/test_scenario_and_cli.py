"""Scenarios read from a file, options defined in one, and the runner.

Three things that used to need a browser now do not: reading a saved scenario,
defining the four options RIM lets a user define, and running a plan. All three
are plain Python and none of them imports Streamlit, which is what makes them
testable here and scriptable anywhere.
"""
from __future__ import annotations

import json

import pytest

from rim import control_options as co
from rim import custom_options as custom
from rim import scenario as scenarios
from rim.scenario import ScenarioError
from tools import run_scenario

WHEAT, BARLEY, CANOLA, LEGUME, VOLUNTEER = range(5)


@pytest.fixture
def save_file(tmp_path):
    """Write a save payload to disk and hand back the path."""
    def write(payload, name="broomehill.rim.json"):
        target = tmp_path / name
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target
    return write


# -- Reading a scenario without Streamlit -------------------------------------


def test_the_shipped_default_is_a_runnable_scenario() -> None:
    scenario = scenarios.default()

    assert scenario.years == 10
    assert scenario.name == "default"
    assert scenario.custom_options is None


def test_a_saved_file_round_trips(save_file) -> None:
    original = scenarios.default()

    reloaded = scenarios.load(save_file(original.as_save_payload()))

    assert reloaded.strategy == original.strategy
    assert reloaded.profile == original.profile
    assert reloaded.name == "broomehill"


def test_a_partial_file_still_runs(save_file) -> None:
    """A hand-written scenario should not have to restate every default."""
    scenario = scenarios.load(save_file({
        "format": scenarios.SAVE_FORMAT,
        "version": scenarios.SAVE_FORMAT_VERSION,
        "profile": {"farm_name": "Wickepin"},
        "strategy": [{"crop": "Wheat"}, {"crop": "Canola"}],
    }))

    assert scenario.profile["farm_name"] == "Wickepin"
    assert scenario.profile["seed_bank_start"] == 20      # from the defaults
    assert scenario.years == 2
    assert [row["year"] for row in scenario.strategy] == [1, 2]


def test_an_old_vocabulary_is_carried_forward_on_read(save_file) -> None:
    scenario = scenarios.load(save_file({
        "format": scenarios.SAVE_FORMAT,
        "version": 1,
        "strategy": [{"crop": "Wheat", "knockdown": "Double knock-down",
                      "pre_emergent": "Yes", "post_emergent": "Yes",
                      "spring_option": "Swathing"}],
    }))

    row = scenario.strategy[0]
    assert row["knockdown"] == "Double knock-down"
    assert row["pre_emergent"] == "Trifluralin + triallate"
    assert row["spring_swathe"] == "Swathe only"
    assert "post_emergent" not in row


@pytest.mark.parametrize("payload, expected", [
    ([], "should hold a JSON object"),
    ({"format": "something-else"}, "not a RIM Online save file"),
    ({"format": scenarios.SAVE_FORMAT, "version": 99}, "newer version"),
    ({"format": scenarios.SAVE_FORMAT, "strategy": []}, "non-empty list"),
    ({"format": scenarios.SAVE_FORMAT, "profile": 3}, "should be an object"),
])
def test_a_broken_file_says_what_is_wrong(payload, expected) -> None:
    with pytest.raises(ScenarioError, match=expected):
        scenarios.from_payload(payload)


def test_a_missing_file_says_so(tmp_path) -> None:
    with pytest.raises(ScenarioError, match="does not exist"):
        scenarios.load(tmp_path / "nope.rim.json")


def test_reading_a_scenario_needs_no_streamlit() -> None:
    """The whole point of splitting reading from applying."""
    import ast
    import pathlib

    source = pathlib.Path("rim/scenario.py").read_text(encoding="utf-8")
    imported = {
        node.module or ""
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import) for alias in node.names
    }

    assert not any(name.startswith("streamlit") for name in imported)
    assert not any(name.startswith("utils") for name in imported)


# -- Options a user defines ---------------------------------------------------


def _pack(**options):
    return {"format": custom.FORMAT, "version": custom.FORMAT_VERSION,
            "options": options}


def test_a_defined_option_replaces_the_workbooks_placeholder() -> None:
    overrides = custom.parse(_pack(spring_1={
        "name": "Spring grazing crash",
        "control": {"default": 0.55},
        "cost_per_ha": {"default": 12.0},
    }))

    assert co.names("spring_others", overrides)[1] == "Spring grazing crash"
    assert co.control("spring_others", "Spring grazing crash", WHEAT, overrides) == 0.55
    assert co.cost("spring_others", "Spring grazing crash", WHEAT, overrides) == 12.0


def test_defining_one_slot_leaves_the_others_alone() -> None:
    overrides = custom.parse(_pack(spring_1={"name": "Mine"}))

    names = co.names("spring_others", overrides)
    assert names == ["None", "Mine", "Custom spring option 2"]
    assert co.control("spring_others", "Mine", WHEAT, overrides) == \
           co.control("spring_others", "Custom spring option 1", WHEAT)


def test_a_defined_option_never_leaks_into_the_default_registry() -> None:
    """One Streamlit server serves many browsers; this must stay per-scenario."""
    overrides = custom.parse(_pack(harvest_1={"name": "Impact mill"}))

    assert "Impact mill" in co.names("harvest_others", overrides)
    assert "Impact mill" not in co.names("harvest_others")


def test_per_crop_exceptions_are_honoured() -> None:
    overrides = custom.parse(_pack(spring_1={
        "control": {"default": 0.6, "Canola": 0.0},
        "cost_per_ha": {"default": 10.0, "Wheat": 14.0},
    }))

    assert co.control("spring_others", "Custom spring option 1", WHEAT, overrides) == 0.6
    assert co.control("spring_others", "Custom spring option 1", CANOLA, overrides) == 0.0
    assert co.cost("spring_others", "Custom spring option 1", WHEAT, overrides) == 14.0
    assert co.cost("spring_others", "Custom spring option 1", CANOLA, overrides) == 10.0


def test_a_zero_control_stops_the_option_being_offered() -> None:
    """The same reading the workbook's own zeros already get."""
    overrides = custom.parse(_pack(spring_1={"control": {"default": 0.6, "Canola": 0.0}}))

    assert "Custom spring option 1" in co.usable_names("spring_others", WHEAT, overrides)
    assert "Custom spring option 1" not in co.usable_names("spring_others", CANOLA, overrides)


def test_a_renamed_slot_still_answers_to_its_old_name() -> None:
    """Otherwise renaming would strand every plan that used it."""
    overrides = custom.parse(_pack(spring_1={"name": "Spring grazing crash"}))

    assert co.canonical("spring_others", "Custom spring option 1", overrides) == \
           "Spring grazing crash"


@pytest.mark.parametrize("payload, expected", [
    ({"options": {}}, "not a RIM Online options file"),
    (_pack(), "defines no options"),
    (_pack(spring_9={"name": "x"}), "Unknown slot"),
    (_pack(spring_1={}), "defines nothing"),
    (_pack(spring_1={"name": "  "}), "non-empty string"),
    (_pack(spring_1={"control": {"Wheat": 0.5}}), "needs a 'default'"),
    (_pack(spring_1={"control": {"default": 1.5}}), "outside 0.0 to 1.0"),
    (_pack(spring_1={"control": {"default": 0.5, "Sorghum": 0.2}}),
     "crops this model does not have"),
    (_pack(spring_1={"cost_per_ha": {"default": -1}}), "outside 0.0"),
    (_pack(spring_1={"control": "lots"}), "should be a number"),
])
def test_a_bad_options_file_says_what_is_wrong(payload, expected) -> None:
    with pytest.raises(custom.CustomOptionError, match=expected):
        custom.parse(payload)


def test_a_bare_number_is_accepted_as_the_default() -> None:
    overrides = custom.parse(_pack(spring_1={"control": 0.4, "cost_per_ha": 9}))

    assert co.control("spring_others", "Custom spring option 1", WHEAT, overrides) == 0.4
    assert co.cost("spring_others", "Custom spring option 1", VOLUNTEER, overrides) == 9.0


def test_defined_options_reach_the_engine_and_the_bill(save_file) -> None:
    overrides = custom.parse(_pack(harvest_1={
        "name": "Impact mill", "control": {"default": 0.95},
        "cost_per_ha": {"default": 30.0},
    }))
    base = scenarios.default().as_save_payload()
    plain = scenarios.from_payload(base)

    with_mill = scenarios.from_payload({
        **base,
        "options": {**base["options"],
                    "custom_options": {str(r): s for r, s in overrides.items()}},
        "strategy": [dict(row, harvest_others="Impact mill")
                     for row in base["strategy"]],
    })

    before = run_scenario.simulate(plain)
    after = run_scenario.simulate(with_mill)

    assert float(after["yearly"]["weed_control_cost"].iloc[0]) == pytest.approx(
        float(before["yearly"]["weed_control_cost"].iloc[0]) + 30.0)
    assert float(after["yearly"]["ryegrass_plants_m2"].iloc[0]) < \
           float(before["yearly"]["ryegrass_plants_m2"].iloc[0])


# -- The command-line runner --------------------------------------------------


def test_it_runs_the_shipped_default_with_no_arguments(capsys) -> None:
    assert run_scenario.main([]) == 0

    printed = capsys.readouterr().out
    assert "default" in printed
    assert "nominal annuity" in printed


def test_it_runs_several_scenarios_at_once(save_file, capsys) -> None:
    base = scenarios.default().as_save_payload()
    one = save_file(base, "broomehill.rim.json")
    two = save_file(base, "kojonup.rim.json")

    assert run_scenario.main([str(one), str(two)]) == 0

    printed = capsys.readouterr().out
    assert "broomehill" in printed and "kojonup" in printed


def test_an_options_file_applies_before_the_plan_is_read(save_file, tmp_path, capsys) -> None:
    """The plan is canonicalised against the options, so order matters.

    Injecting the definitions afterwards would leave the name unrecognised and
    the choice silently cleared -- which is exactly what happened first time.
    """
    base = scenarios.default().as_save_payload()
    base["strategy"] = [dict(row, harvest_others="Impact mill")
                        for row in base["strategy"]]
    plan = save_file(base, "milled.rim.json")

    options = tmp_path / "opts.json"
    options.write_text(json.dumps(_pack(harvest_1={
        "name": "Impact mill", "control": {"default": 0.95},
        "cost_per_ha": {"default": 30.0}})), encoding="utf-8")

    loaded = run_scenario.load_all([str(plan)], str(options))

    assert loaded[0].strategy[0]["harvest_others"] == "Impact mill"
    assert run_scenario.main([str(plan), "--options", str(options)]) == 0


def test_it_reports_a_plan_the_model_would_ignore(save_file, capsys) -> None:
    base = scenarios.default().as_save_payload()
    base["strategy"] = [dict(row, crop="Canola", post_emergent_1="Topik")
                        for row in base["strategy"]]

    code = run_scenario.main([str(save_file(base, "wrong.rim.json"))])

    assert code == 0, "a warning, not a failure, unless --strict"
    assert "decision(s) the model ignores" in capsys.readouterr().err


def test_strict_refuses_a_plan_the_model_would_ignore(save_file) -> None:
    base = scenarios.default().as_save_payload()
    base["strategy"] = [dict(row, crop="Canola", post_emergent_1="Topik")
                        for row in base["strategy"]]

    assert run_scenario.main(
        [str(save_file(base, "wrong.rim.json")), "--strict"]
    ) == 1


def test_a_broken_file_fails_without_a_traceback(tmp_path, capsys) -> None:
    bad = tmp_path / "bad.rim.json"
    bad.write_text("{not json", encoding="utf-8")

    assert run_scenario.main([str(bad)]) == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("fmt, expected", [
    ("csv", "summary.csv"),
    ("json", "results.json"),
    ("excel", "results.xlsx"),
])
def test_it_writes_the_formats_it_offers(tmp_path, fmt, expected) -> None:
    out = tmp_path / "results"

    assert run_scenario.main(["--format", fmt, "--out", str(out), "--quiet"]) == 0
    assert (out / expected).is_file()


def test_a_file_format_without_a_destination_says_so() -> None:
    with pytest.raises(SystemExit, match="needs --out"):
        run_scenario.main(["--format", "csv"])


def test_json_output_carries_every_year(capsys) -> None:
    assert run_scenario.main(["--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert len(payload["yearly"]["default"]) == 10
    assert payload["summaries"][0]["scenario"] == "default"


# -- The app's own export is the CLI's input ----------------------------------


class FakeState(dict):
    """Stand-in for st.session_state, which supports attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_the_file_the_app_saves_is_the_file_the_runner_reads(monkeypatch, tmp_path, capsys) -> None:
    """The contract between the two ends: one format, written once, read once.

    This drives utils.session.export_bytes -- the bytes behind the app's own
    Save button -- and feeds them straight to the command line, so a divergence
    between what the app writes and what the runner accepts fails here rather
    than in someone's hands.
    """
    import utils.session as session
    from rim.defaults import (DEFAULT_OPTIONS, DEFAULT_PRICES, DEFAULT_PROFILE,
                              build_default_strategy)

    overrides = custom.parse(_pack(harvest_1={
        "name": "Impact mill", "control": {"default": 0.95},
        "cost_per_ha": {"default": 30.0}}))

    state = FakeState(
        profile_current={**DEFAULT_PROFILE, "farm_name": "Wickepin"},
        prices_current=dict(DEFAULT_PRICES),
        options_current={**DEFAULT_OPTIONS,
                         "custom_options": {str(r): s for r, s in overrides.items()}},
        strategy_current=[dict(row, harvest_others="Impact mill")
                          for row in build_default_strategy(10)],
        profile_slots={}, strategy_slots={},
    )
    monkeypatch.setattr(session.st, "session_state", state)

    saved = tmp_path / "wickepin.rim.json"
    saved.write_bytes(session.export_bytes())

    scenario = scenarios.load(saved)

    assert scenario.name == "wickepin"
    assert scenario.profile["farm_name"] == "Wickepin"
    assert scenario.custom_options is not None, "the user's own options travelled"
    assert scenario.strategy[0]["harvest_others"] == "Impact mill"

    assert run_scenario.main([str(saved), "--quiet"]) == 0

    # And the option it carries is actually priced, not just carried.
    result = run_scenario.simulate(scenario)
    plain = run_scenario.simulate(scenarios.default())
    assert float(result["yearly"]["weed_control_cost"].iloc[0]) == pytest.approx(
        float(plain["yearly"]["weed_control_cost"].iloc[0]) + 30.0)


def test_the_two_ends_agree_on_the_format_name_and_version() -> None:
    """Two modules name the format; they must not drift apart."""
    import utils.session as session

    assert session.SAVE_FORMAT_VERSION == scenarios.SAVE_FORMAT_VERSION
    assert session.export_bundle.__doc__  # sanity: still the documented path
