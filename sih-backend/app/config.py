"""
Central configuration for the app. All values can be overridden via a .env
file or real environment variables (see .env.example).
"""
from pydantic_settings import BaseSettings
from typing import Tuple


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Industrial Fire & Thermal Source Detection API"
    ENV: str = "development"

    # --- Database ---
    # Defaults to a local SQLite file so the project runs with zero setup.
    # Swap to e.g. postgresql+psycopg2://user:pass@host:5432/dbname for prod.
    DATABASE_URL: str = "sqlite:///./firewatch.db"

    # --- NASA FIRMS ---
    # Get a free MAP_KEY at https://firms.modaps.eosdis.nasa.gov/api/map_key/
    FIRMS_MAP_KEY: str = "PASTE_YOUR_FIRMS_MAP_KEY_HERE"
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    # VIIRS_SNPP_NRT | VIIRS_NOAA20_NRT | VIIRS_NOAA21_NRT | MODIS_NRT
    FIRMS_SOURCE: str = "VIIRS_SNPP_NRT"
    FIRMS_DAY_RANGE: int = 1  # 1-10 days of data per pull

    # Bounding box (west, south, east, north) — defaults to India.
    BBOX: Tuple[float, float, float, float] = (68.0, 6.5, 97.5, 37.5)

    # --- OpenStreetMap (Overpass) ---
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"

    # --- Classification thresholds ---
    INDUSTRIAL_PROXIMITY_KM: float = 1.0       # detection within this radius of an OSM industrial node -> INDUSTRIAL
    PERSISTENCE_GRID_KM: float = 0.5           # grid-cell size used to group repeat detections at "the same place"
    PERSISTENCE_WINDOW_DAYS: int = 30          # look-back window for persistence
    PERSISTENCE_MIN_DETECTIONS: int = 5        # >= this many hits in the window -> PERSISTENT_THERMAL

    # --- Background ingestion ---
    AUTO_INGEST_ENABLED: bool = True
    AUTO_INGEST_INTERVAL_MINUTES: int = 180

    class Config:
        env_file = ".env"


settings = Settings()
