"""Event endpoints: list, detail, analyze, generate SMS."""

from fastapi import APIRouter, HTTPException

from app.schemas.market import EventOut, SmsDeckOut, SmsOut
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
def generate_sms(event_id: int, style: str = "hook"):
    if pipeline.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="event not found")
    return pipeline.generate_sms(event_id, style)


@router.post("/events/{event_id}/generate-sms-deck", response_model=SmsDeckOut)
def generate_sms_deck(event_id: int, style: str = "hook"):
    if pipeline.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="event not found")
    return pipeline.generate_sms_deck(event_id, style)


@router.post("/events/{event_id}/sms/{version}/refresh", response_model=SmsOut)
def refresh_sms_card(event_id: int, version: str, deck_id: str, style: str = "hook"):
    out = pipeline.refresh_sms_card(event_id, deck_id, version, style)
    if out is None:
        raise HTTPException(status_code=404, detail="deck not found")
    return out


@router.post("/events/{event_id}/sms/refresh-all", response_model=SmsDeckOut)
def refresh_sms_all(event_id: int, style: str = "hook"):
    if pipeline.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="event not found")
    return pipeline.refresh_sms_all(event_id, style)
