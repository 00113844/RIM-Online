# How RIM works

The model, as the workbook implements it. Cell references are the evidence; the 2013 user
guide (`RIM_User_Guide.md`) supplies the wording for assumptions the formulas only imply.

RIM represents one paddock, on an average farm in the Southern Australian grainbelt, in an
**average year with no climatic variation**. Everything is per hectare or per m². It is a
learning and comparison tool, not a seasonal forecast — that assumption is load-bearing and
worth repeating to anyone reading the outputs.

---

## 1. The seed bank is the whole argument

Ryegrass seed sitting in the soil is a *stock*. Each year some germinates, some dies, some
stays dormant, and whatever survives to spring puts seed back. Over a decade the stock
either compounds or is drawn down, and almost nothing achievable in one season matters as
much as which of those a paddock is on.

Years are joined by exactly one number:

```
Bio results!E11 = D20
```

The seed left in the soil next autumn becomes next year's opening seed bank. Everything
else about a year is computed from that opening figure and the strategy chosen for the year.

Year 1 starts from `+Options!AG96 × AG124` (1000 seeds/m² by default).

---

## 2. Seven periods, five flushes

The guide names **seven time periods**:

| # | Period |
|---|---|
| 1 | Prior to break |
| 2 | 0–10 days after break |
| 3 | 10–20 days after break |
| 4 | Before post-emergence spray |
| 5 | Early spring |
| 6 | Before harvest |
| 7 | Summer |

Ryegrass emerges across them in **five flushes**, not all at once — and this is the single
most important mechanic in the model. Each control catches only what has emerged by the
time it is applied. A pre-emergent sprayed at seeding cannot touch a plant that comes up six
weeks later; a post-emergent catches everything standing and nothing still in the soil.

Two cascades run down the season in parallel (`Bio results` rows 3–8 and 11–16):

```
SEED BANK                            PLANTS
D11  end of summer                   D3  = D11 · g1
D12  = D11 · (1-g1)                  D4  = D3·C164 + D12·g2·C167
D13  = D12 · (1-g2) · C159           D5  = D4·C165 + D13·g3·C167
D14  = D13 · (1-g3) · C160           D6  = D5·C166 + D14·g4·C167
D15  = D14 · (1-g4)                  D7  = D6·C168 + D15·g5
D16  = D15 · (1-g5) · (1-loss)       D8  = D7·C169·C314
```

Note the asymmetry in rows 4–6: established plants take the stage multiplier, but each
**newly emerged flush takes `C167`**, the pre-emergent multiplier, because a pre-emergent is
still active in the soil when they come up. Miss that and nothing downstream is right.

**The fractions are shares of what is still left**, not of the original bank. Flush 1 takes
5% of the bank; flush 2 takes 35% of what remains after that, and so on. Germination
fractions come from `Calcs!C151:C155`, which select one of six `+Options` columns by
sown-or-regenerating × tickle-or-plough × no-till-or-full-cut.

Season totals, from the user guide and confirmed at `+Options` rows 111 and 121:

| | No tickle | With tickle |
|---|---|---|
| Sown crops and pastures | 70% | 80% |
| Regenerated pastures | 75% | 85% |

Stirring the soil brings more up early. That is a tactic, not a side effect: **bring the
weed up on purpose, then kill it**, rather than leaving it to emerge behind your herbicide.

---

## 3. Control is staged, and options are crop-specific

Every option becomes a *survival factor* — the fraction of ryegrass that lives through it —
via `Calcs` rows 55–97, an `HLOOKUP` into the option × crop table at `Calcs!N54:T97`.

The trick that makes this compact: the activation cell holds the **crop code**, not a
boolean. `Calcs!C7:C49` write the year's crop code (0–6) where an option is selected and
leave the cell blank otherwise, so one cell says both *whether* an option applies and *which
column* of the control table to read. Topik controls 90% of ryegrass in wheat and nothing in
canola, and that falls straight out of the lookup.

Those per-option factors are then combined into seven per-stage multipliers
(`Calcs!C99`, `C164:C170`), which are what the cascade above actually applies.

Two gates decide whether an option counts at all:

- **`2.Strategy!D66`** — is the paddock sown this year? True for any crop, and for the first
  year of a clover or Cadiz phase, which must be re-sown. It suppresses seeding and
  soil-applied herbicides on a regenerating pasture.
- **`2.Strategy!D65`** — does a knock-down get its own effect? With dry or wet sowing there
  is no gap before seeding, so the knockdown would kill the cohort the seeding operation
  already accounts for. Excel suppresses it rather than double-count.

---

## 4. Seed production, and why crop competition is a control

The stand that survives to spring sets seed, and how much depends on crowding
(`Bio results!D17`):

```
seed per plant = max_seed / (constant + C177 + crop_competitiveness × plant_density)
```

`C177` is not the raw plant count. It is a **competition-weighted density**
(`Calcs!C174:C177`): the plant cascade re-run with each flush scaled by how competitive it
actually is. For dry or wet sowing those weights run 1, 0.3, 0.1, 0.02 — a plant that
emerged with the crop competes fully, one that came up weeks later barely competes at all.
Sow later and the later flushes emerge nearer the crop, so they count for more.

The `crop_competitiveness × plant_density` term is why a **high seeding rate suppresses seed
set** even though it kills nothing. Two phytotoxicity discounts follow: one if any herbicide
was used (`Calcs!P48`), one if any spring operation involved a spray (`P49`).

Finally `Bio results!D20` applies harvest weed seed control **to newly set seed only** —
seed already shed on the ground never enters the header — and what remains loses a fixed
fraction over summer.

The user guide flags the two equations that are not simple arithmetic, and they are exactly
these: **ryegrass seed production integrating crop competition**, and **yield integrating
ryegrass competition**.

---

## 5. Yield

`Bio results` rows 23–50. Weed-free yield per crop is adjusted by a chain of management
effects — phytotoxicity, late or early sowing, not swathing, crop topping, mouldboarding,
and a benefit from previous green or brown manuring — then by the ryegrass burden.

Maximum yield lost to ryegrass at >300 plants/m²: wheat 60% (up to 2 t/ha), barley 45%,
canola 60%, legumes 60%.

Rotation effects run through the key at `Calcs!E189` into Table 8 (`Calcs!C193:M291`): a
cereal after a pasture phase, a legume crop or canola gains yield; canola or a legume with
only a one-year break between them loses 10%. Effects of some choices persist up to three
years.

---

## 6. Finances

`Eco results`. Receipts are yield × price, plus hay, silage, baling and livestock. Costs are
seeding, harvest, and weed control — the latter itemised **one line per control option**
(`Eco results` rows 15–57), mirroring the same option list as the control table.

A long-term average, the **nominal annuity**, accounts for tax, inflation and interest using
Excel's `PMT`. `PMT` also computes machinery repayments for HWSC equipment over roughly
eight years — the workbook assumes an average farm already owns a harvester, seeder and
sprayer, so only specialist weed-seed machinery carries a capital cost.

---

## 7. Where it lives in the workbook

The whole thing is a **ten-column vectorisation**: one spreadsheet column per simulation
year, the same formulas repeated across ten. See [`02-workbook-map.md`](02-workbook-map.md).
