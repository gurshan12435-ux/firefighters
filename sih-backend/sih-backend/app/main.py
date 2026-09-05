from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import fires, industrial_sources, alerts, stats
from app.services.scheduler import start_scheduler, stop_scheduler

# Create tables on startup (fine for SQLite/hackathon use; use Alembic for prod migrations)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Detects and classifies industrial fires vs. persistent (undocumented) "
        "thermal sources vs. vegetation fires, by correlating NASA FIRMS active-fire "
        "data with OpenStreetMap industrial facility locations. Built for SIH25162."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fires.router)
app.include_router(industrial_sources.router)
app.include_router(alerts.router)
app.include_router(stats.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
