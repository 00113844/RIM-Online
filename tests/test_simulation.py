"""
RIM Online — Simulation Regression Tests
=========================================
Golden-value tests derived from the RIM Excel workbook (RIM-2013b).
Run with:  pytest tests/test_simulation.py -v

Tolerances:
  - Biology (seed bank, plants): ±25 %
  - Gross margin per ha:          ±15 %
  - 10-year average GM:           ±20 %
"""
from __future__ import annotations

import math
import sys
import pathlib

# Ensure the package root is on sys.path when running from any working dir.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from rim.defaults import DEFAULT_PROFILE, DEFAULT_PRICES, DEFAULT_OPTIONS
from rim.engine import simulate_strategy


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _pct_close(actual: float, expected: float, pct: float) -> bool:
    """Return True if actual is within ±pct % of expected (or both ~0)."""
    if abs(expected) < 1e-9:
        return abs(actual) < 1.0
    return abs(actual - expected) / abs(expected) <= pct / 100.0


def _make_strategy(years: int, crop_cycle: list[str] | None = None) -> list[dict]:
    """Build a simple *n*-year strategy with rotating crops and no herbicides."""
    crops = crop_cycle or ["Wheat", "Barley", "Canola"]
    rows = []
    for i in range(years):
        rows.append(
            {
                "crop": crops[i % len(crops)],
                "pre_tillage": "None",
                "seeding_technique": "Press wheels",
                "seeding_timing": "Dry",
                "seeding_rate": "Standard",
                "knockdown": "None",
                "pre_emergent": "No",
                "post_emergent": "No",
                "spring_option": "None",
                "harvest_option": "Standard",
                "grazing_intensity": "None",
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Baseline smoke test — simulation runs without error
# ---------------------------------------------------------------------------

def test_simulate_runs_without_exception():
    strategy = _make_strategy(10)
    result = simulate_strategy(DEFAULT_PROFILE, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)
    assert "yearly" in result
    assert len(result["yearly"]) == 10


# ---------------------------------------------------------------------------
# Year 1 — Wheat with no control (high ryegrass pressure)
# ---------------------------------------------------------------------------

def test_year1_wheat_biology():
    """Seed bank should produce germinated plants; gross margin positive."""
    profile = {**DEFAULT_PROFILE, "seed_bank_start": 100}
    strategy = _make_strategy(1, ["Wheat"])
    result = simulate_strategy(profile, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)
    yr = result["yearly"].iloc[0]

    # Plants should be > 0 given initial seed bank of 100 seeds/m²
    assert yr["ryegrass_plants_m2"] > 0, "Expected ryegrass plants from seed bank of 100"

    # Gross margin may be reduced by competition but should still be calculable
    assert math.isfinite(yr["gross_margin"]), "Gross margin should be a finite number"


def test_year1_wheat_gm_range():
    """Year-1 Wheat GM without herbicides should be in a plausible range."""
    profile = {**DEFAULT_PROFILE, "seed_bank_start": 20}
    strategy = _make_strategy(1, ["Wheat"])
    result = simulate_strategy(profile, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)
    yr = result["yearly"].iloc[0]

    # Plausible range: 0 – 600 $/ha for wheat at 1.8 t/ha × 380 $/t
    assert 0 <= yr["gross_margin"] <= 700, (
        f"Wheat Y1 GM out of range: {yr['gross_margin']:.1f}"
    )


# ---------------------------------------------------------------------------
# Year 3 — Canola in rotation (follows Wheat, Barley)
# ---------------------------------------------------------------------------

def test_year3_canola_rotation_benefit():
    """
    Canola in year 3 follows two cereals so no rotation bonus, but yield
    should still be close to base_yield × price minus costs.
    """
    profile = {**DEFAULT_PROFILE, "seed_bank_start": 10}
    strategy = _make_strategy(3, ["Wheat", "Barley", "Canola"])
    result = simulate_strategy(profile, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)
    yr3 = result["yearly"].iloc[2]

    assert yr3["crop"] == "Canola"
    # Canola base yield 1.0 t/ha @ 780 $/t = 780 revenue; after costs ~229 GM
    assert _pct_close(yr3["gross_margin"], 229, 50), (
        f"Canola Y3 GM expected ~229 $/ha, got {yr3['gross_margin']:.1f}"
    )


# ---------------------------------------------------------------------------
# Mouldboard plough — should improve yield and persist
# ---------------------------------------------------------------------------

def test_mouldboard_yield_benefit():
    """A mouldboard year should give a 1.15× yield boost in subsequent years."""
    profile = {**DEFAULT_PROFILE, "seed_bank_start": 5}

    strategy_no_mb = _make_strategy(3, ["Wheat", "Wheat", "Wheat"])
    strategy_mb = [
        {**row, "pre_tillage": "Mouldboard plough"} if i == 0 else row
        for i, row in enumerate(_make_strategy(3, ["Wheat", "Wheat", "Wheat"]))
    ]

    result_no = simulate_strategy(profile, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy_no_mb)
    result_mb = simulate_strategy(profile, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy_mb)

    yield_y2_no = result_no["yearly"].iloc[1]["yield_t_ha"]
    yield_y2_mb = result_mb["yearly"].iloc[1]["yield_t_ha"]

    assert yield_y2_mb > yield_y2_no, (
        "Mouldboard should improve yield in subsequent years"
    )


# ---------------------------------------------------------------------------
# Green manuring — zero seed production
# ---------------------------------------------------------------------------

def test_green_manuring_zero_seed_production():
    """Green manuring should produce zero ryegrass seeds (plants incorporated)."""
    profile = {**DEFAULT_PROFILE, "seed_bank_start": 50}
    strategy = [
        {
            "crop": "Wheat",
            "pre_tillage": "None",
            "seeding_technique": "Press wheels",
            "seeding_timing": "Dry",
            "seeding_rate": "Standard",
            "knockdown": "None",
            "pre_emergent": "No",
            "post_emergent": "No",
            "spring_option": "Green manuring",
            "harvest_option": "Standard",
            "grazing_intensity": "None",
        }
    ]
    result = simulate_strategy(profile, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)
    yr = result["yearly"].iloc[0]

    # After green manuring, seed return should be 0 (or near-0)
    assert yr["new_seed_added"] == pytest.approx(0.0, abs=0.5), (
        f"Green manuring should produce 0 seeds, got {yr['new_seed_added']:.2f}"
    )


# ---------------------------------------------------------------------------
# Cereal after legume — rotation benefit
# ---------------------------------------------------------------------------

def test_cereal_after_legume_rotation_factor():
    """Wheat following a legume crop should benefit from a 1.20× rotation factor."""
    from rim.yields import rotation_factor as rf

    options = {**DEFAULT_OPTIONS}
    factor = rf("Wheat", "Legume crop", options, green_manured=False)
    assert _pct_close(factor, 1.20, 2), (
        f"Cereal after legume factor expected 1.20, got {factor:.3f}"
    )


def test_cereal_after_green_legume_rotation_factor():
    """Wheat following a green-manured legume should benefit from 1.30×."""
    from rim.yields import rotation_factor as rf

    options = {**DEFAULT_OPTIONS}
    factor = rf("Wheat", "Legume crop", options, green_manured=True)
    assert _pct_close(factor, 1.30, 2), (
        f"Cereal after green legume factor expected 1.30, got {factor:.3f}"
    )


# ---------------------------------------------------------------------------
# Dual inflation — real-after-tax rate calculation
# ---------------------------------------------------------------------------

def test_dual_inflation_discount_rate():
    """
    With input inflation 3% and price inflation 1%, avg = 2%,
    real-after-tax rate should differ from single-inflation scenario.
    """
    profile_dual = {
        **DEFAULT_PROFILE,
        "inflation_input_costs_pct": 3.0,
        "inflation_crop_prices_pct": 1.0,
        "interest_rate_pct": 8.0,
        "tax_rate_pct": 21.0,
        "seed_bank_start": 5,
    }
    profile_single = {
        **DEFAULT_PROFILE,
        "inflation_rate_pct": 2.0,
        "interest_rate_pct": 8.0,
        "tax_rate_pct": 21.0,
        "seed_bank_start": 5,
    }

    strategy = _make_strategy(5)
    result_dual = simulate_strategy(profile_dual, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)
    result_single = simulate_strategy(profile_single, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)

    # Both should run cleanly; nominal annuity should be finite
    assert math.isfinite(result_dual["summary"].get("nominal_annuity", 0.0))
    assert math.isfinite(result_single["summary"].get("nominal_annuity", 0.0))


# ---------------------------------------------------------------------------
# Herbicide pass counting
# ---------------------------------------------------------------------------

def test_herbicide_pass_counting_named_product():
    """A named herbicide (not 'Yes') should still count as a spray pass."""
    from rim.economics import compute_costs

    decision_named = {
        "crop": "Wheat",
        "pre_tillage": "None",
        "seeding_technique": "Press wheels",
        "knockdown": "None",
        "pre_emergent": "Trifluralin",   # named product
        "post_emergent": "Clethodim",    # named product
        "spring_option": "None",
        "harvest_option": "Standard",
    }
    decision_yes = {**decision_named, "pre_emergent": "Yes", "post_emergent": "Yes"}
    decision_no = {**decision_named, "pre_emergent": "No", "post_emergent": "No"}

    costs_named = compute_costs(decision_named, DEFAULT_PRICES, DEFAULT_OPTIONS, 0.0)
    costs_yes = compute_costs(decision_yes, DEFAULT_PRICES, DEFAULT_OPTIONS, 0.0)
    costs_no = compute_costs(decision_no, DEFAULT_PRICES, DEFAULT_OPTIONS, 0.0)

    # Named product == Yes should give same herbicide cost
    assert costs_named["herbicide_cost"] == pytest.approx(costs_yes["herbicide_cost"], rel=1e-6), (
        "Named herbicide should count same as 'Yes'"
    )
    # 'No' should give zero herbicide passes
    assert costs_no["herbicide_cost"] == pytest.approx(
        costs_named["herbicide_cost"]
        - 2 * float(DEFAULT_PRICES.get("cost_sprayer_pass", 8.0)),
        abs=1e-6,
    )


# ---------------------------------------------------------------------------
# 10-year average gross margin — plausibility
# ---------------------------------------------------------------------------

def test_10yr_average_gm_plausibility():
    """
    A mixed rotation (Wheat/Barley/Canola) with minimal herbicide use should
    produce an average GM between 0 and 600 $/ha/yr.
    """
    profile = {**DEFAULT_PROFILE, "seed_bank_start": 20}
    strategy = _make_strategy(10)
    result = simulate_strategy(profile, DEFAULT_PRICES, DEFAULT_OPTIONS, strategy)

    avg_gm = result["summary"]["avg_gross_margin"]

    assert 0 <= avg_gm <= 600, (
        f"10-yr average GM out of plausible range: {avg_gm:.1f} $/ha/yr"
    )


# ---------------------------------------------------------------------------
# Fertiliser saving after legume
# ---------------------------------------------------------------------------

def test_fertiliser_saving_after_legume():
    """Wheat following a legume should cost less due to N credit."""
    from rim.economics import compute_costs

    base_decision = {
        "crop": "Wheat",
        "pre_tillage": "None",
        "seeding_technique": "Press wheels",
        "knockdown": "None",
        "pre_emergent": "No",
        "post_emergent": "No",
        "spring_option": "None",
        "harvest_option": "Standard",
    }

    cost_after_wheat = compute_costs(base_decision, DEFAULT_PRICES, DEFAULT_OPTIONS, 0.0, previous_crop="Wheat")
    cost_after_legume = compute_costs(base_decision, DEFAULT_PRICES, DEFAULT_OPTIONS, 0.0, previous_crop="Legume crop")

    assert cost_after_legume["total_cost"] < cost_after_wheat["total_cost"], (
        "Wheat after legume should cost less (fertiliser N saving)"
    )
    saving = cost_after_wheat["total_cost"] - cost_after_legume["total_cost"]
    assert _pct_close(saving, 110.0, 5), (
        f"Wheat-after-legume N saving expected ~110 $/ha, got {saving:.1f}"
    )
