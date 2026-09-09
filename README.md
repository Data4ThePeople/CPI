# CPI diesel exposure

Gasoline is the fuel everyone watches. In the CPI it is **2.895%** of the
index — bought directly, by households, and that direct purchase is
essentially its entire role.

Diesel bought directly is **0.086%**. Thirty-four times smaller. That number
is why diesel gets ignored, and it is the wrong number to look at: diesel is
not something households buy, it is the input cost that moves everything they
do buy. Counted that way it reaches **44.4% of the index**.

This project builds a treemap of every mutually exclusive CPI category, sized
by relative importance and colored by how diesel reaches it, with a written
explanation attached to each one.

```
gasoline, direct       2.895%
diesel, direct         0.086%   (33.7x smaller)
diesel reach            44.4%   (60 of 81 categories, 15.3x gasoline)
embedded diesel cost    1.94%   (0.67x gasoline's direct weight)
```

## Running it

Python 3.9+, and Jinja2 is the only dependency — the BLS workbook is parsed
with `zipfile` and `ElementTree` from the standard library.

```
.venv/bin/pip install -r requirements.txt

PYTHONPATH=src .venv/bin/python -m cpi_diesel.build                 # dist/index.html + data
PYTHONPATH=src .venv/bin/python -m cpi_diesel.build --artifact      # dist/artifact.html
PYTHONPATH=src .venv/bin/python -m cpi_diesel.render_static --all-modes
PYTHONPATH=src .venv/bin/python -m tests.test_cut                   # guardrails
```

`dist/index.html` is one self-contained file with no external requests, so it
drops into a Substack or Prismic iframe as is. `dist/artifact.html` is the
same page emitted as content only, for hosts that supply their own document
skeleton. `data/processed/cpi_diesel.csv` carries every category with its
weight, tier and narrative.

## Embedding it in Prismic

Prismic renders this as an `html_embed` slice — **fullWidth**, with a fixed
pixel height from the slice's `embed_height` field. The house default is
**780px**, which is what `::: embed 780px` emits and what the layout is tuned
against.

In the post's Markdown, either drop the raw iframe in (the converter turns it
into `html_embed`, `fullWidth`, `embed_height`):

```html
<iframe src="https://<pages-host>/cpi-diesel/#embed=1"
        width="100%" height="780" loading="lazy" style="border:0"
        title="Diesel in the CPI basket"></iframe>
```

…or write `::: embed 780px` to emit an empty slice and paste into it in the
Prismic dashboard.

### How the framed layout differs

`#embed=1` forces it; otherwise it auto-detects with `window.self !== top`, and
`#embed=0` forces the full layout back. Framed, the page:

- drops the masthead and the notes — the article around it already carries the
  headline and the caveats, and inside a fixed height they are the two most
  expensive blocks on the page;
- becomes a flex column that fills exactly the given height, with `overflow:
  hidden`, so **nothing scrolls inside the frame** and every spare pixel goes
  to the treemap;
- keeps one provenance stamp, the single credit line that survives;
- swaps the stat tiles and buttons to terse labels so all four tiles hold one
  row down to ~620px — the full sentences orphan the fourth tile onto a row of
  its own and cost the chart 75px;
- below ~620px drops the nine-row legend and the provenance stamp — together
  ~125px of a fixed 780 — for a two-line minimal key plus a pointer to the
  desktop version. The key collapses the six diesel tiers into one light-to-dark
  strip labelled with the total, and keeps separate swatches only for the three
  categorical fills (gasoline, other fuel, no diesel), so the encoding still
  reads without spending the height nine rows would cost.

Sizing is measured off the element, never the viewport, and the responsive
rules are **container queries** rather than media queries: inside the Prismic
oEmbed the viewport does not describe the space the page is actually given. A
`ResizeObserver` refits the chart when the column changes without the window
firing anything.

Verified at 380×780, 700×780 and 1100×780 — no scrollbars, no clipped labels.
On a 380px phone frame the chart gets ~570px of the 780, against ~250px before
any of this.

`dist/artifact.html` sets `window.CPI_STANDALONE`, because that host frames the
page but supplies its own document chrome — there the full layout is correct.

### Two levers to leave alone

`CANONICAL_URL` and `ROBOTS` default to empty deliberately, following
`NFP_Treemap`:

- **Do not set `ROBOTS` to noindex.** The only controlled test of how Googlebot
  treats iframes (Grimm, 2022) found a parent page can rank for content that
  exists only in the framed URL, and that a noindex on the framed URL removes
  that ability. Noindexing this file would strip the chart's content from every
  article embedding it.
- **Do not point `CANONICAL_URL` at the embedding article.** A small tool and a
  long article are not equivalent pages, and Google ignores canonicals between
  URLs that are not equivalent.

## Where the numbers come from

[Relative importance of components in the Consumer Price Indexes, December
2025](https://www.bls.gov/cpi/tables/relative-importance/home.htm), Table 1,
CPI-U column. That table is published only as XLSX — it is not in the BLS API
and not in `download.bls.gov/pub/time.series/cu/` — so there is no API key to
manage here.

### The cut is mutually exclusive, and that is checked

The item tree is truncated at depth 3: every node at depth ≤ 3 with no
children at depth ≤ 3. `Motor fuel` and `Household energy` are then split one
level further, because a collapsed `Motor fuel` tile would hide the entire
gasoline-versus-diesel comparison, and because home heating oil is the same
distillate cut as diesel and belongs in the direct tier rather than buried
inside electricity.

That gives **81 categories summing to 100%**. The build asserts it. No
category contains any other, which is what makes summing them legitimate.

### Two defects in the published BLS table

Both were found by asserting that every parent's weight equals the sum of its
children. They were the only two failures, and both are unambiguous:

| Row | Published | Correct | Evidence |
|---|---|---|---|
| `Alcoholic beverages` | level 3, under Food | level 2, beside Food | Food and beverages 14.539 − Food 13.698 = 0.841 |
| `Information technology, hardware and services` | level 3, under Communication | level 4, under Information and information processing | Communication 3.244 vs children 4.959 (+1.715) |

The second fix has to carry the whole subtree. Moving the node from level 3 to
4 without also moving its five children off level 4 makes them siblings of
their own parent.

Uncorrected, a depth-3 cut sums to **101.712%** instead of 100%.

`Special aggregate indexes` (row 301 onward — core, energy, services less rent
of shelter) overlap the expenditure tree rather than partitioning it, and are
excluded. Including them double-counts with no visible symptom.

## Editing the narratives

Every category carries a written explanation of how diesel reaches it. They
are drafted in `src/cpi_diesel/exposure_tiers.py`, but the place to edit them
is the spreadsheet:

```
PYTHONPATH=src .venv/bin/python -m cpi_diesel.narratives --export   # data/narratives.csv
# ...edit in Excel, Numbers or anything else...
PYTHONPATH=src .venv/bin/python -m cpi_diesel.narratives --check    # validate before building
PYTHONPATH=src .venv/bin/python -m cpi_diesel.build                 # edits flow into the chart
```

Once `data/narratives.csv` exists it is the source of truth and overrides the
Python defaults — no code change needed. `tier`, `intensity` and `narrative`
are all editable; `major_group` and `weight` are there for context while
editing and are ignored on read, since they come from BLS.

`--check` refuses anything that would silently produce a wrong chart: an
unknown tier, a misspelled category name, a duplicate row, an intensity
outside 0–1, an empty narrative, or a category dropped from the sheet. Export
will not clobber an existing sheet without `--force`.

## The tiers are editorial

The weights are BLS's. The exposure tiers and narratives are ours: a judgment
about freight intensity, not a measured cost share, and not a BLS aggregate.
Every assignment lives in `src/cpi_diesel/exposure_tiers.py` with its reasoning
written out, so it can be argued with one category at a time.

| Tier | Weight | What it means |
|---|---|---|
| Diesel, bought directly | 0.23% | Diesel or the distillate next to it — heating oil, consumer diesel |
| Delivered by a diesel vehicle | 1.81% | Transit, intercity bus and rail, parcel delivery, refuse collection |
| Refrigerated freight | 8.94% | Food at home, pet food |
| Heavy freight | 10.57% | Vehicles, furniture, appliances, tools |
| Service that runs on trucked inputs | 15.62% | Restaurants, hospitals, lodging, vehicle repair |
| Light freight | 7.22% | Apparel, drugs, personal care, toys |
| **Diesel-exposed total** | **44.38%** | |
| Gasoline, bought directly | 2.90% | The comparison anchor |
| Other fuel, not diesel | 4.14% | Airline fares (jet fuel), electricity and piped gas |
| No meaningful diesel content | 48.58% | Owners' equivalent rent, rent, insurance, tuition, telecom |

Air travel is genuinely fuel-exposed, but to jet fuel; electricity and piped
gas to their own fuels. Both are kept out of the diesel total on purpose —
folding them in would be the first thing a skeptical reader attacked.

## What the headline does and does not say

"Diesel reaches 44.4% of the index" means diesel is an input cost somewhere
inside categories making up 44.4% of the basket. It does **not** mean diesel
drives 44.4% of inflation.

Weighting each category by a rough estimate of how much of its delivered cost
is actually diesel gives an embedded diesel cost of about **1.94% of the
index** — roughly two-thirds of gasoline's entire direct weight, but spread
across 60 categories instead of sitting in one box. Breadth is the claim this
project makes with confidence. The second number is there so the first cannot
be read as magnitude.

## House conventions this follows

- One published series per charted figure; the diesel grouping is labeled as
  editorial wherever it appears, because it is a sum across categories.
- Nothing hardcoded — every figure recomputes at render time, so a BLS
  revision produces corrected output rather than stale output.
- No CDN, no charting library. The interactive is vanilla canvas inlined into
  a single file, following `NFP_Treemap`.
- `download.bls.gov` rejects bare user agents, so requests carry a
  browser-like prefix and a contact address (`CPI_DIESEL_CONTACT`).
