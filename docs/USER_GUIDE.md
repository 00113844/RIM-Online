# RIM Online — how the model works, and how your files work

A guide for people using the tool, not maintaining it. Two halves:

1. **[How RIM works](#part-1--how-rim-works)** — the argument the model is making.
2. **[Your files](#part-2--your-files)** — what comes out, what goes back in, and which file
   holds which information.

---

# Part 1 — How RIM works

## The one idea

RIM is not a spray calculator. It is an argument about a **seed bank** — the ryegrass seed
sitting in your soil — and what a decade of decisions does to it.

Every ryegrass plant that sets seed this spring is next autumn's problem, and the autumn
after that. A paddock either draws its seed bank down over the years or lets it compound.
Almost nothing you can do in a single season matters as much as which of those two you are
on.

That is why the tool asks for **ten years** rather than one, and why the strip of bars across
the top of the Strategy page — the seed bank spine — is the first thing you see.

## Ryegrass does not all come up at once

It emerges in **five flushes** through autumn and winter. This is the single most important
mechanism in the model, because **each control only catches what has already emerged**.

A pre-emergent sprayed at seeding cannot touch a plant that comes up six weeks later. A
post-emergent catches everything standing on the day, and nothing still in the soil.

For a sown paddock, no-till, no tickle:

| Flush | Share of the seed bank *still left* |
|---|---|
| 1 | 5% |
| 2 | 35% |
| 3 | 40% |
| 4 | 35% |
| 5 | 15% |

Read those carefully: each figure is a share of what **remains**, not of the original. A big
bank puts up big flushes all season.

The fractions change with how you establish the crop. A tickle stirs the soil and brings more
up early — flush 2 rises from 35% to 55% — which is good if you are about to spray and bad if
you are not. Full-cut seeding raises every flush.

**Flush 5 is the one that gets away.** It emerges after the post-emergent has been and gone,
so nothing between seeding and harvest touches it. That is why late-season options — crop
topping, swathing, harvest weed seed control — exist at all.

## What a year looks like

Each of the ten years runs the same sequence:

1. **Germination.** A share of the seed bank comes up, in five flushes, set by your sowing
   system and whether you tickled.
2. **Control.** Every decision you made for that year removes a share of what is standing when
   it is applied. They combine multiplicatively — two 90% controls leave 1%, not −80%.
3. **Competition.** The surviving ryegrass and the crop compete. A dense, vigorous crop
   suppresses ryegrass; ryegrass costs the crop yield.
4. **Seed set.** What survives to spring sets seed, unless spring management stopped it.
5. **Carry-over.** New seed plus what did not germinate becomes next year's bank, less
   natural mortality.

## The decisions you make, per year

| Decision | Choices |
|---|---|
| Crop or pasture | Wheat, Barley, Canola, Legume crop, Volunteer pasture, Sub-Clover pasture, Cadiz pasture |
| Sowing time | Dry, Wet, Delayed (1–2 wks), +Delayed (3 wks) |
| Sowing system | No-till, Full-cut (wide points) |
| Sowing rate | Standard, High |
| Tillage | None, Tickle, Mouldboard plough |
| Knock-down | None, Glyphosate, Paraquat, Double knock-down |
| Pre-emergent | None, Trifluralin + triallate, Propyzamide, Sakura, Boxer Gold, Triazine |
| Post-emergent ×3 | None, Topik, Hussar, Clethodim, Glyphosate, Paraquat |
| Spring option | None, Green manuring, Brown manuring, Mowing + spray, Silage + spray, Hay + spray, Crop topping |
| Spring — swathe | None, Swathe only, Swathe + spray |
| Spring — other | None, plus anything you define yourself |
| Grazing | None, Standard, High |
| Harvest control | Standard, Chaff cart + burn dumps, Narrow windrow burn, Harrington Seed Destructor, Chaff tramlining, Bale Direct System |
| Harvest — other | None, Whole paddock burn, plus anything you define yourself |

Three post-emergent slots means you can spray up to three times in a year, and you pay for
three passes.

## What a herbicide does depends on the crop

This is the part a yes/no answer cannot express, and it is why the products are named.

| Post-emergent | Wheat / Barley | Canola / Legume | Pasture |
|---|---|---|---|
| Topik | 90% | — | — |
| Hussar | 95% | — | — |
| Clethodim | — | 90% | — |
| Glyphosate | — | 90% | — |
| Paraquat | — | — | 65% |

A dash is not a gap in the data — it is the model saying the product does nothing there.
Topik is a grass-selective cereal herbicide, so it is rated at zero in canola.

**The tool acts on this.** In the year-by-year editor a product that does nothing in that
year's crop is not offered at all. If one arrives from the all-years grid — which cannot vary
its dropdown per row — it is cleared and reported, rather than left looking effective while
quietly costing you money.

Costs work the same way: Glyphosate is $26/ha in a crop and $22/ha in a pasture; Sakura is
$48/ha where Triazine is $8/ha.

## Impossible decisions are prevented, not corrected

Some choices cannot work at all, and the tool switches them off with the reason shown:

- A knock-down with dry or wet sowing — there is no gap between spraying and seeding.
- A pre-emergent on a regenerating pasture — there is no seeding pass to carry it.
- Grazing a crop — it changes neither ryegrass nor livestock income.
- Harvest weed seed control on pasture — there is no header going through.

While anything in the plan is inconsistent, **results are withheld entirely**. Numbers from a
plan the model half-ignores look authoritative and quietly answer a different question.

## A note on where the numbers come from

RIM Online is a reimplementation of the **RIM-2013b** Excel/VBA model built at UWA. The
control rates, costs and crop parameters are read directly from that workbook — none of them
are typed in by hand.

The whole-run engine is still being brought to exact agreement with the workbook. Treat the
**shape** of a comparison — which strategy draws the bank down harder, which costs more — as
sound, and exact figures as provisional.

---

# Part 2 — Your files

## Three formats, and only two of them come back

| File | Extension | Direction | What it is for |
|---|---|---|---|
| **Scenario** | `.rim.json` | out **and** in | Your whole session. The one that restores your work. |
| **Options pack** | `.json` | out **and** in | Spring and harvest operations you define yourself. |
| **Workbook** | `.xlsx` | out only | Reading and sharing. Does **not** load back. |

> **The short version.** One `.rim.json` holds everything. If you only ever save one file,
> save that.

## File 1 — the scenario (`.rim.json`)

**Where:** *Keep this work* → **Save to a file**. The panel is on both the **Paddock profile**
and the **Strategy** page, and both save the same complete file — it does not matter which one
you use.

**Filename:** named for your paddock and dated, e.g. `North-Paddock-2026-09-04.rim.json`.

**To restore:** the same panel, **Load a saved file**. Everything comes back at once.

### What is inside

```json
{
  "format": "rim-online-save",
  "version": 5,
  "profile":  { ... },
  "prices":   { ... },
  "options":  { ... },
  "strategy": [ ... ],
  "profile_slots":       { ... },
  "strategy_slots":      { ... },
  "strategy_slot_names": { ... }
}
```

| Section | Holds |
|---|---|
| `profile` | Farm and paddock name, farm size, area for machinery repayment, base yields per crop, sheep gross margin, **starting seed bank**, interest, inflation (input costs and crop prices separately), tax, rotation shares |
| `prices` | Grain prices per crop, hay and silage, sheep price, and the operating costs — no-till, full-cut extra, tickle, high seeding rate extra, sprayer pass, insurance, fertiliser, seed, loan term, machinery capital |
| `options` | Germination rates, natural seed mortality, fecundity, stocking rates, tillage control — **and your own defined options**, if you have loaded any |
| `strategy` | The ten-year plan: one object per year, 17 fields each (see below) |
| `profile_slots` | Profile slots 1–4, each a complete profile + prices + options bundle |
| `strategy_slots` | Strategy slots 0–6, each a ten-year plan |
| `strategy_slot_names` | The names you typed for those slots |

One year of `strategy` looks like this:

```json
{
  "year": 1,
  "crop": "Wheat",
  "seeding_timing": "Dry",
  "seeding_technique": "No-till",
  "seeding_rate": "Standard",
  "pre_tillage": "None",
  "knockdown": "None",
  "pre_emergent": "Trifluralin + triallate",
  "post_emergent_1": "Topik",
  "post_emergent_2": "None",
  "post_emergent_3": "None",
  "spring_option": "None",
  "spring_swathe": "None",
  "spring_others": "None",
  "grazing_intensity": "None",
  "harvest_option": "Standard",
  "harvest_others": "None"
}
```

It is plain text and readable. You can open it, check it, and hand-edit it if you want to —
the names are exactly what the dropdowns show.

### Three things worth knowing

**Slots are not saved on their own.** Profile and strategy slots live in your browser session
only — close the tab and they are gone. They travel *inside* the `.rim.json`, so saving the
file keeps them and loading it brings them all back.

**Older files always load.** The format is at version 5, and every version back to 1 still
opens. If a plan was written when options had different names, the names are recognised and
brought up to date on load. You will see a note saying so.

**A partial file works.** Anything you leave out falls back to the shipped default, so a
hand-written scenario need not restate everything:

```json
{
  "format": "rim-online-save",
  "version": 5,
  "profile": {"farm_name": "Wickepin", "seed_bank_start": 100},
  "strategy": [{"crop": "Wheat"}, {"crop": "Canola"}]
}
```

## File 2 — your own options (`rim-custom-options.json`)

**Where:** **Strategy** page → *Spring and harvest options of your own*. There is a **Download
an example to edit** button, and an uploader beside it.

RIM's spreadsheet keeps room for four operations you invent — two spring, two harvest —
because four cells is what fits on the sheet. **Here there is no limit.** Spring and harvest
each have a single *Other* column in the plan, so you still choose one per year: a longer
list, not a wider model.

```json
{
  "format": "rim-online-options",
  "version": 2,
  "options": [
    {"for": "spring",
     "name": "Spring grazing crash",
     "control":     {"default": 0.55, "Canola": 0.0},
     "cost_per_ha": {"default": 12.0}},

    {"for": "harvest",
     "name": "Weed seed impact mill",
     "control":     {"default": 0.95},
     "cost_per_ha": {"default": 30.0, "Legume crop": 26.0}}
  ]
}
```

| Field | Meaning |
|---|---|
| `for` | `spring` or `harvest` — which *Other* dropdown it appears in |
| `name` | What you see in the dropdown. Two options of the same kind cannot share a name |
| `control` | Share of ryegrass it kills, 0 to 1. For scale: a knock-down is 0.95, crop topping 0.75, whole-paddock burning 0.60 |
| `cost_per_ha` | Dollars per hectare, including the operation |

`control` and `cost_per_ha` each take a `default` plus any per-crop exceptions, written with
the crop names the app uses. Above, the grazing crash costs $12/ha everywhere and kills 55% —
except in canola, where it does nothing.

**A control of zero is a real answer.** Set it and RIM stops offering that option for that
crop, exactly as it does for its own products. That is better than letting you pick something
that quietly costs money and achieves nothing.

**Loading any spring options replaces RIM's two spring placeholders**, and the same for
harvest. Everything else on those dropdowns — whole-paddock burning, for one — stays.

**You do not need to keep this file.** Once loaded, your options are stored inside the
scenario, so the `.rim.json` carries them. Keep the options file if you want to reuse the same
operations across different paddocks, or share them with a colleague.

**These are your numbers, not RIM's.** Everything else in the model traces back to the
RIM-2013b workbook. An option you define is only as good as the control rate you give it.
Treat a made-up rate as a question — *what would this need to achieve to pay?* — rather than
as an answer.

## File 3 — the workbook (`.xlsx`)

**Where:** **Export** page → **Download scenario as Excel**.

| Sheet | Holds |
|---|---|
| `Strategy` | The ten-year plan as a grid, in the editor's own words |
| `Paddock profile` | Group / Setting / Value |
| `Prices` | Group / Setting / Value |
| `Options` | Group / Setting / Value |
| `Results …` | One sheet per strategy you are holding, year by year |

It leads with the **inputs**, so someone opening it can see what was asked as well as what
happened. It exports even when nothing has been simulated, so a plan still blocked by the
validation gate can be sent on.

**It does not load back into RIM Online.** For that, use the `.rim.json`.

## Which file do I want?

| You want to… | Use |
|---|---|
| Stop for the day and carry on tomorrow | `.rim.json` |
| Send a colleague something they can edit in RIM | `.rim.json` |
| Send a colleague something to open in Excel | `.xlsx` |
| Chart or analyse the numbers elsewhere | `.xlsx` |
| Reuse your own operations on another paddock | options `.json` |
| Compare many paddocks at once | `.rim.json` files + the command-line runner |

## Running scenarios without the browser

If you are comparing several paddocks, the same `.rim.json` files the Save button writes can
be run from a command line:

```console
python -m tools.run_scenario broomehill.rim.json kojonup.rim.json
python -m tools.run_scenario plan.rim.json --options my-options.json
python -m tools.run_scenario *.rim.json --format excel --out results/
```

It prints a comparison table by default, or writes CSV, JSON or a workbook. It warns about any
decision the model would ignore, and `--strict` refuses to run such a plan at all. With no
file at all it runs the shipped default, which is a quick way to check an install.

## If something goes wrong

| What you see | What it means |
|---|---|
| *That is not a RIM Online save file* | The `format` line is missing or wrong — it is probably an options pack, or another program's JSON |
| *That file was written by a newer version* | Saved by a newer build than you are running. Update, or ask for it to be re-saved |
| *That is not a RIM Online options file* | You loaded a scenario into the options uploader, or the other way round. They are different formats |
| *spring option 1: needs a 'control'* | An options file with something missing — the message names the option and the field |
| *…names crops this model does not have* | A crop name is misspelled in your options file; it lists the ones it accepts |
| Results will not appear | The plan holds a decision the model cannot act on. The panel above the grid says which year and what to change |

---

*RIM Online — Ryegrass Integrated Management · The University of Western Australia and AHRI*
