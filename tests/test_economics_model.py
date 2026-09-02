"""Verify rim.economics_model reproduces Eco results!E3:E73 exactly.

Expected values are the workbook's own economics rows, in each fixture's
``reference.eco_detail``, and the nominal annuity in ``expected.summary``.

The annuity is the reason this file exists as much as the gross margin is: it is
the most misreadable formula in the workbook, and the pre-port engine got its
shape wrong.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim.calcs import simulate_years
from rim.economics_model import (
    load_cost_table,
    load_parameters,
    machinery_repayments,
    nominal_annuity,
    weed_control_cost,
)
from tests.chain import ECO_ROWS, fixtures, walk

TOLERANCE = 1e-6


@pytest.mark.parametrize("fixture_path", fixtures(), ids=lambda p: p.stem)
def test_economics_rows_match_excel(fixture_path: Path) -> None:
    for year in walk(fixture_path):
        produced = year.result.economics
        for field, row in ECO_ROWS.items():
            expected = float(year.expected_eco[row] or 0.0)
            assert getattr(produced, field) == pytest.approx(expected, abs=TOLERANCE), (
                f"{fixture_path.stem}, year {year.year}, {field} (Eco results E{row})"
            )


@pytest.mark.parametrize("fixture_path", fixtures(), ids=lambda p: p.stem)
def test_nominal_annuity_matches_excel(fixture_path: Path) -> None:
    """EcoSum!P5 — the long-term average the interface reports."""
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    excel = fixture["inputs"]["excel"]
    expected = fixture["expected"]["summary"]["values"]["avg_gross_margin"]

    results = simulate_years(excel["strategy"], **excel["history"])
    produced = nominal_annuity([r.economics for r in results])

    assert produced == pytest.approx(float(expected), abs=TOLERANCE)


def test_the_annuity_compounds_rather_than_averaging() -> None:
    """Eco results E68 earns interest on the balance, so timing matters.

    Two runs with the same total gross margin but the good year in a different
    place must not give the same annuity. A discounted average would.
    """
    from rim.economics_model import YearEconomics

    def year(margin: float) -> YearEconomics:
        return YearEconomics(
            grain_receipts=margin + 100.0, hay_receipts=0.0, silage_receipts=0.0,
            bale_receipts=0.0, pasture_receipts=0.0, total_receipts=margin + 100.0,
            non_weed_costs=100.0, weed_control_costs=0.0, total_costs=100.0,
            gross_margin=margin,
        )

    early_good = [year(500.0)] + [year(100.0)] * 9
    late_good = [year(100.0)] * 9 + [year(500.0)]

    assert nominal_annuity(early_good) != pytest.approx(nominal_annuity(late_good))
    assert nominal_annuity(early_good) > nominal_annuity(late_good)


def test_every_priced_option_names_the_cell_that_activates_it() -> None:
    """Mostly r - 98, but Calcs C128 and C129 are transposed. Pin both."""
    table = load_cost_table()

    assert table["128"]["activation_cell"] == 31   # Brown M
    assert table["129"]["activation_cell"] == 30   # Topping
    assert table["116"]["activation_cell"] == 18   # full-cut, which has no survival row
    for row, entry in table.items():
        assert 7 <= entry["activation_cell"] <= 49, row


def test_full_cut_is_charged_even_though_it_has_no_survival_row() -> None:
    """Calcs!C116 prices it; C66 carries no formula. Routing costs via the
    survival block would drop this silently."""
    charged = weed_control_cost({18: 0}, crop_code=0)

    assert charged > 0


def test_the_cost_table_keeps_both_crop_column_mappings() -> None:
    """24 rows put Clover in T and Cadiz in S; 13 do the reverse.

    Reading the block with one mapping mis-costs every spring and harvest option
    on pasture, which is exactly the kind of error that survives review.
    """
    signatures = {entry["column_signature"] for entry in load_cost_table().values()}

    assert signatures == {"NOPQRST", "NOPQRTS"}


def test_machinery_is_paid_for_after_it_stops_being_used() -> None:
    """Calcs!C352:C358 — the age counter runs on, so year 8 still pays."""
    parameters = load_parameters()
    term = int(parameters["machinery_loan_term_years"])
    rates = parameters["machinery_repayments"]

    # Narrow windrow burner in year 1 only, wheat throughout.
    activations = [{42: 0}] + [{} for _ in range(11)]
    charges = machinery_repayments(activations, [0] * 12, rates, term)

    assert charges[0] == pytest.approx(rates["narrow_windrow"])
    assert charges[term - 1] == pytest.approx(rates["narrow_windrow"])
    assert charges[term] == 0.0


def test_pasture_years_carry_no_harvest_machinery() -> None:
    """No header pass, no repayment."""
    parameters = load_parameters()
    charges = machinery_repayments(
        [{42: 5}], [5], parameters["machinery_repayments"],
        int(parameters["machinery_loan_term_years"]))

    assert charges == [0.0]


def test_parameters_are_generated_with_provenance() -> None:
    payload = json.loads((Path(__file__).resolve().parents[1]
                          / "data" / "calcs_cost_table.json").read_text(encoding="utf-8"))

    assert payload["_source"]["generated_by"] == "tools/extract_params.py"
    assert payload["_source"]["ranges"]["table"] == "Calcs!N105:T147"
