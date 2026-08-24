---
name: parity-fixture-protocol
description: How trusted Excel outputs are captured into committed fixtures, the two capture paths, and the one rule that must never be broken.
metadata:
  type: project
---

`tests/test_excel_parity.py` compares `simulate_strategy()` against fixtures in
`tests/fixtures/excel_parity/`, listed in `manifest.json`.

**The rule: never generate expected fixture values by running the Python engine.** That makes
the test a tautology and destroys the only signal the project has.

## Two capture paths

**Cheap path - the workbook's own saved scenario.** openpyxl returns the values Excel cached
when it last recalculated and saved. For the stored scenario those are exact full-precision
floats. No Excel, no recalculation, works on any platform:

    .venv\Scripts\python -m tools.capture_fixture

**Full path - a new scenario.** `tools/excel_oracle.py` copies the workbook to a temp dir,
drives a hidden Excel instance with macros force-disabled (`AutomationSecurity = 3`), writes
inputs into `2.Strategy!D4:M19`, calls `CalculateFullRebuild()`, and reads `.Value2` - never
`.Text`, which would bake display rounding into the fixture:

    .venv\Scripts\python -m tools.capture_fixture --scenario scenarios/<name>.json

`tools/excel_oracle.py --selftest` recalculates the workbook without changing an input and
checks the result against openpyxl's cache to 1e-6 across every EcoSum and TabSum field. It
passes. That is what licenses the cheap path.

## Fixture contents

Exact profile/prices/options/strategy inputs (both Excel-native under `inputs.excel` and
translated under `inputs.strategy`), per-year expected values, summary values, source workbook
version, the `Sheet!Cell` each value came from, units, explicit tolerances, and a `reference`
block holding the full TabSum stage table as the target for the staged population port.

Fixture inputs are translated by `rim/excel_inputs.py`, which is **knowingly lossy** - its
`TRANSLATION_LOSSES` tuple names each loss so a parity report can distinguish a genuine model
error from a vocabulary artefact.

Output ranges: current strategy `EcoSum`/`PopSum`/`TabSum`; saved comparisons `EcoA`/`EcoB`,
`PopA`/`PopB`, `TabA`/`TabB`.

**Why:** Before this, the manifest was empty - the parity test had never compared anything, so
the project believed it had a parity harness while shipping an unvalidated model.

**How to apply:** Any calculation change adds or updates a fixture. Use
`tools/parity_report.py` while working; `pytest` only tells you pass/fail. See
[[excel-is-source-of-truth]].
