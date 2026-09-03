from __future__ import annotations

from copy import deepcopy

DEFAULT_PROFILE = {
    "farm_name": "",
    "paddock_name": "",
    "farm_size_ha": 1000.0,
    "farm_area_ha": 1000.0,
    "base_yields": {
        "Wheat": 1.8,
        "Barley": 1.6,
        "Canola": 1.0,
        "Legume crop": 1.0,
        "Volunteer pasture": 1.0,
        "Sub-Clover pasture": 1.0,
        "Cadiz pasture": 1.0,
    },
    "sheep_gm_per_dse": 55.0,
    "seed_bank_start": 20,
    "interest_rate_pct": 8.0,
    "inflation_input_costs_pct": 3.0,
    "inflation_crop_prices_pct": 1.0,
    "inflation_rate_pct": 2.0,
    "tax_rate_pct": 21.0,
    "rotation_shares": {
        "cereal": 0.6,
        "canola": 0.2,
        "legume": 0.2,
    },
}

DEFAULT_PRICES = {
    "Wheat": 380.0,
    "Barley": 280.0,
    "Canola": 780.0,
    "Legume crop": 450.0,
    "Hay": 180.0,
    "Silage": 120.0,
    "sheep_price": 95.0,
    "cost_no_till": 90.0,
    "cost_full_cut_extra": 20.0,
    "cost_tickle": 18.0,
    "cost_high_seeding_rate_extra": 10.0,
    "cost_sprayer_pass": 8.0,
    "cost_crop_insurance": 10.0,
    "cost_fertiliser": 70.0,
    "cost_seed": 35.0,
    "loan_term_years": 8,
    "machinery_capital": {
        "HSD": 240000.0,
        "BDS": 190000.0,
        "Chaff cart": 80000.0,
        "Chaff tramlining": 120000.0,
        "Narrow windrow": 45000.0,
        "Standard harvest reference": 60000.0,
    },
}

DEFAULT_OPTIONS = {
    "yield_loss_max": {
        "Wheat": 0.60,
        "Barley": 0.45,
        "Canola": 0.60,
        "Legume crop": 0.60,
        "Volunteer pasture": 0.35,
        "Sub-Clover pasture": 0.35,
        "Cadiz pasture": 0.35,
    },
    "competition_coeff": {
        "Wheat": 0.85,
        "Barley": 0.70,
        "Canola": 0.95,
        "Legume crop": 0.90,
        "Volunteer pasture": 0.40,
        "Sub-Clover pasture": 0.45,
        "Cadiz pasture": 0.48,
    },
    "germination_rate": {
        "default": 0.80,
        "tickle": 0.85,
        "pasture": 0.75,
    },
    "natural_seed_mortality": 0.20,
    "fecundity_base": 12.0,
    "stocking_rate": {
        "standard": 4.5,
        "high": 6.5,
    },
    # Weed control is no longer rated here. Each option has its own effect and
    # its own cost, and both depend on the crop, so both are read from the
    # workbook's tables -- rim/control_options.py, Calcs rows 55-97 and
    # 105-147. Only tillage stays, which those tables treat as a seeding
    # operation rather than a control option.
    "control_effect": {
        "pre_tillage": {
            "None": 0.00,
            "Tickle": 0.15,
            "Mouldboard plough": 0.98,
        },
    },
    # Weed-control costs are no longer listed here either. The workbook prices
    # every option per crop in Calcs!N105:T147, paired to its control row 50
    # above; rim/control_options.py reads both.
}

DEFAULT_STRATEGY_ROW = {
    "crop": "Wheat",
    "seeding_timing": "Dry",
    "seeding_technique": "No-till",
    "seeding_rate": "Standard",
    "pre_tillage": "None",
    "knockdown": "None",
    # The first product the workbook lists that works in wheat, for each slot
    # (Calcs rows 58 and 71). The shipped plan sprayed both before products
    # existed; naming them keeps that intent and makes the rate a real one.
    "pre_emergent": "Triflur+Triallate",
    "post_emergent_1": "Topik",
    "post_emergent_2": "None",
    "post_emergent_3": "None",
    "spring_option": "None",
    "spring_swathe": "None",
    "spring_others": "None",
    "grazing_intensity": "None",
    "harvest_option": "Standard",
    "harvest_others": "None",
}


def build_default_strategy(years: int = 10) -> list[dict]:
    return [{"year": i + 1, **deepcopy(DEFAULT_STRATEGY_ROW)} for i in range(years)]


def get_default_state() -> dict:
    return {
        "profile_current": deepcopy(DEFAULT_PROFILE),
        "prices_current": deepcopy(DEFAULT_PRICES),
        "options_current": deepcopy(DEFAULT_OPTIONS),
        "strategy_current": build_default_strategy(10),
    }
