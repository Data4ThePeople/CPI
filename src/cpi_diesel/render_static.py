"""Static treemap for print and blog embedding.

    python -m cpi_diesel.render_static [--mode all|gasoline|diesel]

Writes SVG. Pure stdlib -- the same squarified layout the canvas renderer
uses, so the static image and the interactive page agree pixel for pixel in
proportion. Keeping it dependency-free means the whole project still runs on
the 3.9 interpreter in .venv with only Jinja2 installed.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List
from xml.sax.saxutils import escape

from . import config, fuel_prices
from .transform import MAJOR_ORDER, build_payload

W, H = 1600, 1000
PAD, GAP, HEADER = 28, 3, 22
TOP = 168          # masthead + scoreboard
BOTTOM = 132       # legend + footnote

PARCH, PANEL, INK, MUTED, GRID = "#faf3df", "#f4ead2", "#2b2317", "#6b5d3f", "#cdbb96"
DIM = "#ece4cd"
TIER_COLOR = {
    "light_freight": "#cfe0e8", "freight_dependent_service": "#a8c6d4",
    "heavy_freight": "#7aa7bd", "cold_chain": "#4d84a3",
    "diesel_service": "#2e6485", "direct_diesel": "#17455f",
    "gasoline_direct": "#712b13", "other_fuel": "#b9a06a", "none": "#e2dac4",
}
LIGHT_TYPE = {"direct_diesel", "diesel_service", "cold_chain", "gasoline_direct"}
LEGEND_ORDER = [
    "direct_diesel", "diesel_service", "cold_chain", "heavy_freight",
    "freight_dependent_service", "light_freight", "gasoline_direct",
    "other_fuel", "none",
]
SERIF = "Georgia, 'Times New Roman', serif"


def _worst(row, side, scale):
    total = sum(n["weight"] * scale for n in row)
    lo = min(n["weight"] * scale for n in row)
    hi = max(n["weight"] * scale for n in row)
    return max(side * side * hi / (total * total), total * total / (side * side * lo))


def squarify(nodes: List[Dict], x, y, w, h) -> List[Dict]:
    """Bruls/Huizing/van Wijk squarified treemap. Mirrors static/treemap.js."""
    out = []
    items = sorted(nodes, key=lambda n: -n["weight"])
    total = sum(n["weight"] for n in items)
    if total <= 0 or w <= 0 or h <= 0:
        return out
    scale = (w * h) / total

    i = 0
    while i < len(items):
        side = min(w, h)
        row = [items[i]]
        i += 1
        while i < len(items) and _worst(row + [items[i]], side, scale) <= _worst(row, side, scale):
            row.append(items[i])
            i += 1
        thickness = sum(n["weight"] * scale for n in row) / side
        offset = 0.0
        for node in row:
            length = (node["weight"] * scale) / thickness
            if w >= h:
                out.append({"node": node, "x": x, "y": y + offset, "w": thickness, "h": length})
            else:
                out.append({"node": node, "x": x + offset, "y": y, "w": length, "h": thickness})
            offset += length
        if w >= h:
            x += thickness
            w -= thickness
        else:
            y += thickness
            h -= thickness
    return out


def _grouped(payload) -> List[Dict]:
    """Groups with sub-threshold residuals pooled, matching the canvas view."""
    out = []
    for group in MAJOR_ORDER:
        mine = [r for r in payload["records"] if r["major_group"] == group]
        items = [r for r in mine if r["weight"] >= config.SLIVER_THRESHOLD]
        small = [r for r in mine if r["weight"] < config.SLIVER_THRESHOLD]
        if small:
            items = items + [{
                "display_name": "Other small items",
                "weight": round(sum(r["weight"] for r in small), 3),
                "tier": small[0]["tier"],
                "diesel_exposed": all(r["diesel_exposed"] for r in small),
            }]
        out.append({
            "name": group,
            "weight": sum(r["weight"] for r in mine),
            "items": sorted(items, key=lambda r: -r["weight"]),
        })
    return out


def _text(x, y, s, size=13, fill=INK, weight="normal", anchor="start", opacity=1.0):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SERIF}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
        f'opacity="{opacity}">{escape(s)}</text>'
    )


def _tw(s: str, size: float) -> float:
    """Approximate rendered width. Georgia averages ~0.50 em across mixed case;
    0.54 is a deliberate overestimate so labels never overflow their tile."""
    return len(s) * size * 0.54


def _tw_digits(s: str, size: float) -> float:
    """Width of a price string.

    Georgia's bold numerals are old-style and wide; 0.62 em per figure and per
    dollar sign, 0.28 for the dot, calibrated against a rendered $5.96 rather
    than guessed. Underestimating here runs the following label into the price.
    """
    return sum(0.28 if c == "." else 0.62 for c in s) * size


def _tw_caps(s: str, size: float) -> float:
    """Width of an all-caps string. Georgia's capitals run ~0.72 em."""
    return len(s) * size * 0.72


def _fits(s: str, size: float, width: float) -> bool:
    return _tw(s, size) <= width


def _wrap(text: str, size: float, width: float, max_lines: int):
    """Greedy word wrap, or None if the text will not fit in max_lines."""
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if _fits(trial, size, width) or not current:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                return None
    if current:
        lines.append(current)
    if len(lines) > max_lines or any(not _fits(l, size, width) for l in lines):
        return None
    return lines


def render(mode: str = "all") -> Path:
    payload = build_payload()
    summary = payload["summary"]

    def lit(rec):
        if mode == "all":
            return True
        if mode == "gasoline":
            return rec["tier"] == "gasoline_direct"
        return rec.get("diesel_exposed", False)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{PARCH}"/>',
    ]

    # --- masthead -----------------------------------------------------------
    parts.append(_text(PAD, 48, "Gasoline gets the attention. Diesel gets everything else.",
                       size=34, weight="bold"))
    parts.append(_text(PAD, 76,
                       "Every mutually exclusive category in the Consumer Price Index, "
                       "sized by its published relative importance.",
                       size=16, fill=MUTED))

    # --- scoreboard ---------------------------------------------------------
    stats = [
        (f'{summary["gasoline_direct"]}%', "Gasoline, bought directly", TIER_COLOR["gasoline_direct"]),
        (f'{summary["diesel_direct"]}%',
         f'Diesel, bought directly — {summary["gasoline_over_diesel_direct"]}× smaller',
         TIER_COLOR["direct_diesel"]),
        (f'{summary["exposed_share"]}%',
         f'Of the index diesel reaches — {summary["reach_ratio"]}× gasoline',
         TIER_COLOR["direct_diesel"]),
    ]
    box_w = (W - PAD * 2 - 2 * 14) / 3
    for i, (num, label, color) in enumerate(stats):
        bx = PAD + i * (box_w + 14)
        parts.append(f'<rect x="{bx:.1f}" y="98" width="{box_w:.1f}" height="52" '
                     f'fill="{PANEL}" stroke="{GRID}" rx="3"/>')
        parts.append(_text(bx + 12, 126, num, size=27, weight="bold", fill=color))
        parts.append(_text(bx + 12, 143, label, size=11.5, fill=MUTED))

    # --- treemap ------------------------------------------------------------
    cx, cy = PAD, TOP
    cw, ch = W - PAD * 2, H - TOP - BOTTOM
    parts.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" '
                 f'fill="{PANEL}" stroke="{GRID}"/>')

    for cell in squarify(_grouped(payload), cx, cy, cw, ch):
        gx, gy = cell["x"] + GAP, cell["y"] + GAP
        gw, gh = max(0, cell["w"] - GAP * 2), max(0, cell["h"] - GAP * 2)
        head = min(HEADER, gh)

        for tile in squarify(cell["node"]["items"], gx, gy + head, gw, max(0, gh - head)):
            rec = tile["node"]
            on = lit(rec)
            fill = TIER_COLOR[rec["tier"]] if on else DIM
            parts.append(f'<rect x="{tile["x"]:.1f}" y="{tile["y"]:.1f}" '
                         f'width="{max(0, tile["w"] - 1):.1f}" '
                         f'height="{max(0, tile["h"] - 1):.1f}" fill="{fill}"/>')
            if rec["tier"] == "gasoline_direct" and mode != "diesel":
                parts.append(f'<rect x="{tile["x"] + 0.8:.1f}" y="{tile["y"] + 0.8:.1f}" '
                             f'width="{max(0, tile["w"] - 2.6):.1f}" '
                             f'height="{max(0, tile["h"] - 2.6):.1f}" fill="none" '
                             f'stroke="{INK}" stroke-width="1.6"/>')
            if not on or tile["w"] < 38 or tile["h"] < 20:
                continue
            color = PARCH if rec["tier"] in LIGHT_TYPE else INK
            avail_w, avail_h = tile["w"] - 10, tile["h"] - 8
            lines = size = None
            for candidate in (13, 12, 11, 10, 9, 8):
                room = int(avail_h // (candidate + 2))
                if room < 1:
                    continue
                lines = _wrap(rec["display_name"], candidate,
                              avail_w, min(3, room))
                if lines:
                    size = candidate
                    break
            if not lines:
                continue
            y = tile["y"] + size + 3
            for line in lines:
                parts.append(_text(tile["x"] + 5, y, line, size=size, fill=color))
                y += size + 2
            # The share only earns its place when the label already fits.
            if y + size <= tile["y"] + tile["h"] - 2:
                parts.append(_text(tile["x"] + 5, y, f'{rec["weight"]:.2f}%',
                                   size=size - 1, fill=color, opacity=0.75))

        if head >= 13:
            label = cell["node"]["name"]
            size = 13 if _fits(label, 13, gw - 56) else 11
            # A narrow group must not bleed into its neighbor.
            if not _fits(label, size, gw - 4):
                while len(label) > 1 and not _fits(label + "\u2026", size, gw - 4):
                    label = label[:-1]
                label += "\u2026"
            parts.append(_text(gx + 1, gy + head - 7, label, size=size, weight="bold"))
            share = f'{cell["node"]["weight"]:.1f}%'
            if _tw(label, size) + _tw(share, 11) + 14 <= gw:
                parts.append(_text(gx + gw - 1, gy + head - 7, share, size=11,
                                   fill=MUTED, anchor="end"))
            parts.append(f'<line x1="{gx:.1f}" y1="{gy + head - 2:.1f}" '
                         f'x2="{gx + gw:.1f}" y2="{gy + head - 2:.1f}" '
                         f'stroke="{GRID}"/>')

    # --- legend -------------------------------------------------------------
    ly = H - BOTTOM + 24
    tiers = {t["key"]: t for t in payload["tiers"]}
    col_w = (W - PAD * 2) / 3
    for i, key in enumerate(LEGEND_ORDER):
        lx = PAD + (i % 3) * col_w
        yy = ly + (i // 3) * 21
        weight = summary["by_tier"].get(key, {}).get("weight", 0.0)
        parts.append(f'<rect x="{lx:.1f}" y="{yy - 10:.1f}" width="13" height="13" '
                     f'fill="{TIER_COLOR[key]}" stroke="{GRID}" rx="2"/>')
        parts.append(_text(lx + 19, yy, tiers[key]["label"], size=12.5, weight="bold"))
        parts.append(_text(lx + col_w - 34, yy, f"{weight:.2f}%", size=12.5,
                           fill=MUTED, anchor="end"))

    parts.append(_text(
        PAD, H - 22,
        f'Diesel reaches {summary["exposed_share"]}% of the index as an input '
        f'cost. That is breadth — where diesel reaches, not how hard it pushes.',
        size=12, fill=MUTED))
    parts.append(_text(
        W - PAD, H - 22,
        f'Weights: {config.SOURCE_PUBLISHER}, relative importance, December {config.RI_YEAR}. '
        f'Exposure tiers are editorial.',
        size=12, fill=MUTED, anchor="end"))

    parts.append("</svg>")

    config.DIST_DIR.mkdir(parents=True, exist_ok=True)
    out = config.DIST_DIR / f"cpi_diesel_treemap_{mode}.svg"
    out.write_text("\n".join(parts))
    return out


# Social cards render at a few hundred pixels wide in a feed, where an 81-tile
# treemap is unreadable. The card carries the comparison alone, at a size that
# survives being shrunk. 1200x630 is the standard link-preview ratio.
CARD_W, CARD_H = 1200, 630


def render_card() -> Path:
    """The link-preview card: the two numbers, nothing else."""
    payload = build_payload()
    summary = payload["summary"]

    gas = TIER_COLOR["gasoline_direct"]
    dsl = TIER_COLOR["direct_diesel"]
    mid = CARD_W / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" '
        f'height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}">',
        f'<rect width="{CARD_W}" height="{CARD_H}" fill="{PARCH}"/>',
        # Two blocks, areas in the same ratio as the numbers, so the graphic
        # says what the figures say before anyone reads them.
        f'<rect x="64" y="300" width="{(summary["gasoline_direct"] / summary["exposed_share"]) * 440:.0f}" '
        f'height="26" fill="{gas}"/>',
        f'<rect x="{mid + 24:.0f}" y="300" width="440" height="26" fill="{dsl}"/>',
    ]
    parts.append(_text(64, 92, "Gasoline gets the attention.", size=44, weight="bold"))
    parts.append(_text(64, 146, "Diesel gets everything else.", size=44, weight="bold", fill=dsl))
    parts.append(_text(64, 190, "Share of the Consumer Price Index each fuel reaches",
                       size=21, fill=MUTED))

    parts.append(_text(64, 278, f'{summary["gasoline_direct"]:.1f}%', size=86,
                       weight="bold", fill=gas))
    parts.append(_text(64, 360, "GASOLINE", size=19, weight="bold", fill=INK))
    parts.append(_text(64, 386, "Bought directly. One line item.", size=18, fill=MUTED))

    parts.append(_text(mid + 24, 278, f'{summary["exposed_share"]}%', size=86,
                       weight="bold", fill=dsl))
    parts.append(_text(mid + 24, 360, "DIESEL", size=19, weight="bold", fill=INK))
    parts.append(_text(mid + 24, 386, "An input cost inside almost half the basket.",
                       size=18, fill=MUTED))

    parts.append(f'<line x1="64" y1="448" x2="{CARD_W - 64}" y2="448" stroke="{GRID}"/>')
    parts.append(_text(64, 492,
                       f'Diesel bought directly is just {summary["diesel_direct"]}% — '
                       f'{summary["gasoline_over_diesel_direct"]}x smaller than gasoline. '
                       f'It reaches the rest as freight.',
                       size=20, fill=INK))
    parts.append(_text(64, 534,
                       f'{config.PUBLISHER_NAME}  ·  Weights: {config.SOURCE_PUBLISHER}, '
                       f'relative importance, December {config.RI_YEAR}',
                       size=16, fill=MUTED))
    parts.append("</svg>")

    config.DIST_DIR.mkdir(parents=True, exist_ok=True)
    out = config.DIST_DIR / "cpi_diesel_card.svg"
    out.write_text("\n".join(parts))
    return out


# The type-scaled sign. Letter size carries the ratio between the two figures,
# so the graphic states the finding before anyone reads a number.
#
# Colors are the pump convention -- red gasoline, green diesel -- pushed off
# pure red/green, which is the exact axis red-green colorblindness runs along.
# The red goes warm and the green goes teal so the pair still separates under
# protanopia. Size is doing the work regardless; this is belt and braces.
SIGN_W, SIGN_H = 1200, 630
SIGN_BG = "#0d0f10"
SIGN_RED = "#f04a22"
SIGN_GREEN = "#12b981"
SIGN_DIM = "#8b8f92"


def render_sign(scale: str = "linear") -> Path:
    """A price sign where the diesel price is set ~15x the gasoline price.

    The claim is about attention, not about the prices: diesel touches 44.4%
    of the basket against gasoline's 2.9%, so the diesel number is roughly 15
    times more worth watching. The digits are sized to that ratio and the
    header says so, because 15x is emphatically *not* the ratio between the
    two prices.

    scale="linear" sets digit height to the ratio (~15x). scale="area" uses
    its square root (~4x), so digit *area* carries it, which is how eyes judge
    type and the same reason bubble charts size by area rather than radius.
    """
    payload = build_payload()
    summary = payload["summary"]
    prices = fuel_prices.latest()

    gas_pct = round(summary["gasoline_direct"], 1)
    diesel_pct = summary["exposed_share"]
    ratio = diesel_pct / gas_pct
    factor = ratio if scale == "linear" else ratio ** 0.5

    # Pump signs truncate rather than round -- $5.967 posts as 5.96 and 9/10.
    def posted(name: str) -> str:
        return f"${int(prices[name].dollars * 100) / 100:.2f}"

    margin = 54
    LABEL = 23.0

    big = 300.0
    while _tw_digits(posted("diesel"), big) > SIGN_W - margin * 2 and big > 40:
        big -= 4
    small = big / factor

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIGN_W}" '
        f'height="{SIGN_H}" viewBox="0 0 {SIGN_W} {SIGN_H}">',
        '<defs><filter id="glow" x="-30%" y="-30%" width="160%" height="160%">'
        '<feGaussianBlur stdDeviation="7" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>'
        '</feMerge></filter></defs>',
        f'<rect width="{SIGN_W}" height="{SIGN_H}" fill="{SIGN_BG}"/>',
    ]
    parts.append(_text(margin, 46,
                       "EACH PRICE SIZED BY HOW MUCH OF YOUR SPENDING THAT "
                       "FUEL TOUCHES",
                       size=14, fill=SIGN_DIM, weight="bold"))

    # --- gasoline: the number you look at ----------------------------------
    y_gas = 128
    parts.append(_text(margin, y_gas, "GASOLINE", size=LABEL, weight="bold",
                       fill=SIGN_RED))
    x = margin + _tw_caps("GASOLINE", LABEL) + 18
    parts.append(_text(x, y_gas, posted("gasoline"), size=small, weight="bold",
                       fill=SIGN_RED))
    parts.append(_text(x + _tw_digits(posted("gasoline"), small) + 18, y_gas,
                       f"touches {gas_pct}% of what you spend", size=LABEL - 4,
                       fill="#9aa0a3"))

    # --- diesel: the number you should be looking at -----------------------
    y_label = 196
    parts.append(_text(margin, y_label, "DIESEL", size=LABEL, weight="bold",
                       fill=SIGN_GREEN))
    parts.append(_text(margin + _tw_caps("DIESEL", LABEL) + 18, y_label,
                       f"touches {diesel_pct}% of what you spend",
                       size=LABEL - 4, fill="#f2ede0"))

    y_price = y_label + big * 0.80
    parts.append(f'<g filter="url(#glow)">')
    parts.append(_text(margin, y_price, posted("diesel"), size=big,
                       weight="bold", fill=SIGN_GREEN))
    parts.append("</g>")
    parts.append(_text(SIGN_W - margin, y_price - 8,
                       f"{ratio:.0f}x", size=76, weight="bold",
                       fill="#f2ede0", anchor="end"))
    parts.append(_text(SIGN_W - margin, y_price + 26,
                       "more of your spending", size=19, fill=SIGN_DIM,
                       anchor="end"))

    # --- footer ------------------------------------------------------------
    parts.append(f'<line x1="{margin}" y1="{SIGN_H - 92}" '
                 f'x2="{SIGN_W - margin}" y2="{SIGN_H - 92}" stroke="#2b2f31"/>')
    parts.append(_text(margin, SIGN_H - 62,
                       f"Diesel is bought directly by almost nobody — "
                       f"{summary['diesel_direct']}% of the index. It reaches "
                       f"the rest as freight, inside {summary['exposed_count']} "
                       f"of the {summary['categories']} categories.",
                       size=17, fill="#c9cccd"))
    parts.append(_text(margin, SIGN_H - 38,
                       f"Retail prices, week of {prices['diesel'].week}: U.S. "
                       f"Energy Information Administration via FRED. Sizing is "
                       f"share of the CPI each fuel reaches, not the price ratio.",
                       size=14, fill=SIGN_DIM))
    parts.append(_text(margin, SIGN_H - 16,
                       f"{config.PUBLISHER_NAME}  ·  CPI weights: "
                       f"{config.SOURCE_PUBLISHER}, December {config.RI_YEAR}",
                       size=14, fill=SIGN_DIM))
    parts.append("</svg>")

    config.DIST_DIR.mkdir(parents=True, exist_ok=True)
    out = config.DIST_DIR / f"cpi_diesel_sign_{scale}.svg"
    out.write_text("\n".join(parts))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="all",
                        choices=["all", "gasoline", "diesel"])
    parser.add_argument("--all-modes", action="store_true")
    parser.add_argument("--card", action="store_true",
                        help="render the 1200x630 link-preview card instead")
    parser.add_argument("--sign", choices=["linear", "area"], default=None,
                        help="render the type-scaled sign; linear sets letter "
                             "height to the ratio, area sets letter area")
    args = parser.parse_args()
    if args.sign:
        path = render_sign(args.sign)
        print(f"wrote {path.relative_to(config.ROOT)} "
              f"({path.stat().st_size / 1e3:.0f} KB)")
        return 0
    if args.card:
        path = render_card()
        print(f"wrote {path.relative_to(config.ROOT)} "
              f"({path.stat().st_size / 1e3:.0f} KB)")
        return 0
    modes = ["all", "gasoline", "diesel"] if args.all_modes else [args.mode]
    for mode in modes:
        path = render(mode)
        print(f"wrote {path.relative_to(config.ROOT)} "
              f"({path.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
