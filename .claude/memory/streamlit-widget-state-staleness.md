# Streamlit widget state goes stale, and it has cost this project twice

`st.session_state[key]` for a widget wins over the `value=`/`index=` argument
once the widget exists. Streamlit honours the argument only on first creation.
So any code path that replaces the underlying data from *outside* the widget --
loading a slot, loading a file, resetting to defaults, a fix-it button -- leaves
the widget holding the old value, and the widget writes it straight back.

**Deleting the key is not enough.** A widget's identity is its key, and the
browser still holds a widget with that id: it re-sends the old value on the next
message, so the server forgets and is immediately reminded. Verified in a real
browser -- loading a slot left the old farm name in the box. To genuinely reset a
*keyed* widget you must change its identity. Put a generation number in the key
(`utils.session.profile_widget_key`) and bump it when the data is replaced; the
browser then draws a new widget seeded from `value=`.

Unkeyed widgets do not have this problem: their auto-generated id includes
`value=`, so changing the data changes the id and they re-seed on their own. The
cost is that nothing can address them by key.

`st.form` adds a second, sharper edge: a form withholds its widgets' values from
session state until its own submit button is pressed. Anything rendered *above*
the form therefore reads the last-submitted values, not what is on screen.

## Where it has bitten

1. **The year editor reverting to Year 01** (fixed 2026-09-01). Hidden editors
   re-applied stale widget state over the current plan. Fix:
   `utils.session.reset_editor_widgets()`, called from every path that replaces
   `strategy_current`, plus only one editor live at a time. That helper only
   deletes keys, so it may carry the latent flaw described above; it has not
   misbehaved in a browser, and the year editor's `st.rerun()` may be covering
   for it. Revisit if the symptom returns.
2. **Profile slots saving the wrong farm** (fixed 2026-09-02). The slot toolbar
   sits above the profile fields, which were wrapped in three `st.form`s. Save
   captured the last-submitted bundle, so a farm renamed but not "updated" was
   saved under its old name -- while prices, assigned on every rerun, *did*
   change. Fill the page and save, and the slot held new prices under the old
   farm's name. Fix: no forms on that page, explicit keys on every field,
   `utils.session.PROFILE_WIDGETS` mapping key -> bundle path, and
   `commit_profile_widgets()` / `reset_profile_widgets()` as the two halves.

## The pattern to follow

- Give every widget an explicit `key`.
- Keep one table mapping key -> where the value belongs, and commit through it.
- Any path that replaces the data from outside must retire those keys -- change
  the identity, do not merely delete the entry.
- Prefer live widgets over `st.form` on pages whose values other controls read.
- A button whose effect the *same run* must render -- a picker labelled from
  what the button just saved -- belongs in `on_click`. Callbacks run before the
  script body; a body handler acts after the widget above it has already drawn,
  so the display lags by one interaction. Streamlit also keeps a keyed widget's
  rendered label when only its option strings change, so anything that must read
  correctly right away is better as plain markdown than as a widget label.
- A `format_func` must not read session state: `AppTest` evaluates it outside a
  script run, so the widget cannot be serialised and every `.run()` after it
  fails with a bare `AttributeError: _widget_state`. Precompute the labels and
  format through a plain dict.

## It also bites on deploy

Streamlit reloads page files but not deeply-imported modules, and that holds on
Streamlit Cloud. A deploy touching a page and a `utils/` module together can run
the new page against the old module, which fails at import and shows a traceback
that reads like broken code:

    ImportError: cannot import name 'commit_profile_widgets' from 'utils.session'

Seen 2026-09-03 after `3f9cf53`, with the name present on `origin/main` the whole
time. Check the remote before debugging; if the name is there, reboot the app
(Manage app -> Reboot) rather than changing anything.

## Testing it

`streamlit.testing.v1.AppTest` drives real pages. Enter through `app.py` and
`switch_page(...)` -- `AppTest.from_file` on a file in `pages/` leaves the
multipage registry unbuilt and `st.page_link` raises `KeyError: 'url_pathname'`.

`AppTest` injects widget state directly, so it *cannot* reproduce the `st.form`
half of this bug: a `set_value` on a form widget behaves as if submitted. Tests
written against `AppTest` will pass on a page that is broken in a browser. Pin
the absence of forms structurally instead -- `tests/test_profile_slots.py`
asserts no "Update" button survives.

See `tests/test_profile_slots.py` and `tests/test_strategy_state.py`.
