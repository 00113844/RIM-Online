"""The UI's 'this choice does nothing' rules must match the workbook's gates.

Excel does not refuse an impossible selection — it accepts it and drops it from
the calculation. On screen that is indistinguishable from an option that worked,
which is how someone ends up believing they are controlling ryegrass when they
are not. These rules surface that, so each one has to be true.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils.applicability import gates, ineffective_choices, neutralise, summarise

TABLE8 = Path(__file__).resolve().parents[1] / "data" / "calcs_table8.json"

CROP_KEYS = ("0", "1", "2", "3")       # wheat, barley, canola, legume
PASTURE_KEYS = ("4", "7", "10")        # first year of volunteer, clover, Cadiz


def _year(**overrides) -> dict:
    base = {
        "year": 1, "crop": "Wheat", "seeding_timing": "Dry",
        "seeding_technique": "No-till", "seeding_rate": "Standard",
        "pre_tillage": "None", "knockdown": "None", "pre_emergent": "None",
        "post_emergent_1": "None", "post_emergent_2": "None",
        "post_emergent_3": "None", "spring_option": "None",
        "grazing_intensity": "None", "harvest_option": "Standard",
    }
    base.update(overrides)
    return base


def _fields(findings) -> set[str]:
    return {f["field"] for f in findings}


# ── The claims each rule rests on, checked against the generated data ─────────

def test_table8_gives_crops_no_grazing_or_stocking() -> None:
    """The grazing rule is only honest if every crop key really is zero."""
    table = json.loads(TABLE8.read_text(encoding="utf-8"))["by_key"]

    for key in CROP_KEYS:
        entry = table[key]
        for column in (
            "ryegrass_control_standard_grazing",
            "ryegrass_control_high_grazing",
            "stocking_standard",
            "stocking_high",
        ):
            assert entry[column] == 0, f"Table 8 key {key} ({entry['label']}), {column}"

    for key in PASTURE_KEYS:
        assert table[key]["ryegrass_control_standard_grazing"] > 0


# ── The rules themselves ──────────────────────────────────────────────────────

def test_grazing_a_crop_does_nothing() -> None:
    findings = ineffective_choices([_year(crop="Canola", grazing_intensity="Standard")])

    assert "Grazing" in _fields(findings)
    assert "livestock income" in findings[0]["reason"]


def test_grazing_a_pasture_is_fine() -> None:
    findings = ineffective_choices(
        [_year(crop="Sub-Clover pasture", grazing_intensity="Standard")]
    )

    assert "Grazing" not in _fields(findings)


def test_knockdown_is_gated_by_dry_or_wet_sowing() -> None:
    """2.Strategy!D65 — no gap before seeding, so it is not counted twice."""
    for timing in ("Dry", "Wet"):
        findings = ineffective_choices(
            [_year(seeding_timing=timing, knockdown="Single knock-down")]
        )
        assert "Knock-down" in _fields(findings), timing

    delayed = ineffective_choices(
        [_year(seeding_timing="Delayed (1-2 wks)", knockdown="Single knock-down")]
    )
    assert "Knock-down" not in _fields(delayed)


def test_unsown_pasture_ignores_seeding_and_pre_emergent() -> None:
    """2.Strategy!D66 — volunteer pasture regenerates, it is never sown."""
    plan = [_year(crop="Volunteer pasture", pre_emergent="Triazine", seeding_rate="High")]

    # All four seeding-related decisions are gated, so the editor disables them.
    blocked = gates(plan)[0]
    assert {"pre_emergent", "seeding_technique", "seeding_rate", "seeding_timing"} <= set(blocked)

    # Only the pre-emergent is *cleared*: a sowing system has no meaningful
    # "off" value, so it is left alone and simply never read.
    assert _fields(ineffective_choices(plan)) == {"Pre-emergent"}


def test_first_year_of_clover_is_sown_so_pre_emergent_counts() -> None:
    """A clover phase is re-sown in its first year, then regenerates."""
    plan = [
        _year(year=1, crop="Wheat"),
        _year(year=2, crop="Sub-Clover pasture", pre_emergent="Triazine"),
        _year(year=3, crop="Sub-Clover pasture", pre_emergent="Triazine"),
    ]
    findings = ineffective_choices(plan)
    flagged = {f["year"] for f in findings if f["field"] == "Pre-emergent"}

    assert 2 not in flagged, "year 2 is sown, so the pre-emergent applies"
    assert 3 in flagged, "year 3 regenerates, so it does not"


def test_harvest_control_needs_a_harvest() -> None:
    findings = ineffective_choices(
        [_year(crop="Volunteer pasture", harvest_option="HSD")]
    )

    assert "Harvest control" in _fields(findings)


def test_standard_harvest_is_not_flagged() -> None:
    """'Standard' is the absence of weed seed control, not a choice that failed."""
    findings = ineffective_choices(
        [_year(crop="Volunteer pasture", harvest_option="Standard")]
    )

    assert "Harvest control" not in _fields(findings)


def test_a_clean_plan_raises_nothing() -> None:
    findings = ineffective_choices([
        _year(year=1, crop="Wheat", seeding_timing="Delayed (1-2 wks)",
              knockdown="Single knock-down", pre_emergent="Sakura",
              harvest_option="Narrow windrow burn"),
    ])

    assert findings == []
    assert summarise(findings) == ""


def test_summary_counts_distinct_problems_not_rows() -> None:
    """The same mistake repeated for ten years is one problem, not ten."""
    plan = [_year(year=n, knockdown="Single knock-down") for n in range(1, 11)]

    assert summarise(ineffective_choices(plan)).startswith("One choice was cleared")


def test_neutralise_leaves_no_impossible_value_behind() -> None:
    """The grid cannot disable a cell, so the plan is cleaned after every edit."""
    plan = [
        _year(year=1, crop="Canola", grazing_intensity="Standard"),
        _year(year=2, crop="Volunteer pasture", harvest_option="HSD", pre_emergent="Triazine"),
    ]

    cleaned, changes = neutralise(plan)

    assert cleaned[0]["grazing_intensity"] == "None"
    assert cleaned[1]["harvest_option"] == "Standard"
    assert cleaned[1]["pre_emergent"] == "None"
    assert len(changes) == 3
    # Running it again finds nothing left to clear.
    assert neutralise(cleaned)[1] == []


def test_neutralise_leaves_valid_choices_alone() -> None:
    plan = [_year(crop="Sub-Clover pasture", grazing_intensity="High",
                  seeding_timing="Delayed (1-2 wks)", knockdown="Double knock-down")]

    cleaned, changes = neutralise(plan)

    assert changes == []
    assert cleaned[0]["grazing_intensity"] == "High"
    assert cleaned[0]["knockdown"] == "Double knock-down"
