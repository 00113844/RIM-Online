# RIM Online — delivery roadmap

Where the project is, what stands between it and release, and what "done" looks like.

For the granular backlog see [`TASKS.md`](TASKS.md). For how the software works see
[`ARCHITECTURE.md`](ARCHITECTURE.md). For the model itself see
[`data/extracted_RIM_Excel_Information/`](data/extracted_RIM_Excel_Information/README.md).

---

## 1. What this is

RIM Online reimplements **RIM-2013b**, a bioeconomic model of ryegrass management built in
Excel and VBA at UWA. Users describe a paddock, plan ten years of management, and compare
strategies on gross margin and ryegrass population.

The workbook is the specification; Python is an implementation of it. That ordering is not
negotiable and is enforced by the parity harness — see [`CLAUDE.md`](CLAUDE.md).

**Core user flow:** define the paddock → build a ten-year strategy → compare results.

---

## 2. Where the project is, as of 2026-09-02

| | State |
|---|---|
| **Calculation engine** | **Complete and exact.** All seven blocks ported into `rim/calcs.py`. |
| **Parity evidence** | Four fixtures captured from the workbook; 200 comparisons through the full chain, worst relative error 5.7×10⁻¹⁴; all four nominal annuities exact. |
| **Parameters** | Nine files generated from the workbook by `tools/extract_params.py`. Nothing hand-transcribed. |
| **Streamlit app** | Complete and polished — profile, strategy, four results pages, export, guide. |
| **The join between them** | **Missing.** The app still calls the pre-port `rim/engine.py`. |
| **Test suite** | 154 passing. The 4 failures are the whole-model fixtures, which exercise the old engine. |

### The one thing that matters most

The engine reproduces the workbook exactly, and **no user can see it**. `rim/calcs.py` is
imported by tests and nothing else; `utils/session.py` calls `rim.engine.simulate_strategy`.
Every number in the interface still comes from the unverified pre-port model.

Measured on the shipped default plan, both from 20 seeds/m² so only the model differs: the
app draws the seed bank down **8%** over ten years, the ported engine **98%**. Drawing the
seed bank down is the point of RIM.

Everything below is ordered around closing that gap first.

---

## 3. Phases to release

### Phase 1 — Connect the engine *(next)*

Rewire `rim/engine.py` onto `rim/calcs.py`, preserving the `simulate_strategy()` contract
(`yearly`, `summary`, `machinery_repayments`). The four parity fixtures turn green at this
point, and they are the definition of done for the phase.

Needs a translation from the app's strategy dicts to the workbook's own labels.
`rim/excel_inputs.py` does that today but lossily; Phase 2 removes the loss.

**Done when:** `pytest -q` is fully green and the Population page shows the seed bank
actually collapsing under a real herbicide programme.

### Phase 2 — Product-level vocabulary

The strategy editor offers generic options where the workbook names products: 13 named
herbicides collapse to five choices, three post-emergent slots to one, and three decision
rows (spring swathe, spring others, harvest others) do not exist. RIM's two user-definable
spring and two harvest options are absent entirely.

The engine already works in workbook-native labels, so this is a UI and schema change, not a
model change. It unlocks per-product costs, per-product gating in the year editor, and
retires `rim/excel_inputs.py`.

**Done when:** every option in `data/strategy_vocabulary.json` is selectable, and
`TRANSLATION_LOSSES` is empty.

### Phase 3 — Verify the workflow

Profile and strategy save/load, A/B comparison, exports and charts checked against workbook
behaviour now that the numbers agree. Focused UI checks for the paths a user actually takes.

**Done when:** a reviewer can follow the RIM user guide end to end in the app and get the
workbook's answers.

### Phase 4 — Release readiness

CI running `pytest -q` on every change; a documented fixture-capture procedure for
maintainers; accessibility, responsive and export acceptance; deployment.

**Done when:** someone other than the current maintainer can capture a fixture, run the
suite, and deploy.

---

## 4. Excel sheet → app page

| Excel sheet | Where it went |
|---|---|
| `Title` | `pages/0_Welcome.py` |
| `1.Profile`, `+Prices`, `+Options` | `pages/1_Paddock_Profile.py` |
| `2.Strategy` | `pages/2_Strategy.py` |
| `3. Out Eco` | `pages/3_Results_Economics.py` |
| `3. Out C&G` | `pages/3_Results_Yields.py` |
| `3. Out Pop` | `pages/3_Results_Population.py` |
| `3. Out Tab` | `pages/3_Results_Tables.py` |
| `Export` | `pages/4_Export.py` |
| Help forms, red-triangle comments | `pages/4_How_RIM_Works.py` and inline help |
| `Calcs`, `Bio results`, `Eco results` | `rim/` — not exposed |
| `Dev` | Not carried over |

VBA behaviour is reimplemented natively: profile and strategy slots, A/B comparison, PDF and
Excel export. The lock/unlock, zoom and tutorial-form machinery has no equivalent outside
Excel and was deliberately dropped.

---

## 5. Decisions worth not revisiting

1. **The workbook wins.** Where Python and Excel disagree, Python is wrong — including where
   the workbook is itself wrong. Two reproduced defects are logged in `INCONSISTENCIES.md`.
2. **Parameters are generated, never typed.** `tools/extract_params.py` writes `data/`; hand
   editing anything there will be overwritten and loses provenance.
3. **Fixture values never come from Python.** That would make the parity test a tautology.
4. **Slots are session-only; files are the durable route.** A `.rim.json` holds the profile,
   prices, options, the current plan and every filled slot.
5. **Impossible decisions are prevented, not corrected.** The year editor disables what the
   model cannot act on; the gate withholds results rather than showing numbers computed from
   a plan the model half-ignores.
6. **No unlock system.** Excel's protection guarded a spreadsheet interface; it has no
   meaning here.
