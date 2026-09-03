from __future__ import annotations

from rim import control_options
from rim.rotation import app_crop_code


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

    # Every weed-control decision's effect depends on the crop it is applied
    # to -- Topik takes 90% of the ryegrass in wheat and nothing in canola,
    # swathing does nothing at all on pasture -- so all of them are read from
    # the workbook's own table rather than a flat rate in `options`. The only
    # one left in `options` is tillage, which that table treats as a seeding
    # operation. See rim/control_options.py.
    crop_code = app_crop_code(decision.get("crop", "Wheat"))

    parts = [pre_tillage_control]
    parts += [
        control_options.control(field, decision.get(field), crop_code)
        for field in control_options.FIELDS
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
    spring_swathe: str = "None",
) -> float:
    """How much seed the survivors set, after what spring did to them.

    These multipliers are the pre-port engine's own and have no workbook cell
    behind them; TASKS item 3 replaces the whole of this with Bio results
    D17:D20. They are keyed by ``Calcs`` row rather than by name, so renaming
    an option cannot silently turn green manuring back into a full seed set.
    """
    fecundity = float(options.get("fecundity_base", 12.0))

    # Calcs 82 green manuring and 78 brown manuring incorporate the plants
    # before they seed; 81 mowing, 83 hay and 84 silage cut most of it; 79 crop
    # topping sterilises some of the heads.
    by_row = {82: 0.0, 78: 0.0, 81: 0.05, 83: 0.10, 84: 0.10, 79: 0.25}

    spring_row = control_options.row_of("spring_option", spring_option)
    spring_multiplier = by_row.get(spring_row, 1.0)

    # Swathing is its own decision (2.Strategy row 16) and can be taken
    # alongside a spring option. Whichever cuts seed set harder governs.
    swathe_row = control_options.row_of("spring_swathe", spring_swathe)
    swathe_multiplier = 0.30 if swathe_row in (87, 88) else 1.0

    competition_effect = 1.0 - crop_competition_strength(crop)
    return max(
        survivors * fecundity * max(competition_effect, 0.15)
        * min(spring_multiplier, swathe_multiplier),
        0.0,
    )
