"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.db.session import init_db


def _warmup(pipeline) -> None:
    try:
        pipeline.refresh()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        from app.tasks.scheduler import start_scheduler

        start_scheduler()
    except Exception:
        pass
    # Pre-warm market data in the background so the first page load is fast.
    try:
        import threading

        from app.services.market_pipeline import pipeline

        threading.Thread(target=_warmup, args=(pipeline,), daemon=True).start()
    except Exception:
        pass
    yield
    try:
        from app.tasks.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:
        pass


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


app.include_router(api_router, prefix="/api")

# Serve the built frontend (used for single-service deploys such as Render).
# In local dev the Vite dev server serves the frontend instead, so this is a
# no-op when the dist folder is absent.
_dist = (
    Path(settings.frontend_dist)
    if settings.frontend_dist
    else Path(__file__).resolve().parents[2] / "frontend" / "dist"
)
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
