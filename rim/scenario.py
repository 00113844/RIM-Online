"""A whole scenario, read and written without Streamlit anywhere near it.

``.rim.json`` has always held everything needed to reproduce a run -- paddock
profile, prices, options, the ten-year plan -- but the only code that could read
one wrote straight into ``st.session_state``, so a save file could not be
replayed except through a browser. This module is the reading, separated from
the applying. ``utils/session.py`` still does the applying for the app;
``tools/run_scenario.py`` uses this directly.

Keeping the two apart is what makes the save format testable on its own, and it
is why the command-line runner needs no Streamlit at all.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from rim import control_options
from rim.defaults import (
    DEFAULT_OPTIONS,
    DEFAULT_PRICES,
    DEFAULT_PROFILE,
    build_default_strategy,
)
from rim.herbicides import upgrade_strategy

# Three files, because a paddock and a plan are answers to different questions.
# A course can hand out one paddock and collect thirty plans against it; a
# consultant can carry one paddock between plans. The combined file is still
# there, and is still what "keep all my work" means.
SAVE_FORMAT = "rim-online-save"           # everything
PROFILE_FORMAT = "rim-online-profile"     # the paddock: profile, prices, options
STRATEGY_FORMAT = "rim-online-strategy"   # the plan, and the slots beside it

# The newest of each this build writes. Older ones are read and carried forward;
# see rim/herbicides.py for what changed at each step of the combined format.
SAVE_FORMAT_VERSION = 5
PROFILE_FORMAT_VERSION = 1
STRATEGY_FORMAT_VERSION = 1

# Which sections belong to which file. A combined file holds every one.
PROFILE_SECTIONS: tuple[str, ...] = ("profile", "prices", "options", "profile_slots")
STRATEGY_SECTIONS: tuple[str, ...] = (
    "strategy", "strategy_slots", "strategy_slot_names",
)

_VERSIONS: dict[str, int] = {
    SAVE_FORMAT: SAVE_FORMAT_VERSION,
    PROFILE_FORMAT: PROFILE_FORMAT_VERSION,
    STRATEGY_FORMAT: STRATEGY_FORMAT_VERSION,
}

# What each file is called when it is offered for download.
SUFFIXES: dict[str, str] = {
    SAVE_FORMAT: ".rim.json",
    PROFILE_FORMAT: ".profile.json",
    STRATEGY_FORMAT: ".strategy.json",
}


class ScenarioError(ValueError):
    """The file is not a usable scenario. The message says why."""


@dataclass(frozen=True)
class Scenario:
    """One paddock, one plan, ready to simulate."""

    profile: dict
    prices: dict
    options: dict
    strategy: list[dict]
    name: str = "scenario"
    source_version: int = SAVE_FORMAT_VERSION
    profile_slots: dict = field(default_factory=dict)
    strategy_slots: dict = field(default_factory=dict)
    strategy_slot_names: dict = field(default_factory=dict)

    @property
    def custom_options(self):
        """This scenario's own option definitions, if it carries any."""
        return control_options.custom_from(self.options)

    @property
    def years(self) -> int:
        return len(self.strategy)

    def as_save_payload(self) -> dict:
        """The scenario as a ``.rim.json`` body, at the current format."""
        return {
            "format": SAVE_FORMAT,
            "version": SAVE_FORMAT_VERSION,
            "profile": self.profile,
            "prices": self.prices,
            "options": self.options,
            "strategy": self.strategy,
            "profile_slots": self.profile_slots,
            "strategy_slots": self.strategy_slots,
            "strategy_slot_names": self.strategy_slot_names,
        }

    def as_profile_payload(self) -> dict:
        """Just the paddock: profile, prices, options and the profile slots."""
        return {
            "format": PROFILE_FORMAT,
            "version": PROFILE_FORMAT_VERSION,
            "profile": self.profile,
            "prices": self.prices,
            "options": self.options,
            "profile_slots": self.profile_slots,
        }

    def as_strategy_payload(self) -> dict:
        """Just the plan, and the slots kept beside it."""
        return {
            "format": STRATEGY_FORMAT,
            "version": STRATEGY_FORMAT_VERSION,
            "strategy": self.strategy,
            "strategy_slots": self.strategy_slots,
            "strategy_slot_names": self.strategy_slot_names,
        }


def _merged(base: Mapping, override: Any, what: str) -> dict:
    """A saved section over the defaults, so a partial file still runs.

    Missing keys are a normal thing in a hand-written scenario, and filling them
    from the defaults is better than refusing the file. A section of the wrong
    shape is a mistake worth reporting.
    """
    if override is None:
        return dict(base)
    if not isinstance(override, Mapping):
        raise ScenarioError(f"'{what}' should be an object, not {type(override).__name__}.")
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = {**out[key], **value}
        else:
            out[key] = value
    return out


def kind_of(payload: Any) -> str:
    """Which of the three files this is, validated. Raises if it is none.

    Checked here rather than at each call site so one message covers a file
    dropped into the wrong uploader, which is the mistake people actually make.
    """
    if not isinstance(payload, Mapping):
        raise ScenarioError("The file should hold a JSON object.")

    declared = payload.get("format")
    if declared not in _VERSIONS:
        raise ScenarioError(
            "That is not a RIM Online file. Expected \"format\" to be one of: "
            + ", ".join(f'"{name}"' for name in _VERSIONS)
            + "."
        )

    version = payload.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool):
        raise ScenarioError(f"'version' should be a whole number, not {version!r}.")
    if version > _VERSIONS[declared]:
        raise ScenarioError(
            f"That file was written by a newer version of RIM Online "
            f"({declared} format {version}, this build reads "
            f"{_VERSIONS[declared]})."
        )
    return declared


def describe_kind(kind: str) -> str:
    """What to call this file when telling someone what they just loaded."""
    return {
        SAVE_FORMAT: "a full scenario",
        PROFILE_FORMAT: "a paddock profile",
        STRATEGY_FORMAT: "a strategy",
    }.get(kind, kind)


def merge_payloads(*payloads: Any) -> dict:
    """One combined payload from any mix of the three files.

    Later payloads win section by section, so pairing a shared paddock with each
    of thirty plans is ``merge_payloads(paddock, plan)`` thirty times. Sections a
    file does not carry are simply absent, and ``from_payload`` fills them from
    the shipped defaults.
    """
    combined: dict = {"format": SAVE_FORMAT, "version": SAVE_FORMAT_VERSION}
    for payload in payloads:
        if payload is None:
            continue
        kind = kind_of(payload)
        sections = (PROFILE_SECTIONS if kind == PROFILE_FORMAT
                    else STRATEGY_SECTIONS if kind == STRATEGY_FORMAT
                    else PROFILE_SECTIONS + STRATEGY_SECTIONS)
        for section in sections:
            if section in payload:
                combined[section] = payload[section]
    return combined


def from_payload(payload: Any, *, name: str = "scenario") -> Scenario:
    """Build a :class:`Scenario` from any of the three files.

    A profile file arrives with no plan and a strategy file with no paddock;
    each is filled from the shipped defaults, so either runs on its own. Accepts
    every format version this build has written -- a plan saved against an older
    vocabulary is carried forward here, once, so nothing downstream has to know
    there ever was one.
    """
    kind = kind_of(payload)
    if kind != SAVE_FORMAT:
        payload = merge_payloads(payload)
    version = payload.get("version", 1)

    options = _merged(DEFAULT_OPTIONS, payload.get("options"), "options")

    strategy = payload.get("strategy")
    if strategy is None:
        strategy = build_default_strategy(10)
    if not isinstance(strategy, list) or not strategy:
        raise ScenarioError("'strategy' should be a non-empty list of years.")
    if not all(isinstance(row, Mapping) for row in strategy):
        raise ScenarioError("Every entry in 'strategy' should be an object.")

    upgraded = upgrade_strategy(
        [dict(row) for row in strategy], control_options.custom_from(options)
    )
    for position, row in enumerate(upgraded, start=1):
        row.setdefault("year", position)

    return Scenario(
        profile=_merged(DEFAULT_PROFILE, payload.get("profile"), "profile"),
        prices=_merged(DEFAULT_PRICES, payload.get("prices"), "prices"),
        options=options,
        strategy=upgraded,
        name=name,
        source_version=version,
        profile_slots=dict(payload.get("profile_slots") or {}),
        strategy_slots=dict(payload.get("strategy_slots") or {}),
        strategy_slot_names=dict(payload.get("strategy_slot_names") or {}),
    )


def read_payload(path: str | Path) -> dict:
    """The raw JSON of a save file, with readable errors. No interpretation.

    Separate from :func:`load` so a caller that must change the options *before*
    the plan is read -- the command-line runner applying a custom options file,
    say -- can do so without a second copy of the error handling. The plan is
    canonicalised against the options, so injecting them afterwards is too late.
    """
    target = Path(path)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ScenarioError(f"{target} does not exist.") from None
    except UnicodeDecodeError:
        raise ScenarioError(f"{target} is not UTF-8 text.") from None
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{target} is not readable JSON: {exc}.") from None
    return payload


def name_for(path: str | Path) -> str:
    """The scenario name a file implies: its stem, without .rim.json."""
    target = Path(path)
    stem = target.name
    # Longest first, so ".strategy.json" is not left as ".strategy" by ".json".
    for suffix in sorted((*SUFFIXES.values(), ".json"), key=len, reverse=True):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem or target.name


def load(path: str | Path) -> Scenario:
    """Read a ``.rim.json`` from disk. The file's stem names the scenario."""
    return from_payload(read_payload(path), name=name_for(path))


def default() -> Scenario:
    """The shipped paddock and plan, for a run with no file to start from."""
    return from_payload(
        {
            "format": SAVE_FORMAT,
            "version": SAVE_FORMAT_VERSION,
            "profile": dict(DEFAULT_PROFILE),
            "prices": dict(DEFAULT_PRICES),
            "options": dict(DEFAULT_OPTIONS),
            "strategy": build_default_strategy(10),
        },
        name="default",
    )
