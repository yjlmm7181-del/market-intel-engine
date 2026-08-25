"""Market pipeline: collect data → build events → persist → serve.

Single entry point used by both the API (on-demand) and the scheduler.
Data sources degrade gracefully: Moomoo (behind a circuit breaker) → yfinance;
AI → deterministic template; news → empty list if unreachable.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from app.analyzers.ai_analyst import AIAnalyst
from app.analyzers.event_engine import EventEngine, EventStock, MarketEventData
from app.collectors.index_collector import IndexCollector, IndexQuote
from app.collectors.mover_collector import MoverCollector, StockMover
from app.collectors.news_collector import NewsCollector
from app.core.config import settings
from app.db.session import SessionLocal
from app.generators.sms_generator import SmsGenerator
from app.models.entities import MarketEvent, NewsItem, SmsMessage
from app.providers.ai.openai_provider import AIProvider
from app.providers.circuit_breaker import CircuitBreakerProvider
from app.providers.fallback import YFinanceProvider
from app.providers.moomoo import MoomooOpenDConnector
from app.providers.news.moomoo_news import MoomooNewsProvider
from app.services.dedup import Dedup


@dataclass
class Snapshot:
    indexes: list[IndexQuote] = field(default_factory=list)
    movers: list[StockMover] = field(default_factory=list)
    news: list[dict] = field(default_factory=list)
    events: list[MarketEventData] = field(default_factory=list)


class MarketPipeline:
    def __init__(self) -> None:
        moomoo = CircuitBreakerProvider(
            MoomooOpenDConnector(host=settings.moomoo_host, port=settings.moomoo_port)
        )
        yf = YFinanceProvider()
        self.index_collector = IndexCollector(moomoo, yf)
        self.mover_collector = MoverCollector(moomoo, yf, top_n=settings.mover_top_n)
        self.news_collector = NewsCollector(
            MoomooNewsProvider(base_url=settings.news_base_url, lang=settings.news_lang),
            Dedup(),
            size=settings.news_size,
        )
        ai = AIProvider(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            model=settings.ai_model,
        )
        self.engine = EventEngine()
        self.analyst = AIAnalyst(ai)
        self.sms = SmsGenerator(ai)

        self._cache: dict = {}
        self._cache_ts = 0.0

    # -- collection --------------------------------------------------------
    def refresh(self) -> Snapshot:
        indexes = self.index_collector.collect()
        all_movers = self.mover_collector.collect_all()
        top_movers = self._top_n(all_movers, settings.mover_top_n)
        news = self.news_collector.collect()
        events = self.engine.build(all_movers, news, indexes)
        for e in events:
            e.ai_summary, e.summary_source = self.analyst.summarize(e)

        snap = Snapshot(indexes=indexes, movers=top_movers, news=news, events=events)
        self._persist(snap)
        self._cache = self._to_dict(snap)
        self._cache_ts = time.time()
        return snap

    def get_overview(self, force: bool = False) -> dict:
        if not force and self._cache and (time.time() - self._cache_ts) < settings.cache_ttl_seconds:
            return self._cache
        self.refresh()
        return self._cache

    def clear_cache(self) -> None:
        self._cache = {}
        self._cache_ts = 0.0

    @staticmethod
    def _top_n(movers: list[StockMover], n: int) -> list[StockMover]:
        s = sorted(
            movers,
            key=lambda m: m.change_rate if m.change_rate is not None else -1e9,
            reverse=True,
        )
        return s[:n]

    # -- persistence -------------------------------------------------------
    def _persist(self, snap: Snapshot) -> None:
        try:
            db = SessionLocal()
            try:
                for n in snap.news:
                    nid = n.get("news_id") or ""
                    if not nid:
                        continue
                    if db.query(NewsItem).filter(NewsItem.news_id == nid).first() is None:
                        db.add(NewsItem(
                            news_id=nid,
                            title=n.get("title", ""),
                            url=n.get("url", ""),
                            publish_time=int(n.get("publish_time") or 0),
                            news_type=int(n.get("news_type") or 1),
                            source="moomoo",
                        ))
                for e in snap.events:
                    row = db.query(MarketEvent).filter(MarketEvent.theme == e.theme).first()
                    if row is None:
                        row = MarketEvent(theme=e.theme, title=e.title)
                        db.add(row)
                    row.title = e.title
                    row.heat_score = e.heat_score
                    row.index_key = e.index_key
                    row.index_change = e.index_change
                    row.set_stocks([
                        {"symbol": s.symbol, "name": s.name, "change_rate": s.change_rate}
                        for s in e.stocks
                    ])
                    row.set_news(e.news)
                    row.ai_summary = e.ai_summary
                    row.summary_source = e.summary_source
                    db.flush()
                    e.id = row.id
                db.commit()
            finally:
                db.close()
        except Exception:
            # Persistence is best-effort; the API still serves live data.
            pass

    # -- events ------------------------------------------------------------
    def get_event(self, event_id: int) -> Optional[dict]:
        db = SessionLocal()
        try:
            row = db.query(MarketEvent).filter(MarketEvent.id == event_id).first()
            if row is None:
                return None
            return self._row_to_dict(row)
        finally:
            db.close()

    def _row_to_dict(self, row: MarketEvent) -> dict:
        stocks = [EventStock(s["symbol"], s["name"], s["change_rate"]) for s in row.get_stocks()]
        e = MarketEventData(
            theme=row.theme, title=row.title, heat_score=row.heat_score, id=row.id,
            index_key=row.index_key, index_change=row.index_change,
            stocks=stocks, news=row.get_news(),
            ai_summary=row.ai_summary, summary_source=row.summary_source,
        )
        return self.event_to_dict(e)

    def event_to_dict(self, e: MarketEventData) -> dict:
        return {
            "id": e.id,
            "theme": e.theme,
            "title": e.title,
            "heat_score": e.heat_score,
            "index_key": e.index_key,
            "index_change": e.index_change,
            "stocks": [{"symbol": s.symbol, "name": s.name, "change_rate": s.change_rate}
                       for s in e.stocks],
            "news": e.news,
            "ai_summary": e.ai_summary,
            "summary_source": e.summary_source,
        }

    # -- sms ---------------------------------------------------------------
    def generate_sms(self, event_id: int) -> list[dict]:
        event_dict = self.get_event(event_id)
        if event_dict is None:
            return []
        event = self._dict_to_event(event_dict)
        drafts = self.sms.generate(event)
        saved: list[dict] = []
        db = SessionLocal()
        try:
            for d in drafts:
                msg = SmsMessage(event_id=event_id, version=d.version, body=d.body, cta=d.cta)
                db.add(msg)
                db.flush()
                saved.append({"id": msg.id, "event_id": event_id,
                              "version": d.version, "body": d.body, "cta": d.cta})
            db.commit()
        finally:
            db.close()
        return saved

    def list_sms(self) -> list[dict]:
        db = SessionLocal()
        try:
            rows = db.query(SmsMessage).order_by(SmsMessage.id.desc()).limit(30).all()
            return [{"id": r.id, "event_id": r.event_id, "version": r.version,
                     "body": r.body, "cta": r.cta} for r in rows]
        finally:
            db.close()

    def regenerate_sms(self, sms_id: int) -> Optional[dict]:
        db = SessionLocal()
        try:
            row = db.query(SmsMessage).filter(SmsMessage.id == sms_id).first()
            event_id = row.event_id if row is not None else None
        finally:
            db.close()
        if event_id is None:
            return None
        event_dict = self.get_event(event_id)
        if event_dict is None:
            return None
        drafts = self.sms.generate(self._dict_to_event(event_dict))
        d = drafts[0] if drafts else None
        if d is None:
            return None
        db = SessionLocal()
        try:
            msg = SmsMessage(event_id=event_id, version="R", body=d.body, cta=d.cta)
            db.add(msg)
            db.flush()
            out = {"id": msg.id, "event_id": event_id, "version": "R", "body": d.body, "cta": d.cta}
            db.commit()
            return out
        finally:
            db.close()

    def analyze_event(self, event_id: int) -> Optional[dict]:
        db = SessionLocal()
        try:
            row = db.query(MarketEvent).filter(MarketEvent.id == event_id).first()
            if row is None:
                return None
            event = MarketEventData(
                theme=row.theme, title=row.title, heat_score=row.heat_score, id=row.id,
                index_key=row.index_key, index_change=row.index_change,
                stocks=[EventStock(s["symbol"], s["name"], s["change_rate"])
                        for s in row.get_stocks()],
                news=row.get_news(),
            )
            summary, source = self.analyst.summarize(event)
            event.ai_summary, event.summary_source = summary, source
            row.ai_summary = summary
            row.summary_source = source
            db.commit()
            return self.event_to_dict(event)
        finally:
            db.close()

    @staticmethod
    def _dict_to_event(d: dict) -> MarketEventData:
        return MarketEventData(
            theme=d["theme"], title=d["title"], heat_score=d["heat_score"], id=d["id"],
            index_key=d["index_key"], index_change=d["index_change"],
            stocks=[EventStock(s["symbol"], s["name"], s["change_rate"]) for s in d["stocks"]],
            news=d["news"], ai_summary=d["ai_summary"], summary_source=d["summary_source"],
        )

    # -- serialization -----------------------------------------------------
    def _to_dict(self, snap: Snapshot) -> dict:
        return {
            "indexes": [{"key": q.key, "name": q.name, "last_price": q.last_price,
                         "change_rate": q.change_rate, "source": q.source}
                        for q in snap.indexes],
            "movers": [{"symbol": m.symbol, "name": m.name, "last_price": m.last_price,
                        "change_rate": m.change_rate, "source": m.source}
                       for m in snap.movers],
            "news": [{"news_id": n.get("news_id", ""), "title": n.get("title", ""),
                      "url": n.get("url", ""), "publish_time": int(n.get("publish_time") or 0),
                      "source": "moomoo"} for n in snap.news],
            "events": [self.event_to_dict(e) for e in snap.events],
        }


pipeline = MarketPipeline()
