---
name: measured-parity-gap
description: The size and shape of the Excel-vs-Python gap as first measured on 2026-08-24, to judge whether later work is actually converging.
metadata:
  type: project
---

First real measurement, two fixtures, `tools/parity_report.py`.

**`susceptible_2022_lorf`** - the workbook's own saved 10-year strategy.
Excel average GM 84.875 $/ha/yr. Every asserted field fails. Year 1 gross margin: Excel
22.449, Python 270.755 (12.1x). Ryegrass diverges in both directions across the run - Python
is 0.28x Excel in year 1 but 0.01x by year 8, so the errors are structural, not a scale factor.

**`continuous_wheat_no_control`** - ten years of wheat, every control switched off.
Excel: ryegrass escapes to a ceiling of ~18,763 plants/m2, seed bank saturates at ~25,362
seeds/m2, GM settles at -240.91 $/ha. Python: GM settles at +13.78 $/ha. Python has no
saturation behaviour and no catastrophic-loss regime at all.

Cleanest isolated defect this exposed: with no herbicides selected, Excel charges 0.00 $/ha of
weed control; Python charges 10.441 $/ha every year regardless.

**Why:** These numbers are the baseline. A later change that improves one field while
widening another is not progress, and without a recorded starting point that is easy to miss.

**How to apply:** Re-run `tools/parity_report.py` after each ported block and compare against
these figures. See [[engine-port-status]] and [[parity-fixture-protocol]].
