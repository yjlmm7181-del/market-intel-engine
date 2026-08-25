"""Event endpoints: list, detail, analyze, generate SMS."""

from fastapi import APIRouter, HTTPException

from app.schemas.market import EventOut, SmsOut
from app.services.market_pipeline import pipeline

router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[EventOut])
def list_events():
    return pipeline.get_overview()["events"]


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int):
    e = pipeline.get_event(event_id)
    if e is None:
        raise HTTPException(status_code=404, detail="event not found")
    return e


@router.post("/events/{event_id}/analyze", response_model=EventOut)
def analyze_event(event_id: int):
    e = pipeline.analyze_event(event_id)
    if e is None:
        raise HTTPException(status_code=404, detail="event not found")
    return e


@router.post("/events/{event_id}/generate-sms", response_model=list[SmsOut])
def generate_sms(event_id: int):
    if pipeline.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="event not found")
    return pipeline.generate_sms(event_id)
