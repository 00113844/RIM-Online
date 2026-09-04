"""User-facing copy that more than one editor shows.

Two reasons this is its own module rather than constants beside the widgets.

**It stops the two editors drifting apart.** The year editor and the all-years
grid explain the same decision, and an explanation that is right in one place
and stale in the other is worse than one place having none.

**It survives a half-updated deploy.** Streamlit re-executes page files but
keeps already-imported modules in ``sys.modules``, so a deploy that changes a
page and a ``utils/`` module together can run the new page against the old
module. A page importing a *newly added* name from an existing module then dies
at import:

    ImportError: cannot import name 'FIELD_HELP' from 'utils.year_editor'

That has now happened twice. A module the old container never imported cannot be
stale -- it is not in ``sys.modules``, so it loads from disk. Putting shared copy
here means a page never has to wait for an existing module to grow an attribute.
See ``.claude/memory/streamlit-widget-state-staleness.md``.
"""
from __future__ import annotations

from rim.herbicides import POST_EMERGENT_FIELDS

# Why three boxes labelled Spray 1/2/3 are not three timings. The mechanism is
# Calcs!P35:P39 counting how many slots name a product and Calcs!C168 raising
# that product's survival to the power of the count -- a repeat compounds rather
# than adding a stage, and nothing about the labels says so.
POST_EMERGENT_NOTE = (
    "Three sprays in the same season — not three timings. All three act at "
    "the same point, so these are extra passes rather than earlier or later "
    "ones. Naming one product twice compounds it: Topik twice leaves 1% of "
    "the ryegrass where once leaves 10%. Each spray is a pass you pay for."
)

POST_EMERGENT_HELP = (
    "One post-emergent application. The three sprays all act at the same "
    "point in the season; repeat a product to compound its effect, or name "
    "two to cover different weeds. Leave as None if you are not spraying."
)

# A line under a group heading, where the grouping itself needs explaining.
GROUP_NOTES: dict[str, str] = {
    "Post-emergent sprays": POST_EMERGENT_NOTE,
}

# Tooltips, for a decision whose name does not carry its meaning.
FIELD_HELP: dict[str, str] = {
    field: POST_EMERGENT_HELP for field in POST_EMERGENT_FIELDS
}
