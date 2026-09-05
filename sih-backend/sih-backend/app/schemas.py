from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.models import ClassificationType, IndustrialSourceType


# ---------- Fire Detection ----------

class FireDetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    latitude: float
    longitude: float
    brightness: Optional[float] = None
    frp: Optional[float] = None
    confidence: Optional[str] = None
    acq_date: datetime
    daynight: Optional[str] = None
    classification: ClassificationType
    matched_source_id: Optional[int] = None
    distance_to_source_km: Optional[float] = None
    created_at: datetime


class FireDetectionList(BaseModel):
    count: int
    results: List[FireDetectionOut]


# ---------- Industrial Source ----------

class IndustrialSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str] = None
    osm_id: Optional[str] = None
    source_type: IndustrialSourceType
    latitude: float
    longitude: float
    created_at: datetime


class IndustrialSourceCreate(BaseModel):
    name: Optional[str] = None
    source_type: IndustrialSourceType = IndustrialSourceType.OTHER_INDUSTRIAL
    latitude: float
    longitude: float


# ---------- Alerts ----------

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fire_detection_id: int
    classification: ClassificationType
    severity: str
    message: str
    latitude: float
    longitude: float
    acknowledged: bool
    created_at: datetime


# ---------- Ingestion / stats ----------

class IngestResponse(BaseModel):
    fetched: int
    new_detections: int
    classified: dict
    alerts_created: int


class StatsResponse(BaseModel):
    total_detections: int
    by_classification: dict
    total_industrial_sources: int
    total_alerts: int
    unacknowledged_alerts: int
