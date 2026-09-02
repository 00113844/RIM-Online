r"""Generate the workbook inventory and the Excel-vs-app coverage audit.

Usage:
    .venv\Scripts\python -m tools.extract_documentation

Writes machine-readable inventories into data/extracted_RIM_Excel_Information/.
Everything here is derived from the workbook and from ``tools/cell_map.py``, so
the coverage figures cannot drift away from what the port actually consumes:
add a row to the cell map and the audit reflects it on the next run.

The prose files in the same folder are written by hand and cite these numbers.
"""
from __future__ import annotations

import collections
import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any

from tools import cell_map as cm
from tools import workbook_reader as wr

OUT_DIR = wr.REPO_ROOT / "data" / "extracted_RIM_Excel_Information"
FORMULAS = wr.REPO_ROOT / "Rim_Formulas.md"

CELL = re.compile(r"([A-Z]{1,2})(\d+)")

# Which Calcs rows the ported engine reads. Derived from the cell map where it
# exists, listed explicitly where a module hard-codes the reference.
EXTRA_CONSUMED_CALCS = {
    **{r: "rim/population.py — germination fraction, cohort %d" % (n + 1)
       for n, r in enumerate(range(151, 156))},
    159: "rim/population.py — ploughing burial, no +delayed sowing",
    160: "rim/population.py — ploughing burial, with +delayed sowing",
    **{r: "rim/seed_set.py — competition-weighted density" for r in range(174, 178)},
    **{r: "rim/population.py — grazing survival" for r in (310, 311, 312, 313, 314, 322, 324)},
    **{r: "rim/seed_set.py — post-emergent use counts" for r in cm.POST_EM_USE_COUNT_ROWS},
    **{r: "rim/seed_set.py — application counters" for r in (40, 44, 45, 46, 47, 48, 49)},
    **{r: "rim/rotation.py / rim/population.py — Table 8 lookup" for r in range(193, 292)},
}

PORTED_BIO_ROWS = set(range(3, 9)) | set(range(11, 21))


def _formula_rows() -> dict[str, set[int]]:
    """Every (sheet, row) that carries a formula, from Rim_Formulas.md."""
    rows: dict[str, set[int]] = collections.defaultdict(set)
    for line in FORMULAS.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        match = CELL.fullmatch(fields[1])
        if match:
            rows[fields[0]].add(int(match.group(2)))
    return rows


def _consumed_calcs() -> dict[int, str]:
    """Calcs row -> which ported module reads it."""
    consumed: dict[int, str] = {}
    for name, row in cm.ROTATION_ROWS.items():
        consumed[row] = f"rim/rotation.py — {name}"
    for row in cm.ACTIVATION_ROWS:
        consumed[row] = "rim/activation.py — option activation"
    for row in cm.SURVIVAL_ROWS:
        consumed[row] = "rim/survival.py — stage survival factor"
    for row in cm.MULTIPLIER_ROWS:
        consumed[row] = "rim/stage_multipliers.py — stage multiplier"
    consumed.update(EXTRA_CONSUMED_CALCS)
    return consumed


def _label(ws, row: int, columns: tuple[int, ...] = (2, 3, 4)) -> str:
    for column in columns:
        value = ws.cell(row, column).value
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _runs(values: list[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    out, start, prev = [], values[0], values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
        else:
            out.append((start, prev))
            start = prev = value
    out.append((start, prev))
    return out


def build() -> dict[str, Any]:
    workbook = wr.load()
    rows = _formula_rows()
    consumed = _consumed_calcs()
    calcs_ws = workbook[cm.SHEET_CALCS]

    calcs_rows = rows.get(cm.SHEET_CALCS, set())
    bio_rows = rows.get(cm.SHEET_BIO, set())
    eco_rows = rows.get(cm.SHEET_ECO, set())

    calcs_index = {
        str(row): {
            "label": _label(calcs_ws, row),
            "read_by": consumed.get(row),
        }
        for row in sorted(calcs_rows)
    }

    bio_ws = workbook[cm.SHEET_BIO]
    eco_ws = workbook[cm.SHEET_ECO]

    unused_calcs = sorted(calcs_rows - set(consumed))
    header = {
        "generated_by": "tools/extract_documentation.py",
        "workbook": cm.WORKBOOK_VERSION,
        "file": wr.find_workbook().name,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "warning": "Generated file. Do not hand-edit; rerun tools/extract_documentation.py.",
    }

    inventory = {
        "_source": header,
        "sheets": {
            sheet: {"formula_rows": len(rows[sheet]),
                    "first_row": min(rows[sheet]), "last_row": max(rows[sheet])}
            for sheet in sorted(rows, key=lambda s: -len(rows[s]))
            if rows[sheet]
        },
        "coverage": {
            "Calcs": {
                "formula_rows": len(calcs_rows),
                "read_by_port": len(calcs_rows & set(consumed)),
                "not_read": len(unused_calcs),
            },
            "Bio results": {
                "formula_rows": len(bio_rows),
                "read_by_port": len(bio_rows & PORTED_BIO_ROWS),
                "not_read": len(bio_rows - PORTED_BIO_ROWS),
            },
            "Eco results": {
                "formula_rows": len(eco_rows),
                "read_by_port": 0,
                "not_read": len(eco_rows),
            },
        },
        "unused_calcs_blocks": [
            {"from": a, "to": b, "rows": b - a + 1,
             "label": _label(calcs_ws, a) or _label(calcs_ws, a + 1)}
            for a, b in sorted(_runs(unused_calcs), key=lambda r: -(r[1] - r[0]))
            if b - a + 1 >= 2
        ],
        "unported_bio_rows": {
            str(row): _label(bio_ws, row, (3,))
            for row in sorted(bio_rows - PORTED_BIO_ROWS)
            if _label(bio_ws, row, (3,))
        },
        "unported_eco_rows": {
            str(row): _label(eco_ws, row, (4, 3, 2))
            for row in sorted(eco_rows)
            if _label(eco_ws, row, (4, 3, 2))
        },
    }

    calcs_doc = {"_source": header, "rows": calcs_index}
    return {"workbook_inventory.json": inventory, "calcs_row_index.json": calcs_doc}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in build().items():
        target = OUT_DIR / name
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {target.relative_to(wr.REPO_ROOT)}")

    coverage = json.loads((OUT_DIR / "workbook_inventory.json").read_text(encoding="utf-8"))["coverage"]
    for sheet, figures in coverage.items():
        total = figures["formula_rows"]
        share = 100 * figures["not_read"] / total if total else 0
        print(f"  {sheet:<12} {figures['read_by_port']:>3}/{total:<3} rows read by rim/  "
              f"({share:.0f}% unused)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
