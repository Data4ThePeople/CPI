"""Turn the parsed tree into the payload the chart and the CSV both read."""
from __future__ import annotations

from typing import Dict, List

from . import config, exposure_tiers, narratives, parse

MAJOR_ORDER = [
    "Food and beverages", "Housing", "Apparel", "Transportation",
    "Medical care", "Recreation", "Education and communication",
    "Other goods and services",
]

# Long published names that cannot be read at tile size. The BLS name is kept
# in `item_name` so the published label always travels with the number.
DISPLAY_NAMES = {
    "Club membership for shopping clubs, fraternal, or other organizations, "
    "or participant sports fees": "Club memberships and sports fees",
    "Water and sewer and trash collection services": "Water, sewer and trash",
    "Owners' equivalent rent of residences": "Owners' equivalent rent",
    "Cable, satellite, and live streaming television service":
        "Cable, satellite and streaming TV",
    "Tools, hardware, outdoor equipment and supplies":
        "Tools, hardware and outdoor",
    "Information and information processing": "Phone, internet and computers",
    "Tuition, other school fees, and childcare": "Tuition and childcare",
    "Purchase, subscription, and rental of video": "Video subscriptions",
    "Window and floor coverings and other linens": "Floor coverings and linens",
    "Other household equipment and furnishings": "Other home furnishings",
    "Sports vehicles including bicycles": "Bicycles and sports vehicles",
    "Pet services including veterinary": "Vet and pet services",
    "Motor vehicle maintenance and repair": "Vehicle maintenance and repair",
    "Motor vehicle parts and equipment": "Vehicle parts and tires",
    "Educational books and supplies": "Textbooks and school supplies",
    "Music instruments and accessories": "Musical instruments",
    "Photographic equipment and supplies": "Photo equipment",
    "Sewing machines, fabric and supplies": "Sewing and fabric",
    "Recorded music and music subscriptions": "Recorded music",
    "Tobacco products other than cigarettes": "Other tobacco",
    "Alcoholic beverages away from home": "Alcohol away from home",
    "Alcoholic beverages at home": "Alcohol at home",
    "Fuel oil and other fuels": "Heating oil and other fuels",
    "Gasoline (all types)": "Gasoline",
    "Other motor fuels": "Diesel and other motor fuels",
    "Professional services": "Doctors, dentists and eye care",
    "Hospital and related services": "Hospitals",
    "Miscellaneous personal services": "Legal, financial and funeral services",
}


def build_records() -> List[Dict]:
    """One record per mutually exclusive category, tier and narrative attached."""
    nodes = parse.build_tree()
    categories = parse.cut(nodes)
    # data/narratives.csv, when it exists, is the source of truth -- edits made
    # in the spreadsheet win over the drafted defaults in exposure_tiers.py.
    edits = narratives.load()

    records = []
    for node in categories:
        assignment = edits.get(node.name) or exposure_tiers.lookup(node.name)
        tier = exposure_tiers.TIERS[assignment.tier]
        records.append({
            "item_name": node.name,
            "display_name": DISPLAY_NAMES.get(node.name, node.name),
            "major_group": parse.major_group(nodes, node),
            "weight": round(node.cpi_u, 3),
            "tier": assignment.tier,
            "tier_label": tier.label,
            "diesel_exposed": tier.diesel,
            "narrative": assignment.narrative,
        })
    records.sort(
        key=lambda r: (MAJOR_ORDER.index(r["major_group"]), -r["weight"])
    )
    return records


def summarise(records: List[Dict]) -> Dict:
    """The headline statistics, all recomputed -- none hardcoded."""
    total = sum(r["weight"] for r in records)
    exposed = sum(r["weight"] for r in records if r["diesel_exposed"])
    by_name = {r["item_name"]: r for r in records}

    gasoline = by_name["Gasoline (all types)"]["weight"]
    diesel_direct = by_name["Other motor fuels"]["weight"]

    by_tier = {}
    for record in records:
        slot = by_tier.setdefault(record["tier"], {"weight": 0.0, "count": 0})
        slot["weight"] += record["weight"]
        slot["count"] += 1
    for slot in by_tier.values():
        slot["weight"] = round(slot["weight"], 3)

    return {
        "total": round(total, 3),
        "categories": len(records),
        "exposed_weight": round(exposed, 3),
        "exposed_share": round(exposed / total * 100, 1),
        "exposed_count": sum(1 for r in records if r["diesel_exposed"]),
        "gasoline_direct": gasoline,
        "diesel_direct": diesel_direct,
        "gasoline_over_diesel_direct": round(gasoline / diesel_direct, 1),
        "reach_ratio": round(exposed / gasoline, 1),
        "by_tier": by_tier,
    }


def build_payload() -> Dict:
    records = build_records()
    summary = summarise(records)

    # Guardrails. Each of these catches a different way a revised BLS vintage
    # could silently produce a wrong chart.
    if abs(summary["total"] - 100.0) > config.TOLERANCE:
        raise ValueError(
            f"the category cut sums to {summary['total']}, not 100 -- it is no "
            f"longer mutually exclusive"
        )
    for name, expected in config.ANCHORS.items():
        actual = next(r["weight"] for r in records if r["item_name"] == name)
        if abs(actual - expected) > 0.001:
            raise ValueError(
                f"anchor {name!r} is {actual}, expected {expected}. The whole "
                f"comparison rests on this number -- confirm the new vintage "
                f"before updating config.ANCHORS."
            )
    names = [r["item_name"] for r in records]
    if len(names) != len(set(names)):
        raise ValueError("duplicate category in the cut")

    return {
        "records": records,
        "summary": summary,
        "tiers": [t._asdict() for t in exposure_tiers.TIERS.values()],
        "major_order": MAJOR_ORDER,
        "source": {
            "url": config.SOURCE_URL,
            "title": config.SOURCE_TITLE,
            "publisher": config.SOURCE_PUBLISHER,
        },
        "sliver_threshold": config.SLIVER_THRESHOLD,
    }
