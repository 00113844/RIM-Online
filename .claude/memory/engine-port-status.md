---
name: engine-port-status
description: Which blocks of the Excel model have been genuinely ported to Python versus still approximated by the original reimplementation.
metadata:
  type: project
---

Tracks the formula-level port of RIM-2013b into `rim/`. Update this whenever a block lands.

| # | Block | Excel range | Status |
| --- | --- | --- | --- |
| 1 | Crop / rotation coding | `Calcs!E184`, `E187:E189` | not started |
| 2 | Option activation | `Calcs!C7:C27` | not started |
| 3 | Stage survival factors | `Calcs!C75:C83` (`HLOOKUP` into `$N$54:$T$98`) | not started |
| 4 | Seasonal population model | `Bio results!D3:D20` | not started |
| 5 | Seed set and competition | `Bio results!D17`, `D23:D39`, `Calcs!C177` | not started |
| 6 | Yield | `Bio results!D38:D50` | not started |
| 7 | Economics | `Eco results!E3:E59` | not started |

Everything not marked ported is the original independent reimplementation and should be
treated as unverified - see [[excel-is-source-of-truth]].

**Why:** Without this table it is impossible to tell, reading `rim/`, which code is evidence
backed and which is invented. Both look equally confident.

**How to apply:** Port in the order above (each block depends on the ones before it). Run
`tools/parity_report.py` after each and commit with the `Sheet!Cell` range cited.
