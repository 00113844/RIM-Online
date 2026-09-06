"""The interface the pages depend on, fingerprinted.

Streamlit Cloud warm-restarts on a new commit: page files are re-executed from
disk while already-imported modules stay in ``sys.modules``. A deploy that
changes a page and a ``utils/`` or ``rim/`` module together then runs the new
page against the old module. Three deploys have died that way -- twice on a name
the old module did not have yet, once on a function whose signature had changed.

Changing ``requirements.txt`` forces a cold rebuild instead, so every module
comes from disk. The rule is therefore: **bump the build marker in
``requirements.txt`` in the same commit as any change to the interface the pages
import.** This module makes that checkable rather than remembered.

    python -m tools.deploy_interface           # show the fingerprint
    python -m tools.deploy_interface --write   # accept it, after bumping

``tests/test_deploy_interface.py`` fails when the fingerprint has moved and the
marker has not.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import inspect
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECORD = ROOT / ".deploy-interface.json"
FIRST_PARTY = ("utils.", "rim.")


def page_files() -> list[pathlib.Path]:
    """Every script Streamlit executes: the entrypoint and the pages."""
    return sorted(ROOT.glob("pages/*.py")) + [ROOT / "app.py"]


def imported_names() -> dict[str, list[str]]:
    """What the pages import from first-party modules, module by module."""
    out: dict[str, set[str]] = {}
    for path in page_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if not node.module.startswith(FIRST_PARTY):
                continue
            out.setdefault(node.module, set()).update(a.name for a in node.names)
    return {module: sorted(names) for module, names in sorted(out.items())}


def fingerprint() -> tuple[str, list[str]]:
    """A hash of every imported name's shape, plus the lines behind it."""
    lines: list[str] = []
    for module_name, names in imported_names().items():
        module = importlib.import_module(module_name)
        for name in names:
            attribute = getattr(module, name, None)
            if attribute is None:
                shape = "MISSING"
            elif callable(attribute) and not isinstance(attribute, type):
                try:
                    shape = str(inspect.signature(attribute))
                except (TypeError, ValueError):
                    shape = "callable"
            else:
                shape = type(attribute).__name__
            lines.append(f"{module_name}.{name}{shape}")
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]
    return digest, lines


def build_marker() -> str:
    """The marker in requirements.txt whose change forces a cold rebuild."""
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    found = re.search(r"^#\s*build:\s*(\S+)\s*$", text, re.M)
    if not found:
        raise SystemExit(
            "requirements.txt has no '# build:' marker. Add one — changing that "
            "file is what forces Streamlit Cloud to rebuild cold."
        )
    return found.group(1)


def recorded() -> dict:
    if not RECORD.is_file():
        return {}
    return json.loads(RECORD.read_text(encoding="utf-8"))


def write() -> dict:
    digest, _ = fingerprint()
    record = {"build": build_marker(), "fingerprint": digest}
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.deploy_interface")
    parser.add_argument("--write", action="store_true",
                        help="Record the current fingerprint and build marker.")
    parser.add_argument("--verbose", action="store_true",
                        help="List every name behind the fingerprint.")
    args = parser.parse_args(argv)

    digest, lines = fingerprint()
    if args.write:
        record = write()
        print(f"recorded build {record['build']} fingerprint {record['fingerprint']}")
    else:
        print(f"build {build_marker()} fingerprint {digest} "
              f"({len(lines)} names across {len(imported_names())} modules)")
    if args.verbose:
        for line in lines:
            print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
