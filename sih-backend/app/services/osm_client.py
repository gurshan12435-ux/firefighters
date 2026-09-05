"""
Pulls known industrial facility locations from OpenStreetMap via the
Overpass API, so we have a "known sources" registry to correlate FIRMS
detections against.
"""
import json
from typing import List, Dict

import requests

from app.config import settings
from app.models import IndustrialSourceType

# Overpass query fragments -> our internal source type
TAG_QUERIES = {
    IndustrialSourceType.CEMENT_PLANT: ['["industrial"="cement"]', '["product"="cement"]'],
    IndustrialSourceType.STEEL_PLANT: ['["industrial"="steel"]', '["product"="steel"]'],
    IndustrialSourceType.POWER_PLANT: ['["power"="plant"]', '["power"="generator"]'],
    IndustrialSourceType.OIL_GAS_REFINERY: ['["man_made"="petroleum_well"]', '["industrial"="oil"]', '["landuse"="industrial"]["industrial"="refinery"]'],
    IndustrialSourceType.GAS_FLARE: ['["man_made"="flare"]'],
    IndustrialSourceType.MINING: ['["landuse"="quarry"]', '["industrial"="mine"]'],
}


class OverpassError(Exception):
    pass


def _build_query(bbox) -> str:
    west, south, east, north = bbox
    bbox_str = f"{south},{west},{north},{east}"  # Overpass wants south,west,north,east

    clauses = []
    for stype, tag_filters in TAG_QUERIES.items():
        for tag_filter in tag_filters:
            clauses.append(f'node{tag_filter}({bbox_str});')
            clauses.append(f'way{tag_filter}({bbox_str});')

    body = "\n  ".join(clauses)
    return f"""
    [out:json][timeout:60];
    (
      {body}
    );
    out center;
    """


def fetch_industrial_sources() -> List[Dict]:
    """Query Overpass for industrial facilities inside the configured bbox."""
    query = _build_query(settings.BBOX)

    try:
        resp = requests.post(settings.OVERPASS_URL, data={"data": query}, timeout=90)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OverpassError(f"Failed to reach Overpass API: {e}") from e

    data = resp.json()
    elements = data.get("elements", [])

    results = []
    for el in elements:
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue

        tags = el.get("tags", {})
        source_type = _classify_tags(tags)

        results.append({
            "osm_id": f"{el.get('type')}/{el.get('id')}",
            "name": tags.get("name"),
            "source_type": source_type,
            "latitude": lat,
            "longitude": lon,
            "raw_tags": json.dumps(tags),
        })

    return results


def _classify_tags(tags: Dict) -> IndustrialSourceType:
    if tags.get("power") in ("plant", "generator"):
        return IndustrialSourceType.POWER_PLANT
    if tags.get("man_made") == "flare":
        return IndustrialSourceType.GAS_FLARE
    if "cement" in json.dumps(tags).lower():
        return IndustrialSourceType.CEMENT_PLANT
    if "steel" in json.dumps(tags).lower():
        return IndustrialSourceType.STEEL_PLANT
    if tags.get("landuse") == "quarry" or tags.get("industrial") == "mine":
        return IndustrialSourceType.MINING
    if "refin" in json.dumps(tags).lower() or "petro" in json.dumps(tags).lower():
        return IndustrialSourceType.OIL_GAS_REFINERY
    return IndustrialSourceType.OTHER_INDUSTRIAL
