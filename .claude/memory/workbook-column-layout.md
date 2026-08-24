---
name: workbook-column-layout
description: RIM-2013b is a 10-column vectorisation - one spreadsheet column per simulation year - which makes a faithful Python port tractable.
metadata:
  type: project
---

Each simulation year is one column. The same formulas repeat across ten columns.

| Block | Year 1 | Year 10 | Contents |
| --- | --- | --- | --- |
| `2.Strategy` | `D` | `M` | User decisions. Row 4 = crop; rows 5-18 = per-year decisions (rows 11/12/13 = the three post-emergent slots); rows 64-66 = derived flags read by `Calcs!C7` and `Calcs!C151`. |
| `Calcs` | `C` | `L` | ~370 rows of per-year intermediates. |
| `Bio results` | `D` | `M` | Population and yield outputs. |
| `Eco results` | `E` | `N` | Revenue, costs, gross margin. |

Years chain through the seed bank: `Bio results!E11 = D20`.

Per-crop parameters are columns in `+Options`: `AG`=Wheat, `AH`=Barley, `AI`=Canola,
`AJ`=Legume, roughly rows 56-145.

Crop code, `Calcs!E184`: Wheat=0, Barley=1, Canola=2, Legume=3, Volunt.=4, Clover=5, Cadiz=6.

Key lookup tables: `Calcs!$N$54:$T$98` (option to stage survival factor, via `HLOOKUP` in
`Calcs!C75:C83`) and `Calcs!$C193:$M291` (rotation table, via `VLOOKUP` keyed by `Calcs!E189`).

**Why:** This is the discovery that makes a faithful port feasible - one Python function
computing a single year's intermediates, iterated ten times, reproduces the entire workbook.
Without it the model looks like an intractable 5,000-formula tangle.

**How to apply:** Structure `rim/calcs.py` as one year's column-C block and loop it. See
[[engine-port-status]].
