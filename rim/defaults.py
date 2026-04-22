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
    "control_effect": {
        "pre_tillage": {
            "None": 0.00,
            "Tickle": 0.15,
            "Mouldboard plough": 0.98,
        },
        "knockdown": {
            "None": 0.00,
            "Single knock-down": 0.55,
            "Double knock-down": 0.75,
        },
        "pre_emergent": {
            "No": 0.00,
            "Yes": 0.45,
        },
        "post_emergent": {
            "No": 0.00,
            "Yes": 0.50,
        },
        "spring": {
            "None": 0.00,
            "Green manuring": 1.00,
            "Brown manuring": 1.00,
            "Mowing": 0.90,
            "Hay & Silage": 0.90,
            "Topping": 0.40,
            "Swathing": 0.45,
        },
        "harvest": {
            "Standard": 0.30,
            "Whole paddock burn": 0.85,
            "Narrow windrow burn": 0.85,
            "Chaff-tramlining": 0.85,
            "Chaff cart+dumps": 0.85,
            "HSD": 0.85,
            "BDS": 0.85,
        },
    },
    "timing_factor": {
        "Dry": 1.00,
        "Wet": 1.02,
        "Delayed (1-2 wks)": 0.96,
        "+Delayed (3 wks)": 0.90,
    },
    "seeding_rate_factor": {
        "Standard": 1.00,
        "High": 1.04,
    },
    "spring_yield_factor": {
        "None": 1.00,
        "Green manuring": 0.05,
        "Brown manuring": 0.10,
        "Mowing": 0.85,
        "Hay & Silage": 0.80,
        "Topping": 0.95,
        "Swathing": 0.97,
    },
    "rotation_factor": {
        "default": 1.00,
        "cereal_after_legume": 1.20,
        "cereal_after_green_legume": 1.30,
        "cereal_after_canola": 1.05,
        "canola_after_legume": 1.06,
        "short_break_penalty": 0.90,
        "mouldboard_benefit": 1.15,
    },
    "costs": {
        "spring": {
            "None": 0.0,
            "Green manuring": 100.0,
            "Brown manuring": 8.0,
            "Mowing": 100.0,
            "Hay & Silage": 35.0,
            "Topping": 8.0,
            "Swathing": 35.0,
        },
        "harvest": {
            "Standard": 0.0,
            "Whole paddock burn": 12.0,
            "Narrow windrow burn": 10.0,
            "Chaff-tramlining": 14.0,
            "Chaff cart+dumps": 16.0,
            "HSD": 20.0,
            "BDS": 18.0,
        },
    },
}

DEFAULT_STRATEGY_ROW = {
    "crop": "Wheat",
    "seeding_timing": "Dry",
    "seeding_technique": "No-till",
    "seeding_rate": "Standard",
    "pre_tillage": "None",
    "knockdown": "Single knock-down",
    "pre_emergent": "Yes",
    "post_emergent": "Yes",
    "spring_option": "None",
    "grazing_intensity": "None",
    "harvest_option": "Standard",
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
