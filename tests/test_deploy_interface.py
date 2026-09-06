"""Changing what the pages import must force a cold rebuild.

Streamlit Cloud warm-restarts on a new commit: page files are re-executed from
disk while already-imported modules stay in ``sys.modules``. A deploy that
changes a page and a ``utils/`` or ``rim/`` module together then runs the new
page against the old module.

Three deploys have died that way:

    ImportError: cannot import name 'commit_profile_widgets' from 'utils.session'
    ImportError: cannot import name 'FIELD_HELP' from 'utils.year_editor'
    TypeError:   save_load_controls() takes 1 positional argument but 2 given

The first two are a name the old module did not have yet, and can be dodged by
putting shared things in a module no old container ever imported. The third is a
function whose *shape* changed, and no amount of moving it helps -- the cached
function is simply wrong.

What does work is changing ``requirements.txt``, which makes Cloud rebuild the
environment cold so every module comes from disk. This test enforces that: move
the interface without bumping the marker and the suite says so, here, rather
than a user meeting a redacted TypeError.
"""
from __future__ import annotations

import pytest

from tools import deploy_interface


def test_the_marker_and_the_interface_were_recorded_together() -> None:
    record = deploy_interface.recorded()
    assert record, (
        "No .deploy-interface.json. Create it with:\n"
        "    python -m tools.deploy_interface --write"
    )

    digest, _ = deploy_interface.fingerprint()
    marker = deploy_interface.build_marker()

    if digest == record["fingerprint"]:
        return

    assert marker != record["build"], (
        f"\nThe interface the pages import has changed "
        f"({record['fingerprint']} -> {digest}) but the build marker in "
        f"requirements.txt is still {marker!r}.\n\n"
        f"Streamlit Cloud warm-restarts on a commit and keeps old modules in "
        f"sys.modules, so the new pages would run against the old ones and the "
        f"deploy would break. Changing requirements.txt forces a cold rebuild.\n\n"
        f"    1. bump the '# build:' line in requirements.txt\n"
        f"    2. python -m tools.deploy_interface --write\n"
    )


def test_every_name_a_page_imports_actually_exists() -> None:
    """A missing name is the exact crash this is all about."""
    _, lines = deploy_interface.fingerprint()

    missing = [line for line in lines if line.endswith("MISSING")]

    assert missing == [], f"pages import names that do not exist: {missing}"


def test_the_pages_are_all_looked_at() -> None:
    """A page added without being covered would slip the check."""
    names = deploy_interface.imported_names()

    assert "utils.session" in names, "the busiest module is not being fingerprinted"
    assert len(deploy_interface.page_files()) >= 8


@pytest.mark.parametrize("module", ["utils.save_load", "utils.year_editor"])
def test_the_modules_that_broke_deploys_are_covered(module) -> None:
    assert module in deploy_interface.imported_names()
