"""
Thin client around NASA FIRMS' "area" CSV API.

Docs: https://firms.modaps.eosdis.nasa.gov/api/
Endpoint shape:
  https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}
where AREA is "west,south,east,north" or "world".
"""
import csv
import io
from datetime import datetime
from typing import List, Dict

import requests

from app.config import settings


class FirmsClientError(Exception):
    pass


def fetch_active_fires() -> List[Dict]:
    """
    Pull the latest active fire / thermal anomaly detections for the
    configured bounding box and return them as a list of plain dicts.
    """
    west, south, east, north = settings.BBOX
    area = f"{west},{south},{east},{north}"

    url = (
        f"{settings.FIRMS_BASE_URL}/{settings.FIRMS_MAP_KEY}/"
        f"{settings.FIRMS_SOURCE}/{area}/{settings.FIRMS_DAY_RANGE}"
    )

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FirmsClientError(f"Failed to reach FIRMS API: {e}") from e

    text = resp.text.strip()
    if not text or text.lower().startswith("invalid"):
        raise FirmsClientError(f"FIRMS API returned an unexpected response: {text[:200]}")

    reader = csv.DictReader(io.StringIO(text))
    records = []
    for row in reader:
        try:
            lat = float(row.get("latitude"))
            lon = float(row.get("longitude"))
        except (TypeError, ValueError):
            continue

        acq_date_str = row.get("acq_date", "")
        acq_time_str = (row.get("acq_time") or "0000").zfill(4)
        try:
            acq_dt = datetime.strptime(
                f"{acq_date_str} {acq_time_str}", "%Y-%m-%d %H%M"
            )
        except ValueError:
            acq_dt = datetime.utcnow()

        records.append({
            "source": settings.FIRMS_SOURCE,
            "external_id": f"{row.get('latitude')}_{row.get('longitude')}_{acq_date_str}_{acq_time_str}",
            "latitude": lat,
            "longitude": lon,
            "brightness": _safe_float(row.get("bright_ti4") or row.get("brightness")),
            "frp": _safe_float(row.get("frp")),
            "confidence": row.get("confidence"),
            "acq_date": acq_dt,
            "daynight": row.get("daynight"),
        })

    return records


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
