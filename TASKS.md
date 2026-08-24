# Outstanding work

Ordered by what unblocks what. Status as of 2026-08-24, branch `parity-framework`.

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

## 3. Finish the engine port — blocks 6 and 7

**Independent of 1 and 2.** Blocks 1–5 are done and biological parity is exact
(640 comparisons, worst relative error 5.9e-16). Remaining:

- **Block 6 — yield and competition**, `Bio results!D23:D50`.
- **Block 7 — economics**, `Eco results!E3:E59`.

Then rewire `rim/engine.py` to call `rim.calcs`, preserving the `simulate_strategy()`
contract (`yearly`, `summary`, `machinery_repayments`).

**Until this lands the app's numbers are the old unverified model.** The four failing
fixtures in `tests/test_excel_parity.py` cannot move before it. Ten years of continuous
wheat currently reports +$349/ha average gross margin and a seed bank falling to zero,
where Excel gives −$240.91/ha and ryegrass escaping to ~18,763 plants/m².

---

## 4. Smaller items

- **`data/defaults.json` is dead.** Unread at runtime and deliberately untracked.
  Replace `rim/defaults.py`'s hand-transcribed scalars with a loader over generated
  data, as `tools/extract_params.py` already does for the other six files.
- **Streamlit only reloads pages, not deeply-imported modules.** Editing anything under
  `utils/` needs a server restart; the file watcher will not pick it up. Worth a line in
  the README when one exists.
- **`ROADMAP.md`** predates the port and describes a seven-period loop the workbook does
  not have. Either fold it into `ARCHITECTURE.md` or mark it historical.
- **The UWA/AHRI branding was reworked** in the redesign. The navy and gold came from an
  explicit AHRI request, so the new treatment should be shown to whoever owns that.

---

## Done

- Agent framework: `CLAUDE.md`, `.claude/memory/`.
- Excel parity harness: two capture paths, self-test agreeing to 1e-6, four fixtures.
- Engine port blocks 1, 2, 3, 3b, 4, 5 — full biological parity.
- Six parameter files generated from the workbook, never hand-typed.
- `ARCHITECTURE.md`, and a published visual companion.
- Interface redesign around the seed-bank spine.
- Impossible decisions enforced: disabled in the year editor, cleared from the grid.
- Work can be saved to and loaded from a `.rim.json` file.
