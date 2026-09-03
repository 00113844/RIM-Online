# Outstanding work

Ordered by what unblocks what. Status as of 2026-09-03, branch `main`.

Background: [`ARCHITECTURE.md`](ARCHITECTURE.md) · Rules: [`CLAUDE.md`](CLAUDE.md) ·
Port status: [`.claude/memory/engine-port-status.md`](.claude/memory/engine-port-status.md)

---

## 1. Product-level vocabulary — herbicides named, knock-down still generic

**Done 2026-09-03.** Pre- and post-emergent herbicides are named, and each one's
effect is read per crop from `Calcs!N54:T97` via `data/calcs_survival_table.json`
(`rim/herbicides.py`). The single post-emergent boolean became the workbook's three
slots, `2.Strategy` rows 11-13. Flat invented rates -- pre-em 0.45, post-em 0.50 --
are gone from `rim/defaults.py`.

| Decision | Excel | App |
|---|---|---|
| Pre-emergent | 5 named products | **5 named products** |
| Post-emergent | 5 named products across **3 slots** | **5 products, 3 slots** |
| Knock-down | Glyphosate, Paraquat, DoubleK | None / Single / Double |
| Spring — swathe | W/o Spray, With Spray | column missing |
| Spring — others | Define 1st, Define 2nd | column missing |
| Harvest — others | B.all, Define 1st, Define 2nd | column missing |

**What is left**

- Knock-down products. Rows 55-57 hold Glyphosate 0.95, Paraquat 0.95 and
  Glyphosate/Paraquat 1.00; the app still offers Single/Double against invented
  0.55/0.75. Same shape as the work just done, so it is now small.
- The three missing columns (`spring_swathe`, `spring_others`, `harvest_others`)
  and RIM's two user-definable spring and two harvest options.
- Per-product **costs**. Control now comes from the workbook; cost is still a flat
  sprayer pass per application (`rim/economics.py`), where `Calcs!N105:T147` prices
  each product separately. Note the column-swap trap recorded in item 4.

---

## 2. ~~Per-product applicability rules~~ — DONE for herbicides

Done 2026-09-03 alongside item 1. A control of 0 in `data/calcs_survival_table.json`
means the product does nothing on that crop, and the app now reads it that way:

- Topik and Hussar do nothing on canola, legume or any pasture.
- Clethodim and post-emergent Glyphosate work only on canola and legume.
- Post-emergent Paraquat works only on pastures.
- Triflur+Triallate and Sakura do nothing on pasture; Triazine does.

`utils.applicability.product_options` narrows the year editor's dropdown to what works,
and `product_mismatch` catches a choice arriving from the grid, which cannot vary its
options per row. `tests/test_herbicides.py` re-reads the generated table for every rule.

Outstanding only for the decisions item 1 has not reached yet — knock-down products and
the three missing columns.

---

## 3. Rewire the app onto the ported engine

**The app does not use the ported engine at all.** `rim/calcs.py` and its five modules
reproduce the workbook's biology exactly, and are imported by nothing outside `tests/`.
`utils/session.py` calls `rim.engine.simulate_strategy` — the original pre-port model — so
every number a user sees comes from the unverified one, and the exact engine is dead code.

Measured on the shipped default plan, both starting from 20 seeds/m² so only the model
differs: the app draws the seed bank down **8%** over ten years; the ported engine draws it
down **98%**. Drawing the seed bank down is the entire point of RIM, and the app does not
show it happening.

The biological outputs — ryegrass counts and seed bank — could be switched over now, ahead
of items 4 and 5, which would make the Population page correct while economics catches up.
Doing so means adapting `simulate_years()` output into the `simulate_strategy()` contract
(`yearly`, `summary`, `machinery_repayments`), and translating the app's strategy dicts into
the workbook's own labels — `rim/excel_inputs.py` already does that, lossily, and item 1
removes the loss.

See `data/extracted_RIM_Excel_Information/04-coverage-audit.md`.

---

## 4. ~~Finish the engine port — blocks 6 and 7~~ — DONE

Ported 2026-09-02. `rim/yield_model.py` (`Bio results!D23:D54`) and
`rim/economics_model.py` (`Eco results!E3:E73`). The chain reproduces the workbook
from the strategy grid alone: 200 comparisons across four fixtures, worst error
5.7e-14, all four nominal annuities exact.

**This did not turn the parity fixtures green**, and it was never going to:
`tests/test_excel_parity.py` exercises `rim.engine.simulate_strategy`, the pre-port
model. That is item 3.

---

## 5. A headless CLI, so scenarios can be run without the browser

Everything the model does is reachable only through Streamlit today. There is no
way to run a profile and a strategy from the command line, which makes three
things awkward: comparing several farms, regression-testing the app's numbers
against the workbook, and reproducing a user's report from the `.rim.json` they
send.

The pieces already exist. `.rim.json` holds a whole scenario
(`utils/session.py`, `export_bundle()`); `utils/export.py` writes the same
scenario to a workbook; `rim.engine.simulate_strategy()` takes plain dicts and
imports no Streamlit.

**The work** — a `tools/run_scenario.py` that takes one or more `.rim.json`
files, runs each, and writes results as CSV, JSON or an Excel workbook:

```console
.venv\Scripts\python -m tools.run_scenario scenarios/*.rim.json --out results/
.venv\Scripts\python -m tools.run_scenario broomehill.rim.json --compare kojonup.rim.json
```

Needs a loader that reads a save file **without** `st.session_state` — the
current `import_bundle()` writes straight into session state, so the reading and
the applying have to come apart first. That split is small and makes the save
format testable on its own.

Worth doing after item 3: run through `rim/calcs.py` and the CLI becomes a way
to check the app against a fixture, not just a convenience.

---

## 6. Smaller items

- **`data/defaults.json` is dead.** Unread at runtime and deliberately untracked.
  Replace `rim/defaults.py`'s hand-transcribed scalars with a loader over generated
  data, as `tools/extract_params.py` already does for the other six files.
- **Streamlit only reloads pages, not deeply-imported modules.** Editing anything under
  `utils/` needs a server restart; the file watcher will not pick it up. Worth a line in
  the README when one exists.

  This reaches **Streamlit Cloud too**, and there it looks like a bug in the code. A
  deploy that changes a page and a `utils/` module together can leave the new page
  running against the old module, and the page dies on import:

  ```
  ImportError: cannot import name 'commit_profile_widgets' from 'utils.session'
  ```

  Seen on 2026-09-03 after `3f9cf53`, with the correct code on `origin/main`. The fix is
  Manage app -> Reboot; nothing in the repo needs changing. Check `origin/main` before
  believing the traceback -- if the name is there, it is the deployment that is stale.
- **The UWA/AHRI branding was reworked** in the redesign. The navy and gold came from an
  explicit AHRI request, so the new treatment should be shown to whoever owns that.

---

## Done

- Agent framework: `CLAUDE.md`, `.claude/memory/`.
- Excel parity harness: two capture paths, self-test agreeing to 1e-6, four fixtures.
- Engine port, all seven blocks — biology and economics, exact against four fixtures.
- Nine parameter files generated from the workbook, never hand-typed.
- `ARCHITECTURE.md`, and a published visual companion.
- Interface redesign around the seed-bank spine.
- Impossible decisions enforced: disabled in the year editor, cleared from the grid.
- Work can be saved to and loaded from a `.rim.json` file.
- `data/extracted_RIM_Excel_Information/` — how the model works, and the coverage audit.
- `ROADMAP.md` rewritten as the delivery roadmap.
- Named herbicides: five pre-emergent and five post-emergent products, rated per
  crop from the workbook, across its three post-emergent slots.
- Scenario export carries its inputs, not only its results (`utils/export.py`).
- Profile slots save the farm on screen, and say which farm they hold. The page
  no longer batches its fields behind `st.form`; see
  `.claude/memory/streamlit-widget-state-staleness.md`.
