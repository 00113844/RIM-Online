# RIM Online — Agent Contract

RIM Online is a Streamlit/Python reimplementation of the **RIM-2013b** Excel/VBA bioeconomic
model (Ryegrass Integrated Management). The Excel workbook is the behavioural specification.
Python is an implementation of it, never the reference for it.

## Source of truth — strict order

When Python and any of these disagree, Python is wrong:

1. An approved parity fixture in `tests/fixtures/excel_parity/`
2. An Excel formula in `Rim_Formulas.md` (cited as `Sheet!Cell`)
3. A VBA procedure (`RIM_VBA.txt`, `Profile.bas`, `Forms_Graphs.bas`, `Entry_Exit_Lock.bas`, `zPrint.bas`)
4. A field in `RIM_Extracted_information.json` / `RIM_Extracted_information_WalkThrough.json`
5. The Python code in `rim/`

**Never invent model behaviour.** Every calculation change starts from a named formula, a VBA
procedure, an extracted field, or a failing parity fixture. If you cannot cite one, you are
guessing — say so and stop. The project has already been burned by this: see
`.claude/memory/excel-is-source-of-truth.md`.

## Workbook layout

The workbook is a 10-column vectorisation — one column per simulation year:

| Block | Year 1 | Year 10 | What it is |
|---|---|---|---|
| `2.Strategy` | col `D` | col `M` | User decisions (row 4 = crop, rows 5–18 = decisions, rows 64–66 = derived flags) |
| `Calcs` | col `C` | col `L` | ~370 rows of per-year intermediates |
| `Bio results` | col `D` | col `M` | Population/yield outputs |
| `Eco results` | col `E` | col `N` | Revenue, costs, gross margin |

Years chain through the seed bank: `Bio results!E11 = D20`. One Python function computing a
single year's intermediates, iterated ten times, reproduces the whole workbook.

Per-crop parameters live in `+Options` columns `AG`/`AH`/`AI`/`AJ` = Wheat/Barley/Canola/Legume.
Crop code (`Calcs!E184`): Wheat=0, Barley=1, Canola=2, Legume=3, Volunt.=4, Clover=5, Cadiz=6.

## Layering

- `rim/` — all simulation logic. No Streamlit imports.
- `pages/`, `utils/` — presentation and session-state adapters only. No model arithmetic.
- `tools/` — developer tooling (Excel COM oracle, parameter extraction, parity reporting).
  Not imported by the deployed app; may depend on `pywin32`.
- `data/` — parameters **generated** from the workbook. Do not hand-edit; regenerate.

## Public contract — do not break

`rim.engine.simulate_strategy(profile, prices, options, strategy_rows)` returns a dict with
exactly these keys:

- `yearly` — a `pandas.DataFrame`, one row per simulation year
- `summary` — a dict of scalar aggregates
- `machinery_repayments` — a dict of per-hectare HWSC repayments

Adding fields is fine. Renaming or removing them is not.

## Parity fixtures

Fixtures are reviewed evidence captured from the workbook. They are committed so `pytest` runs
on machines without Excel. Two capture paths exist:

- **The workbook's own saved scenario** -- `tools/workbook_reader.py` reads openpyxl's cached
  values. Exact floats, no Excel required, works anywhere.
- **A new scenario** -- `tools/excel_oracle.py` drives a real Excel instance to write inputs
  and recalculate. Windows + Excel + pywin32 only.

`tools/excel_oracle.py --selftest` proves the two agree to 1e-6 across every EcoSum and TabSum
field, which is what makes the cheap path trustworthy.

**Never generate expected fixture values by running the Python engine.** That turns the test
into a tautology and is the single most damaging thing you can do to this project.

Each fixture records: exact profile/prices/options/strategy inputs, per-year expected values,
summary values, the source workbook version, the `Sheet!Cell` reference each value was read
from, units, and explicit absolute/relative tolerances.

## Commands

```console
.venv\Scripts\python -m pytest -q                     # full suite
.venv\Scripts\python -m pytest tests/test_excel_parity.py -q     # parity only
.venv\Scripts\python -m tools.parity_report             # where and by how much it diverges
.venv\Scripts\python -m tools.capture_fixture           # re-capture the workbook's saved state
streamlit run app.py                                    # manual UI check

# Requires Excel + pywin32 (pip install -r requirements-dev.txt):
.venv\Scripts\python -m tools.excel_oracle --selftest   # verify the cell map round-trips
.venv\Scripts\python -m tools.capture_fixture --scenario scenarios/<name>.json
```

`pytest -q` after any change to `rim/` or `tests/`. A manual UI pass after any change to
`app.py`, `pages/`, or `utils/`.

## Conventions

- Cite evidence as `Sheet!Cell` in code comments and commit messages — e.g.
  `# Bio results!D13: survivors after pre-emergent, scaled by Calcs!C159`.
- Monetary comparisons in $/ha; biological comparisons in the fixture's recorded units.
- Record unresolved Excel-vs-Python differences in `INCONSISTENCIES.md`. That file is an
  audit log, not a claim of parity.

## Documentation

[`TASKS.md`](TASKS.md) is the backlog: what is outstanding, in dependency order.
[`ARCHITECTURE.md`](ARCHITECTURE.md) explains how the software works and why -- the workbook's
ten-column shape, the five-cohort season model, the block chain, and the parity harness. Read it
before changing anything in `rim/`.

## Memory

Durable project facts live in `.claude/memory/`, indexed by `.claude/memory/MEMORY.md`.
Read the index at the start of a session. Update `engine-port-status.md` whenever a block of
the engine port lands.


## Context:

Extracted from the Excel File: `What is RIM ?

RIM is a decision support system for farmers, advisers, agronomists and students. RIM is designed to provide information and insight into the long-term management of ryegrass, one of the most important agricultural weeds in Australia. 
RIM integrates numerous agronomic, biological and economic information. "What-if" scenarios simulate ryegrass numbers in a field over time and its impact on yield and profit. An average year in the Southern Australian wheatbelt is assumed, without climatic variability. However, RIM allows users to customise various parameters to represent regional conditions in their particular area. Advanced users can further investigate the underlying bioeconomic model by unlocking RIM and accessing the background parameters and calculations.

RIM can help provide answers to questions such as:
    ● Which combination of control options and rotations provides the best overall management system in the long-term?
    ● How fast can a ryegrass problem develop?
    ● How can I maintain my income if I cannot rely on herbicides?
    ● If a pasture phase is included, how long should it be for?
    ● Is it worth investing in specific machinery? Is a particular treatment (e.g. green manuring) a profitable practice? If so, under what circumstances?`