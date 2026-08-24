"""Verify rim.activation reproduces Calcs!C7:C49 exactly.

This closes the chain. Blocks 1, 3 and 3b were each tested against Excel using
Excel's own intermediates as input; block 2 supplies the missing link, so
``test_full_chain_from_strategy_grid`` can start from nothing but the strategy
grid and reach the stage multipliers.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim.activation import (
    ROWS,
    activation_cells,
    is_sown,
    knockdown_counts,
    load_vocabulary,
)
from rim.rotation import history_columns, rotation_codes
from rim.stage_multipliers import MULTIPLIER_ROWS, stage_multipliers
from rim.survival import survival_factors

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "excel_parity"
MANIFEST = FIXTURE_DIR / "manifest.json"

TOLERANCE = 1e-9


def _fixtures() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [FIXTURE_DIR / name for name in manifest["scenarios"]]


def _chain_inputs(fixture_path: Path):
    """Derive each year's crop code and its two predecessors, as Calcs does."""
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    excel = fixture["inputs"]["excel"]
    strategy, history = excel["strategy"], excel["history"]

    codes = rotation_codes([row.get("enterprise") for row in strategy], **history)
    two_ago, one_ago = history_columns(**history)

    previous = [one_ago.crop_code] + [c.crop_code for c in codes[:-1]]
    before = [two_ago.crop_code, one_ago.crop_code] + [c.crop_code for c in codes[:-2]]
    return fixture, strategy, codes, previous, before


@pytest.mark.parametrize("fixture_path", _fixtures(), ids=lambda p: p.stem)
def test_activation_matches_excel(fixture_path: Path) -> None:
    fixture, strategy, codes, previous, before = _chain_inputs(fixture_path)
    expected_years = fixture["reference"]["activation"]

    for year_strategy, codes_row, prev, prev2, expected in zip(
        strategy, codes, previous, before, expected_years
    ):
        actual = activation_cells(
            year_strategy,
            crop_code=codes_row.crop_code,
            prev_crop_code=prev,
            prev2_crop_code=prev2,
        )
        for row in ROWS:
            want = expected.get(str(row))
            got = actual[row]
            if want is None:
                assert got is None, (
                    f"{fixture_path.stem}, year {expected['year']}, Calcs!C{row}: "
                    f"expected blank, got {got}"
                )
            else:
                assert got == pytest.approx(float(want), abs=TOLERANCE), (
                    f"{fixture_path.stem}, year {expected['year']}, Calcs!C{row}: "
                    f"expected {want}, got {got}"
                )


@pytest.mark.parametrize("fixture_path", _fixtures(), ids=lambda p: p.stem)
def test_full_chain_from_strategy_grid(fixture_path: Path) -> None:
    """Strategy grid -> rotation -> activation -> survival -> multipliers.

    Nothing from Excel is used as an intermediate here, only as the expected
    result. This is the first point at which the ported blocks stand alone.
    """
    fixture, strategy, codes, previous, before = _chain_inputs(fixture_path)
    expected_years = fixture["reference"]["stage_multipliers"]

    for year_strategy, codes_row, prev, prev2, expected in zip(
        strategy, codes, previous, before, expected_years
    ):
        activation = activation_cells(
            year_strategy,
            crop_code=codes_row.crop_code,
            prev_crop_code=prev,
            prev2_crop_code=prev2,
        )
        multipliers = stage_multipliers(
            activation,
            survival_factors(activation),
            crop_code=codes_row.crop_code,
            post_emergent_slots=[
                year_strategy.get(f"post_emergent_{n}") for n in (1, 2, 3)
            ],
            pre_emergent_selected=bool(year_strategy.get("pre_emergent")),
        )

        for row in MULTIPLIER_ROWS:
            if expected[str(row)] is None:
                continue
            assert multipliers[row] == pytest.approx(
                float(expected[str(row)]), abs=TOLERANCE
            ), (
                f"{fixture_path.stem}, year {expected['year']}, Calcs!C{row}: "
                f"expected {expected[str(row)]}, got {multipliers[row]}"
            )


def test_activation_writes_the_crop_code() -> None:
    """Calcs!C7:C49 write E$184, not a boolean -- that is what keys the lookup."""
    on_canola = activation_cells(
        {"enterprise": "Canola", "time_of_sowing": "Wet", "pre_emergent": "Sakura"},
        crop_code=2, prev_crop_code=0, prev2_crop_code=0,
    )

    assert on_canola[12] == 2.0
    assert on_canola[11] is None


def test_wet_sowing_is_the_default_not_a_label_match() -> None:
    """Calcs!C20: AND(C19="",C21="",C22="",D66="yes") -- the residual case."""
    unspecified = activation_cells(
        {"enterprise": "Wheat"}, crop_code=0, prev_crop_code=0, prev2_crop_code=0
    )
    delayed = activation_cells(
        {"enterprise": "Wheat", "time_of_sowing": "Delayed"},
        crop_code=0, prev_crop_code=0, prev2_crop_code=0,
    )

    assert unspecified[20] == 0.0
    assert delayed[20] is None
    assert delayed[21] == 0.0


def test_knockdown_gate_closes_when_there_is_no_gap_before_seeding() -> None:
    """2.Strategy!D65 -- dry and wet sowing suppress the knock-down's own effect."""
    vocabulary = load_vocabulary()

    assert knockdown_counts("Dry", sown=True, vocabulary=vocabulary) is False
    assert knockdown_counts("Wet", sown=True, vocabulary=vocabulary) is False
    assert knockdown_counts("Delayed", sown=True, vocabulary=vocabulary) is True
    # An unsown pasture always lets the knock-down through.
    assert knockdown_counts("Wet", sown=False, vocabulary=vocabulary) is True


def test_knockdown_gate_observed_in_the_saved_workbook() -> None:
    """The workbook picks Glyphosate in year 1 with wet sowing, and C7 stays blank."""
    cells = activation_cells(
        {"enterprise": "Wheat", "time_of_sowing": "Wet", "knock_down": "Glyphosate"},
        crop_code=0, prev_crop_code=0, prev2_crop_code=0,
    )
    delayed = activation_cells(
        {"enterprise": "Wheat", "time_of_sowing": "Delayed", "knock_down": "Glyphosate"},
        crop_code=0, prev_crop_code=0, prev2_crop_code=0,
    )

    assert cells[7] is None
    assert delayed[7] == 0.0


def test_sown_gate_covers_crops_and_first_year_pastures() -> None:
    """2.Strategy!D66 via Calcs!P46/P47 -- a regenerating pasture is not sown."""
    assert is_sown(0, 0, 0) is True                     # wheat
    assert is_sown(5, 0, 0) is True                     # first year of clover
    assert is_sown(5, 5, 0) is False                    # clover continuing
    assert is_sown(5, 0, 5) is False                    # clover within 2 years
    assert is_sown(6, 0, 0) is True                     # first year of Cadiz
    assert is_sown(6, 6, 0) is False                    # Cadiz continuing
    assert is_sown(4, 0, 0) is False                    # volunteer is never sown


def test_post_emergents_match_any_of_three_slots() -> None:
    """Calcs!C23:C27 test OR(D11=..., D12=..., D13=...)."""
    third_slot = activation_cells(
        {"enterprise": "Wheat", "post_emergent_3": "Hussar"},
        crop_code=0, prev_crop_code=0, prev2_crop_code=0,
    )

    assert third_slot[24] == 0.0
    assert third_slot[23] is None


def test_unstocked_profile_slot_blocks_the_herbicide() -> None:
    """Calcs!C10: the profile must stock the product for it to activate."""
    vocabulary = load_vocabulary()
    strategy = {"enterprise": "Wheat", "pre_emergent": "Triflur+Tria"}

    stocked = activation_cells(strategy, crop_code=0, prev_crop_code=0, prev2_crop_code=0)
    cleared = activation_cells(
        strategy, crop_code=0, prev_crop_code=0, prev2_crop_code=0,
        profile_products={**vocabulary["profile_products"], "C20": ""},
    )

    assert stocked[10] == 0.0
    assert cleared[10] is None


def test_placeholder_rows_have_no_activation() -> None:
    """Calcs!C32 and C45 have no formula, which is why survival rows 80/93 never fire."""
    assert 32 not in ROWS
    assert 45 not in ROWS


def test_vocabulary_is_generated_with_provenance() -> None:
    vocabulary = load_vocabulary()

    assert vocabulary["_source"]["generated_by"] == "tools/extract_params.py"
    assert vocabulary["products"]["P89"] == "Topik"
    assert vocabulary["categories"]["D78"] == "Dry"
    assert vocabulary["profile_products"]["C26"] == "Topik"
