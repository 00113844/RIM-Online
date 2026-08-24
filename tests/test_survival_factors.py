"""Verify rim.survival reproduces Calcs rows 55-97 exactly.

Each fixture carries both halves of the comparison, straight from Excel:
``reference.activation`` (Calcs!C7:C49, the inputs) and
``reference.survival_factors`` (Calcs rows 55-97, the expected outputs). Taking
the activation cells from Excel rather than deriving them means this block is
tested on its own, before ``Calcs!C7:C27`` is ported.

Between the registered fixtures, 35 of the 37 survival rows are exercised with a
factor other than 1.0. The two that are not -- rows 80 and 93 -- are the
workbook's own "empty slot for adding a..." placeholders, which have no dropdown
entry and so cannot be selected. ``test_only_placeholder_rows_are_unexercised``
holds that line.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim.survival import ROWS, load_table, option_label, survival_factors

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "excel_parity"
MANIFEST = FIXTURE_DIR / "manifest.json"

# Calcs rows 80 and 93 are labelled "empty slot for adding a ..." in the
# workbook and have no entry in any dropdown list.
PLACEHOLDER_ROWS = {80, 93}

TOLERANCE = 1e-9


def _fixtures() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [FIXTURE_DIR / name for name in manifest["scenarios"]]


def _reference(fixture_path: Path) -> tuple[list[dict], list[dict]]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    reference = fixture["reference"]
    return reference["activation"], reference["survival_factors"]


@pytest.mark.parametrize("fixture_path", _fixtures(), ids=lambda p: p.stem)
def test_factors_match_excel(fixture_path: Path) -> None:
    activation_years, expected_years = _reference(fixture_path)

    for activation, expected in zip(activation_years, expected_years):
        actual = survival_factors(activation)
        for row in ROWS:
            if expected[str(row)] is None:
                continue
            assert actual[row] == pytest.approx(float(expected[str(row)]), abs=TOLERANCE), (
                f"{fixture_path.stem}, year {activation['year']}, "
                f"Calcs!C{row} ({option_label(row)}): "
                f"expected {expected[str(row)]}, got {actual[row]}"
            )


def test_only_placeholder_rows_are_unexercised() -> None:
    """Guard against the block being 'verified' with most options switched off."""
    exercised = set()
    for fixture_path in _fixtures():
        _, expected_years = _reference(fixture_path)
        for expected in expected_years:
            for row in ROWS:
                value = expected[str(row)]
                if value is not None and abs(float(value) - 1.0) > 1e-12:
                    exercised.add(row)

    unexercised = set(ROWS) - exercised
    assert unexercised == PLACEHOLDER_ROWS, (
        "Coverage changed. Rows never exercised with a factor other than 1.0: "
        + ", ".join(f"C{row} ({option_label(row)})" for row in sorted(unexercised))
    )


def test_inactive_options_survive_untouched() -> None:
    """Calcs!C55 etc. return 1 when the activation cell is blank."""
    factors = survival_factors({row: None for row in range(7, 50)})

    assert set(factors) == set(ROWS)
    assert all(value == 1.0 for value in factors.values())


def test_activation_holds_the_crop_code_that_selects_the_column() -> None:
    """One cell says both *whether* an option applies and *which* crop column to read.

    Topik (Calcs!C71 <- C23) controls 90% of ryegrass in wheat (code 0) and
    nothing in canola (code 2), per Calcs!N71 and P71.
    """
    on_wheat = survival_factors({23: 0})
    on_canola = survival_factors({23: 2})

    assert on_wheat[71] == pytest.approx(0.1)
    assert on_canola[71] == pytest.approx(1.0)


def test_seeding_rows_key_on_establishment_not_crop() -> None:
    """Calcs!C68:C70 read columns P/Q (no-till / full-cut), set by Calcs!C18."""
    no_till = survival_factors({20: 0})
    full_cut = survival_factors({20: 0, 18: 0})

    assert no_till[68] == pytest.approx(0.6)   # 1 - 0.4
    assert full_cut[68] == pytest.approx(0.2)  # 1 - 0.8


def test_seeding_skips_volunteer_pasture() -> None:
    """Calcs!C69: AND(C21<>"", C21<>4) -- volunteer pasture is not sown."""
    on_wheat = survival_factors({21: 0})
    on_volunteer = survival_factors({21: 4})

    assert on_wheat[69] == pytest.approx(0.6)
    assert on_volunteer[69] == 1.0


def test_row_68_accepts_either_source_cell() -> None:
    """Calcs!C68: AND(OR(C19<>"",C20<>""), OR(C19<>"",C20<>4)).

    C19 alone activates it whatever the crop; C20 alone does not when the crop
    is volunteer pasture.
    """
    via_c19 = survival_factors({19: 4})
    via_c20 = survival_factors({20: 4})

    assert via_c19[68] == pytest.approx(0.6)
    assert via_c20[68] == 1.0


def test_table_is_generated_with_provenance() -> None:
    """The control table must be regenerated from the workbook, never hand-typed."""
    payload = json.loads((Path(__file__).resolve().parents[1]
                          / "data" / "calcs_survival_table.json").read_text(encoding="utf-8"))

    assert payload["_source"]["generated_by"] == "tools/extract_params.py"
    assert payload["_source"]["ranges"]["table"] == "Calcs!N54:T97"
    assert payload["crop_codes"] == list(range(7))
    assert len(load_table()) == 43
