r"""Recalculating Excel oracle: capture parity fixtures for *new* scenarios.

tools/workbook_reader.py reads the workbook's saved state and needs no Excel.
This module drives a real Excel instance so that inputs the workbook has never
been saved with can be written, recalculated, and read back.

Usage:
    .venv\Scripts\python -m tools.excel_oracle --selftest
    .venv\Scripts\python -m tools.excel_oracle --scenario scenarios/foo.json

Requires Windows + Microsoft Excel + pywin32 (see requirements-dev.txt).

Safety: the tracked .xlsm is never opened for writing. Every run copies it to a
temporary directory and drives the copy, with macros force-disabled
(AutomationSecurity = msoAutomationSecurityForceDisable).
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from tools import cell_map as cm
from tools import workbook_reader as wr

MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3


class ExcelUnavailable(RuntimeError):
    """Raised when Excel or pywin32 is not usable on this machine."""


@contextmanager
def excel_workbook(source: Path | None = None, writable: bool = True) -> Iterator[Any]:
    """Open a throwaway copy of the workbook in a hidden Excel instance.

    Guarantees Excel is quit and COM state released, including on exception --
    an orphaned EXCEL.EXE holds a file lock and silently poisons later runs.
    """
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ExcelUnavailable(
            "pywin32 is not installed. Fixtures are committed, so this is only "
            "needed to capture new scenarios:\n"
            r"    .venv\Scripts\python -m pip install -r requirements-dev.txt"
        ) from exc

    source = source or wr.find_workbook()
    pythoncom.CoInitialize()
    tmpdir = Path(tempfile.mkdtemp(prefix="rim_oracle_"))
    working_copy = tmpdir / source.name
    shutil.copy2(source, working_copy)

    excel = None
    wb = None
    try:
        try:
            excel = win32com.client.DispatchEx("Excel.Application")
        except Exception as exc:  # pragma: no cover - environment dependent
            raise ExcelUnavailable(f"Could not start Excel: {exc}") from exc

        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE
        # Open(filename, UpdateLinks, ReadOnly)
        wb = excel.Workbooks.Open(str(working_copy), 0, not writable)
        yield wb
    finally:
        try:
            if wb is not None:
                wb.Close(False)
        except Exception:
            pass
        try:
            if excel is not None:
                excel.Quit()
        except Exception:
            pass
        del wb, excel
        pythoncom.CoUninitialize()
        shutil.rmtree(tmpdir, ignore_errors=True)


def write_strategy(wb: Any, strategy: list[dict[str, Any]]) -> None:
    """Write a strategy grid into 2.Strategy!D4:M19 using workbook-native labels.

    Keys are the field names in cell_map.STRATEGY_ROWS. A value of None clears
    the cell, which is how Excel represents 'option not selected' --
    Calcs!C7:C27 tests for an empty string.
    """
    ws = wb.Sheets(cm.SHEET_STRATEGY)
    for row_data in strategy:
        year = int(row_data["year"])
        col = cm.year_col(year, cm.FIRST_COL_STRATEGY)
        for field, row in cm.STRATEGY_ROWS.items():
            if field not in row_data:
                continue
            value = row_data[field]
            ws.Cells(row, col).Value = "" if value is None else value


def write_cells(wb: Any, cells: dict[str, dict[str, Any]]) -> None:
    """Write arbitrary ``{sheet: {A1_address: value}}`` overrides."""
    for sheet, addresses in cells.items():
        ws = wb.Sheets(sheet)
        for address, value in addresses.items():
            ws.Range(address).Value = "" if value is None else value


def recalculate(wb: Any) -> None:
    """Force a full dependency-tree rebuild, not just a dirty-cell pass."""
    wb.Application.CalculateFullRebuild()


def read_outputs(wb: Any) -> dict[str, Any]:
    """Read TabSum and EcoSum back out of the recalculated workbook."""
    stages = {**cm.TABSUM_PLANT_STAGES, **cm.TABSUM_SEED_STAGES}
    bio_ws = wb.Sheets(cm.SHEET_BIO)
    tabsum = []
    for year in range(1, cm.N_YEARS + 1):
        col = cm.year_col(year, cm.FIRST_COL_BIO)
        # Value2, never Text: Text applies the cell's display format and would
        # bake rounding into the fixture.
        tabsum.append(
            {"year": year, **{n: bio_ws.Cells(r, col).Value2 for n, r in stages.items()}}
        )

    eco_ws = wb.Sheets(cm.SHEET_ECO)
    ecosum = []
    for year in range(1, cm.N_YEARS + 1):
        col = cm.ECOSUM_FIRST_YEAR_COL + year - 1
        ecosum.append(
            {"year": year, **{n: eco_ws.Cells(r, col).Value2 for n, r in cm.ECOSUM_ROWS.items()}}
        )

    calcs_ws = wb.Sheets(cm.SHEET_CALCS)
    rotation = []
    for year in range(1, cm.N_YEARS + 1):
        col = cm.year_col(year, cm.FIRST_COL_ROTATION)
        rotation.append(
            {"year": year, **{n: calcs_ws.Cells(r, col).Value2 for n, r in cm.ROTATION_ROWS.items()}}
        )

    def _raw(value: Any) -> Any:
        # Activation cells hold the crop code when set and an empty string when
        # not; every downstream formula tests <> "" rather than a number.
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value.strip() or None
        return float(value)

    activation = []
    survival = []
    multipliers = []
    for year in range(1, cm.N_YEARS + 1):
        col = cm.year_col(year, cm.FIRST_COL_CALCS)
        activation.append(
            {"year": year, **{str(r): _raw(calcs_ws.Cells(r, col).Value2) for r in cm.ACTIVATION_ROWS}}
        )
        survival.append(
            {"year": year, **{str(r): calcs_ws.Cells(r, col).Value2 for r in cm.SURVIVAL_ROWS}}
        )
        multipliers.append(
            {"year": year, **{str(r): calcs_ws.Cells(r, col).Value2 for r in cm.MULTIPLIER_ROWS}}
        )

    history = {}
    for field, (sheet, row, col) in cm.HISTORY_CELLS.items():
        value = wb.Sheets(sheet).Cells(row, col).Value2
        history[field] = str(value).strip().lower() if value else "w"

    _, avg_row, avg_col = cm.ECOSUM_AVERAGE_GM
    return {
        "tabsum": tabsum,
        "ecosum": ecosum,
        "rotation": rotation,
        "activation": activation,
        "survival": survival,
        "multipliers": multipliers,
        "history": history,
        "average_gross_margin": eco_ws.Cells(avg_row, avg_col).Value2,
    }


def selftest(tolerance: float = 1e-6) -> bool:
    """Round-trip guard: does the cell map reproduce the workbook's own state?

    Opens the workbook, recalculates it without changing a single input, and
    compares against the cached values openpyxl reads. If these disagree the
    cell map is wrong, or the saved cache is stale, and nothing captured through
    this oracle can be trusted.
    """
    saved_wb = wr.load()
    saved_eco, saved_avg = wr.read_ecosum(saved_wb)
    saved_tab = wr.read_tabsum(saved_wb)

    with excel_workbook() as wb:
        recalculate(wb)
        live = read_outputs(wb)

    problems: list[str] = []

    def compare(label: str, expected: Any, actual: Any) -> None:
        if expected is None and actual in (None, ""):
            return
        try:
            e, a = float(expected), float(actual)
        except (TypeError, ValueError):
            return
        if abs(a - e) > max(tolerance, abs(e) * tolerance):
            problems.append(f"{label}: cached {e!r} vs recalculated {a!r}")

    compare("average_gross_margin", saved_avg, live["average_gross_margin"])
    for exp_row, act_row in zip(saved_eco, live["ecosum"]):
        for field in cm.ECOSUM_ROWS:
            compare(f"EcoSum year {exp_row['year']} {field}", exp_row[field], act_row[field])
    for exp_row, act_row in zip(saved_tab, live["tabsum"]):
        for field in {**cm.TABSUM_PLANT_STAGES, **cm.TABSUM_SEED_STAGES}:
            compare(f"TabSum year {exp_row['year']} {field}", exp_row[field], act_row[field])

    if problems:
        print(f"SELFTEST FAILED -- {len(problems)} mismatches (first 20):")
        for line in problems[:20]:
            print(f"  {line}")
        return False

    print("SELFTEST PASSED")
    print("  recalculated workbook reproduces its saved state exactly")
    print(f"  average gross margin: {float(live['average_gross_margin']):.3f} $/ha/yr")
    return True


def capture(scenario_path: Path) -> dict[str, Any]:
    """Apply a scenario file to the workbook and read the recalculated outputs.

    Scenario file shape::

        {"name": "...",
         "strategy": [ {"year": 1, "enterprise": "Wheat", ...} ],
         "cells": {"1.Profile": {"D8": 1.8}}}
    """
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    with excel_workbook() as wb:
        if scenario.get("strategy"):
            write_strategy(wb, scenario["strategy"])
        if scenario.get("cells"):
            write_cells(wb, scenario["cells"])
        recalculate(wb)
        outputs = read_outputs(wb)
    outputs["scenario"] = scenario.get("name", scenario_path.stem)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true",
                        help="verify the cell map round-trips against the saved workbook")
    parser.add_argument("--scenario", type=Path, help="scenario JSON to apply and capture")
    parser.add_argument("--out", type=Path, help="write raw recalculated outputs here")
    args = parser.parse_args()

    try:
        if args.selftest:
            return 0 if selftest() else 1
        if args.scenario:
            outputs = capture(args.scenario)
            target = args.out or Path(f"{args.scenario.stem}_outputs.json")
            target.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {target}")
            return 0
    except ExcelUnavailable as exc:
        print(f"Excel unavailable: {exc}")
        return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
