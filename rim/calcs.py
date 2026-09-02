"""One year of the workbook, and the ten-year chain over it.

Composes the ported blocks in the order the workbook evaluates them. Each
simulation year is one column of ``Calcs`` (C..L), ``Bio results`` (D..M) and
``Eco results`` (E..N); this module is that column, and :func:`simulate_years`
walks it across the ten.

Years are joined by one number. ``Bio results!E11 = D20``: the seed bank left in
the soil next autumn becomes the next year's starting seed bank. Everything else
about a year -- germination, control, competition, seed set -- is computed from
that opening seed bank and the strategy chosen for the year.

Block order, and where each lives:

===== ============================== ==========================
Block Excel                          Module
===== ============================== ==========================
1     ``Calcs`` 184-189              ``rim/rotation.py``
2     ``Calcs`` C7:C49               ``rim/activation.py``
3     ``Calcs`` 55-97                ``rim/survival.py``
3b    ``Calcs`` C99, C164:C170       ``rim/stage_multipliers.py``
4     ``Bio results`` D3:D8, D11:D16 ``rim/population.py``
5     ``Bio results`` D17:D20        ``rim/seed_set.py``
===== ============================== ==========================

Yield (``Bio results!D23:D50``) and economics (``Eco results``) are not ported
yet, so this module reproduces the biology only -- exactly the ``TabSum`` block.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from rim.activation import activation_cells, is_sown
from rim.population import (
    SeasonState,
    germination_fractions,
    grazing_survival,
    plough_burial,
    run_season,
    starting_seed_bank,
)
from rim.population import load_table8
from rim.rotation import YearCodes, history_columns, rotation_codes
from rim.seed_set import (
    YearClose,
    close_year,
    cohort_competitiveness,
    effective_density,
    herbicide_applications,
    spring_spray_operations,
)
from rim.stage_multipliers import (
    load_constants,
    post_emergent_use_counts,
    stage_multipliers,
)
from rim.economics_model import (
    YearEconomics,
    machinery_loan_term,
    machinery_repayment_by_machine,
    machinery_repayments,
    nominal_annuity,
    stocking_rate,
    year_economics,
)
from rim.survival import survival_factors
from rim.yield_model import YieldResult, compute_yield

POST_EMERGENT_FIELDS = ("post_emergent_1", "post_emergent_2", "post_emergent_3")

# Calcs!C17 -- ploughing, whose yield benefit never expires.
MOULDBOARD_CELL = 17


@dataclass(frozen=True)
class YearResult:
    """Everything one column of the workbook produces, biology only."""

    year: int
    codes: YearCodes
    activation: dict[int, float | None]
    survival: dict[int, float]
    multipliers: dict[int, float]
    season: SeasonState
    weighted_density: float          # Calcs!C177
    close: YearClose
    yields: YieldResult              # Bio results D23:D54
    economics: YearEconomics         # Eco results E3:E63

    @property
    def plants(self) -> tuple[float, ...]:
        """Bio results D3:D8 -- the six ryegrass plant stages."""
        return self.season.plants

    @property
    def mature_plants(self) -> float:
        """Bio results!D8 -- mature ryegrass setting seed."""
        return self.season.plants[5]

    @property
    def seed_bank_next_autumn(self) -> float:
        """Bio results!D20 -- and the next year's D11."""
        return self.close.next_autumn

    @property
    def gross_margin(self) -> float:
        """Eco results!E63 -- receipts less every cost, $/ha."""
        return self.economics.gross_margin

    @property
    def grain_yield(self) -> float:
        """Bio results!D42:D45 -- what was actually harvested, t/ha."""
        return self.yields.grain_yield

    def tabsum(self) -> dict[str, float]:
        """This year's column of TabSum, by the workbook's own captions."""
        plants = self.season.plants
        seeds = self.season.seed_bank
        return {
            "first_chance_to_seed": plants[0],
            "ten_days_after_break": plants[1],
            "twenty_days_after_break": plants[2],
            "post_emergence_spray_time": plants[3],
            "early_spring": plants[4],
            "mature_setting_seed": plants[5],
            "end_of_summer": seeds[0],
            "after_first_chance_to_seed": seeds[1],
            "seeds_ten_days_after_break": seeds[2],
            "seeds_twenty_days_after_break": seeds[3],
            "seeds_post_emergence_spray_time": seeds[4],
            "seeds_spring": seeds[5],
            "seed_produced_per_plant": self.close.seed_per_plant,
            "seed_produced_per_m2": self.close.seed_produced,
            "just_before_harvest": self.close.before_harvest,
            "seeds_next_autumn": self.close.next_autumn,
        }


def run_year(
    strategy: Mapping[str, Any],
    *,
    seed_bank_start: float,
    codes: YearCodes,
    prev_crop_code: int,
    prev2_crop_code: int,
    year: int,
    mouldboard_ever: bool = False,
    machinery_repayment: float = 0.0,
    previous_activation: Mapping[int, Any] | None = None,
) -> YearResult:
    """Evaluate one column: strategy in, biology out."""
    constants = load_constants()

    activation = activation_cells(
        strategy,
        crop_code=codes.crop_code,
        prev_crop_code=prev_crop_code,
        prev2_crop_code=prev2_crop_code,
    )
    survival = survival_factors(activation)
    slots = [strategy.get(field) for field in POST_EMERGENT_FIELDS]
    multipliers = stage_multipliers(
        activation,
        survival,
        crop_code=codes.crop_code,
        post_emergent_slots=slots,
        pre_emergent_selected=bool(strategy.get("pre_emergent")),
    )

    germination = germination_fractions(
        activation, sown=is_sown(codes.crop_code, prev_crop_code, prev2_crop_code)
    )
    season = run_season(
        seed_bank_start,
        germination,
        multipliers,
        burial=plough_burial(activation),
        grazing=grazing_survival(activation, codes.rotation_key),
        seed_loss_pre_harvest=constants["seed_loss_pre_harvest"],
    )

    weighted_density = effective_density(
        season.seed_bank,
        season.plants[0],
        germination,
        multipliers,
        cohort_competitiveness(activation),
    )
    close = close_year(
        activation=activation,
        crop_code=codes.crop_code,
        plants_spray_time=season.plants[4],
        plants_mature=season.plants[5],
        seed_bank_spring=season.seed_bank[5],
        weighted_density=weighted_density,
        harvest_multiplier=multipliers[170],
        herbicide_count=herbicide_applications(
            activation, post_emergent_use_counts(slots, activation)
        ),
        spring_spray_count=spring_spray_operations(activation),
        summer_seed_loss=constants["seed_loss_over_summer"],
    )

    # Block 6 -- yield. Table 8 supplies the weed-free potential and the
    # nitrogen credit, both keyed on this year's rotation key.
    table8 = load_table8()["by_key"].get(str(int(codes.rotation_key)), {})
    sprays = herbicide_applications(
        activation, post_emergent_use_counts(slots, activation)
    )
    yields = compute_yield(
        activation,
        crop_code=codes.crop_code,
        phase_code=codes.phase_code,
        weed_free_from_table8=table8.get("weed_free_yield", 0.0),
        ryegrass_early_spring=season.plants[4],
        herbicide_applications=sprays,
        mouldboard_ever=mouldboard_ever,
        two_years_ago_crop_code=prev2_crop_code,
        previous_activation=previous_activation,
    )

    # Block 7 -- economics.
    economics = year_economics(
        activation,
        crop_code=codes.crop_code,
        rotation_key=codes.rotation_key,
        grain_yield=yields.grain_yield,
        fodder_yield=yields.fodder_yield,
        baled_yield=yields.baled_yield,
        stocking_dse=stocking_rate(activation, table8),
        nitrogen_saving=table8.get("nitrogen_saving", 0.0),
        machinery_repayment=machinery_repayment,
    )

    return YearResult(
        year=year,
        codes=codes,
        activation=activation,
        survival=survival,
        multipliers=multipliers,
        season=season,
        weighted_density=weighted_density,
        close=close,
        yields=yields,
        economics=economics,
    )


def simulate_years(
    strategy_rows: Sequence[Mapping[str, Any]],
    *,
    one_year_ago: str = "w",
    two_years_ago: str = "w",
    seed_bank_start: float | None = None,
) -> list[YearResult]:
    """Run the biological model across a strategy, chaining the seed bank.

    ``strategy_rows`` holds the workbook's own labels, one dict per year, keyed
    by the field names in ``tools/cell_map.py``. ``seed_bank_start`` defaults to
    the workbook's own year-1 figure (``+Options!AG96 * AG124``).
    """
    codes = rotation_codes(
        [row.get("enterprise") for row in strategy_rows],
        one_year_ago=one_year_ago,
        two_years_ago=two_years_ago,
    )
    two_ago, one_ago = history_columns(
        one_year_ago=one_year_ago, two_years_ago=two_years_ago
    )
    previous = [one_ago.crop_code] + [c.crop_code for c in codes[:-1]]
    before = [two_ago.crop_code, one_ago.crop_code] + [c.crop_code for c in codes[:-2]]

    seed_bank = starting_seed_bank() if seed_bank_start is None else float(seed_bank_start)

    # Machinery repayment cannot be worked out a year at a time: a machine's age
    # counter starts when it is first used and runs for the loan term, so year 8
    # is still paying for a header bought in year 1. Activation is pure and needs
    # only the strategy and the crop codes, so derive it for the whole run first.
    activations = [
        activation_cells(row, crop_code=code.crop_code,
                         prev_crop_code=prev, prev2_crop_code=prev2)
        for row, code, prev, prev2 in zip(strategy_rows, codes, previous, before)
    ]
    repayments = machinery_repayments(
        activations,
        [code.crop_code for code in codes],
        machinery_repayment_by_machine(),
        machinery_loan_term(),
    )

    results: list[YearResult] = []
    mouldboard_ever = False
    for index, (row, code, prev, prev2) in enumerate(
        zip(strategy_rows, codes, previous, before)
    ):
        # Bio results!D27 expands its COUNTIF range each year, so the mouldboard
        # yield benefit is permanent once earned.
        mouldboard_ever = mouldboard_ever or (
            activations[index].get(MOULDBOARD_CELL) not in (None, "")
        )
        result = run_year(
            row,
            seed_bank_start=seed_bank,
            codes=code,
            prev_crop_code=prev,
            prev2_crop_code=prev2,
            year=index + 1,
            mouldboard_ever=mouldboard_ever,
            machinery_repayment=repayments[index],
            previous_activation=activations[index - 1] if index else None,
        )
        results.append(result)
        # Bio results!E11 = D20 -- the only thread between years.
        seed_bank = result.seed_bank_next_autumn

    return results
