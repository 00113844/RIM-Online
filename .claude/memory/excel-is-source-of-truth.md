---
name: excel-is-source-of-truth
description: The RIM-2013b workbook defines correct behaviour; the Python engine is measurably wrong and must never be used as a reference.
metadata:
  type: feedback
---

The Excel workbook (RIM-2013b, `Ryegrass-RIM-...-DOWNLOAD-NOW.xlsm`) is the behavioural
specification. Never derive expected values, defaults, or model structure from `rim/`.

Measured evidence, Excel's own default Year 1 (`Wheat`, `Wet`, `Glyphosate`, `Triflur+Tria`,
`Topik`, `No-till`, `Standard`, `Narr+B.`):

| Output | Excel | Python |
| --- | ---: | ---: |
| Gross margin | $22.45/ha | $282.14/ha |
| Weed-control cost | $43.00/ha | $26.44/ha |
| Mature ryegrass | 52.60 plants/m2 | 16.00 plants/m2 |

**Why:** `rim/` was written as an independent reimplementation that resembles RIM rather than
a port of it. Its numbers look plausible in isolation, which is exactly what makes them
dangerous - a reviewer reading only the Python sees nothing wrong.

**How to apply:** Start every calculation change from a cited `Sheet!Cell` formula, a VBA
procedure, an extracted-information field, or a failing parity fixture. If you cannot cite
one, say you are guessing and stop. See [[audit-tuned-wrong-structure]] and
[[parity-fixture-protocol]].
