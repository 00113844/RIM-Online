"""Verify rim.rotation reproduces Calcs rows 184-189 exactly.

Expected values are the workbook's own cached/recalculated Calcs cells, carried
in each parity fixture's ``reference.rotation_codes`` block. Unlike the economic
and biological outputs these are integers with no modelling tolerance: the port
either reproduces the cascade or it does not.

Coverage across the registered fixtures spans wheat, barley (both the
``carry == 0`` and ``carry + 22`` branches of row 187), legume, consecutive
canola, all three pasture types, pasture run lengths, and the pasture-to-crop
carry of row 186.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim.rotation import CROP_CODE, rotation_codes

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "excel_parity"
MANIFEST = FIXTURE_DIR / "manifest.json"

CASCADE_FIELDS = (
    "crop_code",
    "phase_code",
    "pasture_carry",
    "barley_code",
    "break_since_canola",
    "rotation_key",
)


def _fixtures() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [FIXTURE_DIR / name for name in manifest["scenarios"]]


def _load(fixture_path: Path) -> tuple[list[str], dict[str, str], list[dict]]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    excel = fixture["inputs"]["excel"]
    labels = [row.get("enterprise") for row in excel["strategy"]]
    history = excel.get("history", {"one_year_ago": "w", "two_years_ago": "w"})
    return labels, history, fixture["reference"]["rotation_codes"]


@pytest.mark.parametrize("fixture_path", _fixtures(), ids=lambda p: p.stem)
def test_cascade_matches_excel(fixture_path: Path) -> None:
    labels, history, expected_rows = _load(fixture_path)
    actual_rows = rotation_codes(labels, **history)

    assert len(actual_rows) == len(expected_rows)

    for expected, actual in zip(expected_rows, actual_rows):
        for field in CASCADE_FIELDS:
            assert getattr(actual, field) == int(expected[field]), (
                f"{fixture_path.stem}, year {expected['year']} "
                f"({labels[expected['year'] - 1]}), {field}: "
                f"expected {int(expected[field])}, got {getattr(actual, field)}"
            )


def test_fixtures_cover_every_enterprise() -> None:
    """Guard against the cascade being 'verified' on a narrow rotation."""
    seen = set()
    for fixture_path in _fixtures():
        labels, _, _ = _load(fixture_path)
        seen.update(label for label in labels if label)

    missing = set(CROP_CODE) - seen
    assert not missing, f"No fixture exercises these enterprises: {sorted(missing)}"


def test_blank_enterprise_yields_sentinel_key() -> None:
    """Calcs!E189 returns -1 when the enterprise cell is empty."""
    codes = rotation_codes(["Wheat", None, ""])

    assert codes[0].rotation_key == 0
    assert codes[1].rotation_key == -1
    assert codes[2].rotation_key == -1


def test_pasture_phase_counts_consecutive_years() -> None:
    """Calcs!E185: clover runs code 7 then 8 then 9 for three-or-more years."""
    codes = rotation_codes(["Clover"] * 4)

    assert [c.phase_code for c in codes] == [7, 8, 9, 9]


def test_pasture_carry_advances_by_eleven_then_stops() -> None:
    """Calcs!E186 adds 11 a year after the pasture ends, halting at 24."""
    codes = rotation_codes(["Clover", "Wheat", "Wheat", "Wheat"])

    assert [c.pasture_carry for c in codes] == [7, 18, 29, 0]


def test_barley_after_pasture_takes_the_offset_branch() -> None:
    """Calcs!E187: barley adds 22 to a live carry, or codes 1 when there is none."""
    no_carry = rotation_codes(["Barley"])
    after_pasture = rotation_codes(["Clover", "Barley"])

    assert no_carry[0].barley_code == 1
    assert after_pasture[1].barley_code == 18 + 22
