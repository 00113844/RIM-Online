# RIM Online — Inconsistencies & Audit Log

Audit date: 2026-04-22  
Source of truth: `Rim_Formulas.md` (Excel workbook RIM-2013b), `RIM_VBA.txt`, `Entry_Exit_Lock.bas`, `Forms_Graphs.bas`  
Affected files: `rim/defaults.py`, `rim/ryegrass.py`, `rim/yields.py`, `rim/engine.py`, `rim/economics.py`

---

## Summary

25 parameter/logic mismatches were identified between the original VBA/Excel model and the initial Python port. All have been corrected. Each item below documents the source reference, the old value, the corrected value, and the affected file.

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

- **Herbicide cost by product**: Current model uses cost-per-spray-pass; named herbicide product pricing (glyphosate, trifluralin, etc.) not yet itemised.
- **Per-crop seed/establishment cost dict**: Currently uses flat `cost_seed` + `cost_no_till`; crop-specific drill/fertiliser mix costs could improve precision.
- **Seasonal rainfall modifier**: No rainfall/water-limited yield adjustment implemented (model assumes average season).
- **Resistance evolution**: Herbicide resistance factor currently not advancing year-on-year within a strategy (static control fractions).
