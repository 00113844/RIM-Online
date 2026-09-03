"""Run RIM scenarios from the command line, with no browser involved.

Everything the model does used to be reachable only through Streamlit, which
made three things awkward: comparing several farms, regression-testing the app's
numbers against the workbook, and reproducing a report from the ``.rim.json``
someone sent you. This runs the same engine the app runs, on the same files the
app writes.

    python -m tools.run_scenario broomehill.rim.json
    python -m tools.run_scenario scenarios/*.rim.json --out results/
    python -m tools.run_scenario a.rim.json b.rim.json --format csv
    python -m tools.run_scenario plan.rim.json --options my-options.json

With no file at all it runs the shipped default paddock and plan, which is a
quick way to see that an install works.

Nothing here knows about Streamlit, and nothing here does model arithmetic: it
reads scenarios with :mod:`rim.scenario`, checks them with
:mod:`utils.applicability`, and simulates with ``rim.engine``. New outputs
belong in :func:`write`, new inputs in :mod:`rim.scenario` -- keeping those apart
is what stops this becoming the second place that knows the save format.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Sequence

from rim import scenario as scenarios
from rim.engine import simulate_strategy
from rim.scenario import Scenario, ScenarioError

FORMATS = ("table", "csv", "json", "excel")


def simulate(scenario: Scenario) -> dict:
    """Run one scenario through the same engine the app uses."""
    return simulate_strategy(
        profile=scenario.profile,
        prices=scenario.prices,
        options=scenario.options,
        strategy_rows=scenario.strategy,
    )


def check(scenario: Scenario) -> list[dict]:
    """Decisions the model cannot act on, the same ones the app blocks."""
    from utils.validation import problems

    return problems(scenario.strategy, scenario.custom_options)


def summarise(name: str, result: dict) -> dict:
    """The headline numbers, flat enough to put in a row of a table."""
    summary = result["summary"]
    yearly = result["yearly"]
    return {
        "scenario": name,
        "years": len(yearly),
        "avg_gross_margin": summary.get("avg_gross_margin"),
        "nominal_annuity": summary.get("nominal_annuity"),
        "avg_weed_control_cost": summary.get("avg_weed_control_cost"),
        "seed_bank_start": float(yearly["seed_bank_start"].iloc[0]),
        "seed_bank_end": float(yearly["seed_bank_end"].iloc[-1]),
    }


def _table(rows: Sequence[dict]) -> str:
    """A plain aligned table -- no dependency, and it pastes into an email."""
    if not rows:
        return "(nothing to report)"
    columns = list(rows[0])

    def cell(value) -> str:
        if isinstance(value, float):
            return f"{value:,.2f}"
        return "" if value is None else str(value)

    widths = {
        column: max(len(column), *(len(cell(row[column])) for row in rows))
        for column in columns
    }
    line = "  ".join(column.replace("_", " ").ljust(widths[column])
                     for column in columns)
    rule = "  ".join("-" * widths[column] for column in columns)
    body = [
        "  ".join(cell(row[column]).ljust(widths[column]) for column in columns)
        for row in rows
    ]
    return "\n".join([line, rule, *body])


def write(results: dict[str, dict], summaries: list[dict], *,
          fmt: str, out: Path | None) -> str:
    """Render the run. Returns whatever should go to stdout."""
    if fmt == "table":
        rendered = _table(summaries)
        if out is not None:
            (out / "summary.txt").write_text(rendered + "\n", encoding="utf-8")
        return rendered

    if fmt == "json":
        payload = {
            "summaries": summaries,
            "yearly": {name: result["yearly"].to_dict("records")
                       for name, result in results.items()},
        }
        rendered = json.dumps(payload, indent=2, default=str)
        if out is not None:
            (out / "results.json").write_text(rendered, encoding="utf-8")
            return f"Wrote {out / 'results.json'}"
        return rendered

    if out is None:
        raise SystemExit(f"--format {fmt} writes files, so it needs --out DIR.")

    if fmt == "csv":
        import pandas as pd

        pd.DataFrame(summaries).to_csv(out / "summary.csv", index=False)
        for name, result in results.items():
            result["yearly"].to_csv(out / f"{name}.csv", index=False)
        return f"Wrote {1 + len(results)} CSV files to {out}"

    if fmt == "excel":
        from utils.export import tables_to_excel_bytes
        import pandas as pd

        sheets = {"Summary": pd.DataFrame(summaries)}
        for name, result in results.items():
            sheets[name[:31]] = result["yearly"]
        target = out / "results.xlsx"
        target.write_bytes(tables_to_excel_bytes(sheets))
        return f"Wrote {target}"

    raise SystemExit(f"Unknown format {fmt!r}. Choose from {', '.join(FORMATS)}.")


def load_all(paths: Sequence[str], options_file: str | None) -> list[Scenario]:
    """Every scenario named on the command line, or the shipped default."""
    from rim import custom_options as custom

    overrides = custom.load(options_file) if options_file else None

    if not paths:
        payloads = [(scenarios.default().as_save_payload(), "default")]
    else:
        payloads = [(scenarios.read_payload(path), scenarios.name_for(path))
                    for path in paths]

    # An options file given here applies to every scenario in the run and
    # replaces anything a file carried, so a comparison is between plans rather
    # than between option sets. It has to go in before the payload is read: the
    # plan is canonicalised against the options, so a name defined here would
    # otherwise be unrecognised and cleared.
    if overrides is not None:
        injected = {str(row): spec for row, spec in overrides.items()}
        for payload, _ in payloads:
            options = dict(payload.get("options") or {})
            options["custom_options"] = injected
            payload["options"] = options

    return [scenarios.from_payload(payload, name=name) for payload, name in payloads]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.run_scenario",
        description="Run RIM scenarios without a browser.",
    )
    parser.add_argument("paths", nargs="*",
                        help=".rim.json files. With none, runs the shipped default.")
    parser.add_argument("--out", metavar="DIR",
                        help="Directory to write into. Created if missing.")
    parser.add_argument("--format", dest="fmt", default="table", choices=FORMATS,
                        help="table (default), csv, json or excel.")
    parser.add_argument("--options", metavar="FILE",
                        help="A custom options file to apply to every scenario.")
    parser.add_argument("--strict", action="store_true",
                        help="Stop if any plan holds a decision the model ignores.")
    parser.add_argument("--quiet", action="store_true",
                        help="Only report failures.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    out = Path(args.out) if args.out else None
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)

    try:
        loaded = load_all(args.paths, args.options)
    except ScenarioError as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 2
    except Exception as problem:            # a bad options file says why itself
        print(f"error: {problem}", file=sys.stderr)
        return 2

    results: dict[str, dict] = {}
    summaries: list[dict] = []
    unusable = 0

    for scenario in loaded:
        found = check(scenario)
        if found:
            unusable += 1
            where = "; ".join(
                f"year {problem['year']} {problem['field']} = {problem['choice']}"
                for problem in found[:4]
            )
            more = "" if len(found) <= 4 else f" (and {len(found) - 4} more)"
            print(f"warning: {scenario.name}: {len(found)} decision(s) the model "
                  f"ignores — {where}{more}", file=sys.stderr)
            if args.strict:
                continue

        results[scenario.name] = simulate(scenario)
        summaries.append(summarise(scenario.name, results[scenario.name]))

    if not results:
        print("error: nothing ran.", file=sys.stderr)
        return 1

    rendered = write(results, summaries, fmt=args.fmt, out=out)
    if not args.quiet and rendered:
        print(rendered)

    return 1 if (args.strict and unusable) else 0


if __name__ == "__main__":
    raise SystemExit(main())
