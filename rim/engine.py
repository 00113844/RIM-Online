from __future__ import annotations

import numpy_financial as npf
import pandas as pd

from rim.economics import compute_costs, compute_revenue, harvest_machine_cost, machinery_repayment_per_ha
from rim.ryegrass import seed_production, survivors_from_germinated, total_control_fraction
from rim.seed_bank import germinate, germination_rate_for_context, replenish_seed_bank
from rim.yields import compute_actual_yield


def _annuity_from_cashflows(cashflows: list[float], discount_rate: float) -> float:
    if not cashflows:
        return 0.0
    n = len(cashflows)
    if abs(discount_rate) < 1e-9:
        return sum(cashflows) / n

    npv = 0.0
    for i, value in enumerate(cashflows, start=1):
        npv += value / ((1.0 + discount_rate) ** i)
    return -float(npf.pmt(discount_rate, n, npv))


def simulate_strategy(profile: dict, prices: dict, options: dict, strategy_rows: list[dict]) -> dict:
    seed_bank = float(profile.get("seed_bank_start", 20.0))
    previous_crop = None
    last_mouldboard_year = None

    rate_nominal = float(profile.get("interest_rate_pct", 6.0)) / 100.0
    inflation = float(profile.get("inflation_rate_pct", 2.5)) / 100.0
    tax = float(profile.get("tax_rate_pct", 30.0)) / 100.0
    real_after_tax_rate = ((1.0 + rate_nominal) / max(1.0 + inflation, 1e-9) - 1.0) * (1.0 - tax)

    repayments = machinery_repayment_per_ha(
        prices=prices,
        interest_rate_pct=float(profile.get("interest_rate_pct", 6.0)),
        farm_area_ha=float(profile.get("farm_area_ha", profile.get("farm_size_ha", 1000.0))),
    )

    rows = []
    for i, decision in enumerate(strategy_rows, start=1):
        year = int(decision.get("year", i))

        years_since_mouldboard = None
        if last_mouldboard_year is not None:
            years_since_mouldboard = year - last_mouldboard_year

        g_rate = germination_rate_for_context(decision.get("crop", "Wheat"), decision.get("pre_tillage", "None"), options)
        germinated, residual = germinate(seed_bank, g_rate)

        control = total_control_fraction(decision, options, years_since_mouldboard)
        survivors = survivors_from_germinated(germinated, control)

        if decision.get("pre_tillage") == "Mouldboard plough":
            last_mouldboard_year = year

        y = compute_actual_yield(
            decision=decision,
            profile=profile,
            options=options,
            previous_crop=previous_crop,
            ryegrass_plants=survivors,
        )

        new_seed = seed_production(
            survivors=survivors,
            options=options,
            crop=decision.get("crop", "Wheat"),
            spring_option=decision.get("spring_option", "None"),
        )

        seed_bank_end = replenish_seed_bank(
            residual_seed=residual,
            new_seed=new_seed,
            mortality_rate=float(options.get("natural_seed_mortality", 0.20)),
        )

        machinery_cost = harvest_machine_cost(decision, repayments)
        revenue = compute_revenue(
            decision=decision,
            yield_t_ha=y["yield_t_ha"],
            profile=profile,
            prices=prices,
            stocking_dse=y["stocking_dse"],
        )
        costs = compute_costs(decision, prices, options, machinery_cost)

        gross_margin = revenue["total_revenue"] - costs["total_cost"]

        rows.append(
            {
                "year": year,
                "crop": decision.get("crop", "Wheat"),
                "gross_margin": gross_margin,
                "weed_control_cost": costs["weed_control_cost"],
                "income_grain": revenue["income_grain"],
                "income_pasture": revenue["income_pasture"],
                "income_livestock": revenue["income_livestock"],
                "yield_t_ha": y["yield_t_ha"],
                "yield_potential_t_ha": y["yield_potential_t_ha"],
                "ryegrass_penalty_fraction": y["ryegrass_penalty_fraction"],
                "ryegrass_plants_m2": survivors,
                "seed_bank_start": seed_bank,
                "seed_bank_end": seed_bank_end,
                "control_fraction": control,
                "stocking_dse": y["stocking_dse"],
                "new_seed_added": new_seed,
            }
        )

        seed_bank = seed_bank_end
        previous_crop = decision.get("crop", "Wheat")

    df = pd.DataFrame(rows)
    annuity = _annuity_from_cashflows(df["gross_margin"].tolist(), real_after_tax_rate)

    summary = {
        "avg_gross_margin": float(df["gross_margin"].mean()) if not df.empty else 0.0,
        "min_gross_margin": float(df["gross_margin"].min()) if not df.empty else 0.0,
        "max_gross_margin": float(df["gross_margin"].max()) if not df.empty else 0.0,
        "avg_weed_control_cost": float(df["weed_control_cost"].mean()) if not df.empty else 0.0,
        "nominal_annuity": annuity,
        "ending_seed_bank": float(df["seed_bank_end"].iloc[-1]) if not df.empty else 0.0,
    }

    return {
        "yearly": df,
        "summary": summary,
        "machinery_repayments": repayments,
    }
