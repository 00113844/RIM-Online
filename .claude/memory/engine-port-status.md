---
name: engine-port-status
description: Which blocks of the Excel model have been genuinely ported to Python versus still approximated by the original reimplementation.
metadata:
  type: project
---

Tracks the formula-level port of RIM-2013b into `rim/`. Update this whenever a block lands.

| # | Block | Excel range | Status |
| --- | --- | --- | --- |
| 1 | Crop / rotation coding | `Calcs` rows 184-189 | **ported** -- `rim/rotation.py`, `tests/test_rotation_codes.py` |
| 2 | Option activation | `Calcs!C7:C49` | not started -- needs the product vocabulary first |
| 3 | Stage survival factors | `Calcs` rows 55-97 (`HLOOKUP` into `N54:T97`) | **ported** -- `rim/survival.py`, `tests/test_survival_factors.py` |
| 3b | Stage multipliers | `Calcs!C99`, `C164:C170` | **ported** -- `rim/stage_multipliers.py` |
| 4 | Seasonal population model | `Bio results!D3:D20` | not started -- needs `Calcs!C151:C160` (germination) too |
| 5 | Seed set and competition | `Bio results!D17`, `D23:D39`, `Calcs!C177` | not started |
| 6 | Yield | `Bio results!D38:D50` | not started |
| 7 | Economics | `Eco results!E3:E59` | not started |

Everything not marked ported is the original independent reimplementation and should be
treated as unverified - see [[excel-is-source-of-truth]].

Block 1 notes: the cascade needs two lead-in columns (`Calcs!C`/`D`) for the paddock's prior
two years, seeded from the single-letter history cells `Calcs!N181`/`N182` (both `W` by
default, no formula behind them). Years 1-10 are columns `E`..`N` -- two further right than
every other Calcs block, which is easy to get wrong. `rim/rotation.py` is pure integer logic
with no tolerance: it matches Excel exactly or it is broken.

Rotation codes are captured into every fixture's `reference.rotation_codes`, so adding a
fixture automatically widens the coverage this block is tested against.

**Why:** Without this table it is impossible to tell, reading `rim/`, which code is evidence
backed and which is invented. Both look equally confident.

**How to apply:** Port in the order above (each block depends on the ones before it). Run
`tools/parity_report.py` after each and commit with the `Sheet!Cell` range cited.

Block 3 notes: the block is `Calcs` rows 55-97, wider than the `C75:C83` the early audit named.
Three things make it work:

- **The activation cell holds the crop code.** `Calcs!C7:C49` write the year's crop code (0..6)
  where an option is selected and leave the cell blank otherwise, so one cell says both *whether*
  an option applies and *which column* of `N54:T97` to read.
- **Offset == table row.** Column `A` holds the `HLOOKUP` offset, always `row - 54`, so option
  row `r`'s control fraction is in table row `r`. The block and the table are aligned.
- **Blank means no effect.** Excel coerces an empty lookup to 0, giving survival 1. Options that
  do not apply to a crop are blank, not zero.

Exceptions: rows 68-70 (seeding timing) are not crop-indexed -- they read columns `P`/`Q`, which
row 67 labels No-till / Full cut, selected by `Calcs!C18`. Row 68 is fed by two activation cells
(`C19` or `C20`). The `SOURCE` map is not a uniform offset: `78 <- 31` and `79 <- 30` are
transposed.

The control table is now generated, not typed: `tools/extract_params.py` writes
`data/calcs_survival_table.json` with a `_source` header. This is the first piece of Part 2.

**Finding for block 2:** `2.Strategy!D65` gates the knock-down. With Dry or Wet sowing there is
no gap between the knockdown and seeding, so Excel suppresses the knockdown rather than
double-count the same cohort against the seeding operation; only Delayed/+Delayed sowing (or an
ungrazed pasture, via `D66`) opens it. This is why the saved workbook selects Glyphosate in
years 1 and 9 yet `Calcs!C55` never fires.

Block 3b notes (`Calcs!C99`, `C164:C170`): these fold block 3's per-option factors into the seven
per-stage multipliers `Bio results!D3:D20` actually applies. Two traps:

- **Zero and blank are the same to Excel's SUM.** `Calcs!C165` tests `SUM(C19:C22)=0`. Those cells
  hold crop codes and wheat's code *is* 0, so the sum is 0 both when nothing is selected and when
  the crop is wheat. Reproduce by summing numerically, not by counting non-blank cells. This looks
  like a workbook bug; it is faithfully preserved and pinned by a test.
- **Post-emergents apply per slot, not per product.** `Calcs!C168` raises each product's factor to
  the count in `Calcs!P35:P39` -- how many of the three slots name it -- so listing Topik twice
  takes survival from 0.1 to 0.01. A single-slot Python model cannot express this, which is one
  concrete reason the old engine could not converge.

Constants are generated into `data/calcs_stage_constants.json` by `tools/extract_params.py`.

Next (block 4) needs `Calcs!C151:C155` (germination fractions per cohort, switched by
`2.Strategy!D66`, tickle `C16`/`C17` and full-cut `C18`) and `C159`/`C160` (tickle), plus
`+Options!AG96`/`AG124` for the starting seed bank and `AG129`/`AG130` for seed losses.
