"""Render the self-contained treemap page and the tidy data files.

    python -m cpi_diesel.build              -> dist/index.html  (embeddable)
    python -m cpi_diesel.build --artifact   -> dist/artifact.html
    python -m cpi_diesel.build --data-only  -> data/processed/* only

Mirrors NFP_Treemap/src/nfp_treemap/build.py: one render, two targets, one
self-contained file with no external requests.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config
from .fetch import fetch
from .transform import build_payload

TITLE = "Diesel in the CPI Basket"
META_DESCRIPTION = (
    "Every mutually exclusive category in the Consumer Price Index, sized by "
    "relative importance and colored by how diesel reaches it."
)
TEMPLATES = Path(__file__).parent / "templates"
STATIC = Path(__file__).parent / "static"
LOGO_DIR = config.ROOT / "logo"
LOGO_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
MIME = {
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".webp": "image/webp",
}

CSV_FIELDS = [
    "major_group", "item_name", "display_name", "weight", "tier", "tier_label",
    "diesel_exposed", "intensity", "embedded", "narrative",
]


def logo_data_uri() -> str:
    """First image in logo/, inlined. Empty string when there is none.

    Inlined rather than linked because the published page cannot fetch
    external assets, and because a single self-contained file is the whole
    delivery model here.
    """
    if not LOGO_DIR.is_dir():
        return ""
    files = sorted(
        p for p in LOGO_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in LOGO_SUFFIXES
    )
    if not files:
        return ""
    path = files[0]
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:{MIME[path.suffix.lower()]};base64,{encoded}"


def write_data(payload: dict) -> None:
    """Tidy CSV + JSON, so the chart can be rebuilt or checked independently."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    json_path = config.PROCESSED_DIR / "cpi_diesel.json"
    json_path.write_text(json.dumps(payload, indent=2))

    csv_path = config.PROCESSED_DIR / "cpi_diesel.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in payload["records"]:
            writer.writerow({k: record[k] for k in CSV_FIELDS})
    print(f"wrote {json_path.relative_to(config.ROOT)}")
    print(f"wrote {csv_path.relative_to(config.ROOT)}")


def render(payload: dict, output: Path = None, artifact: bool = False) -> Path:
    if output is None:
        output = config.DIST_DIR / ("artifact.html" if artifact else "index.html")
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(enabled_extensions=()),
    )
    template = env.get_template(
        "artifact.html.j2" if artifact else "treemap.html.j2"
    )
    html = template.render(
        title=TITLE,
        description="" if artifact else META_DESCRIPTION,
        canonical="",
        robots="",
        source_url=config.SOURCE_URL,
        source_title=config.SOURCE_TITLE,
        source_publisher=config.SOURCE_PUBLISHER,
        publisher_name=config.PUBLISHER_NAME,
        publisher_url=config.PUBLISHER_URL,
        ri_year=config.RI_YEAR,
        css=(STATIC / "treemap.css").read_text(),
        js=(STATIC / "treemap.js").read_text(),
        export_note="",
        logo=logo_data_uri(),
        s=payload["summary"],
        # Injected into a <script> block, so "</" inside any narrative would
        # terminate it early.
        payload=json.dumps(payload, separators=(",", ":")).replace("</", "<\\/"),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument("--artifact", action="store_true",
                        help="emit page content only, for hosts that supply "
                             "their own document skeleton")
    parser.add_argument("--data-only", action="store_true",
                        help="write data/processed only, skip the HTML")
    args = parser.parse_args()

    fetch()
    payload = build_payload()
    summary = payload["summary"]

    print(f"{summary['categories']} mutually exclusive categories, "
          f"summing to {summary['total']}%")
    print(f"  gasoline, direct      {summary['gasoline_direct']:>6}%")
    print(f"  diesel, direct        {summary['diesel_direct']:>6}%  "
          f"({summary['gasoline_over_diesel_direct']}x smaller)")
    print(f"  diesel reach          {summary['exposed_share']:>6}%  "
          f"({summary['exposed_count']} categories, "
          f"{summary['reach_ratio']}x gasoline)")
    print(f"  embedded diesel cost  {summary['embedded_diesel']:>6}%  "
          f"({summary['embedded_vs_gasoline']}x gasoline's direct weight)")

    write_data(payload)
    if args.data_only:
        return 0

    path = render(payload, args.output, artifact=args.artifact)
    print(f"wrote {path.relative_to(config.ROOT)} "
          f"({path.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
