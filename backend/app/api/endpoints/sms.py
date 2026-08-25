"""SMS endpoints: list + regenerate."""

from fastapi import APIRouter, HTTPException

from app.schemas.market import SmsOut
from app.services.market_pipeline import pipeline

router = APIRouter(tags=["sms"])


@router.get("/sms", response_model=list[SmsOut])
def list_sms():
    return pipeline.list_sms()


@router.post("/sms/{sms_id}/regenerate", response_model=SmsOut)
def regenerate_sms(sms_id: int):
    out = pipeline.regenerate_sms(sms_id)
    if out is None:
        raise HTTPException(status_code=404, detail="sms not found")
    return out
