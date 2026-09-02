# The workbook, sheet by sheet

RIM-2013b looks like an intractable tangle of ~5,000 formulas. It is not. It is a
**ten-column vectorisation**: one spreadsheet column per simulation year, with the same
formulas repeated across all ten.

| Block | Year 1 | Year 10 |
|---|---|---|
| `2.Strategy` | col `D` | col `M` |
| `Calcs` | col `C` | col `L` |
| `Bio results` | col `D` | col `M` |
| `Eco results` | col `E` | col `N` |

So one function evaluating a single column, iterated ten times, reproduces the workbook.
That is what `rim/calcs.py` is.

---

## Formula weight

Where the model actually lives, by count of formula-bearing rows
(`workbook_inventory.json`):

| Sheet | Formulas | Rows | What it is |
|---|---:|---:|---|
| `Calcs` | 3,092 | 311 | The engine room |
| `Bio results` | 800 | 91 | Ryegrass numbers and yields |
| `Eco results` | 780 | 68 | Receipts, costs, gross margin |
| `3. Out Tab` | 516 | 30 | Output tables for the interface |
| `+Options` | 298 | 84 | Biological and agronomic parameters |
| `2.Strategy` | 159 | 46 | The user's ten-year plan |
| `+Prices` | 155 | 50 | Costs and financial parameters |
| `3. Out Pop` / `C&G` / `Eco` | 55 | 24 | Chart feeds |
| `1.Profile` | 16 | 16 | Paddock inputs and stocked products |

`Calcs` alone is 60% of the workbook's formulas. Anything claiming to reproduce RIM has to
reproduce `Calcs`.

---

## The flow

```
1.Profile     paddock, prices, and which herbicide products are stocked
+Prices       machinery, inputs, financial rates
+Options      biology and agronomy parameters, per crop (AG/AH/AI/AJ)
     |
     v
2.Strategy    the ten-year plan: rows 4-19, one column per year
     |
     v
Calcs         the engine room
     |
     +--> Bio results     ryegrass numbers, yields
     +--> Eco results     receipts, costs, gross margin
              |
              v
        3. Out Tab / Pop / C&G / Eco    what the interface draws
```

---

## Inside `Calcs`

The engine room, in the order it evaluates. Ported blocks are marked; see
[`04-coverage-audit.md`](04-coverage-audit.md).

| Rows | What | Ported |
|---|---|---|
| 7–49 | **Option activation** — writes the crop code where an option is chosen | yes |
| 55–97 | **Survival factors** — `HLOOKUP` into the option × crop table `N54:T97` | yes |
| 99, 164–170 | **Stage multipliers** — combine the above into seven per-stage figures | yes |
| **105–147** | **Option costs** — the cost twin of rows 55–97, one row per option | **no** |
| 151–160 | Germination fractions; ploughing burial | yes |
| 174–177 | Competition-weighted ryegrass density | yes |
| 184–189 | **Rotation coding** — enterprise labels to the Table 8 lookup key | yes |
| 193–291 | **Table 8** — yield, grazing control, stocking, N saving by rotation key | yes |
| 297–306 | Nitrogen saving value; environmental cost of cultivation | **no** |
| 310–314 | Grazing effect on ryegrass | yes |
| 318–342 | Stocking rates, pasture returns, hay by pasture type and grazing | **no** |
| 346–358 | HWSC machinery ages and repayments | **no** |
| 362–366 | Yield and price trends; three separate inflation rates | **no** |

The symmetry worth noticing: **rows 55–97 and rows 105–147 are the same option list twice**
— once for what it does to ryegrass, once for what it costs. The port has the first and not
the second.

---

## Parameters

Per-crop parameters are columns: `+Options` `AG` = Wheat, `AH` = Barley, `AI` = Canola,
`AJ` = Legume, roughly rows 56–145.

Crop code (`Calcs!E184`): Wheat 0, Barley 1, Canola 2, Legume 3, Volunt. 4, Clover 5,
Cadiz 6.

The user guide names three kinds of parameter, which is worth knowing before editing any:

1. **Linked to the interface** — the user sets them directly.
2. **Not linked** — critical values reachable only by unlocking the workbook.
3. **Linked via ratio tables** — the user sets one value and the rest are derived from
   reference proportions. Changing the anchor moves the whole family.

Six parameter files are already generated from these sheets into `data/`; see
`tools/extract_params.py`.

---

## Named ranges

| Name | Range | Use |
|---|---|---|
| `Strategy_X` | `2.Strategy!D4:M19` | The current plan |
| `Strategy_0`–`_6` | `2.Strategy!D123:M240` | Saved strategy slots |
| `Profile_Xa/Xb` | `1.Profile!B5:Q27`, `C28:J36` | Current paddock |
| `Profile_1a`–`_4b` | `1.Profile!B90:Q237` | Saved profile slots |
| `TabSum` | `Bio results!C2:M20` | Population output table |
| `EcoSum` | `Eco results!P5:AB17` | Economic output table |
| `PopSum` | `Bio results!O2:R87` | Population chart feed |
| `TabA`/`TabB`, `EcoA`/`EcoB`, `PopA`/`PopB` | — | Frozen A/B comparisons |

`TabSum` and `EcoSum` are what the parity fixtures capture.

---

## VBA

Five modules, all interface machinery rather than model logic:

| Module | Does |
|---|---|
| `Profile.bas` | Save/load paddock profiles to the slot ranges; ryegrass presets |
| `RIM_VBA.txt` | Save/load strategies; freeze results into A/B |
| `Forms_Graphs.bas` | Help forms, chart scaling |
| `Entry_Exit_Lock.bas` | Auto-lock, zoom, entry and exit |
| `zPrint.bas` | PDF export and the Excel data-table dump |

None of it computes anything the model needs. A faithful port can ignore all of it — the
Streamlit app reimplements the useful parts natively.
