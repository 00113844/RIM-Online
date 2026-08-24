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
| 2 | Option activation | `Calcs!C7:C49` | **ported** -- `rim/activation.py`, `tests/test_activation.py` |
| 3 | Stage survival factors | `Calcs` rows 55-97 (`HLOOKUP` into `N54:T97`) | **ported** -- `rim/survival.py`, `tests/test_survival_factors.py` |
| 3b | Stage multipliers | `Calcs!C99`, `C164:C170` | **ported** -- `rim/stage_multipliers.py` |
| 4 | Seasonal population model | `Bio results!D3:D8`, `D11:D16` | **ported** -- `rim/population.py`, `tests/test_population.py` |
| 5 | Seed set and competition | `Bio results!D17:D20`, `Calcs!C174:C177` | not started -- closes the year and chains the seed bank |
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

Block 2 notes (`Calcs!C7:C49`): every cell has the shape
`IF(AND(<label matches>, <profile stocks it>, <gate open>), E$184, "")`. It writes the **crop
code**, not a boolean -- that is what lets one cell key the control-table column in block 3.

Two gates on `2.Strategy` rows 65/66, both needing the previous two years' crop codes (so block 2
depends on block 1):

- `D66` "is the paddock sown?" -- any crop, plus the first year of a clover or Cadiz phase
  (`Calcs!P46`/`P47`). Suppresses seeding and herbicide options on regenerating pasture.
- `D65` "does the knock-down get its own effect?" -- closed for dry/wet sowing, because there is
  no gap before seeding and the knockdown would kill the cohort seeding already accounts for.

`Calcs!C20` (wet sowing) is not a label match but the residual: active when dry, delayed and
+delayed are all blank.

Reproduced workbook quirk: `Calcs!C11` activates Propyzamide but tests `1.Profile!C22`, which is
Sakura's slot, not `C21`. Invisible while both are stocked, which they are by default. Pinned in
`rim/activation.py` as `PROFILE_SLOT_QUIRK`.

Labels are generated into `data/strategy_vocabulary.json`, so the port compares against the
workbook's own dropdown cells rather than transcribed strings.

**Blocks 1, 2, 3 and 3b now chain end to end.** `tests/test_activation.py::test_full_chain_from_
strategy_grid` runs strategy grid -> rotation -> activation -> survival -> multipliers using no
Excel intermediates, and matches `Calcs!C99`/`C164:C170` across all four fixtures.

Block 4 notes (`Bio results!D3:D8`, `D11:D16`): two interleaved cascades. Ryegrass emerges in
**five cohorts**, and each control catches only what has emerged by the time it is applied -- the
thing the original annual-cycle engine could not represent at all.

- Seed bank (rows 11-16) is drawn down cohort by cohort: `D12 = D11*(1-g1)`, etc.
- Plants (rows 3-8) carry survivors through each control and add the next cohort.
- **Rows 4-6 are asymmetric**: established plants take the stage multiplier (`C164`/`C165`/`C166`)
  while each newly emerged cohort takes `C167` instead, because a pre-emergent is still active in
  the soil when they come up. Easy to miss and it changes everything.

Germination fractions (`Calcs!C151:C155`) pick one of six `+Options` columns by sown/regenerating
x tickle-or-plough x no-till/full-cut. Ploughing also buries seed at exactly one cohort boundary
(`C159` without +delayed sowing, `C160` with it). Grazing removes ryegrass before seed set via
`C314 = 1 - C311 - C313`, keyed on the rotation key into Table 8, and is cancelled by any fodder
or manuring option (`C322`/`C324`).

Corrected earlier mislabel: `+Options!AG126` is **plough** seed burial, not tickle control --
`Calcs!C159/C160` gate it on `Calcs!C17`. Renamed in `data/calcs_stage_constants.json`.

`tests/chain.py` composes blocks 1-4 over a fixture; new block tests should use it rather than
re-deriving the chain.
