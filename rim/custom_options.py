"""User-defined spring and harvest options, loaded from a JSON file.

RIM keeps four slots a user can define themselves -- two spring, two harvest
(``1.Profile`` C32:C35, ``Calcs`` rows 85, 86, 96 and 97). The workbook lets you
type a name, a cost and a control rate into the sheet. This app takes the same
four as a small JSON file instead, which is better than typing them into a
browser: a file can be version-controlled, shared with a colleague, reviewed,
and replayed by the command-line runner without a browser at all.

The file looks like this::

    {
      "format": "rim-online-options",
      "version": 1,
      "options": {
        "spring_1": {
          "name": "Spring grazing crash",
          "control": {"default": 0.55, "Canola": 0.0},
          "cost_per_ha": {"default": 12.0, "Wheat": 14.0}
        }
      }
    }

Four slot names are accepted -- ``spring_1``, ``spring_2``, ``harvest_1``,
``harvest_2`` -- and every one is optional. Within a slot, ``control`` and
``cost_per_ha`` take a ``default`` plus any per-crop exceptions, keyed by the
crop names the app uses. A slot left out keeps the workbook's own value.

Control is a proportion of ryegrass killed, 0 to 1. A control of 0 for a crop
means the option does nothing there, which is how the rest of the app already
reads the workbook's own zeros: it stops offering the option for that crop.

The parsed pack travels in the options bundle, under ``custom_options``, so it
is saved with the scenario, passed to the engine like any other parameter, and
never becomes process-wide state -- one Streamlit server serves many browsers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from rim.rotation import APP_CROP_CODE

FORMAT = "rim-online-options"
FORMAT_VERSION = 1

# The slot a user can name, and the Calcs row it overrides.
SLOT_ROWS: dict[str, int] = {
    "spring_1": 85,
    "spring_2": 86,
    "harvest_1": 96,
    "harvest_2": 97,
}

# Which strategy decision each slot belongs to, for error messages.
SLOT_FIELDS: dict[str, str] = {
    "spring_1": "spring_others",
    "spring_2": "spring_others",
    "harvest_1": "harvest_others",
    "harvest_2": "harvest_others",
}


class CustomOptionError(ValueError):
    """The file is not a usable options pack. The message says why."""


def _per_crop(raw: Any, *, slot: str, what: str,
              low: float, high: float) -> dict[int, float] | None:
    """A ``default`` plus per-crop exceptions, resolved to every crop code."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        raw = {"default": raw}
    if not isinstance(raw, Mapping):
        raise CustomOptionError(
            f"{slot}: {what} should be a number, or an object with a "
            f"'default' and any per-crop exceptions."
        )

    unknown = [key for key in raw if key != "default" and key not in APP_CROP_CODE]
    if unknown:
        raise CustomOptionError(
            f"{slot}: {what} names crops this model does not have: "
            f"{', '.join(sorted(unknown))}. Use one of "
            f"{', '.join(sorted(APP_CROP_CODE))}."
        )

    if "default" not in raw:
        raise CustomOptionError(f"{slot}: {what} needs a 'default'.")

    def number(value: Any, where: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CustomOptionError(f"{slot}: {what} for {where} is not a number.")
        if not low <= float(value) <= high:
            raise CustomOptionError(
                f"{slot}: {what} for {where} is {value}, outside {low} to {high}."
            )
        return float(value)

    default = number(raw["default"], "default")
    out = {code: default for code in APP_CROP_CODE.values()}
    for crop, value in raw.items():
        if crop != "default":
            out[APP_CROP_CODE[crop]] = number(value, crop)
    return out


def parse(payload: Any) -> dict[int, dict]:
    """Validate one options pack, returning overrides keyed by Calcs row.

    Raises :class:`CustomOptionError` with a message aimed at whoever wrote the
    file. Anything not overridden is simply absent, and the workbook's own value
    stands.
    """
    if not isinstance(payload, Mapping):
        raise CustomOptionError("The file should hold a JSON object.")
    if payload.get("format") != FORMAT:
        raise CustomOptionError(
            f"This is not a RIM Online options file (expected \"format\": "
            f"\"{FORMAT}\")."
        )
    version = payload.get("version", 1)
    if not isinstance(version, int) or version > FORMAT_VERSION:
        raise CustomOptionError(
            f"That file is version {version}; this build reads up to "
            f"{FORMAT_VERSION}."
        )

    options = payload.get("options")
    if not isinstance(options, Mapping) or not options:
        raise CustomOptionError("The file defines no options.")

    unknown = [slot for slot in options if slot not in SLOT_ROWS]
    if unknown:
        raise CustomOptionError(
            f"Unknown slot(s): {', '.join(sorted(unknown))}. RIM has four: "
            f"{', '.join(SLOT_ROWS)}."
        )

    out: dict[int, dict] = {}
    for slot, spec in options.items():
        if not isinstance(spec, Mapping):
            raise CustomOptionError(f"{slot}: should be an object.")

        override: dict[str, Any] = {}
        name = spec.get("name")
        if name is not None:
            if not isinstance(name, str) or not name.strip():
                raise CustomOptionError(f"{slot}: 'name' should be a non-empty string.")
            override["name"] = name.strip()

        control = _per_crop(spec.get("control"), slot=slot, what="control",
                            low=0.0, high=1.0)
        if control is not None:
            override["control"] = control

        cost = _per_crop(spec.get("cost_per_ha"), slot=slot, what="cost_per_ha",
                         low=0.0, high=100_000.0)
        if cost is not None:
            override["cost"] = cost

        if not override:
            raise CustomOptionError(
                f"{slot}: defines nothing. Give it a name, a control or a cost."
            )
        out[SLOT_ROWS[slot]] = override

    return out


def load(path: str | Path) -> dict[int, dict]:
    """Read and validate an options pack from disk."""
    target = Path(path)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CustomOptionError(f"{target} does not exist.") from None
    except UnicodeDecodeError:
        raise CustomOptionError(f"{target} is not UTF-8 text.") from None
    except json.JSONDecodeError as exc:
        raise CustomOptionError(f"{target} is not readable JSON: {exc}.") from None
    return parse(payload)


def describe(overrides: Mapping[int, dict]) -> list[str]:
    """One line per slot, for showing back what was loaded."""
    rows_to_slot = {row: slot for slot, row in SLOT_ROWS.items()}
    lines = []
    for row, override in sorted(overrides.items()):
        parts = []
        if "control" in override:
            values = set(override["control"].values())
            parts.append(
                f"control {min(values):.0%}" if len(values) == 1
                else f"control {min(values):.0%}-{max(values):.0%}"
            )
        if "cost" in override:
            values = set(override["cost"].values())
            parts.append(
                f"${min(values):,.2f}/ha" if len(values) == 1
                else f"${min(values):,.2f}-${max(values):,.2f}/ha"
            )
        name = override.get("name", rows_to_slot.get(row, str(row)))
        lines.append(f"{name} — {', '.join(parts) if parts else 'name only'}")
    return lines
