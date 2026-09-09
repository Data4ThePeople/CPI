"""Retail fuel prices, for the sign graphic.

The sign shows what the two fuels actually cost, and those move every week.
Hardcoding them would put a stale price on a published image, so they are
fetched and cached the same way the BLS table is.

FRED serves these as plain CSV with no API key, which is why they are used
here rather than the EIA series -- same weekly numbers, no key to manage.
WarTaxViz uses the EIA equivalents (EMD_EPD2D_PTE_NUS_DPG,
EMM_EPMR_PTE_NUS_DPG) where a key is already configured.

    python -m cpi_diesel.fuel_prices [--force]
"""
from __future__ import annotations

import argparse
import csv
import urllib.request
from datetime import date
from typing import Dict, NamedTuple

from . import config

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

# U.S. weekly retail, all formulations, dollars per gallon.
SERIES = {
    "gasoline": "GASREGW",
    "diesel": "GASDESW",
}
MAX_STALENESS_DAYS = 21


class Price(NamedTuple):
    series: str
    week: str
    dollars: float


def _fetch_one(name: str, series: str, force: bool) -> Price:
    cache = config.RAW_DIR / f"fred_{series}.csv"
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not cache.exists() or force:
        request = urllib.request.Request(
            FRED_CSV.format(series=series),
            headers={"User-Agent": config.USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            cache.write_bytes(response.read())

    with cache.open() as handle:
        rows = list(csv.reader(handle))[1:]
    observations = [(d, float(v)) for d, v in rows if v not in (".", "")]
    if not observations:
        raise RuntimeError(f"{series} returned no numeric observations")
    week, dollars = observations[-1]
    return Price(series, week, dollars)


def latest(force: bool = False) -> Dict[str, Price]:
    """Most recent weekly price per fuel, refreshing a stale cache."""
    prices = {n: _fetch_one(n, s, force) for n, s in SERIES.items()}

    # A cache older than a few weeks would put an out-of-date price on a
    # published graphic, so refetch rather than quietly using it.
    if not force:
        newest = max(p.week for p in prices.values())
        age = (date.today() - date.fromisoformat(newest)).days
        if age > MAX_STALENESS_DAYS:
            return latest(force=True)
    return prices


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="refetch even if the cache looks current")
    args = parser.parse_args()
    for name, price in sorted(latest(force=args.force).items()):
        print(f"{name:9s} ${price.dollars:.3f}/gal   week of {price.week}  "
              f"({price.series})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
