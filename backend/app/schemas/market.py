"""Pydantic response schemas for the API."""

from pydantic import BaseModel


class IndexQuoteOut(BaseModel):
    key: str
    name: str
    last_price: float | None = None
    change_rate: float | None = None
    source: str = ""


class MoverOut(BaseModel):
    symbol: str
    name: str = ""
    last_price: float | None = None
    change_rate: float | None = None
    source: str = ""


class NewsOut(BaseModel):
    news_id: str
    title: str
    url: str = ""
    publish_time: int = 0
    source: str = "moomoo"


class NewsRefOut(BaseModel):
    title: str
    url: str = ""


class EventStockOut(BaseModel):
    symbol: str
    name: str = ""
    change_rate: float | None = None


class EventOut(BaseModel):
    id: int
    theme: str
    title: str
    heat_score: int
    index_key: str = ""
    index_change: float | None = None
    stocks: list[EventStockOut] = []
    news: list[NewsRefOut] = []
    ai_summary: str = ""
    summary_source: str = "template"


class SmsOut(BaseModel):
    id: int
    event_id: int
    version: str
    body: str
    cta: str
    body_zh: str = ""


class SmsDeckOut(BaseModel):
    deck_id: str
    messages: list[SmsOut]


class OverviewOut(BaseModel):
    indexes: list[IndexQuoteOut]
    movers: list[MoverOut]
    news: list[NewsOut]
    events: list[EventOut]
