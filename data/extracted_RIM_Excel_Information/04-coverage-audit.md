# Coverage audit: what the app uses, and what it ignores

Generated figures come from `workbook_inventory.json` and `calcs_row_index.json`; regenerate
with `python -m tools.extract_documentation`. The wiring claims below were checked by
grepping the imports.

---

## The finding that matters most

**The app does not use the ported engine at all.**

Blocks 1–5 are ported and reproduce the workbook's biology exactly — 640 comparisons at a
worst relative error of 5.9×10⁻¹⁶. That code lives in `rim/calcs.py` and its five modules.
Grepping every import shows who calls it:

```
rim/calcs.py  imported by  tests/chain.py, tests/test_full_biology.py
              imported by  (nothing else)

utils/session.py:8   from rim.engine import simulate_strategy   <- the app's numbers
```

`utils/session.py` is what every page calls, and it calls **`rim/engine.py`** — the original
pre-port model that does not reproduce Excel. So the verified engine is exercised only by
`pytest`, and every number a user sees comes from the unverified one.

The app does touch two pure helpers from the port — `rim.activation.is_sown` and
`rim.rotation.CROP_CODE`, used by `utils/applicability.py` to grey out impossible choices —
but nothing that produces a figure.

Two consequences worth being plain about:

1. Gross margins, yields, ryegrass counts and seed banks shown in the app are **not** the
   Excel numbers, and the four failing parity fixtures say so.
2. Finishing blocks 6 and 7 is necessary but **not sufficient**. Rewiring `rim/engine.py`
   onto `rim/calcs.py` is a separate step, and without it the port stays invisible.

---

## Row coverage

| Sheet | Formula rows | Read by `rim/` | Not read |
|---|---:|---:|---:|
| `Calcs` | 311 | 195 | **116 (37%)** |
| `Bio results` | 91 | 16 | **75 (82%)** |
| `Eco results` | 68 | 0 | **68 (100%)** |

"Read by `rim/`" means the ported modules consume it. Given the wiring above, the app's
effective use of the Excel engine is **zero rows**.

---

## What the unused parts do

### `Eco results` — the entire economics, 68 rows

Receipts (`E3:E8`): grain, hay, silage, baling, pasture and livestock.
Expenses (`E11:E13`): non-weed-control costs for grain and pasture.
Weed control (`E15:E57`): **one line per control option** — the same option list as the
control table, itemised as cost.
Then gross margin, and the nominal annuity via `PMT` over tax, inflation and interest.

Nothing here is ported. The app computes gross margin with its own invented cost model.

### `Calcs` 105–147 — the cost twin of every option, 43 rows

The single most structurally important omission. Rows 55–97 say what each option does to
ryegrass; rows 105–147 say what each one costs, in the same order, `r + 50`. The port has
the first list and not the second.

Stated plainly: **the app knows what every control option does to ryegrass, and nothing
about what any of it costs.** Every trade-off RIM exists to inform — is this herbicide worth
it, does the seed destructor pay for itself, is a pasture phase cheaper than chemistry — sits
in the half that is missing.

### `Bio results` 23–50 — yield, 28 rows

Weed-free yield per crop, crop plant density, the proportion of weed-free yield retained
under weed pressure, and yield after weeds and haying. Plus the management adjustments:
phytotoxicity, late and early sowing, not swathing, crop topping, mouldboarding, and the
benefit from previous manuring. Also hay, silage and baling yields.

This is block 6, and it is the bridge between the biology that is ported and the economics
that is not.

### `Calcs` 297–306, 318–342 — pasture and livestock, 21 rows

Stocking rates by pasture type and grazing intensity; pasture returns; hay yield for clover,
Cadiz and volunteer under standard, high and no grazing; the value of nitrogen saved after
legumes; the environmental cost of cultivation.

The app has a single `stocking_rate` scalar. Any strategy with a pasture phase is being
costed on a guess.

### `Calcs` 346–358 — HWSC machinery, 13 rows

Machine ages and `PMT` repayments for chaff cart, narrow windrow burner, HSD,
chaff-tramlining, baler and BDS. The app has a `machinery_repayment_per_ha` helper with
hand-entered capital costs rather than the workbook's.

### `Calcs` 362–366 — trends and inflation, 5 rows

Yield and livestock productivity trends, and **three separate inflation rates** — crop sale
prices, sheep product prices, input costs. The app collapses these to two and averages them.

---

## Vocabulary the interface cannot express

| Excel | App |
|---|---|
| Knock-down: 3 named products | None / Single / Double |
| Pre-emergent: 5 named products | Yes / No |
| Post-emergent: 5 named products × **3 slots** | Yes / No, one slot |
| Spring — swathe (2 options) | **no column** |
| Spring — others: Define 1st / 2nd | **no column** |
| Harvest — others: B.all, Define 1st / 2nd | **no column** |

Thirteen named herbicides become five generic choices; three post-emergent slots become one;
three decision rows do not exist. The four user-definable options — RIM's own extension
mechanism, which the user guide directs advanced users to — are absent.

Because product cost and efficacy are set per product at `1.Profile`, this vocabulary gap
and the missing cost table are the same problem seen from two ends.

---

## Excel features deliberately not carried over

Not gaps — decisions, recorded so nobody re-opens them:

| Excel | Status |
|---|---|
| VBA save/load of profiles and strategies | Reimplemented natively, plus a `.rim.json` file |
| Freeze results into A/B | Reimplemented as Hold as A / B |
| PDF and Excel export (`zPrint.bas`) | Reimplemented |
| Unlock / auto-lock, zoom, tutorial forms | Not needed outside Excel |
| Red-triangle cell comments | Replaced by inline help and the guide page |

---

## What would close the gap

In dependency order. The first item is small and changes what users see more than anything
else on the list.

1. **Rewire `rim/engine.py` onto `rim/calcs.py`.** Until this happens the exact engine is
   dead code outside tests. Blocked on 2 and 3 for the economic outputs, but the biological
   outputs — ryegrass counts and seed bank — could be switched over now.
2. **Block 6, yield** — `Bio results!D23:D50`.
3. **Block 7, economics** — `Eco results!E3:E59`, which needs `Calcs!C105:C147`.
4. **Product vocabulary** — named herbicides, three post-emergent slots, the three missing
   decision rows. Unlocks per-product costs and per-product gating.
5. **Pasture, machinery and inflation blocks** — `Calcs` 297–366.

Items 2–4 are already in [`TASKS.md`](../../TASKS.md). Item 1 is not, and should be.
