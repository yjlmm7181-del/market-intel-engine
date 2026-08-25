"""Market endpoints: overview + index quotes."""

from fastapi import APIRouter

from app.schemas.market import IndexQuoteOut, OverviewOut
from app.services.market_pipeline import pipeline

router = APIRouter(tags=["market"])


@router.get("/market/overview", response_model=OverviewOut)
def market_overview():
    return pipeline.get_overview()


@router.get("/market/indexes", response_model=list[IndexQuoteOut])
def market_indexes():
    return pipeline.get_overview()["indexes"]
