r"""Generate rim/ parameter data from the workbook instead of hand-typing it.

Usage:
    .venv\Scripts\python -m tools.extract_params

Reads cached values via openpyxl (no Excel required) and writes JSON into data/.
Every file carries a ``_source`` header naming the workbook version and the
ranges it came from, so provenance is machine-readable.

Do not hand-edit anything this writes -- regenerate it.
See .claude/memory/defaults-are-hand-transcribed.md
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

from tools import cell_map as cm
from tools import workbook_reader as wr

DATA_DIR = wr.REPO_ROOT / "data"


def _source_header(ranges: dict[str, str]) -> dict[str, Any]:
    return {
        "generated_by": "tools/extract_params.py",
        "workbook": cm.WORKBOOK_VERSION,
        "file": wr.find_workbook().name,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "ranges": ranges,
        "warning": "Generated file. Do not hand-edit; rerun tools/extract_params.py.",
    }


def _cell(ws, row: int, col: int) -> float:
    """A blank in this table means 'no effect'.

    Excel's ``1 - HLOOKUP(...)`` coerces an empty cell to 0, giving a survival
    factor of 1. Representing blanks as 0.0 preserves that exactly.
    """
    value = ws.cell(row, col).value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def extract_survival_table() -> dict[str, Any]:
    """Calcs!N54:T97 -- ryegrass control by option and crop code.

    Row 54 is the crop-code header (0..6 across columns N..T). Each row below is
    one control option; column A holds its offset, which is always ``row - 54``,
    and column B its label. The value is the *control* fraction; the workbook
    turns it into a survival factor as ``1 - value``.

    Rows 68-70 (seeding timing) are not crop-indexed. They use columns P and Q
    as no-till and full-cut variants instead, per the header in row 67.
    """
    wb = wr.load()
    ws = wb[cm.SHEET_CALCS]

    header = [ws.cell(cm.SURVIVAL_HEADER_ROW, col).value for col in cm.SURVIVAL_CROP_COLS]
    crop_codes = [int(v) for v in header]
    if crop_codes != list(range(7)):
        raise ValueError(f"Unexpected crop-code header in Calcs row 54: {header!r}")

    options: dict[str, Any] = {}
    for row in range(cm.SURVIVAL_FIRST_ROW, cm.SURVIVAL_LAST_ROW + 1):
        offset = ws.cell(row, 1).value
        label = ws.cell(row, 2).value
        if offset is None:
            continue
        options[str(row)] = {
            "offset": int(offset),
            "label": str(label).strip() if label else "",
            "by_crop_code": {str(code): _cell(ws, row, col)
                             for code, col in zip(crop_codes, cm.SURVIVAL_CROP_COLS)},
            "no_till": _cell(ws, row, cm.SURVIVAL_NO_TILL_COL),
            "full_cut": _cell(ws, row, cm.SURVIVAL_FULL_CUT_COL),
        }

    return {
        "_source": _source_header({
            "table": cm.SURVIVAL_TABLE_RANGE,
            "offsets": f"Calcs!A{cm.SURVIVAL_FIRST_ROW}:A{cm.SURVIVAL_LAST_ROW}",
            "labels": f"Calcs!B{cm.SURVIVAL_FIRST_ROW}:B{cm.SURVIVAL_LAST_ROW}",
            "seeding_variants": "Calcs!P67:Q70 (header row 67: P = no-till, Q = full-cut)",
        }),
        "crop_codes": crop_codes,
        "options": options,
    }


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    target = DATA_DIR / "calcs_survival_table.json"
    payload = extract_survival_table()
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target.relative_to(wr.REPO_ROOT)}  ({len(payload['options'])} options)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
