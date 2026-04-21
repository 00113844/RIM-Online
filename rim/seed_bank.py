from __future__ import annotations


def apply_seed_mortality(seed_bank: float, mortality_rate: float) -> float:
    """Apply annual natural seed-bank mortality."""
    return max(seed_bank * (1.0 - mortality_rate), 0.0)


def germination_rate_for_context(crop: str, pre_tillage: str, options: dict) -> float:
    rates = options.get("germination_rate", {})
    if "pasture" in crop.lower():
        return float(rates.get("pasture", 0.75))
    if pre_tillage == "Tickle":
        return float(rates.get("tickle", 0.85))
    return float(rates.get("default", 0.8))


def germinate(seed_bank: float, germination_rate: float) -> tuple[float, float]:
    germinated = max(seed_bank * germination_rate, 0.0)
    residual = max(seed_bank - germinated, 0.0)
    return germinated, residual


def replenish_seed_bank(residual_seed: float, new_seed: float, mortality_rate: float) -> float:
    return apply_seed_mortality(residual_seed, mortality_rate) + max(new_seed, 0.0)
