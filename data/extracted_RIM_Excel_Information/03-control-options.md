# Control options: what each does, and what each costs

Every control option in RIM exists in **three places**, and understanding that structure is
most of understanding the workbook:

| | Where | What it holds |
|---|---|---|
| 1 | `Calcs` 55–97 ← `N54:T97` | How much ryegrass it kills, **per crop** |
| 2 | `Calcs` 105–147 | What it costs, $/ha |
| 3 | `Eco results` 15–57 | Its line in the gross margin |

The three lists are the **same options in the same order**. An option's control row `r` in
55–97 has its cost twin at exactly `r + 50`. The port has list 1 and neither of the others —
see [`04-coverage-audit.md`](04-coverage-audit.md).

---

## Control by crop

Fraction of ryegrass killed, by crop code: Wheat, Barley, Canola, Legume, Volunt., Clover,
Cadiz. A zero means the option does nothing on that crop — not that it is unavailable, which
is why the app has to gate it explicitly.

| Row | Option | W | B | C | L | V | S | Z |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| 55 | KD/DK: Glyphosate | .95 | .95 | .95 | .95 | .95 | .95 | .95 |
| 56 | KD/DK: Paraquat | .95 | .95 | .95 | .95 | .95 | .95 | .95 |
| 57 | KD/DK: Glyphosate/Paraquat | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 58 | Pre-E: Triflur+Triallate | .80 | .80 | .85 | .85 | 0 | 0 | 0 |
| 59 | Pre-E: Propyzamide | 0 | 0 | .85 | .85 | 0 | 0 | 0 |
| 60 | Pre-E: Sakura | .90 | .90 | .90 | .90 | 0 | 0 | 0 |
| 61 | Pre-E: Boxer Gold | .85 | .85 | .85 | .85 | 0 | 0 | 0 |
| 62 | Pre-E: Triazine | 0 | 0 | .70 | .70 | .50 | .50 | .50 |
| 65 | Mouldboard plough | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 71 | Post-E: Topik | .90 | .90 | 0 | 0 | 0 | 0 | 0 |
| 72 | Post-E: Hussar | .95 | .95 | 0 | 0 | 0 | 0 | 0 |
| 73 | Post-E: Clethodim | 0 | 0 | .90 | .90 | 0 | 0 | 0 |
| 74 | Post-E: Glyphosate | 0 | 0 | .90 | .90 | 0 | 0 | 0 |
| 75 | Post-E: Paraquat | 0 | 0 | 0 | 0 | .65 | .65 | .65 |
| 78 | Spring: Brown M | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 79 | Spring: Topping | .75 | .75 | .75 | .75 | .90 | .90 | .90 |
| 81–84 | Spring: Mow / Green M. / Hay / Silage | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 85–86 | Spring A1 / A2 (user-defined) | .70 | .70 | .70 | .70 | .70 | .70 | .70 |
| 87 | Swathe, without spray | .44 | .44 | .36 | .36 | — | — | — |
| 88 | Swathe, with spray | .90 | .90 | .90 | .90 | — | — | — |
| 89–94 | Harvest: Cart+B., Narr+B., HSD, Tram., BDS+E. | .85 | .85 | .85 | .85 | — | — | — |
| 95 | Harvest: B.all (whole paddock burn) | .60 | .60 | .45 | .45 | .45 | .45 | .45 |
| 96–97 | Harvest B1 / B2 (user-defined) | .70 | .70 | .70 | .70 | .70 | .70 | .70 |

Rows 63, 64, 67, 76, 77 (high seeding rate, tickle, dry sowing, grazing) carry no control
value — they act elsewhere: seeding rate and tickle change *germination*, grazing draws from
Table 8, dry sowing is the baseline. Rows 80 and 93 are the workbook's own "empty slot for
adding an option" placeholders and appear in no dropdown.

**Seeding rows 68–70** are the exception to the crop-indexed table: they read columns `P`/`Q`
instead, which row 67 labels No-till (0.4) and Full cut (0.8).

---

## Product costs and rates

Set per paddock at `1.Profile`, and this is where a herbicide's price and efficacy actually
come from. The defaults in the shipped workbook:

| Profile row | Product | $/ha | Control |
|---|---|--:|--:|
| 16 | Glyphosate | 18 | 95% |
| 17 | Paraquat | 8 | 95% |
| 18 | Glyphosate/Paraquat (double knock) | 26 | 100% |
| 20 | Triflur+Triallate | 22 | 80% |
| 21 | Propyzamide | — | — |
| 22 | Sakura | 40 | 90% |
| 23 | Boxer Gold | 27 | 85% |
| 24 | Triazine | — | — |
| 26 | Topik | 5 | 90% |
| 27 | Hussar | 30 | 95% |
| 28–30 | Clethodim / Glyphosate / Paraquat (post-em) | — | — |

A blank cost means the profile does not stock that product, and `Calcs!C10:C14` / `C23:C27`
gate it out entirely — selecting it does nothing.

> Reproduced quirk worth knowing: `Calcs!C11` activates **Propyzamide** but tests
> `1.Profile!C22`, which is **Sakura**'s slot, not `C21`. Invisible while both are stocked.

---

## Three post-emergent slots

`2.Strategy` rows 11, 12 and 13 are three independent post-emergent choices. `Calcs!P35:P39`
count how many slots name each product, and `Calcs!C168` raises that product's survival
factor to that power — so naming Topik twice takes survival from 0.1 to **0.01**.

A single-slot model cannot express this. It is one concrete reason the pre-port engine could
not converge.

---

## Options the app does not offer at all

| Excel | App |
|---|---|
| Knock-down: Glyphosate, Paraquat, DoubleK | None / Single / Double |
| Pre-emergent: 5 named products | Yes / No |
| Post-emergent: 5 named products × **3 slots** | Yes / No, **1 slot** |
| Spring — swathe: W/o Spray, With Spray | **no column** |
| Spring — others: Define 1st, Define 2nd | **no column** |
| Harvest — others: B.all, Define 1st, Define 2nd | **no column** |

Thirteen named herbicides collapse to five generic choices, three slots to one, and three
whole decision rows do not exist. The two user-definable spring options and two
user-definable harvest options — RIM's extension mechanism, and the thing the user guide
tells advanced users to use — are absent entirely.

---

## Spring options in detail

From the user guide, since the formulas alone do not say why:

| Option | Own cost | Followed by spray | Nutrient removal | Harvest saving | Ryegrass control | Next-year yield |
|---|---|---|---|---|---|---|
| Green manuring | as full-cut | no | no | yes | 100% | benefit |
| Brown manuring | yes (×1.2) | yes | no | yes | 100% | benefit |
| Mowing | yes (×1.2) | yes | no | yes | 100% | benefit |
| Hay & silage | yes (×1.2) | no | yes (less for silage) | yes | 100% | — |
| Topping | yes (×0.5 cereals/canola, ×0.25 legumes/pastures) | no | no | no | variable, higher in pastures | — |
| Swathing | yes | no | no | no | variable, higher in cereals | penalty if **not** done |

The ×multipliers are rates relative to the knock-down products, and include the sprayer
operation cost.

## Harvest weed seed control

| Option | Targets | Residue | Control |
|---|---|---|---|
| Whole paddock burning | chaff, straw, stubble | burn and redistribute | 10–90%, highly variable |
| Narrow windrow burning | chaff, straw | burn | 85% |
| Chaff-tramlining | chaff | redistribute | 85% |
| Chaff cart, burning dumps | chaff | burn | 85% |
| Harrington Seed Destructor | chaff | redistribute | 85% |
| Bale Direct System | chaff, straw | export, plus bale income | 85% |

The 85% default depends on the share of ryegrass seed that actually enters the header — 95%
of what enters is destroyed in good conditions. Machinery repayments for this specialist
equipment run over about eight years (`Calcs` 346–358); the workbook assumes the farm
already owns harvester, seeder and sprayer.
