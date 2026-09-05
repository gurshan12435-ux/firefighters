from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import FireDetection, IndustrialSource, Alert
from app.schemas import StatsResponse

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total_detections = db.query(func.count(FireDetection.id)).scalar() or 0

    by_class_rows = (
        db.query(FireDetection.classification, func.count(FireDetection.id))
        .group_by(FireDetection.classification)
        .all()
    )
    by_classification = {cls.value: count for cls, count in by_class_rows}

    total_sources = db.query(func.count(IndustrialSource.id)).scalar() or 0
    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    unacked = db.query(func.count(Alert.id)).filter(Alert.acknowledged.is_(False)).scalar() or 0

    return {
        "total_detections": total_detections,
        "by_classification": by_classification,
        "total_industrial_sources": total_sources,
        "total_alerts": total_alerts,
        "unacknowledged_alerts": unacked,
    }
