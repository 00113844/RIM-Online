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


def _a1(ws, address: str) -> float:
    """Read an A1-style address, treating a blank as 0 as Excel's arithmetic does."""
    value = ws[address].value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


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
        "plough_seed_burial": {
            "value": opt(126), "cell": "+Options!AG126",
            "used_by": "Calcs!C159/C160, as (1 - value). Gated on Calcs!C17 "
                       "(plough), not on tickle.",
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


def extract_table8() -> dict[str, Any]:
    """Calcs!C193:M291 -- Table 8, keyed by the rotation key from Calcs row 189.

    Column C holds the enterprise code; the VLOOKUP column indices used
    elsewhere are 1-based from there, so ``column_3`` is E, ``column_5`` is G
    and so on. Only the columns the model actually reads are named.
    """
    wb = wr.load()
    ws = wb[cm.SHEET_CALCS]

    rows: dict[str, Any] = {}
    for row in range(cm.TABLE8_FIRST_ROW, cm.TABLE8_LAST_ROW + 1):
        key = ws.cell(row, cm.TABLE8_KEY_COL).value
        if not isinstance(key, (int, float)) or isinstance(key, bool):
            continue
        rows[str(int(key))] = {
            "row": row,
            "label": str(ws.cell(row, 4).value or "").strip(),
            "weed_free_yield": _cell(ws, row, 5),
            "ryegrass_control_standard_grazing": _cell(ws, row, 7),
            "ryegrass_control_high_grazing": _cell(ws, row, 8),
            "stocking_standard": _cell(ws, row, 9),
            "stocking_high": _cell(ws, row, 10),
            "stocking_standard_if_hay": _cell(ws, row, 11),
            "stocking_high_if_hay": _cell(ws, row, 12),
            "nitrogen_saving": _cell(ws, row, 13),
        }

    return {
        "_source": _source_header({"table": cm.TABLE8_RANGE}),
        "note": "Keyed by Calcs row 189 (the rotation key). Column names follow "
                "the captions in Calcs row 193.",
        "by_key": rows,
    }


def extract_germination() -> dict[str, Any]:
    """+Options germination fractions -- the inputs to Calcs!C151:C155.

    Five cohorts germinate through the season. Which column applies depends on
    whether the paddock is sown, whether it was tickled or ploughed, and whether
    the establishment system is full-cut, exactly as Calcs!C151 selects it.
    """
    wb = wr.load()
    ws = wb[cm.SHEET_OPTIONS]

    def col(first_row: int, column: int) -> list[float]:
        return [_cell(ws, first_row + n, column) for n in range(cm.GERMINATION_COHORTS)]

    return {
        "_source": _source_header({
            "regenerating": "+Options!AG105:AI109 (row 104 header: no tickle / + tickle)",
            "sown": "+Options!AG115:AJ119 (row 113/114 headers: tickle x establishment)",
            "starting_seed_bank": "+Options!AG96 * +Options!AG124",
        }),
        "cohorts": cm.GERMINATION_COHORTS,
        "regenerating": {
            "no_tickle": col(cm.GERMINATION_PASTURE_ROW, cm.OPTIONS_WHEAT_COL),
            "tickle": col(cm.GERMINATION_PASTURE_ROW, cm.OPTIONS_CANOLA_COL),
        },
        "sown": {
            "no_tickle_no_till": col(cm.GERMINATION_SOWN_ROW, cm.OPTIONS_WHEAT_COL),
            "no_tickle_full_cut": col(cm.GERMINATION_SOWN_ROW, cm.OPTIONS_BARLEY_COL),
            "tickle_no_till": col(cm.GERMINATION_SOWN_ROW, cm.OPTIONS_CANOLA_COL),
            "tickle_full_cut": col(cm.GERMINATION_SOWN_ROW, cm.OPTIONS_LEGUME_COL),
        },
        "starting_seed_bank": {
            "value": _cell(ws, 96, cm.OPTIONS_WHEAT_COL) * _cell(ws, 124, cm.OPTIONS_WHEAT_COL),
            "cells": "+Options!AG96 * +Options!AG124",
            "used_by": "Bio results!D11, the year-1 seed bank only",
        },
        "plough_seed_burial": {
            "value": _cell(ws, 126, cm.OPTIONS_WHEAT_COL),
            "cell": "+Options!AG126",
            "used_by": "Calcs!C159/C160, as (1 - value) when the paddock was ploughed",
        },
    }


def extract_seed_set() -> dict[str, Any]:
    """+Options parameters behind Bio results!D17:D20 and Calcs!C174:C177.

    Seed production per plant falls as the stand gets denser: it is
    ``max_seed / (density_constant + weighted_ryegrass + crop_competition)``.
    The crop's contribution is its competitiveness times its plant density,
    which is higher at a high seeding rate -- that is how a thicker crop
    suppresses ryegrass seed set.
    """
    wb = wr.load()
    ws = wb[cm.SHEET_OPTIONS]
    crop_cols = {
        "0": cm.OPTIONS_WHEAT_COL,
        "1": cm.OPTIONS_BARLEY_COL,
        "2": cm.OPTIONS_CANOLA_COL,
        "3": cm.OPTIONS_LEGUME_COL,
    }

    def by_crop(row: int) -> dict[str, float]:
        return {code: _cell(ws, row, col) for code, col in crop_cols.items()}

    def cohort_weights(column: int) -> list[float]:
        return [_cell(ws, row, column) for row in range(142, 146)]

    return {
        "_source": _source_header({
            "crop": "+Options!AG59:AJ60 (plant density), AG87:AJ87 (competitiveness)",
            "seed": "+Options!AG133 (max seed), AG135 (density constant), AS182 (pasture)",
            "phytotoxicity": "+Options!AG131 (herbicides), AG132 (spring sprays)",
            "cohort_weights": "+Options!AG142:AI145, by time of sowing",
        }),
        "max_seed_per_m2": _cell(ws, 133, cm.OPTIONS_WHEAT_COL),
        "density_constant": _cell(ws, 135, cm.OPTIONS_WHEAT_COL),
        "pasture_competition": _cell(ws, 182, 45),
        "crop_competitiveness": by_crop(87),
        "plant_density_standard": by_crop(59),
        "plant_density_high": by_crop(60),
        "phytotoxicity_herbicides": {
            "value": _cell(ws, 131, cm.OPTIONS_WHEAT_COL), "cell": "+Options!AG131",
            "used_by": "Bio results!D17, as (1 - value) when Calcs!P48 > 0",
        },
        "phytotoxicity_spring_sprays": {
            "value": _cell(ws, 132, cm.OPTIONS_WHEAT_COL), "cell": "+Options!AG132",
            "used_by": "Bio results!D17, as (1 - value) when Calcs!P49 > 0",
        },
        "cohort_competitiveness": {
            "dry_or_wet": cohort_weights(cm.OPTIONS_WHEAT_COL),
            "delayed": cohort_weights(cm.OPTIONS_BARLEY_COL),
            "plus_delayed": cohort_weights(cm.OPTIONS_CANOLA_COL),
        },
    }


def _cost_column_map() -> dict[int, dict[str, Any]]:
    """Read each cost row's crop-code -> column mapping out of the formulas.

    ``Calcs!C105:C147`` is written as nested IFs rather than an HLOOKUP, and the
    mapping is **not uniform**: rows 105-112 and 121-125 (the herbicides) put
    Clover in column S and Cadiz in T, while the other 24 rows swap them. Read
    with a single mapping, every spring and harvest option is mis-costed on
    clover and Cadiz. Deriving it per row from the formula text means the quirk
    cannot be lost.
    """
    import re

    pattern = re.compile(r"IF\(C\d+=(\d),Calcs!\$([A-Z])\d+")
    # Which activation cell the row tests. Mostly r - 98, but not always:
    # rows 128 and 129 are transposed, exactly as survival rows 78 and 79 are.
    activation_pattern = re.compile(r"^\(?IF\(C(\d+)\s*(?:=|<>)")
    formulas = (wr.REPO_ROOT / "Rim_Formulas.md").read_text(encoding="utf-8", errors="replace")

    mapping: dict[int, dict[int, int]] = {}
    for line in formulas.splitlines():
        fields = line.split("	")
        if len(fields) < 3 or fields[0] != cm.SHEET_CALCS:
            continue
        cell = re.fullmatch(r"C(\d+)", fields[1])
        if not cell:
            continue
        row = int(cell.group(1))
        if not (cm.COST_FIRST_ROW <= row <= cm.COST_LAST_ROW):
            continue
        pairs = pattern.findall(fields[2])
        activation = activation_pattern.match(fields[2].strip())
        if pairs or activation:
            entry: dict[str, Any] = {}
            if pairs:
                # Column letter -> 1-based index; N is 14.
                entry["columns"] = {int(code): ord(col) - ord("A") + 1 for code, col in pairs}
            if activation:
                entry["activation_cell"] = int(activation.group(1))
            mapping[row] = entry
    return mapping


def extract_cost_table() -> dict[str, Any]:
    """Calcs!N105:T147 -- what each control option costs, per crop, in $/ha."""
    wb = wr.load()
    ws = wb[cm.SHEET_CALCS]
    columns = _cost_column_map()

    options: dict[str, Any] = {}
    for row in range(cm.COST_FIRST_ROW, cm.COST_LAST_ROW + 1):
        entry = columns.get(row) or {}
        per_crop = entry.get("columns")
        if not per_crop:
            continue
        label = ws.cell(row, 2).value
        signature = "".join(
            chr(ord("A") + per_crop[code] - 1) if code in per_crop else "?"
            for code in range(7)
        )
        options[str(row)] = {
            "label": str(label).strip() if label else "",
            "survival_row": row - cm.COST_ROW_OFFSET,
            "activation_cell": entry.get("activation_cell", row - 98),
            "column_signature": signature,
            "cost_by_crop_code": {
                str(code): _cell(ws, row, column) for code, column in sorted(per_crop.items())
            },
        }

    signatures = sorted({entry["column_signature"] for entry in options.values()})
    return {
        "_source": _source_header({
            "table": cm.COST_TABLE_RANGE,
            "labels": f"Calcs!B{cm.COST_FIRST_ROW}:B{cm.COST_LAST_ROW}",
            "column_mapping": "derived per row from the nested IFs in Calcs!C105:C147",
        }),
        "note": "Cost twin of the survival table: option row r in Calcs 55-97 has its "
                "cost at r + 50. The crop-code to column mapping is not uniform -- "
                f"observed signatures (crop 0..6): {signatures}. Rows differ in where "
                "Clover and Cadiz sit, so each row records its own.",
        "column_signatures": signatures,
        "options": options,
    }


def extract_economics() -> dict[str, Any]:
    """The scalars Eco results assembles a gross margin and an annuity from."""
    wb = wr.load()
    calcs = wb[cm.SHEET_CALCS]
    prices = wb[cm.SHEET_PRICES]
    options_ws = wb[cm.SHEET_OPTIONS]

    def crop_cols(row: int) -> dict[str, float]:
        return {
            str(code): _cell(options_ws, row, col)
            for code, col in enumerate(
                (cm.OPTIONS_WHEAT_COL, cm.OPTIONS_BARLEY_COL,
                 cm.OPTIONS_CANOLA_COL, cm.OPTIONS_LEGUME_COL)
            )
        }

    _, interest_row, interest_col = cm.INTEREST_CELL
    _, tax_row, tax_col = cm.TAX_CELL

    return {
        "_source": _source_header({
            "non_weed_costs": "Calcs!C299:C302, C306",
            "machinery": f"Calcs!C{cm.MACHINERY_REPAYMENT_ROW}",
            "trends": "Calcs!C362:C366",
            "finance": "+Prices!AV73 (interest), AV74 (tax)",
            "yield": "+Options rows 56, 59, 60, 77, 86, 88, 89 and AG136:AG139",
        }),
        "note": "The nominal annuity is NOT a discounted average. Eco results rows "
                "66-73 carry a compounding after-tax balance across the ten years "
                "(E68 = interest x previous E70) before the PMT. See "
                "rim/economics_model.py.",
        "interest_rate": _cell(prices, interest_row, interest_col),
        "tax_rate": _cell(prices, tax_row, tax_col),
        # Calcs 362-366 compound year on year: year n is (1 + rate) ** n. Storing
        # the rate rather than year 1's factor is what makes that reproducible.
        "trend_rates": {name: _a1(prices, addr)
                        for name, addr in cm.TREND_RATE_CELLS.items()},
        "trends_year_one": {name: _cell(calcs, row, cm.FIRST_COL_CALCS)
                            for name, row in cm.TREND_ROWS.items()},
        "yield_parameters": {name: crop_cols(row)
                             for name, row in cm.YIELD_PARAM_ROWS.items()},
        "ryegrass_competitiveness": {
            str(code): _cell(options_ws, row, cm.OPTIONS_WHEAT_COL)
            for code, row in enumerate(cm.RYEGRASS_COMPETITIVENESS_ROWS)
        },
        "mouldboard_yield_benefit": _cell(
            options_ws, cm.MOULDBOARD_YIELD_BENEFIT_CELL[1],
            cm.MOULDBOARD_YIELD_BENEFIT_CELL[2],
        ),
        "non_weed_crop_cost": {k: _a1(prices, a) for k, a in cm.NON_WEED_CROP_COST.items()},
        "green_manure_saving": {k: _a1(prices, a) for k, a in cm.GREEN_MANURE_SAVING.items()},
        "cultivation_env_cost": _a1(calcs, cm.CULTIVATION_ENV_COST),
        "pasture_cost_volunteer": {k: _a1(prices, a) for k, a in cm.PASTURE_COST_VOLUNTEER.items()},
        "pasture_cost_clover": {k: _a1(prices, a) for k, a in cm.PASTURE_COST_CLOVER.items()},
        "pasture_cost_cadiz": {k: _a1(prices, a) for k, a in cm.PASTURE_COST_CADIZ.items()},
        "prices": {k: _a1(wb[cm.SHEET_PROFILE], a) for k, a in cm.PROFILE_PRICE_CELLS.items()},
        "machinery_repayments": {k: _a1(prices, a)
                                 for k, a in cm.MACHINERY_REPAYMENT_CELLS.items()},
        "machinery_loan_term_years": int(_a1(prices, cm.MACHINERY_LOAN_TERM_CELL)),
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

    table8 = extract_table8()
    _write("calcs_table8.json", table8, f"{len(table8['by_key'])} enterprise keys")

    germination = extract_germination()
    _write("germination.json", germination,
           f"{germination['cohorts']} cohorts x 6 columns")

    seed_set = extract_seed_set()
    _write("seed_set.json", seed_set, "seed production and competition parameters")

    costs = extract_cost_table()
    _write("calcs_cost_table.json", costs, f"{len(costs['options'])} priced options")

    economics = extract_economics()
    _write("economics.json", economics, "yield and finance parameters")

    vocabulary = extract_strategy_vocabulary()
    _write("strategy_vocabulary.json", vocabulary,
           f"{len(vocabulary['categories'])} categories, "
           f"{len(vocabulary['products'])} products, "
           f"{len(vocabulary['profile_products'])} profile slots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
