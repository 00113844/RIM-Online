"""Verify rim.seed_set reproduces Bio results!D17:D20 and Calcs!C174:C177.

The end-to-end match lives in tests/test_full_biology.py. These are the
behaviours worth stating separately, because each encodes a piece of agronomy
that a reader of the formulas alone would have to reverse-engineer.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rim.seed_set import (
    close_year,
    cohort_competitiveness,
    crop_competition,
    herbicide_applications,
    load_parameters,
    spring_spray_operations,
)
from tests.chain import TABSUM_CLOSING_ROWS, fixtures, walk

RELATIVE_TOLERANCE = 1e-9

CAPTION_TO_ATTR = {
    "seed_produced_per_plant": "seed_per_plant",
    "seed_produced_per_m2": "seed_produced",
    "just_before_harvest": "before_harvest",
    "seeds_next_autumn": "next_autumn",
}


@pytest.mark.parametrize("fixture_path", fixtures(), ids=lambda p: p.stem)
def test_closing_rows_match_excel(fixture_path: Path) -> None:
    for year in walk(fixture_path):
        for caption, attribute in CAPTION_TO_ATTR.items():
            expected = year.tabsum[caption]
            if expected is None:
                continue
            actual = getattr(year.result.close, attribute)
            assert actual == pytest.approx(float(expected), rel=RELATIVE_TOLERANCE), (
                f"{fixture_path.stem}, year {year.year}, "
                f"Bio results!D{TABSUM_CLOSING_ROWS[caption]} ({caption}): "
                f"expected {expected}, got {actual}"
            )


def test_later_cohorts_compete_less() -> None:
    """+Options!AG142:AG145 -- a plant that emerges late barely competes."""
    dry = cohort_competitiveness({19: 0})

    assert dry[0] == 1.0
    assert list(dry) == sorted(dry, reverse=True)
    assert dry[-1] < 0.1


def test_later_sowing_gives_later_cohorts_more_standing() -> None:
    """Sow later and the late cohorts emerge nearer the crop, so they compete more."""
    dry_or_wet = cohort_competitiveness({20: 0})
    delayed = cohort_competitiveness({21: 0})
    plus_delayed = cohort_competitiveness({22: 0})

    assert delayed[1] > dry_or_wet[1]
    assert plus_delayed[2] > delayed[2]


def test_high_seeding_rate_suppresses_ryegrass_seed_set() -> None:
    """Calcs!C15 raises plant density, which enlarges the competition term.

    This is the mechanism behind the 'high seeding rate' strategy option: a
    thicker crop leaves ryegrass less room to set seed.
    """
    standard = crop_competition(0, high_seeding_rate=False)
    high = crop_competition(0, high_seeding_rate=True)

    assert high > standard


def test_pasture_uses_a_flat_competition_figure() -> None:
    """+Options!AS182 stands in for all three pasture types."""
    parameters = load_parameters()

    for crop_code in (4, 5, 6):
        assert crop_competition(crop_code, False) == parameters["pasture_competition"]


def test_a_more_competitive_crop_suppresses_seed_set() -> None:
    """Bio results!D17 -- crop competition sits in the denominator.

    Sowing at a high rate raises plant density, which raises the competition
    term and cuts ryegrass seed production. This is the whole point of the
    "high seeding rate" strategy option.
    """
    def close(activation):
        return close_year(
            activation=activation, crop_code=0, plants_spray_time=100.0,
            plants_mature=100.0, seed_bank_spring=0.0, weighted_density=50.0,
            harvest_multiplier=1.0, herbicide_count=0, spring_spray_count=0,
            summer_seed_loss=0.0,
        )

    standard = close({})
    high_rate = close({15: 0})

    assert high_rate.seed_per_plant < standard.seed_per_plant


def test_seed_per_weighted_plant_falls_as_the_stand_thickens() -> None:
    """The density response is per *weighted* plant, not per plant at spraying.

    D17 is ``max_seed / (constant + C177 + crop) * C177 / D7``. The second
    factor converts from weighted plants to the plants standing at spraying
    time, so D17 itself is not monotone in C177 when D7 is held artificially
    fixed. Scaling the stand -- which is what actually happens -- shows the
    crowding response.
    """
    def per_weighted_plant(density: float) -> float:
        result = close_year(
            activation={}, crop_code=0, plants_spray_time=density,
            plants_mature=density, seed_bank_spring=0.0, weighted_density=density,
            harvest_multiplier=1.0, herbicide_count=0, spring_spray_count=0,
            summer_seed_loss=0.0,
        )
        return result.seed_per_plant

    assert per_weighted_plant(1000.0) < per_weighted_plant(10.0)


def test_phytotoxicity_discounts_apply_independently() -> None:
    """Bio results!D17 -- one discount for herbicides, one for spring sprays."""
    parameters = load_parameters()

    def close(herbicides: int, sprays: int):
        return close_year(
            activation={}, crop_code=0, plants_spray_time=100.0, plants_mature=100.0,
            seed_bank_spring=0.0, weighted_density=50.0, harvest_multiplier=1.0,
            herbicide_count=herbicides, spring_spray_count=sprays, summer_seed_loss=0.0,
        )

    base = close(0, 0).seed_per_plant
    herb = 1.0 - parameters["phytotoxicity_herbicides"]["value"]
    spray = 1.0 - parameters["phytotoxicity_spring_sprays"]["value"]

    assert close(1, 0).seed_per_plant == pytest.approx(base * herb)
    assert close(0, 1).seed_per_plant == pytest.approx(base * spray)
    assert close(2, 3).seed_per_plant == pytest.approx(base * herb * spray)


def test_harvest_control_acts_only_on_newly_set_seed() -> None:
    """Bio results!D20 -- seed already shed on the ground never enters the header."""
    result = close_year(
        activation={}, crop_code=0, plants_spray_time=100.0, plants_mature=0.0,
        seed_bank_spring=500.0, weighted_density=50.0, harvest_multiplier=0.0,
        herbicide_count=0, spring_spray_count=0, summer_seed_loss=0.0,
    )

    # No plants set seed, so the whole 500 survives despite 100% harvest control.
    assert result.next_autumn == pytest.approx(500.0)


def test_summer_loss_applies_to_everything_carried_over() -> None:
    result = close_year(
        activation={}, crop_code=0, plants_spray_time=100.0, plants_mature=0.0,
        seed_bank_spring=1000.0, weighted_density=50.0, harvest_multiplier=1.0,
        herbicide_count=0, spring_spray_count=0, summer_seed_loss=0.3,
    )

    assert result.next_autumn == pytest.approx(700.0)


def test_no_plants_at_spraying_time_closes_on_the_seed_bank_alone() -> None:
    """Excel raises #DIV/0! here; with no stand there is no seed to set."""
    result = close_year(
        activation={}, crop_code=0, plants_spray_time=0.0, plants_mature=0.0,
        seed_bank_spring=42.0, weighted_density=0.0, harvest_multiplier=1.0,
        herbicide_count=0, spring_spray_count=0, summer_seed_loss=0.0,
    )

    assert result.seed_per_plant == 0.0
    assert result.next_autumn == pytest.approx(42.0)


def test_application_counts_drive_the_discounts() -> None:
    """Calcs!P48 counts herbicides; Calcs!P49 counts spring sprays."""
    assert herbicide_applications({10: 0, 11: 0}, {23: 2}) == 4
    assert herbicide_applications({}, {}) == 0
    assert spring_spray_operations({40: 0, 35: 0}) == 2
    assert spring_spray_operations({}) == 0
