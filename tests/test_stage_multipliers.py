"""Verify rim.stage_multipliers reproduces Calcs!C99 and C164:C170 exactly.

Each fixture carries the Excel inputs (``reference.activation``,
``reference.survival_factors``, ``reference.rotation_codes`` and the strategy's
post-emergent slots) alongside the expected multipliers, so this block is tested
without depending on block 2.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim.stage_multipliers import (
    MULTIPLIER_ROWS,
    load_constants,
    normal_harvest_factor,
    post_emergent_use_counts,
    stage_multipliers,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "excel_parity"
MANIFEST = FIXTURE_DIR / "manifest.json"

NORMAL_HARVEST_ROW = 99
TOLERANCE = 1e-9


def _fixtures() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [FIXTURE_DIR / name for name in manifest["scenarios"]]


def _years(fixture_path: Path):
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    reference = fixture["reference"]
    return zip(
        fixture["inputs"]["excel"]["strategy"],
        reference["activation"],
        reference["survival_factors"],
        reference["rotation_codes"],
        reference["stage_multipliers"],
    )


@pytest.mark.parametrize("fixture_path", _fixtures(), ids=lambda p: p.stem)
def test_multipliers_match_excel(fixture_path: Path) -> None:
    for strategy, activation, survival, codes, expected in _years(fixture_path):
        factors = {int(k): float(v) for k, v in survival.items()
                   if k != "year" and v is not None}
        actual = stage_multipliers(
            activation,
            factors,
            crop_code=int(codes["crop_code"]),
            post_emergent_slots=[strategy.get(f"post_emergent_{n}") for n in (1, 2, 3)],
            pre_emergent_selected=bool(strategy.get("pre_emergent")),
        )

        for row in MULTIPLIER_ROWS:
            if expected[str(row)] is None:
                continue
            assert actual[row] == pytest.approx(float(expected[str(row)]), abs=TOLERANCE), (
                f"{fixture_path.stem}, year {activation['year']}, Calcs!C{row}: "
                f"expected {expected[str(row)]}, got {actual[row]}"
            )


@pytest.mark.parametrize("fixture_path", _fixtures(), ids=lambda p: p.stem)
def test_normal_harvest_factor_matches_excel(fixture_path: Path) -> None:
    """Calcs!C99 is asserted separately because C170 folds it in."""
    for _strategy, activation, _survival, codes, expected in _years(fixture_path):
        if expected[str(NORMAL_HARVEST_ROW)] is None:
            continue
        actual = normal_harvest_factor(
            {int(k): v for k, v in activation.items() if k != "year"},
            int(codes["crop_code"]),
        )
        assert actual == pytest.approx(
            float(expected[str(NORMAL_HARVEST_ROW)]), abs=TOLERANCE
        ), f"{fixture_path.stem}, year {activation['year']}, Calcs!C99"


def test_post_emergents_apply_once_per_slot() -> None:
    """Calcs!C168 raises each factor to the count in Calcs!P35:P39.

    Naming the same product in two slots halves survival twice -- 0.1 becomes
    0.01 -- which a per-product model could not express.
    """
    activation = {23: 0}
    factors = {71: 0.1, 72: 1.0, 73: 1.0, 74: 1.0, 75: 1.0}

    once = stage_multipliers(activation, factors, crop_code=0,
                             post_emergent_slots=["Topik", None, None])
    twice = stage_multipliers(activation, factors, crop_code=0,
                              post_emergent_slots=["Topik", "Topik", None])

    assert once[168] == pytest.approx(0.1)
    assert twice[168] == pytest.approx(0.01)


def test_use_counts_need_the_activation_cell() -> None:
    """Calcs!P35: IF(C23<>"", ...count..., 0) -- a slot with no activation counts zero."""
    slots = ["Topik", "Topik", None]

    assert post_emergent_use_counts(slots, {23: 0})[23] == 2
    assert post_emergent_use_counts(slots, {23: None})[23] == 0


def test_seeding_sum_conflates_blank_with_wheat() -> None:
    """Calcs!C165 tests SUM(C19:C22)=0, and wheat's crop code is itself 0.

    So the knock-down branch is taken for wheat exactly as it is when nothing
    is selected. This looks like a bug in the workbook and is faithfully
    reproduced; canola (code 2) takes the other branch.
    """
    factors = {55: 0.5, 56: 1.0, 57: 1.0, 65: 1.0, 69: 1.0}

    wheat = stage_multipliers({20: 0}, factors, crop_code=0)
    canola = stage_multipliers({20: 2}, factors, crop_code=2)

    assert wheat[165] == pytest.approx(0.5)
    assert canola[165] == pytest.approx(1.0)


def test_normal_harvest_only_applies_to_crops_left_alone() -> None:
    """Calcs!C99: crops only, and only when no spring or harvest option was chosen."""
    removal = 1.0 - load_constants()["normal_harvest_seed_removal"]

    assert normal_harvest_factor({}, 0) == pytest.approx(removal)
    assert normal_harvest_factor({}, 5) == 1.0            # pasture
    assert normal_harvest_factor({35: 0}, 0) == 1.0       # a spring option was chosen
    assert normal_harvest_factor({42: 0}, 0) == 1.0       # a harvest option was chosen


def test_constants_are_generated_with_provenance() -> None:
    payload = json.loads((Path(__file__).resolve().parents[1]
                          / "data" / "calcs_stage_constants.json").read_text(encoding="utf-8"))

    assert payload["_source"]["generated_by"] == "tools/extract_params.py"
    assert payload["pre_em_survival_floor"]["cell"] == "Calcs!N167"
    assert set(load_constants()) >= {
        "pre_em_survival_floor",
        "pre_em_extra_control",
        "normal_harvest_seed_removal",
    }
