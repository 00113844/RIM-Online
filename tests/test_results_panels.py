"""Holding the same plan as A and as B must not kill the results pages.

Streamlit gives an element an id derived from its type and its arguments. Hold
one plan as both A and B and the two figures are byte-identical, so both charts
claim the same id and the page dies:

    StreamlitDuplicateElementId: There are multiple `plotly_chart` elements
    with the same auto-generated ID.

Two things follow, and both are here: every chart carries a key of its own, so
identical panels can coexist; and the page says plainly that A and B are the
same plan, because comparing something with itself is a mistake worth naming
rather than a state worth rendering twice.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from utils.results_view import panel_key

RESULTS_PAGES = (
    "pages/3_Results_Population.py",
    "pages/3_Results_Economics.py",
    "pages/3_Results_Yields.py",
    "pages/2_Strategy.py",
)


# -- Keys ---------------------------------------------------------------------


def test_a_key_is_stable_and_readable() -> None:
    assert panel_key("seedbank", "Strategy A") == "seedbank_strategy_a"
    assert panel_key("seedbank", "Current plan") == "seedbank_current_plan"


def test_two_panels_never_share_a_key() -> None:
    """The A/B case that crashed."""
    assert panel_key("seedbank", "Strategy A") != panel_key("seedbank", "Strategy B")


def test_two_charts_in_one_panel_never_share_a_key() -> None:
    """The tabs on the yields and economics pages."""
    assert panel_key("yield", "Strategy A") != panel_key("penalty", "Strategy A")


@pytest.mark.parametrize("path", RESULTS_PAGES)
def test_every_chart_on_every_page_is_given_a_key(path) -> None:
    """A chart without one is a duplicate-id crash waiting for two panels."""
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))

    charts = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "plotly_chart"
    ]

    assert charts, f"{path}: no charts found — has the page changed shape?"
    for chart in charts:
        keys = {kw.arg for kw in chart.keywords}
        assert "key" in keys, f"{path} line {chart.lineno}: plotly_chart has no key"


# -- The deprecated width argument --------------------------------------------


def test_nothing_still_uses_use_container_width() -> None:
    """Removed from Streamlit after 2025-12-31; `width=` replaced it."""
    offenders = [
        str(path)
        for path in list(pathlib.Path("pages").glob("*.py"))
                  + list(pathlib.Path("utils").glob("*.py"))
                  + [pathlib.Path("app.py")]
        if "use_container_width" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_the_requirements_floor_supports_width() -> None:
    """`width=` does not exist in the version we used to advertise."""
    requirements = pathlib.Path("requirements.txt").read_text(encoding="utf-8")
    pinned = next(line for line in requirements.splitlines()
                  if line.startswith("streamlit"))
    floor = tuple(int(part) for part in pinned.split(">=")[1].split("."))

    assert floor >= (1, 50)


# -- Saying so ----------------------------------------------------------------


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
    import utils.results_view as view

    fake = FakeState()
    monkeypatch.setattr(view.st, "session_state", fake)
    return fake


def test_two_holds_of_one_plan_are_recognised(state) -> None:
    from utils.results_view import held_plans_are_the_same

    plan = [{"year": 1, "crop": "Wheat"}]
    state["results_A_strategy"] = [dict(row) for row in plan]
    state["results_B_strategy"] = [dict(row) for row in plan]

    assert held_plans_are_the_same()


def test_two_different_plans_are_not(state) -> None:
    from utils.results_view import held_plans_are_the_same

    state["results_A_strategy"] = [{"year": 1, "crop": "Wheat"}]
    state["results_B_strategy"] = [{"year": 1, "crop": "Canola"}]

    assert not held_plans_are_the_same()


def test_holding_only_one_is_not_a_match(state) -> None:
    from utils.results_view import held_plans_are_the_same

    state["results_A_strategy"] = [{"year": 1, "crop": "Wheat"}]

    assert not held_plans_are_the_same()


# -- Holding and releasing keeps the plan beside the numbers ------------------


def test_holding_remembers_the_plan_not_only_the_numbers(monkeypatch) -> None:
    import utils.session as session

    fake = FakeState(
        strategy_current=[{"year": 1, "crop": "Wheat"}],
        results_current={"summary": {}, "yearly": None},
    )
    monkeypatch.setattr(session.st, "session_state", fake)

    session.freeze_results("A")

    assert fake["results_A"] == {"summary": {}, "yearly": None}
    assert fake["results_A_strategy"] == [{"year": 1, "crop": "Wheat"}]

    fake["strategy_current"][0]["crop"] = "Canola"
    assert fake["results_A_strategy"][0]["crop"] == "Wheat", "held, not referenced"


def test_releasing_forgets_the_plans_too(monkeypatch) -> None:
    """A stale held plan would make the sameness check answer about nothing."""
    import utils.session as session

    fake = FakeState(
        results_A={"x": 1}, results_B={"x": 1},
        results_A_strategy=[{"crop": "Wheat"}],
        results_B_strategy=[{"crop": "Wheat"}],
    )
    monkeypatch.setattr(session.st, "session_state", fake)

    session.release_results()

    assert fake["results_A"] is None and fake["results_B"] is None
    assert "results_A_strategy" not in fake
    assert "results_B_strategy" not in fake
