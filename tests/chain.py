"""Compose the ported blocks over a fixture, for tests to assert against.

Blocks 1, 2, 3, 3b and 4 each stand alone, but they only mean anything chained.
This helper runs them in workbook order for one fixture and yields, per year,
everything a test might want to compare against ``reference``.

It deliberately takes only the strategy grid and paddock history from Excel.
The one exception is the year's opening seed bank, which comes from
``reference.tabsum.end_of_summer``: closing the year and handing the seed bank
to the next one is block 5, which is not ported yet.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from rim.activation import activation_cells, is_sown
from rim.population import (
    SeasonState,
    germination_fractions,
    grazing_survival,
    plough_burial,
    run_season,
)
from rim.rotation import YearCodes, history_columns, rotation_codes
from rim.stage_multipliers import load_constants, stage_multipliers
from rim.survival import survival_factors

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "excel_parity"
MANIFEST = FIXTURE_DIR / "manifest.json"

# TabSum caption -> Bio results row, for the stages block 4 produces.
TABSUM_ROWS: dict[str, int] = {
    "first_chance_to_seed": 3,
    "ten_days_after_break": 4,
    "twenty_days_after_break": 5,
    "post_emergence_spray_time": 6,
    "early_spring": 7,
    "mature_setting_seed": 8,
    "end_of_summer": 11,
    "after_first_chance_to_seed": 12,
    "seeds_ten_days_after_break": 13,
    "seeds_twenty_days_after_break": 14,
    "seeds_post_emergence_spray_time": 15,
    "seeds_spring": 16,
}


def fixtures() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [FIXTURE_DIR / name for name in manifest["scenarios"]]


@dataclass(frozen=True)
class Year:
    """One year, with the Python result and the Excel reference side by side."""

    year: int
    strategy: dict[str, Any]
    codes: YearCodes
    activation: dict[int, float | None]
    factors: dict[int, float]
    multipliers: dict[int, float]
    season: SeasonState
    tabsum: dict[str, Any]
    expected_activation: dict[str, Any]
    expected_survival: dict[str, Any]
    expected_multipliers: dict[str, Any]


def walk(fixture_path: Path) -> Iterator[Year]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    excel = fixture["inputs"]["excel"]
    reference = fixture["reference"]
    strategy, history = excel["strategy"], excel["history"]

    codes = rotation_codes([row.get("enterprise") for row in strategy], **history)
    two_ago, one_ago = history_columns(**history)
    previous = [one_ago.crop_code] + [c.crop_code for c in codes[:-1]]
    before = [two_ago.crop_code, one_ago.crop_code] + [c.crop_code for c in codes[:-2]]

    seed_loss = load_constants()["seed_loss_pre_harvest"]

    for index, (row, code, prev, prev2) in enumerate(
        zip(strategy, codes, previous, before)
    ):
        activation = activation_cells(
            row, crop_code=code.crop_code, prev_crop_code=prev, prev2_crop_code=prev2
        )
        factors = survival_factors(activation)
        multipliers = stage_multipliers(
            activation,
            factors,
            crop_code=code.crop_code,
            post_emergent_slots=[row.get(f"post_emergent_{n}") for n in (1, 2, 3)],
            pre_emergent_selected=bool(row.get("pre_emergent")),
        )
        tabsum = reference["tabsum"][index]
        season = run_season(
            tabsum["end_of_summer"],
            germination_fractions(
                activation, sown=is_sown(code.crop_code, prev, prev2)
            ),
            multipliers,
            burial=plough_burial(activation),
            grazing=grazing_survival(activation, code.rotation_key),
            seed_loss_pre_harvest=seed_loss,
        )

        yield Year(
            year=index + 1,
            strategy=row,
            codes=code,
            activation=activation,
            factors=factors,
            multipliers=multipliers,
            season=season,
            tabsum=tabsum,
            expected_activation=reference["activation"][index],
            expected_survival=reference["survival_factors"][index],
            expected_multipliers=reference["stage_multipliers"][index],
        )
