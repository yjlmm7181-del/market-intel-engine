"""Stock endpoints: movers."""

from fastapi import APIRouter

from app.schemas.market import MoverOut
from app.services.market_pipeline import pipeline

router = APIRouter(tags=["stocks"])


@router.get("/stocks/movers", response_model=list[MoverOut])
def stocks_movers():
    return pipeline.get_overview()["movers"]
