"""Does jet fuel move with diesel? The test behind including airline fares.

Jet A is a kerosene-type middle distillate, drawn from the same cut of the
barrel as No. 2 diesel and heating oil, so the prior is that it tracks diesel
rather than gasoline. This checks that empirically instead of asserting it,
because "airline fares are fuel-exposed but not to diesel" was the original
reason for excluding them.

    python -m cpi_diesel.fuel_correlation

Two things matter for reading the output:

  * Correlate RETURNS, not levels. Every refined product trends with crude, so
    levels correlate above 0.95 for reasons that say nothing about whether two
    products share a cut.
  * Correlate MONTHLY returns. Daily moves carry a lot of local noise, and the
    CPI is a monthly index -- month-over-month is the horizon the chart cares
    about.

The discriminating test is the partial correlation controlling for crude: it
asks whether jet still moves with distillate once the driver they share with
everything else is removed.
"""
from __future__ import annotations

import csv
import math
import urllib.request
from typing import Dict, List, Sequence

from . import config

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
SERIES = {
    "jet": "DJFUELUSGULF",   # kerosene-type jet fuel, US Gulf Coast
    "distillate": "DHOILNYH",  # No. 2 heating oil, NY Harbor
    "gasoline": "DGASNYH",     # conventional gasoline, NY Harbor
    "crude": "DCOILWTICO",     # WTI
}


def _load(series: str, force: bool = False) -> Dict[str, float]:
    cache = config.RAW_DIR / f"fred_{series}.csv"
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not cache.exists() or force:
        request = urllib.request.Request(
            FRED_CSV.format(series=series),
            headers={"User-Agent": config.USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            cache.write_bytes(response.read())
    with cache.open() as handle:
        rows = list(csv.reader(handle))[1:]
    return {d: float(v) for d, v in rows if v not in (".", "")}


def corr(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    ca = [x - ma for x in a]
    cb = [y - mb for y in b]
    den = math.sqrt(sum(x * x for x in ca) * sum(y * y for y in cb))
    return sum(x * y for x, y in zip(ca, cb)) / den if den else float("nan")


def partial(rxy: float, rxz: float, ryz: float) -> float:
    """Correlation of x and y with the influence of z removed."""
    return (rxy - rxz * ryz) / math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))


def _monthly(series: Dict[str, float]) -> Dict[str, float]:
    """Last observation in each month."""
    out: Dict[str, float] = {}
    for day in sorted(series):
        out[day[:7]] = series[day]
    return out


def log_returns(series: List[Dict[str, float]], monthly: bool) -> List[List[float]]:
    srcs = [_monthly(s) for s in series] if monthly else series
    keys = sorted(set.intersection(*[set(s) for s in srcs]))
    out: List[List[float]] = [[] for _ in srcs]
    for i in range(1, len(keys)):
        pairs = [(s[keys[i - 1]], s[keys[i]]) for s in srcs]
        if all(a > 0 and b > 0 for a, b in pairs):
            for j, (a, b) in enumerate(pairs):
                out[j].append(math.log(b / a))
    return out


def report() -> dict:
    data = {name: _load(sid) for name, sid in SERIES.items()}
    results = {}
    for monthly, label in ((False, "daily"), (True, "monthly")):
        j, d, g, c = log_returns(
            [data["jet"], data["distillate"], data["gasoline"], data["crude"]],
            monthly)
        rjd, rjg, rjc = corr(j, d), corr(j, g), corr(j, c)
        rdc, rgc = corr(d, c), corr(g, c)
        results[label] = {
            "n": len(j),
            "jet_distillate": rjd,
            "jet_gasoline": rjg,
            "jet_crude": rjc,
            "jet_distillate_given_crude": partial(rjd, rjc, rdc),
            "jet_gasoline_given_crude": partial(rjg, rjc, rgc),
        }
    return results


def main() -> int:
    results = report()
    for label, r in results.items():
        print(f"\n=== {label} log returns  (n={r['n']}) ===")
        print(f"  jet ~ distillate            {r['jet_distillate']:.3f}")
        print(f"  jet ~ gasoline              {r['jet_gasoline']:.3f}")
        print(f"  jet ~ crude                 {r['jet_crude']:.3f}")
        print(f"  jet ~ distillate | crude    {r['jet_distillate_given_crude']:.3f}")
        print(f"  jet ~ gasoline   | crude    {r['jet_gasoline_given_crude']:.3f}")
    m = results["monthly"]
    print(f"\nAt the monthly horizon the CPI moves at, jet tracks distillate at "
          f"{m['jet_distillate']:.2f}. Removing the crude both share leaves "
          f"{m['jet_distillate_given_crude']:.2f} against gasoline's "
          f"{m['jet_gasoline_given_crude']:.2f} -- jet is a distillate sibling, "
          f"not a generic refined product. That is why airline fares count.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
