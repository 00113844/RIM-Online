from __future__ import annotations

from rim import control_options
from rim.herbicides import POST_EMERGENT_FIELDS
from rim.rotation import app_crop_code

# The three groups the cost breakdown reports separately.
HERBICIDE_FIELDS = ("knockdown", "pre_emergent", *POST_EMERGENT_FIELDS)
SPRING_FIELDS = ("spring_option", "spring_swathe", "spring_others")
HARVEST_FIELDS = ("harvest_option", "harvest_others")

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
    # 2.Strategy row 18 now carries the workbook's own labels; these are the
    # machinery-repayment keys they correspond to. Burning everything moved to
    # the harvest-others row and buys no machinery, so it is not here.
    # Calcs row -> the machinery this harvest system needs a repayment for.
    # Keyed by row, not by name: +Prices names the machines and 2.Strategy names
    # the operations, and the two need not agree forever.
    by_row = {
        89: "Chaff cart",
        90: "Narrow windrow",
        91: "HSD",
        92: "Chaff tramlining",
        94: "BDS",
    }
    row = control_options.row_of("harvest_option", decision.get("harvest_option"))
    key = by_row.get(row, "Standard harvest reference")
    return float(repayments.get(key, 0.0))


def compute_revenue(decision: dict, yield_t_ha: float, profile: dict, prices: dict, stocking_dse: float) -> dict:
    crop = decision.get("crop", "Wheat")
    crop_price = float(prices.get(crop, 0.0))

    grain_income = 0.0
    pasture_income = 0.0
    livestock_income = 0.0

    if "pasture" in crop.lower():
        livestock_income = stocking_dse * float(profile.get("sheep_gm_per_dse", 50.0))
        # Calcs rows 83 and 84 -- hay and silage, which the workbook prices
        # separately. Keyed by row so a rename cannot lose the income.
        if control_options.row_of("spring_option", decision.get("spring_option")) in (83, 84):
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


def compute_costs(decision: dict, prices: dict, options: dict, machinery_cost_per_ha: float, previous_crop: str | None = None) -> dict:
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

    # Every weed-control decision is priced by the workbook, per crop, in
    # Calcs!N105:T147 -- $26/ha for a Glyphosate knock-down in a crop and $22 in
    # a pasture, $48 for Sakura, $8 for a bare spray pass. Each post-emergent
    # slot filled is its own application and its own cost. See
    # rim/control_options.py; none of these numbers is ours.
    crop_code = app_crop_code(decision.get("crop", "Wheat"))
    herbicide_cost = sum(
        control_options.cost(field, decision.get(field), crop_code)
        for field in HERBICIDE_FIELDS
    )
    spring_cost = sum(
        control_options.cost(field, decision.get(field), crop_code)
        for field in SPRING_FIELDS
    )
    harvest_cost = sum(
        control_options.cost(field, decision.get(field), crop_code)
        for field in HARVEST_FIELDS
    )

    weed_control_cost = herbicide_cost + spring_cost + harvest_cost + machinery_cost_per_ha
    total = base_cost + weed_control_cost

    # Mouldboard contractor cost: 150 $/ha when used
    if decision.get("pre_tillage") == "Mouldboard plough":
        total += 150.0

    # Fertiliser saving (N benefit) in the season following a legume break
    _FERT_SAVING = {"Canola": 150.0, "Wheat": 110.0, "Barley": 110.0}
    if previous_crop is not None:
        from rim.yields import _is_legume  # local import avoids circular deps
        if _is_legume(previous_crop):
            crop = decision.get("crop", "")
            total -= float(_FERT_SAVING.get(crop, 0.0))

    # Harvester operating cost (~21.94 $/ha) for all grain crops
    pasture_crops = {"Volunteer pasture", "Sub-Clover pasture", "Cadiz pasture"}
    if decision.get("crop", "") not in pasture_crops:
        total += 21.94

    return {
        "base_cost": base_cost,
        "herbicide_cost": herbicide_cost,
        "spring_cost": spring_cost,
        "harvest_cost": harvest_cost,
        "machinery_repayment_cost": machinery_cost_per_ha,
        "weed_control_cost": weed_control_cost,
        "total_cost": total,
    }
