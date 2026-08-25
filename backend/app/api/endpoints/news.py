"""News endpoints."""

from fastapi import APIRouter

from app.schemas.market import NewsOut
from app.services.market_pipeline import pipeline

router = APIRouter(tags=["news"])


@router.get("/news", response_model=list[NewsOut])
def news():
    return pipeline.get_overview()["news"]
