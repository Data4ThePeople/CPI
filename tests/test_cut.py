"""Guardrails on the mutually exclusive cut.

Each test catches a different way a revised BLS vintage could silently produce
a wrong chart. Run with: PYTHONPATH=src .venv/bin/python -m pytest -q
(or without pytest: python -m tests.test_cut)
"""
from __future__ import annotations

from cpi_diesel import config, exposure_tiers, parse
from cpi_diesel.transform import build_payload

NODES = parse.build_tree()
CUT = parse.cut(NODES)
PAYLOAD = build_payload()


def test_expenditure_section_only():
    """The special aggregates overlap the tree and must never be parsed in."""
    assert len(NODES) == config.EXPECTED_NODES
    names = {n.name for n in NODES}
    assert config.STOP_SECTION not in names


def test_cut_sums_to_100():
    """The whole 'mutually exclusive' claim, made checkable."""
    total = sum(n.cpi_u for n in CUT)
    assert abs(total - 100.0) <= config.TOLERANCE, total


def test_no_category_contains_another():
    """No item in the cut may be an ancestor of any other."""
    chosen = {n.idx for n in CUT}
    for node in CUT:
        parent = node.parent
        while parent is not None:
            assert parent not in chosen, f"{node.name} is nested inside another category"
            parent = NODES[parent].parent


def test_anchor_weights():
    """The two numbers the entire comparison rests on."""
    by_name = {n.name: n.cpi_u for n in CUT}
    for name, expected in config.ANCHORS.items():
        assert abs(by_name[name] - expected) < 0.001, (name, by_name[name])


def test_gasoline_and_diesel_are_separate_tiles():
    """A depth-3 cut alone would collapse both into 'Motor fuel'."""
    names = {n.name for n in CUT}
    assert "Gasoline (all types)" in names
    assert "Other motor fuels" in names
    assert "Motor fuel" not in names


def test_every_category_has_a_tier_and_narrative():
    for node in CUT:
        assignment = exposure_tiers.lookup(node.name)
        assert assignment.tier in exposure_tiers.TIERS
        assert len(assignment.narrative) > 40, node.name


def test_no_orphan_assignments():
    """An assignment for a category not in the cut is a stale edit."""
    extra = set(exposure_tiers.EXPOSURE) - {n.name for n in CUT}
    assert not extra, extra


def test_parent_child_sums_after_indent_fixes():
    """build_tree raises on mismatch; this pins the reason it passes."""
    for node in NODES:
        if node.kids:
            total = sum(NODES[k].cpi_u for k in node.kids)
            assert abs(total - node.cpi_u) <= config.TOLERANCE, node.name


def test_jet_fuel_and_grid_power_excluded_from_diesel():
    """Airline fares and electricity are fuel-exposed, but not to diesel."""
    by_name = {r["item_name"]: r for r in PAYLOAD["records"]}
    assert by_name["Airline fares"]["diesel_exposed"] is False
    assert by_name["Energy services"]["diesel_exposed"] is False
    assert by_name["Gasoline (all types)"]["diesel_exposed"] is False


def test_summary_is_internally_consistent():
    s = PAYLOAD["summary"]
    exposed = sum(r["weight"] for r in PAYLOAD["records"] if r["diesel_exposed"])
    assert abs(exposed - s["exposed_weight"]) < 0.01
    assert s["exposed_weight"] > s["gasoline_direct"] * 10


if __name__ == "__main__":
    import sys
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok    {name}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL  {name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)


def test_narrative_sheet_covers_the_cut_exactly():
    """data/narratives.csv is the editable source of truth; keep it in sync."""
    from cpi_diesel import narratives
    sheet = narratives.load()
    if not sheet:
        return  # no sheet exported yet; the Python defaults are in use
    assert set(sheet) == {n.name for n in CUT}


def test_sheet_edits_win_over_python_defaults():
    """The whole point of the sheet: an edit must reach the chart."""
    from cpi_diesel import narratives
    sheet = narratives.load()
    if not sheet:
        return
    by_name = {r["item_name"]: r for r in PAYLOAD["records"]}
    for name, assignment in sheet.items():
        assert by_name[name]["narrative"] == assignment.narrative, name
        assert by_name[name]["tier"] == assignment.tier, name
