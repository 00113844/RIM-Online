"""Verify rim.population reproduces Bio results!D3:D8 and D11:D16 exactly.

Expected values come from each fixture's ``reference.tabsum``, which is the
workbook's own TabSum block -- six ryegrass plant stages and the seed bank at
six points through the season, for every year.

Everything feeding the cascade is computed by the ported blocks: rotation codes,
activation, survival factors and stage multipliers. Only the year's opening seed
bank is taken from Excel, because closing the year is block 5.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rim.population import (
    COHORTS,
    germination_fractions,
    grazing_survival,
    load_germination,
    load_table8,
    plough_burial,
    run_season,
    starting_seed_bank,
)
from tests.chain import TABSUM_ROWS, fixtures, walk

RELATIVE_TOLERANCE = 1e-9


@pytest.mark.parametrize("fixture_path", fixtures(), ids=lambda p: p.stem)
def test_season_matches_tabsum(fixture_path: Path) -> None:
    for year in walk(fixture_path):
        rows = year.result.season.as_rows()
        for caption, row in TABSUM_ROWS.items():
            expected = year.tabsum[caption]
            if expected is None:
                continue
            assert rows[row] == pytest.approx(float(expected), rel=RELATIVE_TOLERANCE), (
                f"{fixture_path.stem}, year {year.year}, Bio results!D{row} "
                f"({caption}): expected {expected}, got {rows[row]}"
            )


def test_year_one_seed_bank_is_the_workbook_default() -> None:
    """Bio results!D11 for year 1 is '+Options'!AG96 * AG124."""
    assert starting_seed_bank() == pytest.approx(1000.0)


def test_ploughing_buries_seed_at_one_cohort_boundary_only() -> None:
    """Calcs!C159/C160 -- which boundary depends on +delayed sowing."""
    burial = 1.0 - float(load_germination()["plough_seed_burial"]["value"])

    assert plough_burial({}) == (1.0, 1.0)
    assert plough_burial({17: 0}) == (pytest.approx(burial), 1.0)
    assert plough_burial({17: 0, 22: 0}) == (1.0, pytest.approx(burial))


def test_germination_column_follows_tillage_and_establishment() -> None:
    """Calcs!C151 picks one of six columns; a sown paddock uses +Options 115-119."""
    germination = load_germination()

    plain = germination_fractions({}, sown=True)
    full_cut = germination_fractions({18: 0}, sown=True)
    tickled = germination_fractions({16: 0}, sown=True)
    regenerating = germination_fractions({}, sown=False)

    assert plain == tuple(germination["sown"]["no_tickle_no_till"])
    assert full_cut == tuple(germination["sown"]["no_tickle_full_cut"])
    assert tickled == tuple(germination["sown"]["tickle_no_till"])
    assert regenerating == tuple(germination["regenerating"]["no_tickle"])
    assert len(plain) == COHORTS


def test_ploughing_counts_as_disturbance_for_germination() -> None:
    """Calcs!C151 tests OR(C16,C17) -- tickle or plough, either one."""
    assert germination_fractions({17: 0}, sown=True) == germination_fractions(
        {16: 0}, sown=True
    )


def test_grazing_reduces_ryegrass_by_the_table_8_fraction() -> None:
    """Calcs!C314 = 1 - C311 - C313, keyed on the rotation key.

    Rotation key 7 is the first year of a clover phase, which Table 8 gives 50%
    ryegrass control under standard grazing and 85% under high grazing.
    """
    entry = load_table8()["by_key"]["7"]

    assert grazing_survival({}, 7) == pytest.approx(1.0)
    assert grazing_survival({28: 5}, 7) == pytest.approx(
        1.0 - entry["ryegrass_control_standard_grazing"]
    )
    assert grazing_survival({29: 5}, 7) == pytest.approx(
        1.0 - entry["ryegrass_control_high_grazing"]
    )


def test_fodder_cancels_grazing() -> None:
    """Calcs!C322/C324 -- a paddock cut for hay or manured is not grazed."""
    assert grazing_survival({28: 5, 35: 5}, 7) == pytest.approx(1.0)
    assert grazing_survival({29: 5, 34: 5}, 7) == pytest.approx(1.0)


def test_high_grazing_supersedes_standard() -> None:
    """Calcs!C310 returns 0 when high grazing is also selected."""
    entry = load_table8()["by_key"]["7"]

    both = grazing_survival({28: 5, 29: 5}, 7)
    assert both == pytest.approx(1.0 - entry["ryegrass_control_high_grazing"])


def test_new_cohorts_take_the_pre_emergent_not_the_stage_multiplier() -> None:
    """Bio results!D4:D6 -- an emerging cohort meets C167, not C164/C165/C166.

    A pre-emergent is still active in the soil when later cohorts come up, so
    they are controlled by it rather than by the spray the standing plants met.
    """
    multipliers = {164: 0.0, 165: 1.0, 166: 1.0, 167: 0.5, 168: 1.0, 169: 1.0}
    state = run_season(
        1000.0, [0.1, 0.2, 0.0, 0.0, 0.0], multipliers, seed_loss_pre_harvest=0.0
    )

    # D3 = 1000*0.1 = 100, all killed by C164 = 0.
    # D4 = 100*0 + (1000*0.9)*0.2*0.5 = 90.
    assert state.plants[0] == pytest.approx(100.0)
    assert state.plants[1] == pytest.approx(90.0)


def test_seed_bank_and_plants_are_complementary() -> None:
    """What germinates leaves the seed bank: D12 = D11 - D3 when nothing else acts."""
    state = run_season(
        1000.0,
        [0.25, 0.0, 0.0, 0.0, 0.0],
        {164: 1.0, 165: 1.0, 166: 1.0, 167: 1.0, 168: 1.0, 169: 1.0},
        seed_loss_pre_harvest=0.0,
    )

    assert state.plants[0] == pytest.approx(250.0)
    assert state.seed_bank[1] == pytest.approx(750.0)
    assert state.seed_bank[0] - state.plants[0] == pytest.approx(state.seed_bank[1])


def test_wrong_cohort_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="germination fractions"):
        run_season(
            1000.0, [0.1, 0.2], {r: 1.0 for r in range(164, 170)},
            seed_loss_pre_harvest=0.0,
        )


def test_tables_are_generated_with_provenance() -> None:
    assert load_germination()["_source"]["generated_by"] == "tools/extract_params.py"
    assert load_table8()["_source"]["ranges"]["table"] == "Calcs!C193:M291"
    assert load_table8()["by_key"]["0"]["label"] == "Wheat"
