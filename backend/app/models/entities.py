"""SQLAlchemy models. Kept portable between Postgres and SQLite
(no JSON/enum column types — JSON-ish fields are stored as TEXT)."""

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class NewsItem(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    news_id = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, default="")
    publish_time = Column(Integer, default=0)  # unix seconds
    news_type = Column(Integer, default=1)
    source = Column(String(32), default="moomoo")
    created_at = Column(DateTime, default=utcnow)


class MarketEvent(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    theme = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    heat_score = Column(Integer, default=0)
    index_key = Column(String(32), default="")
    index_change = Column(Float, nullable=True)
    stocks_json = Column(Text, default="[]")
    news_json = Column(Text, default="[]")
    ai_summary = Column(Text, default="")
    summary_source = Column(String(16), default="template")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def set_stocks(self, stocks: list[dict]) -> None:
        self.stocks_json = json.dumps(stocks)

    def get_stocks(self) -> list[dict]:
        try:
            return json.loads(self.stocks_json or "[]")
        except json.JSONDecodeError:
            return []

    def set_news(self, news: list[dict]) -> None:
        self.news_json = json.dumps(news)

    def get_news(self) -> list[dict]:
        try:
            return json.loads(self.news_json or "[]")
        except json.JSONDecodeError:
            return []


class SmsMessage(Base):
    __tablename__ = "sms"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=False)
    version = Column(String(2), default="A")
    body = Column(Text, nullable=False)
    cta = Column(String(8), default="MORE")
    created_at = Column(DateTime, default=utcnow)
