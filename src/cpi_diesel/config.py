"""Paths, source URLs and the BLS download convention.

Mirrors the house pattern in NFP_Treemap/src/nfp_treemap/config.py.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DIST_DIR = ROOT / "dist"

# --- BLS relative importance table -----------------------------------------
# Relative importance is published only as a standalone XLSX. It is NOT in the
# BLS API (there is no catalog endpoint) and NOT in download.bls.gov/pub/
# time.series/cu/. So there is no API key to manage here -- this is a plain
# static file fetch.
#
# The year in the filename is the *weight* vintage. 2025.xlsx carries the
# December 2025 relative importances, computed from 2024 expenditure weights.
RI_YEAR = 2025
RI_URL = f"https://www.bls.gov/cpi/tables/relative-importance/{RI_YEAR}.xlsx"
RI_LOCAL = RAW_DIR / f"cpi_relative_importance_{RI_YEAR}.xlsx"

# download.bls.gov 403s anything without a browser-like prefix (a bare
# "CPI_Diesel/1.0" or "python-requests/2.32" is rejected), but BLS guidance
# asks callers to identify themselves with a contact address. Do both.
CONTACT_EMAIL = os.environ.get("CPI_DIESEL_CONTACT", "eric@asaltollc.com")
USER_AGENT = f"Mozilla/5.0 CPI_Diesel/1.0 ({CONTACT_EMAIL})"

# Who built this. Shown in the provenance stamp, which is the one credit line
# that survives the embedded layout.
PUBLISHER_NAME = os.environ.get("CPI_DIESEL_PUBLISHER", "Data 4 The People")
PUBLISHER_URL = os.environ.get(
    "CPI_DIESEL_PUBLISHER_URL", "https://www.data4thepeople.com"
)

# Prismic renders the embed as an html_embed slice, fullWidth, with a fixed
# pixel height from its embed_height field. 780px is the house default and
# what the `::: embed 780px` directive emits.
EMBED_HEIGHT = 780

# --- Source attribution shown on the chart ---------------------------------
SOURCE_URL = "https://www.bls.gov/cpi/tables/relative-importance/home.htm"
SOURCE_TITLE = (
    "Relative importance of components in the Consumer Price Indexes, "
    "December 2025"
)
SOURCE_PUBLISHER = "U.S. Bureau of Labor Statistics"

# --- Structure of Table 1 ---------------------------------------------------
# Column A = indent level (0-8), B = item name, C = CPI-U relative importance,
# D = CPI-W. Verified against the 2025 file: 330 rows, of which rows 8-300
# (0-indexed) are the mutually exclusive expenditure tree under an
# "All items = 100" root at row 7.
SHEET = "xl/worksheets/sheet1.xml"

# Row 301 begins "Special aggregate indexes" (core, energy, services less rent
# of shelter, ...). Those OVERLAP the expenditure tree rather than partitioning
# it, so including them double-counts silently. Same lattice-not-a-tree problem
# NFP_Treemap documents for the CES aggregates.
STOP_SECTION = "Special aggregate indexes"
START_SECTION = "Expenditure category"
ROOT_ITEM = "All items"

# Expected node count of the expenditure tree, excluding the root. Asserted at
# parse time so a change in the published table is caught loudly instead of
# quietly reshaping the chart.
EXPECTED_NODES = 293

# --- The cut ----------------------------------------------------------------
# Truncate the item tree at this depth: every node at depth <= CUT_DEPTH with
# no children at depth <= CUT_DEPTH. That set is mutually exclusive and sums
# to 100.
CUT_DEPTH = 3

# Categories to split one level further, because the collapsed parent hides
# the comparison the chart exists to make.
#
#   Motor fuel (2.981) -> Gasoline (all types) 2.895 + Other motor fuels 0.086
#       Non-negotiable. The entire gasoline-vs-diesel contrast lives here.
#   Household energy (3.402) -> Energy services 3.262 + Fuel oil and other
#       fuels 0.140. Home heating oil is the same distillate cut as diesel and
#       belongs in the direct tier, not buried inside electricity.
SPLIT_ITEMS = ("Motor fuel", "Household energy")

# --- Known defects in the published file ------------------------------------
# Two rows carry the wrong indent level. Both were found by asserting that
# every parent's weight equals the sum of its children; these were the only
# two failures in the tree, and both are unambiguous.
#
#   "Alcoholic beverages" (0.840) is emitted at level 3 as a child of Food.
#   It belongs at level 2, sibling to Food under Food and beverages:
#   Food and beverages 14.539 - Food 13.698 = 0.841.
#
#   "Information technology, hardware and services" (1.714) is emitted at
#   level 3 as a child of Communication. It belongs at level 4 under
#   Information and information processing:
#   Communication 3.244 vs children 4.959 (+1.715);
#   Information and information processing 3.181 vs children 1.466 (-1.715).
#
# The demotion must carry the whole subtree. Moving the node from 3 to 4
# without also moving its five children off level 4 would make them siblings
# of their own parent and inflate the child sum to 4.894.
#
# name -> corrected indent level
INDENT_FIXES = {
    "Alcoholic beverages": 2,
    "Information technology, hardware and services": 4,
}

# Anchor values the whole story rests on. Asserted at build time so a revised
# BLS vintage produces a loud failure rather than a quietly wrong chart.
ANCHORS = {
    "Gasoline (all types)": 2.895,
    "Other motor fuels": 0.086,
}

# Tiles below this weight are pooled into one "Other small items" tile per
# major category, so the treemap is not littered with unlabelled slivers.
# They stay in the data; this is presentation only.
SLIVER_THRESHOLD = 0.05

TOLERANCE = 0.05