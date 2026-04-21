# RIM Online — Streamlit App Roadmap

> Ryegrass Integrated Management: translating the Excel/VBA tool into a web app.

---

## 1. Application Overview

RIM is a bioeconomic simulation tool. Users define a paddock, select a multi-year management strategy, and evaluate the results in terms of **gross margins** and **ryegrass population dynamics**. The original tool is a single Excel workbook with VBA macros. The Streamlit version maps each Excel sheet to a page/section and replaces VBA logic with Python.

**Core user flow (3 steps):**
1. **Define Paddock** → set parameters and prices
2. **Select Strategy** → choose crop rotations and weed control options year by year
3. **Compare Results** → view economics, yields, population graphs and data tables

---

## 2. Excel Sheet → Streamlit Page Mapping

| Excel Sheet | Streamlit Page / Section |
|---|---|
| `Title` | Welcome / Landing page |
| `1.Profile` | Step 1 — Paddock Profile |
| `+Prices` | Step 1 — More Prices (expander / sidebar) |
| `+Options` | Step 1 — More Options (expander / sidebar) |
| `2.Strategy` | Step 2 — Strategy Builder |
| `3. Out Eco` | Step 3 — Summary & Economics |
| `3. Out C&G` | Step 3 — Yields & Competition |
| `3. Out Pop` | Step 3 — Ryegrass Population & Seed Bank |
| `3. Out Tab` | Step 3 — Data Tables |
| `Export` | Export (PDF / Excel download buttons) |
| `Dev` | Not exposed (developer sheet) |
| `Calcs` | Not exposed (Python calculation engine) |
| `Bio results` | Not exposed (intermediate calculation results) |
| `Eco results` | Not exposed (intermediate calculation results) |

---

## 3. Page-by-Page Specification

---

### 3.1 Welcome / Landing Page
**Source:** `Title` sheet, `Auto_Entry()` / `Auto_Exit()` in `Entry_Exit_Lock.bas`

**Content:**
- RIM logo and title
- Brief description of the tool (learning/extension tool for agronomists, farmers, students)
- Tutorial checkbox option (show tooltips / guided mode)
- Start button → navigates to Step 1
- Link to Credits & Info

**Streamlit components:** `st.title`, `st.markdown`, `st.checkbox`, `st.button`, `st.page_link`

---

### 3.2 Credits & Info Page
**Source:** `Credits` VBA form (`Show_Credits()` in `Forms_Graphs.bas`)

**Content:**
- Copyright notice (UWA / DAFWA 1993–2013)
- Citation: Lacoste (2013), Pannell et al. (2004)
- Funding acknowledgements (GRDC, AHRI)
- Contact information
- "Unlock" toggle for developer/background view (optional advanced feature)

**Streamlit components:** `st.markdown`, `st.expander`

---

### 3.3 Step 1 — Paddock Profile
**Source:** `1.Profile` sheet, `Profile.bas`, `Help_1P` form

#### 3.3.1 Core Paddock Parameters
| Parameter | Input Type | Notes |
|---|---|---|
| Farm name | `st.text_input` | |
| Paddock name | `st.text_input` | |
| Farm size (ha) | `st.number_input` | |
| Base yields (t/ha) | `st.number_input` × 4 | Wheat, Barley, Canola, Legume |
| Sheep gross margin ($/DSE) | `st.number_input` | Named range `SheepGM` |
| Starting ryegrass seed bank | `st.radio` or `st.select_slider` | Low=2, Medium=20, High=100 seeds/m² (mapped to `SeedNos_SH`) |
| Crop rotation proportions | Grid input | Sum per crop type must ≥ 0.6 |
| Interest rate (%) | `st.number_input` | |
| Inflation rate (%) | `st.number_input` | |
| Tax rate (%) | `st.number_input` | |
| Farm area (ha) | `st.number_input` | For scaling totals |

**Validation:** Progress indicator (counts filled fields). Thresholds: Profile ≥ 26, Prices ≥ 36, Options ≥ 50. Rotation sum check per year column (must ≥ 0.6). Show warning if `AC53 = "Adjust"`.

#### 3.3.2 Profile Save / Load
**Source:** `Profile.bas` — `Save_P1–4`, `Load_P0–4`, `Load_CLEAR`

| Function | VBA Source | Streamlit Implementation |
|---|---|---|
| Save profile to slot 1–4 | `Save_P1()` … `Save_P4()` | `st.button("Save to Slot X")` + `st.session_state` or JSON file |
| Load default profile | `Load_P0()` | `st.button("Load Default")` |
| Load profile from slot 1–4 | `Load_P1()` … `Load_P4()` | `st.selectbox` or 4 buttons |
| Clear current profile | `Load_CLEAR()` | `st.button` + `st.dialog` confirmation |

Profiles store: Prices, Options, Profile (parts a and b), paddock name, farm name.

#### 3.3.3 Ryegrass Seed Bank Preset Buttons
**Source:** `RG_Low()`, `RG_Medium()`, `RG_High()` in `Profile.bas`

- Three quick-set buttons: Low (2), Medium (20), High (100) seeds/m²

---

### 3.4 Step 1 (Extended) — More Prices
**Source:** `+Prices` sheet

#### Grain & Pasture Prices
| Parameter | Notes |
|---|---|
| Wheat price ($/t) | |
| Barley price ($/t) | |
| Canola price ($/t) | |
| Legume crop price ($/t) | |
| Hay price ($/t) | |
| Silage price ($/t) | |
| Sheep price ($/DSE or $/head) | |

#### Machinery & Input Costs
| Parameter | Notes |
|---|---|
| No-till seeding cost ($/ha) | Base cost, includes R&M, fuel |
| Full-cut extra cost ($/ha) | Additional cost over no-till |
| Tickle cost ($/ha) | Extra cultivation cost |
| High seeding rate extra cost ($/ha) | |
| Sprayer cost ($/ha per pass) | Applied per herbicide application |
| Seed cost ($/kg × rate) | Per crop type |
| Fertiliser costs ($/ha) | Per crop type |
| Nutrient savings (legumes) | Calculated from rotation |
| Crop insurance ($/ha) | Not applied if crop sacrifice planned |

#### HWSC Machinery Repayments
| Machine | Capital cost | Repayment ($/ha) via PMT |
|---|---|---|
| Harrington Seed Destructor (HSD) | `+Prices'!O32` | `AR72` |
| Bale Direct System (BDS) | `+Prices'!O31` | `AR73` |
| Chaff cart | `+Prices'!O33` | `AR74` |
| Chaff-tramlining | `+Prices'!O31*2` | `AR75` |
| Narrow windrow burner | `+Prices'!AR61` | `AR76` |
| Standard harvest reference | `+Prices'!O34` | `AR77` |

Repayment formula: `-PMT(interest_rate, loan_term, capital_cost)` ÷ farm_area

#### Financial Parameters
| Parameter | Notes |
|---|---|
| Interest rate (%) | Used in PMT for machinery repayments and annuity |
| Loan term (years) | Default ≈ 8 years |
| Farm area (ha) | Denominator for repayment per-ha |

---

### 3.5 Step 1 (Extended) — More Options
**Source:** `+Options` sheet

#### Crop Variables
| Parameter | Notes |
|---|---|
| Plant density (plants/m²) | Per crop type |
| Kernel weight (g) | Per crop type |
| Harvest index | Per crop type |
| Crop establishment rate (%) | |
| Maximum yield loss from ryegrass (%) | Wheat=60%, Barley=45%, Canola=60%, Legumes=60% |
| Competition factors | Crop vs. ryegrass |

#### Yield Benefits & Penalties (Management)
| Scenario | Default | Adjustable |
|---|---|---|
| Late vs early seeding penalty (cereals) | −3% to −10% per 1.5–3 weeks | Yes |
| Early seeding benefit (canola) | +10% | Yes |
| After green manuring (cereals/legumes) | Positive | Yes |
| After brown manuring / mowing | Positive | Yes |
| Phytotoxicity (pre- & post-emergents) | Negative | Yes |
| If not swathing (cereals/canola) | Negative | Yes |
| Crop topping (all) | −5% | Yes |
| Mouldboard plough (permanent) | Positive (if structural constraints removed) | Yes |

#### Yield Benefits & Penalties (Rotations)
| Scenario | Notes |
|---|---|
| Cereal after volunteer pasture | Positive |
| Cereal after 1-year legume pasture | Positive |
| Cereal after ≥2-year legume pasture | +10% |
| Cereal after legume crop | Positive |
| Cereal after canola | Positive |
| Canola after legume crop | Positive, residual effect for 2nd consecutive |
| Penalty: only 1-year break between cereals (canola/legume) | −10% |
| Nutrient savings after legumes | Yes (K, N) |

#### Ryegrass Variables
| Parameter | Notes |
|---|---|
| Germination patterns (no-till, no tickle) | 80% of seed bank germinates |
| Germination patterns (no-till, + tickle) | 85% of seed bank germinates |
| Germination patterns (regenerated pasture) | 70% / 75% |
| Natural mortality rate | Per period |
| Seed production per plant per cohort | Varies by emergence timing and crop density |
| Competition factors | Ryegrass impact on yields |

#### Pasture Variables
| Parameter | Notes |
|---|---|
| Volunteer stocking rate | Default 4.5 DSE/ha |
| Volunteer + high intensity | Default 6.5 DSE/ha |
| Hay/silage with grazing | Default 1 t/ha + 4 DSE/ha |
| Hay/silage without grazing | Default 2 t/ha |
| Clover ryegrass control (1st year) | Default 50% |
| Clover ryegrass control (≥3-year phase) | Default 80% (85–95% with high grazing) |
| Cadiz ryegrass control | Lower than clover |
| Re-sow interval (sub-clover) | Default: every 3 years if not grown |

#### Harvest Weed Seed Control (HWSC) Options
| Option | Ryegrass Control | Residue | Notes |
|---|---|---|---|
| Standard harvest | 10–90% (highly variable) | — | Baseline |
| Whole paddock burning | Default 85% | Burn all | Includes fire risk cost |
| Narrow windrow burning | Default 85% | Burn + redistribute | |
| Chaff-tramlining | Default 85% | Redistribute chaff | Requires localised herbicide |
| Chaff cart + burning dumps | Default 85% | Burn chaff | |
| Harrington Seed Destructor (HSD) | Default 85% | — | Repayment cost |
| Bale Direct System (BDS) | Default 85% | Export chaff+straw | + bales income |

---

### 3.6 Step 2 — Strategy Builder
**Source:** `2.Strategy` sheet, strategy VBA subs in `RIM_VBA.txt`, `Forms_Graphs.bas`

#### Year-by-Year Strategy Grid
For each of up to **10 years**, users select:

| Decision | Options | Notes |
|---|---|---|
| Crop / Pasture type | Wheat, Barley, Canola, Legume crop, Volunteer pasture, Sub-Clover pasture, Cadiz pasture | Determines rotation code |
| Seeding timing | Dry, Wet, Delayed (1–2 wks), +Delayed (3 wks) | Affects ryegrass germination caught |
| Seeding technique | No-till, Full-cut (wide points) | Full-cut increases germination + control |
| Seeding rate | Standard, High | High rate → better competition |
| Pre-tillage | None, Tickle, Mouldboard plough | Tickle stimulates earlier germination; plough kills 98% seed bank |
| Knock-down herbicide | None, Single knock-down, Double knock-down | Pre-seeding non-selective sprays |
| Pre-emergent herbicide | Yes / No | Effective until post-em. spray |
| Post-emergent herbicide | Yes / No | |
| Spring option | None, Green manuring, Brown manuring, Mowing, Hay & Silage, Topping, Swathing | See spring options table |
| Grazing intensity | None, Standard (default DSE), High intensity | Pasture phases only |
| Harvest option | Standard, Whole paddock burn, Narrow windrow burn, Chaff-tramlining, Chaff cart+dumps, HSD, BDS | |

**Spring Options Detail:**

| Option | Specific Cost | Followed by Spray | Nutrient Removal | Harvest Savings | Ryegrass Control | Yield Impact |
|---|---|---|---|---|---|---|
| Green manuring | Same as full-cut | No | No | Yes | 100% (spray survivors) | +next year |
| Brown manuring | No | Yes (×1.2 rate) | No | Yes | 100% | +next year |
| Mowing | Yes | Yes (×1.2 rate) | No | Yes | 100% | +next year |
| Hay & Silage | Yes | Yes (×1.2 rate) | Yes (less for silage) | Yes | 100% | — |
| Topping | No | Yes (×0.5 cereals/canola, ×0.25 legumes/pastures) | No | No | Variable (higher in pastures) | −5% |
| Swathing | Yes | Yes (×0.5 cereals, ×0.25 others) | No | No | Variable (higher in cereals) | −if not done |

#### Real-Time Graphs (update as selections are made)
**Source:** Charts 10, 14, 15 on `2.Strategy`; `Scale_Str()` in `Forms_Graphs.bas`

| Chart | Content | Type |
|---|---|---|
| Chart 10 | Annual Gross Margin ($/ha) + Mature Ryegrass Survivors (plants/m²) | Dual-axis bar + line |
| Chart 15 | Weed control costs breakdown per year ($/ha) | Stacked bar |
| Chart 14 | Income sources breakdown per year ($/ha) | Stacked bar |

- Toggle: Auto / Fixed scale (Fixed: max 500 plants/m², max 100 $/ha weed, max 600 $/ha income)
- Toggle: Show first graph only / both graphs / hide graphs

#### Strategy Save / Load
**Source:** `Save_S1–6`, `Load_S0–6`, `Load_CLEAR_S` in `RIM_VBA.txt`

| Function | Streamlit Implementation |
|---|---|
| Save strategy to slot 1–6 | 6 save buttons + optional name field |
| Load default strategy (slot 0) | Button |
| Load strategy from slot 1–6 | Dropdown or 6 load buttons |
| Clear current strategy | Button + confirmation dialog |

Each strategy slot stores: the full year-by-year grid (`Strategy_X` range) + strategy name.

#### Compare A / Compare B
**Source:** `StrategyA()`, `StrategyB()`, `Clear_both()` in `RIM_VBA.txt`

- **Compare A**: Freeze current results into slot A (`EcoA`, `PopA`, `TabA`)
- **Compare B**: Freeze current results into slot B (`EcoB`, `PopB`, `TabB`)
- **Clear both**: Wipe A and B comparison slots
- Results pages then show A vs B side by side

---

### 3.7 Step 3 — Summary & Economics (`3. Out Eco`)
**Source:** `3. Out Eco` sheet, `Help_3C` form; data from `EcoA`/`EcoB` ranges

**Charts:**
- Annual gross margin over time: Strategy A (bar) vs Strategy B (bar) — side by side
- Weed control costs: A vs B over years
- Income sources breakdown: A vs B stacked bars
- Long-term nominal annuity (net present value average after tax, inflation, interest)

**Key metrics displayed:**
- Annual gross margin ($/ha) per year
- Average gross margin (nominal annuity) over the simulation period
- Total weed control cost per year
- Income breakdown: grain, pasture/fodder, livestock

**Scale toggle:** Auto / Fixed (same as Strategy page)

---

### 3.8 Step 3 — Yields & Competition (`3. Out C&G`)
**Source:** `3. Out C&G` sheet, `Help_3CG` form

**Charts:**
- Yield penalty from ryegrass burden vs crop potential per year
- Management yield benefits/penalties: rotations, seeding timing, manuring, etc.
- Rotation benefits comparison (A vs B)

---

### 3.9 Step 3 — Ryegrass Population & Seed Bank (`3. Out Pop`)
**Source:** `3. Out Pop` sheet, `Help_3Pop` form; `Scale_Pop()` in `Forms_Graphs.bas`

**Charts (2 panels: Strategy A vs Strategy B):**

| Chart | Primary Axis | Secondary Axis |
|---|---|---|
| Chart 29 (Strategy A) | Ryegrass plants/m² per year | Seed bank (seeds/m²) per year |
| Chart 31 (Strategy B) | Ryegrass plants/m² per year | Seed bank (seeds/m²) per year |

**Scale toggle:**
- Auto: both axes auto-scaled
- Fixed: plants axis max=500, major unit=100; seed bank axis max=25, major unit=5

---

### 3.10 Step 3 — Data Tables (`3. Out Tab`)
**Source:** `3. Out Tab` sheet; data from `TabA`/`TabB` ranges

**Content:**
- Raw numerical data underlying all graphs
- Strategy A and Strategy B columns side by side
- Rows: each year of simulation
- Fields: gross margin, ryegrass plants, seed bank, yield, weed control costs, income components

**Export:**
- Download as Excel (`.xlsx`) — equivalent to `ExportTab()` in `zPrint.bas`

---

### 3.11 Export Page
**Source:** `zPrint.bas` — `PrintPDF()`, `ExportTab()`

| Feature | Excel VBA | Streamlit Equivalent |
|---|---|---|
| Select pages to export | Checkboxes per sheet | `st.multiselect` or `st.checkbox` per tab |
| Export to PDF | `ExportAsFixedFormat(xlTypePDF)` | `reportlab` or `weasyprint` → `st.download_button` |
| Export data tables to Excel | `ExportTab()` + `SaveAs .xlsx` | `pandas` + `openpyxl` → `st.download_button` |
| Auto-filename | `"RIM YYYY-MM-DD HHMM"` | `datetime.now().strftime(...)` |

---

## 4. Calculation Engine (Python Backend)

### 4.1 Simulation Loop
Replaces the `Calcs` hidden sheet and `Bio results` / `Eco results` sheets.

```
for year in range(simulation_years):
    for period in range(7):  # 7 time periods
        1. Apply dormancy / natural mortality to seed bank
        2. Calculate germination cohort for this period
        3. Apply ryegrass control (management option for this period)
        4. Update ryegrass plant count
    5. Calculate seed production (surviving plants × fecundity × competition factor)
    6. Replenish seed bank with new seeds
    7. Calculate yields (base yield × rotation benefits × management penalties × ryegrass competition)
    8. Calculate gross margin (receipts − costs)
    9. Carry over seed bank to next year
```

### 4.2 Key Formulas to Port

| Model Component | Source | Formula Type |
|---|---|---|
| Seed bank dynamics | `Calcs` Tables | Cohort germination fractions, dormancy rate, mortality rate |
| Ryegrass seed production | `+Options` sheet | Seed production × crop competition integration |
| Yield × ryegrass competition | `+Options` sheet | Yield loss = f(plants/m², competition factor) |
| Rotation codes → parameters | `Calcs` Table 1, 7 | Lookup table: crop code → yield benefit/penalty |
| Ryegrass control per option | `Calcs` Table 2 | Lookup: management option → % control per period |
| Control costs | `Calcs` Table 3 | Lookup: option → $/ha cost |
| Gross margin | `Eco results` | Revenue (yield × price) − Costs (seeding + harvest + weed control) |
| Nominal annuity | `Eco results` | Excel `PMT` equivalent: `numpy_financial.pmt(rate, nper, pv)` |
| Machinery repayments | `+Prices` AR column | `-PMT(interest, loan_term, capital_cost) / farm_area` |

### 4.3 Translation of Rotation Codes
From `Calcs` Table 1 — examples from comments in `RIM_VBA.txt`:
- `'0'` = wheat
- `'2'` = canola
- `'53'` = barley as 2nd cereal after a 3-year clover phase

These codes determine which yield benefit/penalty rows from `+Options` apply each year.

### 4.4 Mouldboard Plough Special Case
- Kills 98% of seed bank
- If a second mouldboard is done < 3 years after first: seed bank kill drops to 30% (seeds returned to surface)
- Optional permanent yield benefit if structural constraints are removed

---

## 5. State Management

Streamlit's `st.session_state` replaces Excel named ranges:

| Excel Named Range / Cell | Session State Key | Description |
|---|---|---|
| `Strategy_X` | `strategy_current` | Current year-by-year strategy grid |
| `Strategy_1–6` | `strategy_slots[1–6]` | Saved strategy slots |
| `Profile_Xa`, `Profile_Xb` | `profile_current` | Current paddock profile |
| `Profile_1–4` | `profile_slots[1–4]` | Saved profiles |
| `Prices_X` | `prices_current` | Current prices |
| `Options_X` | `options_current` | Current options |
| `EcoA`, `EcoB` | `results_A`, `results_B` | Frozen comparison results |
| `PopA`, `PopB` | `pop_A`, `pop_B` | Frozen population comparison |
| `TabA`, `TabB` | `tab_A`, `tab_B` | Frozen table comparison |
| `SeedNos_SH` | `profile_current.seed_bank_start` | Starting ryegrass seed bank |
| `AR37` | `strategy_graph_mode` | Graph visibility (0/1/2) |
| `P38` | `strategy_scale_mode` | "Auto" / "Fixed" |
| `S8` | `results_scale_mode` | "Auto" / "Fixed" |
| `AT46` | `print_setup_done` | Whether page setup was run |
| `AT49` | `print_selection` | Selected pages for export |

---

## 6. Help System

Replaces VBA modeless forms (`Help_0T`, `Help_1P`, `Help_2S`, etc.):

| VBA Form | Content | Streamlit |
|---|---|---|
| `Help_0T` | Tutorial / welcome guidance | `st.expander("Tutorial")` or `st.info` |
| `Help_0C` | Credits & Info | Dedicated Credits page |
| `Help_1P` | Profile help | `st.help()` tooltips + `st.expander` |
| `Help_2S` | Strategy help | Inline `st.caption` + `st.expander` |
| `Help_3C` | Economics output help | `st.expander("How to read this chart")` |
| `Help_3Pop` | Population help | `st.expander` |
| `Help_3CG` | Yields & Competition help | `st.expander` |
| `Help_4E` | Export help | `st.expander` |

Red triangle tooltips → `st.help` parameter on each input widget or `st.tooltip`.

---

## 7. Navigation Structure

```
app.py
├── pages/
│   ├── 0_Welcome.py            ← Title sheet
│   ├── 1_Paddock_Profile.py    ← 1.Profile + +Prices + +Options
│   ├── 2_Strategy.py           ← 2.Strategy
│   ├── 3_Results_Economics.py  ← 3. Out Eco
│   ├── 3_Results_Yields.py     ← 3. Out C&G
│   ├── 3_Results_Population.py ← 3. Out Pop
│   ├── 3_Results_Tables.py     ← 3. Out Tab
│   └── 4_Export.py             ← Export
├── rim/
│   ├── engine.py               ← Core simulation loop (replaces Calcs sheet)
│   ├── seed_bank.py            ← Seed bank dynamics
│   ├── ryegrass.py             ← Plant populations, control, seed production
│   ├── economics.py            ← Gross margins, annuity, costs
│   ├── yields.py               ← Yield × competition + rotation benefits
│   ├── options.py              ← Default parameters for all control options
│   └── defaults.py             ← Default profile/prices/options values
├── utils/
│   ├── session.py              ← Session state helpers
│   ├── charts.py               ← Plotly chart builders
│   └── export.py               ← PDF/Excel export helpers
└── data/
    └── defaults.json           ← Baseline parameters (replaces Profile_0, Prices_0, Options_0)
```

---

## 8. Technology Stack

| Concern | Recommended Library |
|---|---|
| Web framework | `streamlit` |
| Numerical simulation | `numpy`, `pandas` |
| Financial functions (PMT/annuity) | `numpy_financial` |
| Charts | `plotly` (interactive, dual-axis support) |
| Excel export | `openpyxl` via `pandas.to_excel()` |
| PDF export | `reportlab` or `weasyprint` |
| Session persistence (profiles/strategies) | `st.session_state` + optional `json` file download/upload |

---

## 9. Phased Implementation Plan

### Phase 1 — Core Engine
- [ ] Port all default parameters from Excel to `defaults.json`
- [ ] Implement `engine.py`: 7-period simulation loop
- [ ] Implement `seed_bank.py`: dormancy, mortality, germination cohorts
- [ ] Implement `ryegrass.py`: plant counts, control rates, seed production
- [ ] Implement `yields.py`: base yield × competition × rotation + management penalties
- [ ] Implement `economics.py`: gross margin, costs, nominal annuity (PMT)
- [ ] Unit tests against known RIM Excel outputs

### Phase 2 — Paddock Profile UI
- [ ] `1_Paddock_Profile.py`: all paddock inputs
- [ ] `+Prices` section (expander): grain prices, machinery costs, HWSC repayments
- [ ] `+Options` section (expander): ryegrass and yield parameters
- [ ] Profile save/load (4 slots + default) using `st.session_state`
- [ ] Ryegrass preset buttons (Low / Medium / High)
- [ ] Profile completeness validation indicator

### Phase 3 — Strategy Builder UI
- [ ] `2_Strategy.py`: 10-year grid with all per-year dropdowns
- [ ] Real-time recalculation on every widget change
- [ ] Dual-axis gross margin + ryegrass line chart (Plotly)
- [ ] Weed control costs bar chart
- [ ] Income breakdown stacked bar chart
- [ ] Auto / Fixed scale toggle
- [ ] Strategy save/load (6 slots + default)
- [ ] Compare A / Compare B / Clear both

### Phase 4 — Results Pages
- [ ] `3_Results_Economics.py`: A vs B gross margins, weed costs, income breakdown
- [ ] `3_Results_Yields.py`: yield penalties from ryegrass and rotation
- [ ] `3_Results_Population.py`: plants/m² and seed bank dual-axis charts, A vs B
- [ ] `3_Results_Tables.py`: raw data tables with `st.dataframe`
- [ ] Scale toggles on all results charts

### Phase 5 — Export & Help
- [ ] `4_Export.py`: select pages, download PDF and Excel
- [ ] Help expanders on each page
- [ ] Credits / Info page
- [ ] Tutorial / guided mode toggle

### Phase 6 — Polish & Deployment
- [ ] Responsive layout (sidebar for profile, main area for strategy/results)
- [ ] Green RIM colour scheme (primary: `#008A3E`)
- [ ] Session persistence: option to download/upload profile as JSON
- [ ] Deployment to Streamlit Community Cloud or internal server

---

## 10. Key Decisions & Notes

1. **Calculation timing:** In Excel, recalculation is automatic on every cell change. In Streamlit, recalculate on every widget interaction (use `st.session_state` to cache results and only recompute when inputs change).
2. **Mouldboard plough history:** Must track per-year history to detect second mouldboard < 3 years — store as a list in session state.
3. **Rotation codes:** The 2-digit code system (`'0'`=wheat, `'53'`=barley after 3yr clover) must be re-implemented as a Python lookup; consider a `dataclass` per year.
4. **PMT function:** Use `numpy_financial.pmt(rate/100, nper, -pv)` — confirm sign convention matches Excel.
5. **Nominal annuity:** Excel uses PMT over 10 years with after-tax, after-inflation discount rate — must replicate exactly.
6. **Ratio tables:** Several parameters (e.g. machinery costs) are stored as ratios relative to a reference value in `+Prices`. Port these as Python dicts.
7. **Profile vs Strategy storage:** Profiles include Prices + Options + Profile data. Strategies are just the year-by-year selection grid. Keep these as separate JSON-serialisable dicts.
8. **No password/unlock system needed:** The "unlock" mechanism in Excel was for protecting the interface from casual edits — not required in a Streamlit app.
