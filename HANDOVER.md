# RIM Online Handover

## Purpose

RIM Online is a Streamlit/Python reimplementation of the RIM-2013b Excel/VBA bioeconomic model.
The Excel workbook is the behavioural source of truth. Agent rules live in [`CLAUDE.md`](CLAUDE.md);
durable project facts live in [`.claude/memory/`](.claude/memory/MEMORY.md).

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for how the model works.

## Current State

- **UI is complete.** Paddock profile, 10-year strategy editing, live results, A/B comparisons,
  tables, and PDF/Excel export all work.
- **The simulation is not a port.** `rim/` is an independently-written model that resembles RIM.
  It preserves the `simulate_strategy()` contract (`yearly`, `summary`, `machinery_repayments`)
  but does not reproduce Excel's numbers.
- **Parity is now measurable.** Two approved fixtures are captured from the workbook and both
  fail against the current engine. That is the intended state: the gap is visible and tracked
  rather than unknown.

Test suite: `13 passed, 2 failed`. The two failures are the parity fixtures.

## How to check Python against Excel

```console
.venv\Scripts\python -m pytest tests/test_excel_parity.py -q   # pass/fail gate
.venv\Scripts\python -m tools.parity_report                    # where and by how much
```

Capturing evidence — two paths, described fully in `.claude/memory/parity-fixture-protocol.md`:

```console
# The workbook's saved scenario. Exact floats via openpyxl. No Excel needed.
.venv\Scripts\python -m tools.capture_fixture

# A new scenario. Drives real Excel; needs pywin32 (pip install -r requirements-dev.txt).
.venv\Scripts\python -m tools.excel_oracle --selftest
.venv\Scripts\python -m tools.capture_fixture --scenario scenarios/<name>.json
```

`--selftest` recalculates the workbook without changing an input and checks the result against
openpyxl's cached values to 1e-6 across every EcoSum and TabSum field. It passes, which is what
makes the no-Excel path trustworthy.

## Tooling

| File | Role |
| --- | --- |
| `tools/cell_map.py` | Every `Sheet!Cell` address, in one place |
| `tools/workbook_reader.py` | Reads the workbook's saved state via openpyxl (no Excel) |
| `tools/excel_oracle.py` | Drives Excel via COM to recalculate new scenarios |
| `tools/capture_fixture.py` | Writes an approved fixture from either path |
| `tools/parity_report.py` | Field-by-field Excel vs Python diff |
| `rim/excel_inputs.py` | Knowingly lossy Excel-label to Python-schema adapter |

## Measured Gap

Baseline recorded 2026-08-24 in `.claude/memory/measured-parity-gap.md`.

`susceptible_2022_lorf` — the workbook's own saved strategy, Excel average GM 84.875 $/ha/yr:

| Output (year 1) | Excel | Python |
| --- | ---: | ---: |
| Gross margin | 22.449 $/ha | 270.755 $/ha |
| Weed-control cost | 58.287 $/ha | 41.831 $/ha |
| Mature ryegrass | 52.598 plants/m² | 14.850 plants/m² |
| Seed bank next autumn | 184.938 seeds/m² | 240.190 seeds/m² |

Ryegrass is 0.28× Excel in year 1 but 0.01× by year 8, so the error is structural, not a scale
factor.

`continuous_wheat_no_control` — ten years of wheat, every control off. Excel lets ryegrass
escape to ~18,763 plants/m² with GM settling at −240.91 $/ha; Python settles at +13.78 $/ha and
has no saturation or catastrophic-loss regime. With no herbicides selected Excel charges
0.00 $/ha weed control; Python charges 10.441 $/ha regardless.

## Why the gap is structural

- **Within-season model.** `TabSum` exposes six ryegrass plant stages and ten seed-bank
  quantities per year (`Bio results!D3:D20`). `rim/engine.py` runs one annual
  germinate → control → seed-set cycle.
- **Control timing.** `Calcs!C7:C27` activates product choices; `Calcs!C75:C83` converts them to
  stage-specific survival factors via `HLOOKUP` into `$N$54:$T$98`; `Bio results!D24:D33` applies
  them in order. Python combines everything into one annual fraction.
- **Herbicide vocabulary.** Excel names products with per-crop-category cost and control
  (`1.Profile!E16/H16` Glyphosate $18/ha 95%; `E20/H20` Triflur+Triallate $22/ha 80%;
  `E26/H26` Topik $5/ha 90%) and offers three post-emergent slots. `rim/options.py` has generic
  `Yes`/`No` and one slot.
- **Parameters.** Excel keys parameters per crop (`+Options!AG/AH/AI/AJ`). `rim/defaults.py`
  hand-transcribes scalars. `data/defaults.json` is stale and unread.

## Next Work

The port order, tracked in `.claude/memory/engine-port-status.md`. Each block depends on the
ones before it; run `tools/parity_report.py` after each and commit citing the `Sheet!Cell` range.

1. Crop/rotation coding — `Calcs!E184`, `E187:E189`
2. Option activation — `Calcs!C7:C27` (needs the product vocabulary first)
3. Stage survival factors — `Calcs!C75:C83`
4. Seasonal population model — `Bio results!D3:D20` *(the block that will move the numbers most)*
5. Seed set and competition — `Bio results!D17`, `D23:D39`, `Calcs!C177`
6. Yield — `Bio results!D38:D50`
7. Economics — `Eco results!E3:E59`

Supporting work: generate `data/*.json` from the workbook (`tools/extract_params.py`, not yet
written) and make `rim/defaults.py` a loader over it; replace `rim/options.py`'s invented labels
with the workbook's own vocabulary and add the three post-emergent slots to
`pages/2_Strategy.py`.

## Working Rules

See [`CLAUDE.md`](CLAUDE.md). In short: start from a cited Excel formula, VBA procedure,
extracted field, or failing fixture; keep calculation logic in `rim/`; never generate expected
fixture values with Python; record unresolved differences in `INCONSISTENCIES.md`.
