from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FireDetection, ClassificationType
from app.schemas import FireDetectionOut, FireDetectionList, IngestResponse
from app.services.classifier import ingest_and_classify
from app.services.firms_client import FirmsClientError

router = APIRouter(prefix="/fires", tags=["Fire Detections"])


@router.post("/ingest", response_model=IngestResponse)
def trigger_ingestion(db: Session = Depends(get_db)):
    """
    Manually trigger a FIRMS pull + classification pass. In production this
    also runs automatically on a schedule (see services/scheduler.py).
    """
    try:
        result = ingest_and_classify(db)
    except FirmsClientError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result


@router.get("/", response_model=FireDetectionList)
def list_fires(
    classification: Optional[ClassificationType] = Query(None),
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    since: Optional[datetime] = Query(None, description="Only detections acquired on/after this timestamp"),
    limit: int = Query(200, le=2000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(FireDetection)

    if classification:
        q = q.filter(FireDetection.classification == classification)
    if min_lat is not None:
        q = q.filter(FireDetection.latitude >= min_lat)
    if max_lat is not None:
        q = q.filter(FireDetection.latitude <= max_lat)
    if min_lon is not None:
        q = q.filter(FireDetection.longitude >= min_lon)
    if max_lon is not None:
        q = q.filter(FireDetection.longitude <= max_lon)
    if since is not None:
        q = q.filter(FireDetection.acq_date >= since)

    total = q.count()
    rows = q.order_by(FireDetection.acq_date.desc()).offset(offset).limit(limit).all()

    return {"count": total, "results": rows}


@router.get("/{fire_id}", response_model=FireDetectionOut)
def get_fire(fire_id: int, db: Session = Depends(get_db)):
    fire = db.query(FireDetection).filter(FireDetection.id == fire_id).first()
    if not fire:
        raise HTTPException(status_code=404, detail="Fire detection not found")
    return fire
