"""Regression checks against reviewed outputs captured from the Excel workbook."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim.engine import simulate_strategy


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "excel_parity"
MANIFEST = FIXTURE_DIR / "manifest.json"


def _is_close(actual: float, expected: float, tolerance: dict) -> bool:
    absolute = float(tolerance.get("absolute", 0.0))
    relative = float(tolerance.get("relative", 0.0))
    difference = abs(actual - expected)
    return difference <= max(absolute, abs(expected) * relative)


def _scenarios() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [FIXTURE_DIR / name for name in manifest["scenarios"]]


def test_parity_manifest_is_valid() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert isinstance(manifest["scenarios"], list)
    assert len(manifest["scenarios"]) == len(set(manifest["scenarios"]))
    for name in manifest["scenarios"]:
        assert (FIXTURE_DIR / name).is_file(), f"Missing parity fixture: {name}"


@pytest.mark.parametrize("fixture_path", _scenarios(), ids=lambda path: path.stem)
def test_matches_captured_excel_outputs(fixture_path: Path) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = simulate_strategy(
        fixture["inputs"]["profile"],
        fixture["inputs"]["prices"],
        fixture["inputs"]["options"],
        fixture["inputs"]["strategy"],
    )

    for expected_year in fixture["expected"]["yearly"]:
        actual_year = result["yearly"].iloc[expected_year["year"] - 1]
        for field, expected in expected_year["values"].items():
            tolerance = expected_year["tolerances"][field]
            assert _is_close(float(actual_year[field]), float(expected), tolerance), (
                f"{fixture_path.stem}, year {expected_year['year']}, {field}: "
                f"expected {expected}, got {actual_year[field]}"
            )

    for field, expected in fixture["expected"]["summary"]["values"].items():
        tolerance = fixture["expected"]["summary"]["tolerances"][field]
        assert _is_close(float(result["summary"][field]), float(expected), tolerance), (
            f"{fixture_path.stem}, summary {field}: expected {expected}, "
            f"got {result['summary'][field]}"
        )