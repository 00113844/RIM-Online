# RIM Online — Inconsistencies & Audit Log

Audit date: 2026-04-22  
Source of truth: `Rim_Formulas.md` (Excel workbook RIM-2013b), `RIM_VBA.txt`, `Entry_Exit_Lock.bas`, `Forms_Graphs.bas`  
Affected files: `rim/defaults.py`, `rim/ryegrass.py`, `rim/yields.py`, `rim/engine.py`, `rim/economics.py`

---

## Summary

25 parameter/logic mismatches were identified between the original VBA/Excel model and the initial Python port. The parameter-level items below have been corrected. Confirmed structural differences remain and are listed separately for parity work.

---

## Parameter Defaults (`rim/defaults.py`)

| # | Parameter | Old value | Correct value | Source |
|---|-----------|-----------|---------------|--------|
| 1a | `base_yields["Wheat"]` | 2.5 t/ha | **1.8 t/ha** | Profile sheet default yield col |
| 1b | `base_yields["Barley"]` | 2.8 t/ha | **1.6 t/ha** | Profile sheet |
| 1c | `base_yields["Canola"]` | 1.8 t/ha | **1.0 t/ha** | Profile sheet |
| 1d | `base_yields["Legume crop"]` | 2.0 t/ha | **1.0 t/ha** | Profile sheet |
| 1e | `base_yields["Sub-Clover pasture"]` | 1.2 DSE | **1.0 DSE** | Profile sheet |
| 1f | `base_yields["Cadiz pasture"]` | 1.1 DSE | **1.0 DSE** | Profile sheet |
| 2 | `sheep_gm_per_dse` | 50.0 $/DSE | **55.0 $/DSE** | +Prices sheet default |
| 3 | `interest_rate_pct` | 6.0 % | **8.0 %** | Profile sheet finance section |
| 4 | `tax_rate_pct` | 30.0 % | **21.0 %** | Profile sheet (small-farm tax rate) |
| 5 | `inflation_rate_pct` (single) | 2.5 % | Split: `inflation_input_costs_pct` = **3.0 %**, `inflation_crop_prices_pct` = **1.0 %** | Profile sheet rows 17–18; Calcs annuity formula |
| 6 | `cost_sprayer_pass` | 14.0 $/ha | **8.0 $/ha** | +Options sheet sprayer cost cell |
| 7a | `control_effect.spring["Green manuring"]` | 0.95 | **1.0** | Calcs C-row herbicide chain: GM = full kill before emergence |
| 7b | `control_effect.spring["Brown manuring"]` | 0.95 | **1.0** | Same as above |
| 8 | `rotation_factor["cereal_after_legume"]` | 1.10 | **1.20** | 3. Out Eco rotation benefit table |
| 9a | `costs.spring["Green manuring"]` | 20.0 $/ha | **100.0 $/ha** | +Options cost table (contractor rate) |
| 9b | `costs.spring["Brown manuring"]` | 25.0 $/ha | **8.0 $/ha** | +Options cost table |
| 10a | Grain price `Wheat` | 350.0 $/t | **380.0 $/t** | +Prices default cells |
| 10b | Grain price `Barley` | 320.0 $/t | **280.0 $/t** | +Prices default cells |
| 10c | Grain price `Canola` | 700.0 $/t | **780.0 $/t** | +Prices default cells |

---

## Biological Model (`rim/ryegrass.py`)

| # | Issue | Old value | Correct value | Source |
|---|-------|-----------|---------------|--------|
| 11a | `seed_production` spring_multiplier `"Green manuring"` | 0.10 | **0.0** | Green manuring incorporates plants before any seed set — Calcs row 72 comment |
| 11b | `seed_production` spring_multiplier `"Brown manuring"` | 0.12 | **0.0** | Same: plants desiccated/rolled before seed maturity |
| 12 | `seed_production` multipliers `"Mowing"`, `"Topping"`, `"Swathing"` | 0.15 / 0.55 / 0.60 | **0.05 / 0.25 / 0.30** | Calcs row 99–102 fecundity reduction factors |

---

## Yield Model (`rim/yields.py`)

| # | Issue | Old value | Correct value | Source |
|---|-------|-----------|---------------|--------|
| 13 | `rotation_factor()` hard-coded cereal_after_legume | 1.10 | **1.20** | Mirrors defaults fix #8; was also hard-coded in function body |
| 14 | Mouldboard permanent yield benefit | Not implemented | **1.15× factor** (persists after any prior-year mouldboard) | Calcs row 85–86 mouldboard residual benefit |
| 15 | `cereal_after_green_legume` | Not implemented | **1.30** | 3. Out Eco rotation table: green-manured legume better than harvested |
| 16 | `spring_yield_factor["Swathing"]` for Canola | 0.97 (penalty) | **1.0** (no penalty; canola benefits from swathing) | Calcs row 112–113 crop×spring interaction |
| 17 | Seeding timing factors | Crop-generic | **Canola more sensitive**: Delayed 1-2wks = 0.92, +3wks = 0.82 | Calcs timing×crop matrix row 95–97 |

---

## Simulation Engine (`rim/engine.py`)

| # | Issue | Old value | Correct value | Source |
|---|-------|-----------|---------------|--------|
| 18a | Discount rate used single inflation for annuity | `inflation_rate_pct = 2.5 %` | Weighted average of `inflation_input_costs_pct` (3%) and `inflation_crop_prices_pct` (1%) | Calcs annuity formula col BG/BH |
| 18b | `mouldboard_ever_used` flag not tracked | Not passed to yield function | Now tracked and forwarded to `compute_actual_yield` | Needed for fix #14 |
| 18c | `previous_spring_option` not tracked | Not passed to yield function | Now tracked and forwarded for green-legume rotation detection | Needed for fix #15 |

---

## Economic Model (`rim/economics.py`)

| # | Issue | Old value | Correct value | Source |
|---|-------|-----------|---------------|--------|
| 19 | Herbicide pass counting used `== "Yes"` | Only counted if exact string "Yes" | `not in ("No", "None", "", None)` — counts any named product | Calcs C row herbicide dropdown logic |
| 20 | Mouldboard contractor cost | Not included | **+150 $/ha** when `pre_tillage == "Mouldboard plough"` | +Options machinery cost table |
| 21 | Harvester operating cost | Not included | **+21.94 $/ha** (6.6 L/ha diesel + maintenance) for all grain crops | +Options machinery operating cost row |
| 22 | Fertiliser saving after legume | Not included | **Canola −150 $/ha**, **Wheat/Barley −110 $/ha** when previous crop was legume | Calcs row 120–122 N-credit calculation |
| 23 | `compute_costs` missing `previous_crop` parameter | Not present | Added as optional param; engine passes `previous_crop` each year | Required for fix #22 |

---

## Remaining Known Limitations

These items are noted for future development but are outside the Phase 1 scope:

- **Measured default-strategy mismatch:** With the workbook's Year 1 selections (`Wheat`, `Wet`, `Glyphosate`, `Triflur+Tria`, `Topik`, `No-till`, `Standard`, `Narr+B.`), recalculated Excel reports gross margin **$22.45/ha**, herbicide cost **$43.00/ha**, mechanical cost **$15.29/ha**, and mature ryegrass **52.60 plants/m2**. Python, supplied the same labels, reports **$282.14/ha**, **$26.44/ha**, and **16.00 plants/m2**. This is diagnostic evidence, not an approved parity fixture, because the Python input schema cannot represent the Excel decisions faithfully.
- **Option vocabulary and UI contract:** Excel uses product-specific knock-down, pre-emergent, post-emergent, and harvest labels (for example `Glyphosate`, `Triflur+Tria`, `Topik`, and `Narr+B.`). `rim/options.py` and the Streamlit strategy editor expose generic `Single knock-down`/`Yes`/`Standard` values instead, so the default workbook strategy cannot be entered without translation. The active Excel profile stores wheat values at `1.Profile!E16/H16` for Glyphosate ($18/ha, 95%), `E20/H20` for Triflur+Triallate ($22/ha, 80%), and `E26/H26` for Topik ($5/ha, 90%).
- **Control timing:** A label-only adapter would still be incorrect. `Calcs!C7:C27` activates product selections, with `Calcs!C23:C27` checking all three post-emergent slots. `Calcs!C75:C83` converts active options to stage-specific survival factors through `HLOOKUP`; `Bio results!D24:D33` applies those factors through the seasonal plant model. The Python engine's one combined annual control fraction cannot reproduce this ordering.
- **Within-season model:** Excel `TabSum` exposes six ryegrass-plant stages and nine seed-bank stages per year. The Python engine currently calculates one annual germination/control/seed-return cycle, so its annual results cannot yet establish period-level parity.
- **Herbicide decision model:** The Excel strategy grid has three separate post-emergent herbicide slots. Python has one `post_emergent` decision, so it cannot represent combinations or their product-specific effects.
- **Input ownership:** `data/defaults.json` is not read at runtime and contains pre-audit defaults. `rim/defaults.py` is the active default source until the JSON artifact is retired or generated from it.
- **Herbicide cost by product**: Current model uses cost-per-spray-pass; named herbicide product pricing (glyphosate, trifluralin, etc.) not yet itemised.
- **Per-crop seed/establishment cost dict**: Currently uses flat `cost_seed` + `cost_no_till`; crop-specific drill/fertiliser mix costs could improve precision.
- **Seasonal rainfall modifier**: No rainfall/water-limited yield adjustment implemented (model assumes average season).
- **Resistance evolution**: Herbicide resistance factor currently not advancing year-on-year within a strategy (static control fractions).

---

## Status update, 2026-08-24 — this audit tuned the wrong structure

The 25 items above are real improvements to a model that does not share Excel's structure. They
should be read as history, not as specification. Parity is now measured directly; see
`.claude/memory/measured-parity-gap.md` for the baseline and `HANDOVER.md` for the port order.

**Measured, not estimated.** Two approved fixtures are captured from the workbook and both fail:

- `susceptible_2022_lorf` (the workbook's own saved strategy): Excel average GM 84.875 $/ha/yr.
  Year 1 gross margin Excel 22.449 vs Python 270.755. Ryegrass is 0.28x Excel in year 1 but
  0.01x by year 8 — the error changes sign and magnitude across the run, so it is structural.
- `continuous_wheat_no_control`: Excel lets ryegrass escape to ~18,763 plants/m² with gross
  margin settling at −240.91 $/ha. Python settles at +13.78 $/ha. Python has no saturation
  behaviour and no catastrophic-loss regime.

**New defect this exposed.** With no herbicides selected, Excel charges 0.00 $/ha of weed
control; Python charges 10.441 $/ha every year regardless. Isolated in
`tools/parity_report.py` output for `continuous_wheat_no_control`.

**Items above with no traceable Excel formula.** These were inferred rather than cited, and the
tests asserting them in `tests/test_simulation.py` should be deleted or re-derived when the port
reaches the relevant block, not preserved:

- #14 mouldboard permanent yield benefit, 1.15x
- #8 / #13 `cereal_after_legume` 1.20 and #15 `cereal_after_green_legume` 1.30
- #22 fertiliser saving after legume, flat −110 / −150 $/ha
- #21 harvester operating cost, +21.94 $/ha
- #20 mouldboard contractor cost, +150 $/ha

**Superseded by the port.** Items #7a/#7b, #11a/#11b, #12, #16, #17, #18a and #19 all concern
control fractions, fecundity multipliers and timing factors that the staged model
(`Bio results!D3:D20`, `Calcs!C75:C83`) replaces wholesale.
