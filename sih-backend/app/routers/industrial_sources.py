from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IndustrialSource, IndustrialSourceType
from app.schemas import IndustrialSourceOut, IndustrialSourceCreate
from app.services.classifier import refresh_industrial_sources
from app.services.osm_client import OverpassError

router = APIRouter(prefix="/industrial-sources", tags=["Industrial Sources"])


@router.post("/refresh")
def refresh_from_osm(db: Session = Depends(get_db)):
    """Pull the latest known industrial facilities from OpenStreetMap (Overpass)."""
    try:
        added = refresh_industrial_sources(db)
    except OverpassError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"added": added}


@router.get("/", response_model=list[IndustrialSourceOut])
def list_sources(
    source_type: Optional[IndustrialSourceType] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    q = db.query(IndustrialSource)
    if source_type:
        q = q.filter(IndustrialSource.source_type == source_type)
    return q.limit(limit).all()


@router.post("/", response_model=IndustrialSourceOut)
def add_source_manually(payload: IndustrialSourceCreate, db: Session = Depends(get_db)):
    """Manually register a facility that OSM doesn't have (or as a correction)."""
    source = IndustrialSource(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(IndustrialSource).filter(IndustrialSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"deleted": source_id}
