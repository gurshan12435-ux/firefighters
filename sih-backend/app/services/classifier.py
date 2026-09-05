"""
Core pipeline: pull FIRMS detections, match them against known OSM
industrial sources, check for spatial-temporal persistence, classify each
detection, and raise alerts for anything that looks like an undocumented
persistent thermal source.
"""
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import FireDetection, IndustrialSource, Alert, ClassificationType
from app.services import firms_client
from app.utils.geo import haversine_km, grid_key
from app.config import settings


def _find_nearest_industrial_source(db: Session, lat: float, lon: float):
    """
    Naive nearest-neighbour scan against known sources. Fine for a
    hackathon-scale dataset (hundreds-to-low-thousands of facilities);
    swap for PostGIS ST_DWithin if this needs to scale further.
    """
    best_source, best_dist = None, None
    for src in db.query(IndustrialSource).all():
        dist = haversine_km(lat, lon, src.latitude, src.longitude)
        if best_dist is None or dist < best_dist:
            best_source, best_dist = src, dist

    if best_source is not None and best_dist <= settings.INDUSTRIAL_PROXIMITY_KM:
        return best_source, best_dist
    return None, None


def _is_persistent(db: Session, grid_cell: str, acq_date: datetime) -> bool:
    """A grid cell counts as persistent if it has enough hits in the lookback window."""
    window_start = acq_date - timedelta(days=settings.PERSISTENCE_WINDOW_DAYS)
    count = (
        db.query(func.count(FireDetection.id))
        .filter(FireDetection.grid_key == grid_cell)
        .filter(FireDetection.acq_date >= window_start)
        .scalar()
    )
    return (count or 0) + 1 >= settings.PERSISTENCE_MIN_DETECTIONS


def classify_detection(db: Session, detection: FireDetection) -> None:
    """Mutates `detection` in place with a classification + match info."""
    source, dist = _find_nearest_industrial_source(db, detection.latitude, detection.longitude)

    if source is not None:
        detection.classification = ClassificationType.INDUSTRIAL
        detection.matched_source_id = source.id
        detection.distance_to_source_km = round(dist, 3)
        return

    if _is_persistent(db, detection.grid_key, detection.acq_date):
        detection.classification = ClassificationType.PERSISTENT_THERMAL
        return

    detection.classification = ClassificationType.VEGETATION_FIRE


def _maybe_create_alert(db: Session, detection: FireDetection) -> bool:
    """Raise an alert for anything that isn't a routine, already-mapped industrial source."""
    if detection.classification == ClassificationType.PERSISTENT_THERMAL:
        message = (
            f"Persistent thermal source detected at ({detection.latitude:.4f}, "
            f"{detection.longitude:.4f}) with no matching industrial facility on record. "
            f"Recurred >= {settings.PERSISTENCE_MIN_DETECTIONS} times in the last "
            f"{settings.PERSISTENCE_WINDOW_DAYS} days — possible undocumented industrial "
            f"activity or illegal burning site."
        )
        severity = "HIGH"
    elif detection.classification == ClassificationType.INDUSTRIAL and (detection.frp or 0) > 50:
        message = (
            f"Unusually high fire radiative power ({detection.frp} MW) at a known industrial "
            f"facility (source_id={detection.matched_source_id}) — worth a manual look."
        )
        severity = "MEDIUM"
    else:
        return False

    db.add(Alert(
        fire_detection_id=detection.id,
        classification=detection.classification,
        severity=severity,
        message=message,
        latitude=detection.latitude,
        longitude=detection.longitude,
    ))
    return True


def ingest_and_classify(db: Session) -> Dict:
    """
    Full pipeline run: fetch new FIRMS points, dedupe against what we already
    have, classify each new one, and generate alerts. Returns a summary dict.
    """
    raw_records = firms_client.fetch_active_fires()
    new_count = 0
    alerts_created = 0
    class_counter: Counter = Counter()

    for rec in raw_records:
        exists = (
            db.query(FireDetection)
            .filter(FireDetection.external_id == rec["external_id"])
            .first()
        )
        if exists:
            continue

        detection = FireDetection(
            source=rec["source"],
            external_id=rec["external_id"],
            latitude=rec["latitude"],
            longitude=rec["longitude"],
            grid_key=grid_key(rec["latitude"], rec["longitude"], settings.PERSISTENCE_GRID_KM),
            brightness=rec["brightness"],
            frp=rec["frp"],
            confidence=rec["confidence"],
            acq_date=rec["acq_date"],
            daynight=rec["daynight"],
        )
        db.add(detection)
        db.flush()  # get detection.id without committing yet

        classify_detection(db, detection)
        class_counter[detection.classification.value] += 1

        if _maybe_create_alert(db, detection):
            alerts_created += 1

        new_count += 1

    db.commit()

    return {
        "fetched": len(raw_records),
        "new_detections": new_count,
        "classified": dict(class_counter),
        "alerts_created": alerts_created,
    }


def refresh_industrial_sources(db: Session) -> int:
    """Pull the latest OSM industrial facility list and upsert into the DB."""
    from app.services import osm_client

    records = osm_client.fetch_industrial_sources()
    added = 0
    for rec in records:
        exists = (
            db.query(IndustrialSource)
            .filter(IndustrialSource.osm_id == rec["osm_id"])
            .first()
        )
        if exists:
            continue
        db.add(IndustrialSource(
            osm_id=rec["osm_id"],
            name=rec["name"],
            source_type=rec["source_type"],
            latitude=rec["latitude"],
            longitude=rec["longitude"],
            raw_tags=rec["raw_tags"],
        ))
        added += 1

    db.commit()
    return added
