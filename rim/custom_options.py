"""Spring and harvest options a user defines, loaded from a JSON file.

RIM keeps four slots a user can define themselves -- two spring, two harvest
(``1.Profile`` C32:C35, ``Calcs`` rows 85, 86, 96 and 97). That four is a
spreadsheet limit, not a model limit: those cells are four cells, and those rows
are four rows. Nothing in the biology or the economics cares how many there are,
because ``spring_others`` and ``harvest_others`` are each a *single* column on
``2.Strategy`` -- only one can be chosen in any year regardless. So here there is
no cap. More options means a longer dropdown, not a wider model.

Options are described in a file rather than typed into the browser, which is the
better place for them: a file can be version-controlled, shared with a
colleague, reviewed, and replayed by the command-line runner with no browser at
all.

The file looks like this::

    {
      "format": "rim-online-options",
      "version": 2,
      "options": [
        {"for": "spring", "name": "Spring grazing crash",
         "control": {"default": 0.55, "Canola": 0.0},
         "cost_per_ha": {"default": 12.0}},
        {"for": "harvest", "name": "Weed seed impact mill",
         "control": {"default": 0.95},
         "cost_per_ha": {"default": 30.0, "Legume crop": 26.0}}
      ]
    }

``control`` is the share of germinated ryegrass the option kills, 0 to 1;
``cost_per_ha`` is dollars per hectare. Both take a ``default`` plus any per-crop
exceptions, keyed by the crop names the app uses, and both are required -- there
is no workbook row behind a defined option to inherit from.

A control of 0 for a crop means the option does nothing there, which is how the
rest of the app already reads the workbook's own zeros: it stops offering the
option for that crop rather than charging for something inert.

**Defining any spring options replaces the workbook's two spring placeholders**,
and likewise for harvest. The placeholders were only ever stand-ins for this.

The older keyed form is still read::

    "options": {"spring_1": {"name": "...", "control": 0.6}}

There, ``spring_1`` and ``spring_2`` mean rows 85 and 86 and ``harvest_1`` /
``harvest_2`` mean 96 and 97, and anything left unset keeps that row's own
workbook value. It is translated into the same shape as the list form, so
nothing downstream has to know which form a file used.

The parsed pack travels in the options bundle, under ``custom_options``, so it
saves with the scenario, passes to the engine like any other parameter, and
never becomes process-wide state -- one Streamlit server serves many browsers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from rim.rotation import APP_CROP_CODE

FORMAT = "rim-online-options"

# 1 was the four keyed slots; 2 added the list form and lifted the cap.
FORMAT_VERSION = 2

# The two decisions a user can define options for, and the word the file uses.
FIELD_FOR: dict[str, str] = {
    "spring": "spring_others",
    "harvest": "harvest_others",
}
FIELDS: tuple[str, ...] = tuple(FIELD_FOR.values())

# The keyed form's slot names, and the Calcs row each one overrides.
SLOT_ROWS: dict[str, int] = {
    "spring_1": 85,
    "spring_2": 86,
    "harvest_1": 96,
    "harvest_2": 97,
}

# A dropdown longer than this is unusable, and wanting one is a sign the user
# wants a tool that builds packs rather than a longer list. Not enforced.
MANY_OPTIONS = 20


class CustomOptionError(ValueError):
    """The file is not a usable options pack. The message says why."""


def _per_crop(raw: Any, *, where: str, what: str,
              low: float, high: float) -> dict[int, float] | None:
    """A ``default`` plus per-crop exceptions, resolved to every crop code."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        raw = {"default": raw}
    if not isinstance(raw, Mapping):
        raise CustomOptionError(
            f"{where}: {what} should be a number, or an object with a "
            f"'default' and any per-crop exceptions."
        )

    unknown = [key for key in raw if key != "default" and key not in APP_CROP_CODE]
    if unknown:
        raise CustomOptionError(
            f"{where}: {what} names crops this model does not have: "
            f"{', '.join(sorted(unknown))}. Use one of "
            f"{', '.join(sorted(APP_CROP_CODE))}."
        )

    if "default" not in raw:
        raise CustomOptionError(f"{where}: {what} needs a 'default'.")

    def number(value: Any, crop: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CustomOptionError(f"{where}: {what} for {crop} is not a number.")
        if not low <= float(value) <= high:
            raise CustomOptionError(
                f"{where}: {what} for {crop} is {value}, outside {low} to {high}."
            )
        return float(value)

    default = number(raw["default"], "default")
    out = {code: default for code in APP_CROP_CODE.values()}
    for crop, value in raw.items():
        if crop != "default":
            out[APP_CROP_CODE[crop]] = number(value, crop)
    return out


def _control(raw: Any, where: str) -> dict[int, float] | None:
    return _per_crop(raw, where=where, what="control", low=0.0, high=1.0)


def _cost(raw: Any, where: str) -> dict[int, float] | None:
    return _per_crop(raw, where=where, what="cost_per_ha", low=0.0, high=100_000.0)


def _name(raw: Any, where: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise CustomOptionError(f"{where}: 'name' should be a non-empty string.")
    return raw.strip()


def _from_list(entries: list, *, version: int) -> dict[str, list[dict]]:
    """The list form: any number of options, each saying what it is for."""
    if version < 2:
        raise CustomOptionError(
            "A list of options needs \"version\": 2. Version 1 files use the "
            f"four named slots: {', '.join(SLOT_ROWS)}."
        )

    out: dict[str, list[dict]] = {field: [] for field in FIELDS}
    for position, entry in enumerate(entries, start=1):
        where = f"option {position}"
        if not isinstance(entry, Mapping):
            raise CustomOptionError(f"{where}: should be an object.")

        kind = entry.get("for")
        if kind not in FIELD_FOR:
            raise CustomOptionError(
                f"{where}: 'for' should be {' or '.join(repr(k) for k in FIELD_FOR)}, "
                f"not {kind!r}."
            )
        where = f"{kind} option {position}"

        name = _name(entry.get("name"), where)
        control = _control(entry.get("control"), where)
        cost = _cost(entry.get("cost_per_ha"), where)
        if control is None:
            raise CustomOptionError(f"{where}: needs a 'control'.")
        if cost is None:
            raise CustomOptionError(f"{where}: needs a 'cost_per_ha'.")

        out[FIELD_FOR[kind]].append({"name": name, "control": control, "cost": cost})

    duplicates = [
        f"{field}: {name}"
        for field, specs in out.items()
        for name in {s["name"] for s in specs}
        if [s["name"] for s in specs].count(name) > 1
    ]
    if duplicates:
        raise CustomOptionError(
            f"Two options share a name, so one could never be chosen: "
            f"{', '.join(sorted(set(duplicates)))}."
        )
    return {field: specs for field, specs in out.items() if specs}


def _from_slots(slots: Mapping) -> dict[str, list[dict]]:
    """The keyed form: up to four slots, patching the workbook's own rows."""
    from rim import control_options

    unknown = [slot for slot in slots if slot not in SLOT_ROWS]
    if unknown:
        raise CustomOptionError(
            f"Unknown slot(s): {', '.join(sorted(unknown))}. The named slots are "
            f"{', '.join(SLOT_ROWS)}. To define more than four, use a list of "
            f"options with \"version\": {FORMAT_VERSION}."
        )

    overrides: dict[int, dict] = {}
    for slot, spec in slots.items():
        if not isinstance(spec, Mapping):
            raise CustomOptionError(f"{slot}: should be an object.")

        override: dict[str, Any] = {}
        if spec.get("name") is not None:
            override["name"] = _name(spec.get("name"), slot)
        control = _control(spec.get("control"), slot)
        if control is not None:
            override["control"] = control
        cost = _cost(spec.get("cost_per_ha"), slot)
        if cost is not None:
            override["cost"] = cost

        if not override:
            raise CustomOptionError(
                f"{slot}: defines nothing. Give it a name, a control or a cost."
            )
        overrides[SLOT_ROWS[slot]] = override

    # Anything a slot leaves unset keeps its own workbook value, so the four
    # rows are read here and the result is the same shape as the list form.
    out: dict[str, list[dict]] = {}
    for field in FIELDS:
        specs = []
        for option in control_options.options_for(field):
            if option.row not in overrides:
                continue
            override = overrides[option.row]
            specs.append({
                "name": override.get("name", option.name),
                "control": dict(override.get("control", option.control)),
                "cost": dict(override.get("cost", option.cost)),
                # This slot *is* that row, so a plan naming the placeholder
                # still resolves after the slot is renamed.
                "replaces": option.row,
            })
        if specs:
            out[field] = specs
    return out


def parse(payload: Any) -> dict[str, list[dict]]:
    """Validate one options pack into ``{field: [spec, ...]}``.

    A field present in the result replaces that decision's whole list; a field
    absent keeps the workbook's. Raises :class:`CustomOptionError` with a
    message aimed at whoever wrote the file.
    """
    if not isinstance(payload, Mapping):
        raise CustomOptionError("The file should hold a JSON object.")
    if payload.get("format") != FORMAT:
        raise CustomOptionError(
            f"This is not a RIM Online options file (expected \"format\": "
            f"\"{FORMAT}\")."
        )
    version = payload.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise CustomOptionError(f"'version' should be a whole number, not {version!r}.")
    if version > FORMAT_VERSION:
        raise CustomOptionError(
            f"That file is version {version}; this build reads up to "
            f"{FORMAT_VERSION}."
        )

    options = payload.get("options")
    if isinstance(options, list):
        parsed = _from_list(options, version=version)
    elif isinstance(options, Mapping):
        parsed = _from_slots(options)
    else:
        raise CustomOptionError(
            "'options' should be a list of options, or an object of named slots."
        )

    if not parsed:
        raise CustomOptionError("The file defines no options.")
    return parsed


def load(path: str | Path) -> dict[str, list[dict]]:
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


def describe(parsed: Mapping[str, list[dict]]) -> list[str]:
    """One line per option, for showing back what was loaded."""
    kinds = {field: kind for kind, field in FIELD_FOR.items()}

    def span(values, fmt: str) -> str:
        low, high = min(values), max(values)
        return fmt.format(low) if low == high else f"{fmt.format(low)}–{fmt.format(high)}"

    lines = []
    for field, specs in parsed.items():
        for spec in specs:
            parts = [
                span(spec["control"].values(), "{:.0%}") + " control",
                span(spec["cost"].values(), "${:,.2f}") + "/ha",
            ]
            lines.append(f"{spec['name']} ({kinds.get(field, field)}) — "
                         + ", ".join(parts))
    return lines
