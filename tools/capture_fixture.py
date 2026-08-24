r"""Capture the workbook's saved scenario as an approved parity fixture.

Usage:
    .venv\Scripts\python -m tools.capture_fixture [--name NAME] [--force]

Reads cached values straight out of the workbook (no Excel required, no
recalculation) and writes tests/fixtures/excel_parity/<name>.json, registering
it in manifest.json.

Expected values come from Excel and only from Excel. Nothing in this module
imports rim.engine -- see .claude/memory/parity-fixture-protocol.md.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any

from rim.defaults import DEFAULT_OPTIONS, DEFAULT_PRICES, DEFAULT_PROFILE
from rim.excel_inputs import TRANSLATION_LOSSES, translate_strategy
from tools import cell_map as cm
from tools import workbook_reader as wr

FIXTURE_DIR = wr.REPO_ROOT / "tests" / "fixtures" / "excel_parity"
MANIFEST = FIXTURE_DIR / "manifest.json"

# Which Excel quantity each simulate_strategy() output field is compared against.
# (python_field, source description, tolerance)
YEARLY_FIELDS: list[tuple[str, str, dict[str, float]]] = [
    ("gross_margin", "EcoSum 'Gross margin ($/ha)' (Eco results row 16)", {"absolute": 0.01, "relative": 0.001}),
    ("weed_control_cost", "EcoSum Herbicides + Mechanical + User's options (rows 11-13)", {"absolute": 0.01, "relative": 0.001}),
    ("ryegrass_plants_m2", "TabSum 'Mature ryegrass setting seed' (Bio results row 8)", {"absolute": 0.01, "relative": 0.001}),
    ("seed_bank_end", "TabSum 'Seeds in soil next autumn' (Bio results row 20)", {"absolute": 0.01, "relative": 0.001}),
]

SUMMARY_FIELDS: list[tuple[str, str, dict[str, float]]] = [
    ("avg_gross_margin", "Eco results!P5, average gross margin over 10 years", {"absolute": 0.01, "relative": 0.001}),
]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def build_fixture(name: str | None = None) -> tuple[str, dict[str, Any]]:
    """Capture the workbook's own saved scenario. Needs no Excel."""
    wb = wr.load()
    scenario = wr.read_profile_scenario_name(wb)
    name = name or _slug(scenario)
    return name, assemble(
        name=name,
        scenario=scenario,
        excel_strategy=wr.read_strategy(wb),
        tabsum=wr.read_tabsum(wb),
        ecosum_and_average=wr.read_ecosum(wb),
        rotation=wr.read_rotation_codes(wb),
        activation=wr.read_activation(wb),
        survival=wr.read_survival_factors(wb),
        history=wr.read_history(wb),
        method="openpyxl cached values from the workbook's saved state "
               "(exact floats; no recalculation, no rounding)",
    )


def build_fixture_from_scenario(scenario_path: Path, name: str | None = None) -> tuple[str, dict[str, Any]]:
    """Capture a new scenario by driving Excel. Requires Excel + pywin32."""
    from tools import excel_oracle

    doc = json.loads(scenario_path.read_text(encoding="utf-8"))
    outputs = excel_oracle.capture(scenario_path)
    name = name or _slug(doc.get("name", scenario_path.stem))
    return name, assemble(
        name=name,
        scenario=doc.get("description") or doc.get("name", scenario_path.stem),
        excel_strategy=doc["strategy"],
        tabsum=outputs["tabsum"],
        ecosum_and_average=(outputs["ecosum"], outputs["average_gross_margin"]),
        rotation=outputs["rotation"],
        activation=outputs["activation"],
        survival=outputs["survival"],
        history=outputs["history"],
        method=f"Excel COM recalculation of scenarios/{scenario_path.name} "
               "(CalculateFullRebuild, Value2 reads, macros force-disabled)",
    )


def assemble(
    *,
    name: str,
    scenario: str,
    excel_strategy: list[dict[str, Any]],
    tabsum: list[dict[str, Any]],
    ecosum_and_average: tuple[list[dict[str, Any]], float | None],
    rotation: list[dict[str, Any]],
    activation: list[dict[str, Any]],
    survival: list[dict[str, Any]],
    history: dict[str, str],
    method: str,
) -> dict[str, Any]:
    """Build the fixture document from Excel-sourced outputs.

    Expected values arrive here already read from Excel. Nothing in this
    function consults the Python engine.
    """
    workbook_path = wr.find_workbook()
    ecosum, average_gm = ecosum_and_average

    # Year 1's starting seed bank is the workbook's own end-of-summer figure.
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile["seed_bank_start"] = tabsum[0]["end_of_summer"]
    profile["paddock_name"] = scenario

    expected_yearly = []
    for eco, tab in zip(ecosum, tabsum):
        weed_cost = sum(
            eco[k] or 0.0
            for k in ("cost_herbicides", "cost_mechanical", "cost_user_options")
        )
        values = {
            "gross_margin": eco["gross_margin"],
            "weed_control_cost": weed_cost,
            "ryegrass_plants_m2": tab["mature_setting_seed"],
            "seed_bank_end": tab["seeds_next_autumn"],
        }
        expected_yearly.append(
            {
                "year": eco["year"],
                "values": values,
                "tolerances": {f: tol for f, _, tol in YEARLY_FIELDS},
                "sources": {f: src for f, src, _ in YEARLY_FIELDS},
            }
        )

    fixture = {
        "schema_version": 1,
        "name": name,
        "scenario": scenario,
        "source": {
            "workbook": cm.WORKBOOK_VERSION,
            "file": workbook_path.name,
            "captured_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "method": method,
            "ranges": {
                "strategy": cm.NAMED_RANGES["Strategy_X"],
                "economics": cm.NAMED_RANGES["EcoSum"],
                "biology": cm.NAMED_RANGES["TabSum"],
            },
        },
        "units": {
            "gross_margin": "$/ha",
            "weed_control_cost": "$/ha",
            "ryegrass_plants_m2": "plants/m2",
            "seed_bank_end": "seeds/m2",
            "avg_gross_margin": "$/ha/yr",
        },
        "translation": {
            "lossy": True,
            "adapter": "rim.excel_inputs.translate_strategy",
            "losses": list(TRANSLATION_LOSSES),
            "note": "profile/prices/options are rim.defaults values, not yet read "
                    "from the workbook; only seed_bank_start is taken from Excel. "
                    "See .claude/memory/defaults-are-hand-transcribed.md",
        },
        "inputs": {
            "excel": {"strategy": excel_strategy, "history": history},
            "profile": profile,
            "prices": copy.deepcopy(DEFAULT_PRICES),
            "options": copy.deepcopy(DEFAULT_OPTIONS),
            "strategy": translate_strategy(excel_strategy),
        },
        "expected": {
            "yearly": expected_yearly,
            "summary": {
                "values": {"avg_gross_margin": average_gm},
                "tolerances": {f: tol for f, _, tol in SUMMARY_FIELDS},
                "sources": {f: src for f, src, _ in SUMMARY_FIELDS},
            },
        },
        "reference": {
            "rotation_codes": rotation,
            "activation": activation,
            "activation_note": "Calcs!C7:C49 -- the crop code where an option is "
                               "active, blank where it is not. Block 2's output; "
                               "used as input by tests/test_survival_factors.py.",
            "survival_factors": survival,
            "survival_note": "Calcs rows 55-97. Asserted by "
                             "tests/test_survival_factors.py against rim.survival.",
            "rotation_note": "Calcs rows 184-189 for years 1..10. Asserted by "
                             "tests/test_rotation_codes.py against rim.rotation.",
            "note": "Full within-season truth table: 6 plant stages and 10 "
                    "seed-bank quantities per year. Not asserted yet -- this is "
                    "the target for the staged population port (Bio results!D3:D20).",
            "tabsum": tabsum,
        },
    }
    return fixture


def register(name: str) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    filename = f"{name}.json"
    if filename not in manifest["scenarios"]:
        manifest["scenarios"].append(filename)
        manifest["scenarios"].sort()
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="fixture name (default: derived from the scenario label)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing fixture")
    parser.add_argument(
        "--scenario",
        type=Path,
        help="scenario JSON to drive Excel with (requires Excel + pywin32). "
             "Omit to capture the workbook's own saved state.",
    )
    args = parser.parse_args()

    if args.scenario:
        name, fixture = build_fixture_from_scenario(args.scenario, args.name)
    else:
        name, fixture = build_fixture(args.name)
    path = FIXTURE_DIR / f"{name}.json"
    if path.exists() and not args.force:
        print(f"{path.relative_to(wr.REPO_ROOT)} already exists; pass --force to overwrite.")
        return 1

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    register(name)

    print(f"Captured {path.relative_to(wr.REPO_ROOT)}")
    print(f"  scenario : {fixture['scenario']}")
    print(f"  years    : {len(fixture['expected']['yearly'])}")
    print(f"  avg GM   : {fixture['expected']['summary']['values']['avg_gross_margin']:.3f} $/ha/yr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
