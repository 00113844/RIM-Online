from __future__ import annotations

import math


def _is_cereal(crop: str) -> bool:
    return crop in {"Wheat", "Barley"}


def _is_legume(crop: str) -> bool:
    return crop in {"Legume crop", "Sub-Clover pasture", "Cadiz pasture"}


def rotation_factor(current_crop: str, previous_crop: str | None, options: dict) -> float:
    factors = options.get("rotation_factor", {})
    if previous_crop is None:
        return float(factors.get("default", 1.0))

    if _is_cereal(current_crop) and _is_legume(previous_crop):
        return float(factors.get("cereal_after_legume", 1.10))
    if _is_cereal(current_crop) and previous_crop == "Canola":
        return float(factors.get("cereal_after_canola", 1.05))
    if current_crop == "Canola" and _is_legume(previous_crop):
        return float(factors.get("canola_after_legume", 1.06))
    if _is_cereal(current_crop) and _is_cereal(previous_crop):
        return float(factors.get("short_break_penalty", 0.90))
    return float(factors.get("default", 1.0))


def yield_penalty_from_ryegrass(crop: str, plants: float, options: dict) -> float:
    max_loss = float(options.get("yield_loss_max", {}).get(crop, 0.60))
    competition = float(options.get("competition_coeff", {}).get(crop, 0.85))
    scaled = math.log1p(max(plants, 0.0)) / math.log1p(500.0)
    penalty = scaled * competition * max_loss
    return min(max(penalty, 0.0), max_loss)


def compute_actual_yield(
    decision: dict,
    profile: dict,
    options: dict,
    previous_crop: str | None,
    ryegrass_plants: float,
) -> dict:
    crop = decision.get("crop", "Wheat")
    base_yield = float(profile.get("base_yields", {}).get(crop, 0.0))

    timing_factor = float(options.get("timing_factor", {}).get(decision.get("seeding_timing", "Dry"), 1.0))
    rate_factor = float(options.get("seeding_rate_factor", {}).get(decision.get("seeding_rate", "Standard"), 1.0))
    spring_factor = float(options.get("spring_yield_factor", {}).get(decision.get("spring_option", "None"), 1.0))
    rot_factor = rotation_factor(crop, previous_crop, options)

    seeding_tech_factor = 0.99 if decision.get("seeding_technique") == "Full-cut (wide points)" else 1.0
    penalty = yield_penalty_from_ryegrass(crop, ryegrass_plants, options)

    potential_yield = base_yield * timing_factor * rate_factor * rot_factor
    actual_yield = potential_yield * seeding_tech_factor * spring_factor * (1.0 - penalty)

    stocking_rate = options.get("stocking_rate", {})
    grazing_intensity = decision.get("grazing_intensity", "None")
    stocking_dse = 0.0
    if "pasture" in crop.lower():
        if grazing_intensity == "Standard":
            stocking_dse = float(stocking_rate.get("standard", 4.5))
        elif grazing_intensity == "High":
            stocking_dse = float(stocking_rate.get("high", 6.5))

    return {
        "yield_t_ha": max(actual_yield, 0.0),
        "yield_potential_t_ha": max(potential_yield, 0.0),
        "ryegrass_penalty_fraction": penalty,
        "stocking_dse": stocking_dse,
    }
