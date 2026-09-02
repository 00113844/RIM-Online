# Extracted RIM Excel information

What the RIM-2013b workbook contains, how its model works, and how much of it the
Streamlit app currently uses.

Sources, in the order [`CLAUDE.md`](../../CLAUDE.md) trusts them: the workbook itself
(`Ryegrass-RIM-…-DOWNLOAD-NOW.xlsm`), `Rim_Formulas.md` (every formula, as `Sheet!Cell`),
the VBA modules, and `RIM_User_Guide.md` (the 2013 user guide, which is the only place
several modelling assumptions are stated in words).

## Files

| File | What it is |
|---|---|
| [`01-how-rim-works.md`](01-how-rim-works.md) | The model: seed bank, seven periods, competition, finances |
| [`02-workbook-map.md`](02-workbook-map.md) | Sheet by sheet — what each holds and which feed which |
| [`03-control-options.md`](03-control-options.md) | Every control option, its effect, its cost, and where both live |
| [`04-coverage-audit.md`](04-coverage-audit.md) | **What the app uses and what it ignores** |
| `workbook_inventory.json` | Generated: formula counts, coverage figures, unused blocks |
| `calcs_row_index.json` | Generated: every `Calcs` formula row, its label, and which module reads it |

## Regenerating

The two JSON files are generated. Do not hand-edit them:

```console
.venv\Scripts\python -m tools.extract_documentation
```

The generator derives coverage from `tools/cell_map.py` and the ported modules, so the
figures cannot drift from what the code actually reads — add a row to the cell map and the
audit reflects it on the next run. The prose files are written by hand and cite those
numbers; if a figure here disagrees with the JSON, the JSON is right.

## The headline

The workbook's biology is reproduced exactly. Its economics are not reproduced at all.

| Sheet | Formula rows | Read by `rim/` | Unused |
|---|---:|---:|---:|
| `Calcs` | 311 | 195 | **116 (37%)** |
| `Bio results` | 91 | 16 | **75 (82%)** |
| `Eco results` | 68 | 0 | **68 (100%)** |

Stated the way it matters to a user: **the app knows what every control option does to
ryegrass, and nothing about what any of it costs.** See
[`04-coverage-audit.md`](04-coverage-audit.md).
