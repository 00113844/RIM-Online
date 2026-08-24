"""The whole biological model, ten years, driven by nothing but the strategy.

This is the test the project existed to make possible. Blocks 1-5 chain through
``rim.calcs.simulate_years``: the strategy grid and the paddock history go in,
and every cell of the workbook's ``TabSum`` block comes out -- six ryegrass
plant stages, ten seed-bank quantities, for each of ten years.

No Excel intermediate is supplied. Years are joined only by the seed bank
(``Bio results!E11 = D20``), so an error in any year compounds into every year
after it; matching to floating-point noise across a full run is a much stronger
statement than matching year by year with Excel's own values fed back in.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rim.calcs import simulate_years
from tests.chain import TABSUM_CLOSING_ROWS, TABSUM_ROWS, fixtures, walk

# Every quantity TabSum reports.
ALL_ROWS = {**TABSUM_ROWS, **TABSUM_CLOSING_ROWS}

# Excel and Python both use IEEE doubles and the same operation order, so the
# only expected difference is accumulated rounding.
RELATIVE_TOLERANCE = 1e-12


@pytest.mark.parametrize("fixture_path", fixtures(), ids=lambda p: p.stem)
def test_tabsum_reproduced_end_to_end(fixture_path: Path) -> None:
    for year in walk(fixture_path):
        produced = year.result.tabsum()
        for caption in ALL_ROWS:
            expected = year.tabsum[caption]
            if expected is None:
                continue
            assert produced[caption] == pytest.approx(
                float(expected), rel=RELATIVE_TOLERANCE
            ), (
                f"{fixture_path.stem}, year {year.year}, "
                f"Bio results!D{ALL_ROWS[caption]} ({caption}): "
                f"expected {expected}, got {produced[caption]}"
            )


@pytest.mark.parametrize("fixture_path", fixtures(), ids=lambda p: p.stem)
def test_seed_bank_is_the_only_thread_between_years(fixture_path: Path) -> None:
    """Bio results!E11 = D20 -- each year opens where the last one closed."""
    previous = None
    for year in walk(fixture_path):
        if previous is not None:
            assert year.result.season.seed_bank[0] == pytest.approx(
                previous.result.seed_bank_next_autumn, rel=RELATIVE_TOLERANCE
            )
        previous = year


def test_year_one_starts_from_the_workbook_default() -> None:
    results = simulate_years([{"enterprise": "Wheat"}])

    assert results[0].season.seed_bank[0] == pytest.approx(1000.0)


def test_uncontrolled_ryegrass_reaches_a_ceiling() -> None:
    """Ten years of wheat with no control: the population saturates.

    The captured Excel scenario settles near 18,763 plants/m2 with a seed bank
    around 25,362 -- behaviour the pre-port engine had no way to produce, since
    it had no density-dependent seed set.
    """
    strategy = [{"enterprise": "Wheat", "time_of_sowing": "Wet",
                 "establishment_system": "No-till"} for _ in range(10)]

    results = simulate_years(strategy)
    late = [r.mature_plants for r in results[-3:]]

    assert late[-1] > 10_000
    # Successive years differ by well under a percent once saturated.
    assert late[-1] == pytest.approx(late[-2], rel=1e-3)


def test_control_drives_the_population_down() -> None:
    """A full herbicide programme should collapse the stand relative to none."""
    def strategy(**extra):
        return [{"enterprise": "Wheat", "time_of_sowing": "Wet",
                 "establishment_system": "No-till", **extra} for _ in range(10)]

    uncontrolled = simulate_years(strategy())
    controlled = simulate_years(
        strategy(pre_emergent="Sakura", post_emergent_1="Topik")
    )

    assert controlled[-1].mature_plants < uncontrolled[-1].mature_plants / 100
