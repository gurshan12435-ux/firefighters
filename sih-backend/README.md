# Industrial Fire & Persistent Thermal Source Detection — Backend

Backend for **SIH25162 (NTRO)**: *AI-Based Detection and Classification of
Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM &
Satellite Data.*

## What it does

1. **Ingests** active-fire / thermal-anomaly detections from **NASA FIRMS**
   (VIIRS/MODIS near-real-time data) for a configured bounding box.
2. **Cross-references** each detection against known industrial facilities
   pulled from **OpenStreetMap** (Overpass API) — cement plants, steel
   plants, power plants, refineries, gas flares, mining/quarries.
3. **Classifies** every detection as one of:
   - `INDUSTRIAL` — within range of a mapped facility (expected/routine).
   - `PERSISTENT_THERMAL` — recurs repeatedly at the same location over a
     rolling window but has **no** mapped facility → likely undocumented
     industrial activity, illegal flaring/burning, etc.
   - `VEGETATION_FIRE` — one-off, no industrial correlation → likely
     wildfire/agricultural burning.
4. **Raises alerts** for anything that looks like an undocumented
   persistent source (or unusually high-intensity industrial activity), for
   a disaster-management dashboard to review.

## Project layout

```
app/
  main.py                    FastAPI app, routers, CORS, scheduler lifecycle
  config.py                  All tunables (bbox, thresholds, API keys) via .env
  database.py                SQLAlchemy engine/session
  models.py                  FireDetection, IndustrialSource, Alert
  schemas.py                 Pydantic request/response models
  routers/
    fires.py                 /fires        list, get, manual ingest trigger
    industrial_sources.py    /industrial-sources   OSM refresh, CRUD
    alerts.py                /alerts       list, acknowledge
    stats.py                 /stats        dashboard summary numbers
  services/
    firms_client.py          NASA FIRMS API wrapper (CSV parsing)
    osm_client.py             Overpass API wrapper + tag classification
    classifier.py             Core matching/persistence/alert logic
    scheduler.py               APScheduler background auto-ingestion
  utils/
    geo.py                    Haversine distance + grid bucketing (no PostGIS needed)
```

## Setup

```bash
cd sih-backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste your free FIRMS_MAP_KEY:
# https://firms.modaps.eosdis.nasa.gov/api/map_key/

uvicorn app.main:app --reload
```

API docs (Swagger UI) at: **http://localhost:8000/docs**

## Typical flow

1. `POST /industrial-sources/refresh` — pull known facilities from OSM
   (do this once at startup, and periodically).
2. `POST /fires/ingest` — pull latest FIRMS detections and classify them.
   (Also runs automatically every `AUTO_INGEST_INTERVAL_MINUTES`.)
3. `GET /fires/?classification=PERSISTENT_THERMAL` — see flagged sources.
4. `GET /alerts/?acknowledged=false` — feed the dashboard's alert list.
5. `GET /stats/` — headline numbers for the dashboard.

## Key endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/fires/ingest` | Trigger a FIRMS pull + classification pass |
| GET | `/fires/` | List detections (filter by classification, bbox, date) |
| GET | `/fires/{id}` | Single detection detail |
| POST | `/industrial-sources/refresh` | Re-pull facilities from OSM |
| GET | `/industrial-sources/` | List known facilities |
| POST | `/industrial-sources/` | Manually add/correct a facility |
| GET | `/alerts/` | List alerts (filter by acknowledged) |
| POST | `/alerts/{id}/acknowledge` | Mark an alert reviewed |
| GET | `/stats/` | Dashboard summary counts |

## Notes / next steps for the hackathon

- **Database**: defaults to SQLite (zero setup). Swap `DATABASE_URL` in
  `.env` to Postgres for a multi-user demo; for real scale, add PostGIS and
  replace the naive nearest-neighbour scan in `classifier.py` with
  `ST_DWithin`.
- **Bounding box** defaults to all of India — narrow it in `config.py` (or
  `.env`) if you want faster demo pulls over a specific state/region.
- **ML angle**: current classification is rule-based (proximity +
  recurrence), which is fast and explainable for judges. If you want an ML
  layer on top, a natural extension is a small classifier trained on
  brightness/FRP/day-night/seasonality patterns to distinguish flaring vs.
  smelting vs. wildfire signatures — the `FireDetection` table already has
  the features (`brightness`, `frp`, `daynight`, `acq_date`) to build that
  on.
- **Satellite imagery**: for the "Satellite Data" part of the problem
  statement (visual confirmation of a flagged site), a good next step is
  wiring in Sentinel Hub / Bhuvan imagery keyed off `latitude`/`longitude`
  when a detection is flagged `PERSISTENT_THERMAL`.
