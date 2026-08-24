---
name: defaults-are-hand-transcribed
description: data/defaults.json is dead code and rim/defaults.py is hand-typed and unverified; parameters should be generated from the workbook.
metadata:
  type: project
---

`data/defaults.json` is **not read at runtime** and holds pre-audit values. `rim/defaults.py`
is the live source, but it was hand-transcribed from the workbook and collapses Excel's
per-crop parameter columns (`+Options!AG/AH/AI/AJ` = Wheat/Barley/Canola/Legume) into scalars.

The fix is to generate parameters from the workbook into `data/` via `tools/extract_params.py`
and make `rim/defaults.py` a thin loader, with a `_source` header on each generated file
naming the workbook version and the ranges read.

Note `.gitignore` excludes `*.json` wholesale, so generated parameters and fixtures need
explicit `!data/*.json` and `!tests/fixtures/**/*.json` negations to be tracked.

**Why:** Hand transcription is where silent divergence enters, and it cannot represent
per-crop structure at all. Two of the three structural gaps in the model trace back to it.

**How to apply:** Never hand-edit anything in `data/` - regenerate it. See
[[workbook-column-layout]] for the parameter block addresses.
