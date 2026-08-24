---
name: audit-tuned-wrong-structure
description: The 25-item INCONSISTENCIES.md audit corrected parameters of a model whose structure was wrong, so most of its fixes are moot.
metadata:
  type: project
---

`INCONSISTENCIES.md` (audit dated 2026-04-22) lists 25 parameter and logic corrections applied
to `rim/`. They were real improvements to the wrong model.

The structural gaps the audit could not reach:

- Excel runs a staged seasonal population model (`Bio results!D3:D20` - six plant stages, nine
  seed-bank stages per year). `rim/engine.py` runs one annual germinate/control/seed-set cycle.
- Excel applies product-specific control at named seasonal stages (`Calcs!C75:C83`). Python
  collapses everything into one `total_control_fraction`.
- Excel has three post-emergent herbicide slots (`Calcs!C23:C27`, `2.Strategy!D11:D13`).
  `rim/options.py` exposes one generic `Yes`/`No`.
- Excel parameters are per-crop columns. Python hardcodes scalars.

Several audit items assert behaviour with no traceable formula - the 1.15x mouldboard yield
factor, the 1.20/1.30 rotation factors, the flat $110/ha nitrogen credit. Tests in
`tests/test_simulation.py` assert these. When the port reaches those blocks the tests will
fail, and that is the correct outcome: delete or re-derive them, do not preserve them.

**Why:** A future session reading INCONSISTENCIES.md would reasonably conclude the model had
been validated against Excel. It has not.

**How to apply:** Treat INCONSISTENCIES.md as history, not specification. See
[[engine-port-status]] and [[excel-is-source-of-truth]].
