from __future__ import annotations


def _combined_fraction(parts: list[float]) -> float:
    remaining = 1.0
    for value in parts:
        remaining *= max(0.0, 1.0 - value)
    return min(max(1.0 - remaining, 0.0), 0.995)


def total_control_fraction(decision: dict, options: dict, years_since_mouldboard: int | None) -> float:
    control = options.get("control_effect", {})

    pre_tillage_name = decision.get("pre_tillage", "None")
    pre_tillage_control = control.get("pre_tillage", {}).get(pre_tillage_name, 0.0)

    # Excel behavior: repeated mouldboard within three years has weaker effect.
    if pre_tillage_name == "Mouldboard plough" and years_since_mouldboard is not None and years_since_mouldboard < 3:
        pre_tillage_control = 0.30

    parts = [
        pre_tillage_control,
        control.get("knockdown", {}).get(decision.get("knockdown", "None"), 0.0),
        control.get("pre_emergent", {}).get(decision.get("pre_emergent", "No"), 0.0),
        control.get("post_emergent", {}).get(decision.get("post_emergent", "No"), 0.0),
        control.get("spring", {}).get(decision.get("spring_option", "None"), 0.0),
        control.get("harvest", {}).get(decision.get("harvest_option", "Standard"), 0.0),
    ]

    if decision.get("seeding_technique") == "Full-cut (wide points)":
        parts.append(0.08)
    if decision.get("seeding_rate") == "High":
        parts.append(0.05)

    return _combined_fraction(parts)


def survivors_from_germinated(germinated: float, control_fraction: float) -> float:
    return max(germinated * (1.0 - control_fraction), 0.0)


def crop_competition_strength(crop: str) -> float:
    strengths = {
        "Wheat": 0.55,
        "Barley": 0.65,
        "Canola": 0.50,
        "Legume crop": 0.45,
        "Volunteer pasture": 0.35,
        "Sub-Clover pasture": 0.45,
        "Cadiz pasture": 0.42,
    }
    return strengths.get(crop, 0.45)


def seed_production(
    survivors: float,
    options: dict,
    crop: str,
    spring_option: str,
) -> float:
    fecundity = float(options.get("fecundity_base", 12.0))
    spring_multiplier = {
        "None": 1.0,
        "Green manuring": 0.10,
        "Brown manuring": 0.12,
        "Mowing": 0.15,
        "Hay & Silage": 0.20,
        "Topping": 0.55,
        "Swathing": 0.60,
    }.get(spring_option, 1.0)

    competition_effect = 1.0 - crop_competition_strength(crop)
    return max(survivors * fecundity * max(competition_effect, 0.15) * spring_multiplier, 0.0)
