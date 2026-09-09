"""The hand-editable narrative sheet.

`exposure_tiers.py` holds the drafted defaults. This module round-trips them
through `data/narratives.csv` so they can be edited in a spreadsheet:

    python -m cpi_diesel.narratives --export     # write the sheet
    ...edit data/narratives.csv...
    python -m cpi_diesel.build                   # picks the edits up

Once the CSV exists it is the source of truth and silently overrides the
Python defaults, so an edit never needs a code change. Delete the file to fall
back to the drafted text.

Written with a UTF-8 BOM so Excel opens the accented characters correctly
without an import dialog; read back with utf-8-sig so the BOM round-trips.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict

from . import config, exposure_tiers, parse
from .exposure_tiers import Assignment

CSV_PATH = config.DATA_DIR / "narratives.csv"

# weight and major_group are written for context while editing and ignored on
# read -- they are derived from BLS and must not be editable here.
FIELDS = ["major_group", "item_name", "weight", "tier", "intensity", "narrative"]
EDITABLE = {"tier", "intensity", "narrative"}


def _ordered_categories():
    nodes = parse.build_tree()
    categories = parse.cut(nodes)
    from .transform import MAJOR_ORDER
    return sorted(
        ((parse.major_group(nodes, n), n) for n in categories),
        key=lambda pair: (MAJOR_ORDER.index(pair[0]), -pair[1].cpi_u),
    )


def export(path: Path = None, force: bool = False) -> Path:
    """Write the editable sheet. Refuses to clobber existing edits."""
    path = path or CSV_PATH
    if path.exists() and not force:
        raise SystemExit(
            f"{path} already exists and holds your edits. Pass --force to "
            f"overwrite it with the drafted defaults from exposure_tiers.py."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for group, node in _ordered_categories():
            assignment = exposure_tiers.lookup(node.name)
            writer.writerow({
                "major_group": group,
                "item_name": node.name,
                "weight": f"{node.cpi_u:.3f}",
                "tier": assignment.tier,
                "intensity": assignment.intensity,
                "narrative": assignment.narrative,
            })
    return path


def load(path: Path = None) -> Dict[str, Assignment]:
    """Read the sheet back. Empty dict when there is none.

    Validated hard rather than merged loosely: a typo in an item name or a
    tier key means the chart would quietly fall back to drafted text for that
    row, which is exactly the kind of silent wrong answer this project keeps
    asserting its way out of.
    """
    path = path or CSV_PATH
    if not path.exists():
        return {}

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    missing_cols = set(FIELDS) - set(rows[0] if rows else {})
    if missing_cols:
        raise ValueError(f"{path} is missing column(s): {sorted(missing_cols)}")

    expected = {node.name for _, node in _ordered_categories()}
    seen, out = set(), {}
    problems = []

    for i, row in enumerate(rows, start=2):
        name = (row.get("item_name") or "").strip()
        if not name:
            continue
        if name not in expected:
            problems.append(f"row {i}: {name!r} is not a CPI category in the cut")
            continue
        if name in seen:
            problems.append(f"row {i}: {name!r} appears more than once")
            continue
        seen.add(name)

        tier = (row.get("tier") or "").strip()
        if tier not in exposure_tiers.TIERS:
            problems.append(
                f"row {i}: tier {tier!r} is not one of "
                f"{sorted(exposure_tiers.TIERS)}"
            )
            continue
        try:
            intensity = float(row.get("intensity") or 0)
        except ValueError:
            problems.append(f"row {i}: intensity {row.get('intensity')!r} is not a number")
            continue
        if not 0 <= intensity <= 1:
            problems.append(f"row {i}: intensity {intensity} is outside 0-1")
            continue

        narrative = (row.get("narrative") or "").strip()
        if len(narrative) < 20:
            problems.append(f"row {i}: narrative for {name!r} is empty or too short")
            continue

        out[name] = Assignment(tier, intensity, narrative)

    absent = expected - seen
    if absent:
        problems.append(f"{len(absent)} category(ies) missing from the sheet: "
                        f"{sorted(absent)[:5]}")
    if problems:
        raise ValueError(
            f"{path} has {len(problems)} problem(s):\n  "
            + "\n  ".join(problems)
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true",
                        help="write data/narratives.csv from the Python defaults")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing sheet, discarding edits")
    parser.add_argument("--check", action="store_true",
                        help="validate the sheet without building anything")
    args = parser.parse_args()

    if args.export:
        path = export(force=args.force)
        print(f"wrote {path.relative_to(config.ROOT)} "
              f"({sum(1 for _ in _ordered_categories())} categories)")
        return 0

    overrides = load()
    if not overrides:
        print(f"no {CSV_PATH.relative_to(config.ROOT)} yet — "
              f"run with --export to create one")
        return 0
    print(f"{CSV_PATH.relative_to(config.ROOT)} is valid: "
          f"{len(overrides)} categories")
    changed = [
        name for name, a in overrides.items()
        if a != exposure_tiers.lookup(name)
    ]
    print(f"{len(changed)} differ from the drafted defaults")
    for name in changed[:10]:
        print(f"  edited: {name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
