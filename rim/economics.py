from __future__ import annotations

import numpy_financial as npf


def machinery_repayment_per_ha(prices: dict, interest_rate_pct: float, farm_area_ha: float) -> dict:
    capital = prices.get("machinery_capital", {})
    nper = int(prices.get("loan_term_years", 8))
    rate = max(interest_rate_pct, 0.0) / 100.0
    denom = max(float(farm_area_ha), 1.0)

    repayments = {}
    for name, value in capital.items():
        ann = -float(npf.pmt(rate, nper, float(value))) if nper > 0 else 0.0
        repayments[name] = ann / denom
    return repayments


def harvest_machine_cost(decision: dict, repayments: dict) -> float:
    map_key = {
        "HSD": "HSD",
        "BDS": "BDS",
        "Chaff cart+dumps": "Chaff cart",
        "Chaff-tramlining": "Chaff tramlining",
        "Narrow windrow burn": "Narrow windrow",
        "Standard": "Standard harvest reference",
        "Whole paddock burn": "Standard harvest reference",
    }
    key = map_key.get(decision.get("harvest_option", "Standard"), "Standard harvest reference")
    return float(repayments.get(key, 0.0))


def compute_revenue(decision: dict, yield_t_ha: float, profile: dict, prices: dict, stocking_dse: float) -> dict:
    crop = decision.get("crop", "Wheat")
    crop_price = float(prices.get(crop, 0.0))

    grain_income = 0.0
    pasture_income = 0.0
    livestock_income = 0.0

    if "pasture" in crop.lower():
        livestock_income = stocking_dse * float(profile.get("sheep_gm_per_dse", 50.0))
        if decision.get("spring_option") == "Hay & Silage":
            pasture_income = yield_t_ha * float(prices.get("Hay", 0.0))
    else:
        grain_income = yield_t_ha * crop_price

    total = grain_income + pasture_income + livestock_income
    return {
        "income_grain": grain_income,
        "income_pasture": pasture_income,
        "income_livestock": livestock_income,
        "total_revenue": total,
    }


def compute_costs(decision: dict, prices: dict, options: dict, machinery_cost_per_ha: float) -> dict:
    base_cost = (
        float(prices.get("cost_no_till", 0.0))
        + float(prices.get("cost_fertiliser", 0.0))
        + float(prices.get("cost_seed", 0.0))
        + float(prices.get("cost_crop_insurance", 0.0))
    )

    if decision.get("seeding_technique") == "Full-cut (wide points)":
        base_cost += float(prices.get("cost_full_cut_extra", 0.0))
    if decision.get("seeding_rate") == "High":
        base_cost += float(prices.get("cost_high_seeding_rate_extra", 0.0))
    if decision.get("pre_tillage") == "Tickle":
        base_cost += float(prices.get("cost_tickle", 0.0))

    spray_pass_cost = float(prices.get("cost_sprayer_pass", 0.0))
    kd = decision.get("knockdown", "None")
    knockdown_passes = {"None": 0.0, "Single knock-down": 1.0, "Double knock-down": 2.0}.get(kd, 0.0)
    herb_passes = knockdown_passes
    herb_passes += 1.0 if decision.get("pre_emergent") == "Yes" else 0.0
    herb_passes += 1.0 if decision.get("post_emergent") == "Yes" else 0.0
    herbicide_cost = herb_passes * spray_pass_cost

    spring_cost = float(options.get("costs", {}).get("spring", {}).get(decision.get("spring_option", "None"), 0.0))
    harvest_cost = float(options.get("costs", {}).get("harvest", {}).get(decision.get("harvest_option", "Standard"), 0.0))

    weed_control_cost = herbicide_cost + spring_cost + harvest_cost + machinery_cost_per_ha
    total = base_cost + weed_control_cost

    return {
        "base_cost": base_cost,
        "herbicide_cost": herbicide_cost,
        "spring_cost": spring_cost,
        "harvest_cost": harvest_cost,
        "machinery_repayment_cost": machinery_cost_per_ha,
        "weed_control_cost": weed_control_cost,
        "total_cost": total,
    }
