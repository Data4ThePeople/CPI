"""Download the BLS relative importance table into data/raw/.

    python -m cpi_diesel.fetch [--force]
"""
from __future__ import annotations

import argparse
import urllib.request

from . import config


def fetch(force: bool = False):
    """Return the local path to the RI workbook, downloading if needed."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    if config.RI_LOCAL.exists() and not force:
        return config.RI_LOCAL

    request = urllib.request.Request(
        config.RI_URL, headers={"User-Agent": config.USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()

    # An error page would be HTML, not a zip container. Catch it here rather
    # than as a confusing BadZipFile three modules later.
    if not body.startswith(b"PK"):
        raise RuntimeError(
            f"{config.RI_URL} did not return an xlsx (got {len(body)} bytes "
            f"starting {body[:32]!r})"
        )
    config.RI_LOCAL.write_bytes(body)
    return config.RI_LOCAL


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="re-download even if the file is already cached")
    args = parser.parse_args()
    path = fetch(force=args.force)
    print(f"{path.relative_to(config.ROOT)}  ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
