"""Economics: a direct port of Eco results!E3:E63 and the annuity at E66:E73.

Receipts minus costs gives a gross margin per year. The costs are itemised the
way the workbook itemises them — **one line per control option**, drawn from the
cost table at ``Calcs!N105:T147``, which is the exact twin of the control table
the survival factors come from.

The annuity is the part worth reading carefully. It is **not** a discounted
average of the yearly gross margins, which is what a reader (and the pre-port
``rim/economics.py``) naturally assumes. ``Eco results`` rows 66-73 carry a
*compounding after-tax balance* forward through the ten years::

    E66 = (grain + hay + silage + bales) x yield_trend x price_inflation
        + pasture x productivity_trend x sheep_inflation
    E67 = costs x input_inflation
    E68 = interest x previous year's E70        <- the compounding term
    E69 = tax x (E66 - E67 + E68)
    E70 = E66 - E67 + E68 - E69                 <- carried into next year
    E72 = N70 / (1 + interest x (1 - tax)) ** 10
    E73 = -PMT(interest x (1 - tax), 10, E72) / (1 - tax)

``E73`` is the figure the interface calls the nominal annuity, and it is what
``EcoSum!P5`` shows.

This module does not touch ``rim/economics.py``, which belongs to the pre-port
engine and is still what the Streamlit app runs on.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy_financial as npf

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ECONOMICS_PATH = DATA_DIR / "economics.json"
COST_TABLE_PATH = DATA_DIR / "calcs_cost_table.json"

GRAIN_CROP_CODES = (0, 1, 2, 3)
SIMULATION_YEARS = 10

# Activation cells the cost side reads.
CELL_FULL_CUT = 18          # Calcs!C298 — environmental cost of cultivation
CELL_SOWN_DRY = 19          # Calcs!C298
CELL_GREEN_MANURE = 34      # Calcs!C299:C302 — fertiliser saved
CELL_HAY = 35               # Eco results!E4
CELL_SILAGE = 36            # Eco results!E5

# Calcs cost row r is charged when activation cell r - 98 is set.
COST_TO_ACTIVATION_OFFSET = 98

# Rotation keys that identify a pasture, and which cost table each reads.
VOLUNTEER_KEYS = ("4", "5", "6")
CLOVER_KEYS = ("7", "8", "9")
CADIZ_KEYS = ("10", "11", "12")


@dataclass(frozen=True)
class YearEconomics:
    """Eco results rows 3-63 for one year, all $/ha."""

    grain_receipts: float       # E3
    hay_receipts: float         # E4
    silage_receipts: float      # E5
    bale_receipts: float        # E6
    pasture_receipts: float     # E7
    total_receipts: float       # E8
    non_weed_costs: float       # E13
    weed_control_costs: float   # E59
    total_costs: float          # E61
    gross_margin: float         # E63


@lru_cache(maxsize=1)
def load_parameters(path: str | None = None) -> dict[str, Any]:
    return _load(Path(path) if path else ECONOMICS_PATH)


@lru_cache(maxsize=1)
def load_cost_table(path: str | None = None) -> dict[str, Any]:
    return _load(Path(path) if path else COST_TABLE_PATH)["options"]


def _load(target: Path) -> dict[str, Any]:
    if not target.is_file():
        raise FileNotFoundError(
            f"{target} is missing. Regenerate it with:\n"
            r"    .venv\Scripts\python -m tools.extract_params"
        )
    return json.loads(target.read_text(encoding="utf-8"))


def _active(value: Any) -> bool:
    return value is not None and value != ""


def weed_control_cost(
    activation: Mapping[int, Any],
    crop_code: int,
    machinery_repayment: float = 0.0,
    cost_table: dict[str, Any] | None = None,
) -> float:
    """Eco results!E15:E59 -- every active option's cost, plus machinery.

    Which activation cell each cost row reads is recorded per row in the
    generated table, because it is mostly ``r - 98`` and occasionally not:
    ``Calcs!C128`` (Brown M) reads ``C31`` and ``C129`` (Topping) reads ``C30``,
    the same transposition the survival block has at rows 78 and 79.

    Do **not** route this through the survival block's SOURCE map either. Some
    options are priced but have no survival row — full-cut seeding is charged at
    ``Calcs!C116`` while ``C66`` carries no formula, because full-cut acts on
    ryegrass through the seeding rows instead — and going that way silently
    drops those costs.
    """
    cost_table = cost_table if cost_table is not None else load_cost_table()
    total = 0.0
    for row, entry in cost_table.items():
        activation_cell = int(entry.get("activation_cell", int(row) - COST_TO_ACTIVATION_OFFSET))
        if not _active(activation.get(activation_cell)):
            continue
        total += float(entry["cost_by_crop_code"].get(str(crop_code), 0.0))
    return total + machinery_repayment


def non_weed_cost(
    activation: Mapping[int, Any],
    *,
    crop_code: int,
    rotation_key: int,
    nitrogen_saving: float,
    parameters: dict[str, Any] | None = None,
) -> float:
    """Eco results!E11:E13 via Calcs!C297:C306 -- everything that is not weed control."""
    parameters = parameters if parameters is not None else load_parameters()

    # Calcs!C298 — environmental cost of cultivation, half per trigger.
    env = float(parameters["cultivation_env_cost"])
    cultivation = sum(
        env / 2.0
        for cell in (CELL_FULL_CUT, CELL_SOWN_DRY)
        if _active(activation.get(cell))
    )

    key = str(int(rotation_key))
    if crop_code in GRAIN_CROP_CODES:
        base = float(parameters["non_weed_crop_cost"][str(crop_code)])
        saving = 0.0
        if _active(activation.get(CELL_GREEN_MANURE)):
            which = "legume" if crop_code == 3 else ("canola" if crop_code == 2 else "cereal")
            saving = float(parameters["green_manure_saving"][which])
        # Legumes fix their own nitrogen, so they take no N-saving credit.
        credit = 0.0 if crop_code == 3 else float(nitrogen_saving)
        return base + cultivation - credit - saving

    # Pastures: the cost depends on which phase year the rotation key names.
    # Calcs!C303:C305 do not add C298 — the cultivation cost is charged on crops
    # only, unlike C299:C302 which all include it.
    if key in VOLUNTEER_KEYS:
        return float(parameters["pasture_cost_volunteer"][key])
    if key in CLOVER_KEYS:
        return float(parameters["pasture_cost_clover"][key])
    if key in CADIZ_KEYS:
        return float(parameters["pasture_cost_cadiz"][key])
    return 0.0


def pasture_returns(
    stocking_dse: float, parameters: dict[str, Any] | None = None
) -> float:
    """Calcs!C327 -- stocking rate times the sheep gross margin per DSE."""
    parameters = parameters if parameters is not None else load_parameters()
    return float(stocking_dse) * float(parameters["prices"]["sheep_gm_per_dse"])


def year_economics(
    activation: Mapping[int, Any],
    *,
    crop_code: int,
    rotation_key: int,
    grain_yield: float,
    fodder_yield: float,
    baled_yield: float,
    stocking_dse: float,
    nitrogen_saving: float,
    machinery_repayment: float = 0.0,
    parameters: dict[str, Any] | None = None,
) -> YearEconomics:
    """Eco results!E3:E63 for one year."""
    parameters = parameters if parameters is not None else load_parameters()
    prices = parameters["prices"]

    grain = (
        float(grain_yield) * float(prices[f"grain_{crop_code}"])
        if crop_code in GRAIN_CROP_CODES else 0.0
    )
    hay = float(fodder_yield) * float(prices["hay"]) if _active(activation.get(CELL_HAY)) else 0.0
    silage = (
        float(fodder_yield) * float(prices["silage"])
        if _active(activation.get(CELL_SILAGE)) else 0.0
    )
    bales = float(baled_yield) * float(prices["bales"])
    pasture = pasture_returns(stocking_dse, parameters)
    receipts = grain + hay + silage + bales + pasture

    non_weed = non_weed_cost(
        activation, crop_code=crop_code, rotation_key=rotation_key,
        nitrogen_saving=nitrogen_saving, parameters=parameters,
    )
    weed = weed_control_cost(activation, crop_code, machinery_repayment)
    costs = non_weed + weed

    return YearEconomics(
        grain_receipts=grain,
        hay_receipts=hay,
        silage_receipts=silage,
        bale_receipts=bales,
        pasture_receipts=pasture,
        total_receipts=receipts,
        non_weed_costs=non_weed,
        weed_control_costs=weed,
        total_costs=costs,
        gross_margin=receipts - costs,
    )


def nominal_annuity(
    years: Sequence[YearEconomics],
    parameters: dict[str, Any] | None = None,
) -> float:
    """Eco results!E66:E73 -- the long-term average, EcoSum!P5.

    A compounding after-tax balance across the whole run, then a PMT. Not a
    discounted average of the yearly gross margins: the ``interest x previous
    balance`` term means an early good year keeps earning.
    """
    parameters = parameters if parameters is not None else load_parameters()
    if not years:
        return 0.0

    interest = float(parameters["interest_rate"])
    tax = float(parameters["tax_rate"])

    rates = parameters["trend_rates"]

    def factor(name: str, year_number: int) -> float:
        """Calcs 362-366 for year n -- the rate compounded n times."""
        return (1.0 + float(rates[name])) ** year_number

    balance = 0.0
    for year_number, year in enumerate(years, start=1):
        # E66 — receipts, grown by the yield and price trends.
        cropping = (
            year.grain_receipts + year.hay_receipts
            + year.silage_receipts + year.bale_receipts
        ) * factor("crop_yield_trend", year_number) * factor("crop_price_inflation", year_number)
        livestock = (
            year.pasture_receipts
            * factor("pasture_productivity_trend", year_number)
            * factor("sheep_price_inflation", year_number)
        )
        inflated_receipts = cropping + livestock

        # E67 — costs, grown by input inflation.
        inflated_costs = year.total_costs * factor("input_cost_inflation", year_number)

        # E68 — interest earned on what the run has accumulated so far.
        interest_earned = interest * balance

        # E69, E70. The previous balance is carried *forward* as well as
        # earning interest: F70 = (F66 - F67 + F68) * (1 - tax) + E70. Year 1
        # has no previous balance, so it starts the chain at zero.
        taxable = inflated_receipts - inflated_costs + interest_earned
        balance = taxable * (1.0 - tax) + balance

    real_rate = interest * (1.0 - tax)
    present_value = balance / (1.0 + real_rate) ** SIMULATION_YEARS   # E72
    return float(-npf.pmt(real_rate, SIMULATION_YEARS, present_value)) / (1.0 - tax)


# --- Stocking and machinery, the two things a year cannot work out alone ----

# Calcs!C319, C321, C323, C325 -- each grazing flag draws a different stocking
# column out of Table 8.
STOCKING_COLUMNS = (
    "stocking_standard",         # C319 <- C310
    "stocking_high",             # C321 <- C312
    "stocking_standard_if_hay",  # C323 <- C322
    "stocking_high_if_hay",      # C325 <- C324
)


def stocking_rate(activation: Mapping[int, Any], table8_entry: Mapping[str, Any]) -> float:
    """Calcs!C318:C325 -- DSE/ha carried this year, before the sheep margin."""
    from rim.population import grazing_flags

    flags = grazing_flags(activation)
    return sum(
        float(table8_entry.get(column, 0.0)) * flag
        for column, flag in zip(STOCKING_COLUMNS, flags)
    )


# Calcs!C346:C357 -- harvest activation cell -> its machine's age counter, and
# Calcs!C358 -> the '+Prices' repayment for that machine.
HWSC_MACHINES = {
    41: "cart_and_burn",
    42: "narrow_windrow",
    43: "harrington_seed_destructor",
    44: "chaff_tramlining",
    45: "spare_slot",
    46: "bale_direct",
}
FIRST_PASTURE_CROP_CODE = 4


def machinery_repayments(
    activations: Sequence[Mapping[int, Any]],
    crop_codes: Sequence[int],
    repayment_by_machine: Mapping[str, float],
    loan_term_years: int,
) -> list[float]:
    """Calcs!C346:C358 -- HWSC machinery repayment, per year, across a run.

    A machine's age counter starts at 1 the year it is first used and increments
    every year after, whether or not it is used again; the repayment is charged
    while the age is 1..``loan_term_years``. So this cannot be computed a year at
    a time — buying a seed destructor in year 1 is still being paid for in year 8.

    Harvest machinery is not charged on a pasture year: there is no header pass.
    """
    ages = {cell: 0 for cell in HWSC_MACHINES}
    out: list[float] = []

    for activation, crop_code in zip(activations, crop_codes):
        charge = 0.0
        for cell, machine in HWSC_MACHINES.items():
            used = (
                crop_code < FIRST_PASTURE_CROP_CODE
                and _active(activation.get(cell))
            )
            ages[cell] = ages[cell] + 1 if ages[cell] > 0 else (1 if used else 0)
            if 0 < ages[cell] <= loan_term_years:
                charge += float(repayment_by_machine.get(machine, 0.0))
        out.append(charge)

    return out


@lru_cache(maxsize=1)
def machinery_repayment_by_machine() -> dict[str, float]:
    """'+Prices'!AR72:AR77 -- the per-hectare repayment for each HWSC machine."""
    parameters = load_parameters()
    return dict(parameters["machinery_repayments"])


@lru_cache(maxsize=1)
def machinery_loan_term() -> int:
    """'+Prices'!O37 -- how many years a machine is paid off over."""
    return int(load_parameters()["machinery_loan_term_years"])
