# Outstanding work

Ordered by what unblocks what. Status as of 2026-09-02, branch `main`.

Background: [`ARCHITECTURE.md`](ARCHITECTURE.md) · Rules: [`CLAUDE.md`](CLAUDE.md) ·
Port status: [`.claude/memory/engine-port-status.md`](.claude/memory/engine-port-status.md)

---

## 1. Product-level vocabulary — the keystone

**Why first:** almost everything else below is blocked on it, and it is the largest
single gap between the app and the workbook.

The strategy editor still offers invented generic options where Excel names products,
each with its own cost and control rate per crop category:

| Decision | Excel | App today |
|---|---|---|
| Knock-down | Glyphosate, Paraquat, DoubleK | None / Single / Double |
| Pre-emergent | 5 named products | Yes / No |
| Post-emergent | 5 named products across **3 slots** | Yes / No, **1 slot** |
| Spring — swathe | W/o Spray, With Spray | column missing |
| Spring — others | Define 1st, Define 2nd | column missing |
| Harvest — others | B.all, Define 1st, Define 2nd | column missing |

So 13 named herbicides collapse to five generic choices, three post-emergent slots to
one, and three whole columns do not exist. Excel also lets a user define two custom
spring and two custom harvest options; those are absent entirely.

**The work**
- Replace `rim/options.py`'s invented lists with the workbook's own, loaded from the
  already-generated `data/strategy_vocabulary.json`.
- Add `post_emergent_1/2/3`, `spring_swathe`, `spring_others`, `harvest_others` to the
  strategy dict and to `pages/2_Strategy.py`.
- Migrate saved strategies in `utils/session.py` and in the `.rim.json` save format
  (bump `SAVE_FORMAT_VERSION`, keep reading version 1).
- Retire `rim/excel_inputs.py`'s lossy adapter as its `TRANSLATION_LOSSES` entries
  become representable.

---

## 2. Per-product applicability rules

**Blocked by 1.** `utils/applicability.py` currently gates at the coarsest level the
generic vocabulary allows. With named products the same machinery gets precise, using
`data/calcs_survival_table.json`, where a control of 0 for a crop means the product
does nothing:

- Topik and Hussar do nothing on canola, legume or any pasture.
- Clethodim and post-emergent Glyphosate work only on canola and legume.
- Post-emergent Paraquat works only on pastures.
- Triflur+Triallate and Sakura do nothing on pasture; Triazine does.

Each becomes a `gates()` rule and a disabled control in `utils/year_editor.py`. Extend
`tests/test_applicability.py` the same way — every rule re-checks the generated data it
depends on, so a rule cannot outlive its evidence.

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
- Scenario export carries its inputs, not only its results (`utils/export.py`).
- Profile slots save the farm on screen, and say which farm they hold. The page
  no longer batches its fields behind `st.form`; see
  `.claude/memory/streamlit-widget-state-staleness.md`.
