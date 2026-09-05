import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, Boolean, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class ClassificationType(str, enum.Enum):
    INDUSTRIAL = "INDUSTRIAL"
    PERSISTENT_THERMAL = "PERSISTENT_THERMAL"   # recurring, not a mapped facility
    VEGETATION_FIRE = "VEGETATION_FIRE"         # one-off, likely wildfire/agri burn
    UNCLASSIFIED = "UNCLASSIFIED"


class IndustrialSourceType(str, enum.Enum):
    CEMENT_PLANT = "CEMENT_PLANT"
    STEEL_PLANT = "STEEL_PLANT"
    POWER_PLANT = "POWER_PLANT"
    OIL_GAS_REFINERY = "OIL_GAS_REFINERY"
    GAS_FLARE = "GAS_FLARE"
    MINING = "MINING"
    OTHER_INDUSTRIAL = "OTHER_INDUSTRIAL"


class FireDetection(Base):
    """A single satellite-detected thermal anomaly / active fire pixel."""
    __tablename__ = "fire_detections"

    id = Column(Integer, primary_key=True, index=True)

    # Source identity (helps de-dupe re-ingested points)
    source = Column(String, nullable=False)               # e.g. VIIRS_SNPP_NRT
    external_id = Column(String, index=True, nullable=True)

    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    grid_key = Column(String, index=True, nullable=False)  # coarse lat/lon bucket, used for persistence grouping

    brightness = Column(Float, nullable=True)      # brightness temperature (Kelvin)
    frp = Column(Float, nullable=True)              # Fire Radiative Power (MW) - intensity proxy
    confidence = Column(String, nullable=True)      # low / nominal / high (or numeric string)
    acq_date = Column(DateTime, nullable=False, index=True)
    daynight = Column(String, nullable=True)         # 'D' or 'N'

    classification = Column(Enum(ClassificationType), default=ClassificationType.UNCLASSIFIED, index=True)
    matched_source_id = Column(Integer, ForeignKey("industrial_sources.id"), nullable=True)
    distance_to_source_km = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    matched_source = relationship("IndustrialSource", back_populates="detections")


class IndustrialSource(Base):
    """A known industrial facility pulled from OpenStreetMap (or manually added)."""
    __tablename__ = "industrial_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    osm_id = Column(String, index=True, nullable=True, unique=False)
    source_type = Column(Enum(IndustrialSourceType), default=IndustrialSourceType.OTHER_INDUSTRIAL)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    raw_tags = Column(Text, nullable=True)  # JSON string of original OSM tags
    created_at = Column(DateTime, default=datetime.utcnow)

    detections = relationship("FireDetection", back_populates="matched_source")


class Alert(Base):
    """Auto-generated alert for disaster-management review."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    fire_detection_id = Column(Integer, ForeignKey("fire_detections.id"), nullable=False)

    classification = Column(Enum(ClassificationType), nullable=False)
    severity = Column(String, default="MEDIUM")   # LOW / MEDIUM / HIGH
    message = Column(Text, nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    fire_detection = relationship("FireDetection")
