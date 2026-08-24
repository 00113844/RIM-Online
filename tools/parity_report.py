r"""Field-by-field Excel vs Python comparison for a parity fixture.

Usage:
    .venv\Scripts\python -m tools.parity_report [fixture ...]

pytest tells you whether parity holds. This tells you where it breaks and by
how much, which is what you need while porting a block of the model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from rim.engine import simulate_strategy
from tools import workbook_reader as wr

FIXTURE_DIR = wr.REPO_ROOT / "tests" / "fixtures" / "excel_parity"


def _within(actual: float, expected: float, tol: dict) -> bool:
    limit = max(float(tol.get("absolute", 0.0)), abs(expected) * float(tol.get("relative", 0.0)))
    return abs(actual - expected) <= limit


def _ratio(actual: float, expected: float) -> str:
    if abs(expected) < 1e-9:
        return "     n/a"
    return f"{actual / expected:7.2f}x"


def report(fixture_path: Path) -> bool:
    fixture: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = simulate_strategy(
        fixture["inputs"]["profile"],
        fixture["inputs"]["prices"],
        fixture["inputs"]["options"],
        fixture["inputs"]["strategy"],
    )

    print("=" * 78)
    print(f"{fixture['name']}  --  {fixture.get('scenario', '')}")
    print(f"source: {fixture['source']['workbook']}, {fixture['source']['method'].splitlines()[0]}")
    print("=" * 78)

    all_pass = True
    fields = list(fixture["expected"]["yearly"][0]["values"])

    for field in fields:
        unit = fixture.get("units", {}).get(field, "")
        print(f"\n{field}  [{unit}]")
        print(f"  {'yr':>3} {'crop':<18} {'Excel':>12} {'Python':>12} {'delta':>12} {'ratio':>9}  ")
        print("  " + "-" * 72)
        for expected_year in fixture["expected"]["yearly"]:
            year = expected_year["year"]
            expected = float(expected_year["values"][field])
            row = result["yearly"].iloc[year - 1]
            actual = float(row[field])
            ok = _within(actual, expected, expected_year["tolerances"][field])
            all_pass &= ok
            print(
                f"  {year:>3} {str(row['crop']):<18} {expected:>12.3f} {actual:>12.3f} "
                f"{actual - expected:>12.3f} {_ratio(actual, expected)}  {'ok' if ok else 'FAIL'}"
            )

    print("\nsummary")
    print("  " + "-" * 72)
    for field, expected in fixture["expected"]["summary"]["values"].items():
        expected = float(expected)
        actual = float(result["summary"][field])
        ok = _within(actual, expected, fixture["expected"]["summary"]["tolerances"][field])
        all_pass &= ok
        print(
            f"  {field:<24} {expected:>12.3f} {actual:>12.3f} "
            f"{actual - expected:>12.3f} {_ratio(actual, expected)}  {'ok' if ok else 'FAIL'}"
        )

    if fixture.get("translation", {}).get("lossy"):
        print("\nKnown translation losses (part of any discrepancy above is these,")
        print("not the model itself):")
        for loss in fixture["translation"]["losses"]:
            print(f"  - {loss}")

    print(f"\nRESULT: {'PARITY' if all_pass else 'NO PARITY'}")
    return all_pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", nargs="*", help="fixture paths (default: all in the manifest)")
    args = parser.parse_args()

    if args.fixtures:
        paths = [Path(f) for f in args.fixtures]
    else:
        manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
        paths = [FIXTURE_DIR / n for n in manifest["scenarios"]]

    if not paths:
        print("No fixtures registered. Run: python -m tools.capture_fixture")
        return 1

    return 0 if all([report(p) for p in paths]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
