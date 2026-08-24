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


def extract_stage_constants() -> dict[str, Any]:
    """The scalars Calcs!C99 and C164:C170 fold into the stage multipliers."""
    wb = wr.load()
    options_ws = wb[cm.SHEET_OPTIONS]
    calcs_ws = wb[cm.SHEET_CALCS]

    def opt(row: int) -> float:
        return float(options_ws.cell(row, cm.OPTIONS_WHEAT_COL).value)

    return {
        "_source": _source_header({
            "options": "+Options!AG126:AG145",
            "calcs": "Calcs!N167 (= '+Options'!H18)",
        }),
        "pre_em_survival_floor": {
            "value": float(calcs_ws.cell(167, 14).value),
            "cell": "Calcs!N167",
            "label": str(calcs_ws.cell(167, 2).value or ""),
            "used_by": "Calcs!C167, added when a knock-down accompanies a pre-emergent",
        },
        "pre_em_extra_control": {
            "value": opt(128), "cell": "+Options!AG128",
            "used_by": "Calcs!C167, as (1 - value)",
        },
        "normal_harvest_seed_removal": {
            "value": opt(134), "cell": "+Options!AG134",
            "used_by": "Calcs!C99, as (1 - value) when no spring or harvest option is chosen",
        },
        "tickle_control": {
            "value": opt(126), "cell": "+Options!AG126",
            "used_by": "Calcs!C159/C160, as (1 - value)",
        },
        "seed_loss_pre_harvest": {
            "value": opt(129), "cell": "+Options!AG129",
            "used_by": "Bio results!D16, as (1 - value)",
        },
        "seed_loss_over_summer": {
            "value": opt(130), "cell": "+Options!AG130",
            "used_by": "Bio results!D20, as (1 - value)",
        },
    }


def extract_strategy_vocabulary() -> dict[str, Any]:
    """The dropdown labels Calcs!C7:C49 compare the strategy grid against.

    The activation formulas never hard-code a label -- they compare a strategy
    cell to a list cell (``'2.Strategy'!$D$78``, ``$P$89`` and so on). Extracting
    those cells keeps the port keyed to the workbook rather than to a
    transcription of it.

    ``1.Profile!C16:C32`` holds the products the paddock profile has configured;
    a herbicide activates only when its profile slot is non-blank.
    """
    wb = wr.load()
    strategy_ws = wb[cm.SHEET_STRATEGY]
    profile_ws = wb[cm.SHEET_PROFILE]

    def text(ws, row: int, col: int) -> str | None:
        value = ws.cell(row, col).value
        return str(value).strip() or None if value is not None else None

    categories = {f"D{row}": text(strategy_ws, row, 4) for row in range(70, 121)}
    products = {f"P{row}": text(strategy_ws, row, 16) for row in range(70, 96)}
    profile = {f"C{row}": text(profile_ws, row, 3) for row in range(14, 36)}

    return {
        "_source": _source_header({
            "categories": "2.Strategy!D70:D120",
            "products": "2.Strategy!P70:P95",
            "profile_products": "1.Profile!C14:C35",
        }),
        "categories": {k: v for k, v in categories.items() if v},
        "products": {k: v for k, v in products.items() if v},
        "profile_products": {k: v for k, v in profile.items() if v},
    }


def _write(name: str, payload: dict[str, Any], summary: str) -> None:
    target = DATA_DIR / name
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target.relative_to(wr.REPO_ROOT)}  ({summary})")


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)

    table = extract_survival_table()
    _write("calcs_survival_table.json", table, f"{len(table['options'])} options")

    constants = extract_stage_constants()
    _write("calcs_stage_constants.json", constants, f"{len(constants) - 1} constants")

    vocabulary = extract_strategy_vocabulary()
    _write("strategy_vocabulary.json", vocabulary,
           f"{len(vocabulary['categories'])} categories, "
           f"{len(vocabulary['products'])} products, "
           f"{len(vocabulary['profile_products'])} profile slots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
