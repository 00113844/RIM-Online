# Outstanding work

Ordered by what unblocks what. Status as of 2026-09-03, branch `main`.

Background: [`ARCHITECTURE.md`](ARCHITECTURE.md) · Rules: [`CLAUDE.md`](CLAUDE.md) ·
Port status: [`.claude/memory/engine-port-status.md`](.claude/memory/engine-port-status.md)

---

## 1. ~~Product-level vocabulary~~ — DONE

**Done 2026-09-03.** Every weed-control decision now uses the workbook's own
vocabulary, rated and priced per crop from `Calcs` rows 55-97 and 105-147 -- the
same option list twice, paired at `r + 50`. `rim/control_options.py` is the one
place that knows which rows belong to which decision on `2.Strategy`; nothing is
typed.

| Decision | Excel | App |
|---|---|---|
| Knock-down | Glyphosate, Paraquat, DoubleK | **the same three** |
| Pre-emergent | 5 named products | **the same five** |
| Post-emergent | 5 products across 3 slots | **the same, 3 slots** |
| Spring option | 6 named operations | **the same six** |
| Spring — swathe | W/o Spray, With Spray | **present** |
| Spring — others | Define 1st, Define 2nd | **present** |
| Harvest | 5 named systems | **the same five** |
| Harvest — others | B.all, Define 1st, Define 2nd | **present** |

Costs come from `Calcs!N105:T147` per option per crop -- Glyphosate is $26/ha in
a crop and $22/ha in a pasture, Sakura $48 against Triazine's $8. The flat
sprayer-pass charge is gone, and so are the invented control rates and the
hand-written cost table in `rim/defaults.py`.

`TRANSLATION_LOSSES` is down from six entries to one: stage timing, which is
`Calcs!C75:C83` applying each control at a named point in the season where the
app applies one combined annual fraction. That is item 3's business, not a
vocabulary problem.

**Still outstanding:** RIM lets a user *define* the two spring and two harvest
slots (`1.Profile` C32:C35) with their own name, cost and control. The app
offers them under the workbook's placeholder names at the workbook's saved
values; it cannot yet edit them.

---

## 2. ~~Per-product applicability rules~~ — DONE

Done 2026-09-03 alongside item 1, and now covering every weed-control decision
rather than only the herbicides. A control of 0 in
`data/calcs_survival_table.json` means the option does nothing on that crop, and
the app reads it that way:

- Topik and Hussar do nothing on canola, legume or any pasture.
- Clethodim and post-emergent Glyphosate work only on canola and legume.
- Post-emergent Paraquat works only on pastures.
- Triflur+Triallate and Sakura do nothing on pasture; Triazine does.

`utils.applicability.product_options` narrows the year editor's dropdown to what works,
and `product_mismatch` catches a choice arriving from the grid, which cannot vary its
options per row. `tests/test_herbicides.py` re-reads the generated table for every rule.

Swathing joins them: `Calcs` rows 87-88 are zero on every pasture, because there
is nothing to swathe.

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
- The whole weed-control vocabulary, rated *and priced* per crop from the
  workbook, including the three decisions the app used to lack.
- Scenario export carries its inputs, not only its results (`utils/export.py`).
- Profile slots save the farm on screen, and say which farm they hold. The page
  no longer batches its fields behind `st.form`; see
  `.claude/memory/streamlit-widget-state-staleness.md`.
