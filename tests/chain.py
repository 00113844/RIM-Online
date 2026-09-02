"""Run the ported model over a fixture, for tests to assert against.

Thin wrapper over :func:`rim.calcs.simulate_years` that pairs each year's result
with the Excel reference block captured in the fixture.

Nothing from Excel is used as an input except the strategy grid and the paddock
history. The seed bank chains year to year through the model itself.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from rim.calcs import YearResult, simulate_years

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

# Bio results rows 23-54 (yield) and Eco results rows 3-63 (economics) that the
# fixtures capture whole, so blocks 6 and 7 can be asserted line by line.
YIELD_GROUPS: dict[str, range] = {
    "weed_free_yield": range(30, 34),
    "grain_yield": range(42, 46),
    "fodder_yield": range(46, 51),
    "baled_yield": range(51, 55),
}
ECO_ROWS: dict[str, str] = {
    "total_receipts": "8",
    "non_weed_costs": "13",
    "weed_control_costs": "59",
    "gross_margin": "63",
}

# Bio results rows 17-20, which close the year.
TABSUM_CLOSING_ROWS: dict[str, int] = {
    "seed_produced_per_plant": 17,
    "seed_produced_per_m2": 18,
    "just_before_harvest": 19,
    "seeds_next_autumn": 20,
}


def fixtures() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [FIXTURE_DIR / name for name in manifest["scenarios"]]


@dataclass(frozen=True)
class Year:
    """One year, with the Python result and the Excel reference side by side."""

    result: YearResult
    strategy: dict[str, Any]
    tabsum: dict[str, Any]
    expected_rotation: dict[str, Any]
    expected_activation: dict[str, Any]
    expected_survival: dict[str, Any]
    expected_multipliers: dict[str, Any]
    expected_yields: dict[str, Any]
    expected_eco: dict[str, Any]

    @property
    def year(self) -> int:
        return self.result.year


def walk(fixture_path: Path) -> Iterator[Year]:
    """Yield each year of a fixture, model result beside Excel reference."""
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    excel = fixture["inputs"]["excel"]
    reference = fixture["reference"]

    results = simulate_years(excel["strategy"], **excel["history"])

    for index, result in enumerate(results):
        yield Year(
            result=result,
            strategy=excel["strategy"][index],
            tabsum=reference["tabsum"][index],
            expected_rotation=reference["rotation_codes"][index],
            expected_activation=reference["activation"][index],
            expected_survival=reference["survival_factors"][index],
            expected_multipliers=reference["stage_multipliers"][index],
            expected_yields=reference["yields"][index],
            expected_eco=reference["eco_detail"][index],
        )
