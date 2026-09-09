"""Read the BLS relative importance XLSX into a validated item tree.

Stdlib only. The published file is a plain xlsx, so zipfile + ElementTree over
sharedStrings.xml and the first worksheet reads it completely -- no pandas, no
openpyxl, and nothing that would push this project off the 3.9 interpreter in
.venv.
"""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from . import config

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


class Node:
    """One row of the expenditure tree."""

    __slots__ = ("idx", "level", "name", "cpi_u", "cpi_w", "parent", "kids")

    def __init__(self, idx: int, level: int, name: str, cpi_u: float,
                 cpi_w: Optional[float]) -> None:
        self.idx = idx
        self.level = level
        self.name = name
        self.cpi_u = cpi_u
        self.cpi_w = cpi_w
        self.parent: Optional[int] = None
        self.kids: List[int] = []

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Node L{self.level} {self.name!r} {self.cpi_u}>"


def _cells(path) -> List[Dict[str, str]]:
    """Worksheet rows as {column letter: value}, shared strings resolved."""
    with zipfile.ZipFile(path) as z:
        strings = [
            "".join(t.text or "" for t in si.iter(NS + "t"))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si")
        ]
        sheet = ET.fromstring(z.read(config.SHEET))

    rows = []
    for row in sheet.iter(NS + "row"):
        record = {}
        for cell in row.iter(NS + "c"):
            ref = cell.get("r") or ""
            column = "".join(ch for ch in ref if ch.isalpha())
            value = cell.find(NS + "v")
            if value is None or value.text is None:
                continue
            record[column] = (
                strings[int(value.text)] if cell.get("t") == "s" else value.text
            )
        rows.append(record)
    return rows


def _expenditure_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Slice out the mutually exclusive expenditure tree.

    Everything from the "All items" root under "Expenditure category" up to,
    but not including, the "Special aggregate indexes" header. The special
    aggregates overlap the tree rather than partitioning it, so letting them
    through would double-count without any visible symptom.
    """
    start = stop = None
    for i, record in enumerate(rows):
        name = record.get("B")
        if name == config.START_SECTION and start is None:
            # The root "All items = 100" sits just below the section header.
            for j in range(i + 1, len(rows)):
                if rows[j].get("B") == config.ROOT_ITEM:
                    start = j + 1
                    break
        elif name == config.STOP_SECTION and start is not None:
            stop = i
            break
    if start is None or stop is None:
        raise ValueError(
            "could not locate the expenditure-category section; the published "
            "table layout has changed"
        )
    return [
        r for r in rows[start:stop]
        if "A" in r and "B" in r and "C" in r
    ]


def _apply_indent_fixes(rows: List[List]) -> None:
    """Correct the two mis-indented rows, carrying whole subtrees.

    See config.INDENT_FIXES for the evidence behind each. A node's subtree is
    every following row with a strictly greater indent level, so shifting the
    node without shifting them would leave children at or above their parent
    and silently reparent them as siblings.
    """
    for i, row in enumerate(rows):
        target = config.INDENT_FIXES.get(row[1])
        if target is None or row[0] == target:
            continue
        delta = target - row[0]
        original = row[0]
        row[0] = target
        for follower in rows[i + 1:]:
            if follower[0] <= original:
                break
            follower[0] += delta


def build_tree(path=None) -> List[Node]:
    """Parse, patch and validate the item tree. Returns nodes in file order."""
    path = path or config.RI_LOCAL
    raw = _expenditure_rows(_cells(path))

    rows = [
        [int(r["A"]), r["B"], float(r["C"]),
         float(r["D"]) if r.get("D") else None]
        for r in raw
    ]
    if len(rows) != config.EXPECTED_NODES:
        raise ValueError(
            f"expected {config.EXPECTED_NODES} expenditure nodes, got "
            f"{len(rows)}; the published table has changed shape"
        )

    _apply_indent_fixes(rows)

    nodes: List[Node] = []
    stack: List[int] = []
    for idx, (level, name, cpi_u, cpi_w) in enumerate(rows):
        while stack and nodes[stack[-1]].level >= level:
            stack.pop()
        node = Node(idx, level, name, cpi_u, cpi_w)
        if stack:
            node.parent = stack[-1]
            nodes[stack[-1]].kids.append(idx)
        nodes.append(node)
        stack.append(idx)

    _validate(nodes)
    return nodes


def _validate(nodes: List[Node]) -> None:
    """Every parent must equal the sum of its children.

    This is what caught both published indent defects. Keeping it as a hard
    failure means a future BLS revision that reshapes the tree stops the build
    instead of quietly producing a chart that no longer sums to 100.
    """
    broken = []
    for node in nodes:
        if not node.kids:
            continue
        total = sum(nodes[k].cpi_u for k in node.kids)
        if abs(total - node.cpi_u) > config.TOLERANCE:
            broken.append((node.name, node.cpi_u, round(total, 3)))
    if broken:
        raise ValueError(f"parent/child weight mismatches after fixes: {broken}")


def major_group(nodes: List[Node], node: Node) -> str:
    """The level-1 ancestor: one of the eight top-level CPI groups."""
    while node.level > 1:
        node = nodes[node.parent]
    return node.name


def cut(nodes: List[Node], depth: int = None,
        splits: tuple = None) -> List[Node]:
    """The mutually exclusive category set.

    Truncate the tree at `depth` -- take every node at depth <= depth with no
    children at depth <= depth -- then push the configured items one level
    further. The result sums to 100 by construction; build.py asserts it.
    """
    depth = config.CUT_DEPTH if depth is None else depth
    splits = config.SPLIT_ITEMS if splits is None else splits

    truncated = [
        n for n in nodes
        if n.level <= depth
        and not any(nodes[k].level <= depth for k in n.kids)
    ]
    out: List[Node] = []
    for node in truncated:
        if node.name in splits and node.kids:
            out.extend(nodes[k] for k in node.kids)
        else:
            out.append(node)
    return out
