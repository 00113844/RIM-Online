"""Every chart builder must render in both scale modes.

The Fixed scale path shipped broken: `gross_margin_and_ryegrass_chart` asked for
`secondary_y`, which only exists on figures built with `make_subplots`, while
these overlay `yaxis2` by hand. Nothing exercised it, so it reached a deployed
app and raised the moment a user chose Fixed on the Economics page.

These are cheap and catch that whole class of fault: build every chart, both
modes, and assert the axis limits actually land.
"""
from __future__ import annotations

import pandas as pd
import pytest

from utils import charts

BUILDERS = (
    charts.gross_margin_and_ryegrass_chart,
    charts.weed_cost_chart,
    charts.income_breakdown_chart,
    charts.seedbank_population_chart,
)

DUAL_AXIS = {
    charts.gross_margin_and_ryegrass_chart:
        (charts.FIXED_MARGIN_RANGE, charts.FIXED_RYEGRASS_RANGE),
    charts.seedbank_population_chart:
        (charts.FIXED_PLANTS_RANGE, charts.FIXED_SEEDBANK_RANGE),
}


def _frame() -> pd.DataFrame:
    """A yearly frame shaped like simulate_strategy()'s, with realistic spread."""
    years = list(range(1, 11))
    return pd.DataFrame({
        "year": years,
        "crop": ["Wheat"] * 10,
        "gross_margin": [22.4, -18.6, 229.3, -138.4, 97.4, 130.4, 119.7, 319.2, 182.5, 71.3],
        "weed_control_cost": [58.2, 101.2, 83.5, 40.1, 16.0, 38.0, 48.7, 50.2, 48.0, 98.7],
        "income_grain": [597.8, 637.0, 753.0, 0.0, 0.0, 0.0, 0.0, 736.7, 697.7, 610.2],
        "income_pasture": [0.0] * 3 + [110.0, 192.5, 247.5, 247.5] + [0.0] * 3,
        "income_livestock": [0.0] * 10,
        "ryegrass_plants_m2": [52.5, 7.5, 0.4, 2.4, 13.8, 51.7, 7.2, 48.4, 24.7, 8.6],
        "seed_bank_end": [184.9, 26.0, 12.5, 127.7, 747.4, 1049.7, 289.7, 185.5, 518.1, 83.8],
        "yield_potential_t_ha": [1.8] * 10,
        "yield_t_ha": [1.57, 1.67, 0.96, 0.0, 0.0, 0.0, 0.0, 1.93, 1.83, 0.78],
        "ryegrass_penalty_fraction": [0.07, 0.01, 0.01, 0.0, 0.0, 0.0, 0.0, 0.06, 0.03, 0.2],
    })


@pytest.mark.parametrize("builder", BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize("fixed", [False, True], ids=["auto", "fixed"])
def test_builder_renders(builder, fixed: bool) -> None:
    figure = builder(_frame(), fixed_scale=fixed)

    assert figure.data, f"{builder.__name__} produced no traces"


def test_yield_and_comparison_charts_render() -> None:
    """These two take no scale flag, but must still build."""
    frame = _frame()

    assert charts.yield_comparison_chart(frame).data
    assert charts.comparison_chart(
        {"A": (frame["year"], frame["gross_margin"]),
         "B": (frame["year"], frame["weed_control_cost"])}
    ).data


@pytest.mark.parametrize("builder", list(DUAL_AXIS), ids=lambda b: b.__name__)
def test_fixed_scale_sets_both_axes(builder) -> None:
    """A dual-axis chart has to pin the right-hand axis too, or Fixed is a lie."""
    primary, secondary = DUAL_AXIS[builder]
    figure = builder(_frame(), fixed_scale=True)

    assert list(figure.layout.yaxis.range) == primary
    assert list(figure.layout.yaxis2.range) == secondary


@pytest.mark.parametrize("builder", list(DUAL_AXIS), ids=lambda b: b.__name__)
def test_auto_scale_pins_nothing(builder) -> None:
    figure = builder(_frame(), fixed_scale=False)

    assert figure.layout.yaxis.range is None
    assert figure.layout.yaxis2.range is None


def test_fixed_scale_keeps_the_axis_styling() -> None:
    """update_layout merges, so the fonts set before the range must survive."""
    figure = charts.gross_margin_and_ryegrass_chart(_frame(), fixed_scale=True)

    assert figure.layout.yaxis2.title.text == "plants/m²"
    assert figure.layout.yaxis2.showgrid is False
