"""Market pipeline: collect data → build events → persist → serve.

Single entry point used by both the API (on-demand) and the scheduler.
Data sources degrade gracefully: Moomoo (behind a circuit breaker) → yfinance;
AI → deterministic template; news → empty list if unreachable.
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from app.analyzers.ai_analyst import AIAnalyst
from app.analyzers.event_engine import EventEngine, EventStock, MarketEventData
from app.collectors.index_collector import IndexCollector, IndexQuote
from app.collectors.mover_collector import MoverCollector, StockMover
from app.collectors.news_collector import NewsCollector
from app.core.config import settings
from app.db.session import SessionLocal
from app.generators.sms_generator import SmsGenerator, VERSIONS
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
        # Separate provider instances per collector so they can run in parallel
        # without sharing connection state.
        def _moomoo():
            return CircuitBreakerProvider(
                MoomooOpenDConnector(host=settings.moomoo_host, port=settings.moomoo_port)
            )

        self.index_collector = IndexCollector(_moomoo(), YFinanceProvider())
        self.mover_collector = MoverCollector(
            _moomoo(), YFinanceProvider(), top_n=settings.mover_top_n
        )
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
        self._cache_file = settings.cache_file
        self._refresh_lock = threading.Lock()
        self._decks: dict = {}

    # -- collection --------------------------------------------------------
    def refresh(self) -> Snapshot:
        # Only one refresh runs at a time; a second caller waits for the
        # in-flight one and reuses its cached result.
        if not self._refresh_lock.acquire(blocking=False):
            self._refresh_lock.acquire()
            self._refresh_lock.release()
            return Snapshot()

        try:
            # Collect indexes / movers / news in parallel to cut cold-start
            # latency (the yfinance batch snapshot is the slowest, ~18s).
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=3) as ex:
                f_idx = ex.submit(self.index_collector.collect)
                f_mov = ex.submit(self.mover_collector.collect_all)
                f_news = ex.submit(self.news_collector.collect)
                indexes = f_idx.result()
                all_movers = f_mov.result()
                news = f_news.result()

            top_movers = self._top_n(all_movers, settings.mover_top_n)
            events = self.engine.build(all_movers, news, indexes)
            for e in events:
                e.ai_summary, e.summary_source = self.analyst.summarize(e)

            snap = Snapshot(indexes=indexes, movers=top_movers, news=news, events=events)
            self._persist(snap)
            self._cache = self._to_dict(snap)
            self._cache_ts = time.time()
            self._save_disk_cache()
            return snap
        finally:
            self._refresh_lock.release()

    def get_overview(self, force: bool = False) -> dict:
        now = time.time()
        if not force and self._cache and (now - self._cache_ts) < settings.cache_ttl_seconds:
            return self._cache
        # Serve the last on-disk snapshot instantly (free tier loses RAM cache
        # when it sleeps) and refresh in the background.
        if not force:
            disk = self._load_disk_cache()
            if disk:
                self._cache = disk
                self._cache_ts = now
                self._refresh_async()
                return self._cache
        self.refresh()
        return self._cache

    def clear_cache(self) -> None:
        self._cache = {}
        self._cache_ts = 0.0

    # -- on-disk snapshot cache -------------------------------------------
    def _save_disk_cache(self) -> None:
        try:
            tmp = self._cache_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"ts": time.time(), "data": self._cache}, f)
            os.replace(tmp, self._cache_file)
        except Exception:
            pass

    def _load_disk_cache(self) -> Optional[dict]:
        try:
            with open(self._cache_file, encoding="utf-8") as f:
                payload = json.load(f)
            data = payload.get("data")
            return data if data else None
        except Exception:
            return None

    def _refresh_async(self) -> None:
        def _run():
            try:
                self.refresh()
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

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
    def generate_sms(self, event_id: int, style: str = "hook") -> list[dict]:
        event_dict = self.get_event(event_id)
        if event_dict is None:
            return []
        event = self._dict_to_event(event_dict)
        self._seed_sms_history()
        drafts = self.sms.generate_deck(event, style)
        return self._persist_drafts(event_id, drafts)

    def generate_sms_deck(self, event_id: int, style: str = "hook") -> dict:
        event_dict = self.get_event(event_id)
        if event_dict is None:
            return {}
        event = self._dict_to_event(event_dict)
        self._seed_sms_history()
        drafts = self.sms.generate_deck(event, style)
        messages = self._persist_drafts(event_id, drafts)
        deck_id = str(uuid4())
        self._decks[deck_id] = {m["version"]: m["body"] for m in messages}
        return {"deck_id": deck_id, "messages": messages}

    def refresh_sms_card(self, event_id: int, deck_id: str, version: str, style: str = "hook") -> Optional[dict]:
        deck = self._decks.get(deck_id)
        if deck is None:
            return None
        event_dict = self.get_event(event_id)
        if event_dict is None:
            return None
        event = self._dict_to_event(event_dict)
        self._seed_sms_history()
        avoid = [body for v, body in deck.items() if v != version]
        draft = self.sms.generate_one(event, version, style, avoid=avoid)
        msg = self._persist_draft(event_id, draft)
        deck[version] = msg["body"]
        return msg

    def refresh_sms_all(self, event_id: int, style: str = "hook") -> dict:
        return self.generate_sms_deck(event_id, style)

    def list_sms(self) -> list[dict]:
        db = SessionLocal()
        try:
            rows = db.query(SmsMessage).order_by(SmsMessage.id.desc()).limit(30).all()
            return [{"id": r.id, "event_id": r.event_id, "version": r.version,
                     "body": r.body, "cta": r.cta, "body_zh": r.body_zh} for r in rows]
        finally:
            db.close()

    def regenerate_sms(self, sms_id: int) -> Optional[dict]:
        db = SessionLocal()
        try:
            row = db.query(SmsMessage).filter(SmsMessage.id == sms_id).first()
            event_id = row.event_id if row is not None else None
            version = row.version if row is not None and row.version in VERSIONS else "A"
        finally:
            db.close()
        if event_id is None:
            return None
        event_dict = self.get_event(event_id)
        if event_dict is None:
            return None
        self._seed_sms_history()
        draft = self.sms.generate_one(self._dict_to_event(event_dict), version)
        return self._persist_draft(event_id, draft)

    # -- sms helpers -------------------------------------------------------
    def _seed_sms_history(self) -> None:
        try:
            db = SessionLocal()
            try:
                rows = db.query(SmsMessage.body).order_by(SmsMessage.id.desc()).limit(200).all()
                self.sms.seed_bodies([r[0] for r in rows])
            finally:
                db.close()
        except Exception:
            pass

    def _persist_drafts(self, event_id: int, drafts) -> list[dict]:
        saved: list[dict] = []
        db = SessionLocal()
        try:
            for d in drafts:
                msg = SmsMessage(event_id=event_id, version=d.version, body=d.body,
                                 cta=d.cta, body_zh=d.body_zh)
                db.add(msg)
                db.flush()
                saved.append({"id": msg.id, "event_id": event_id, "version": d.version,
                              "body": d.body, "cta": d.cta, "body_zh": d.body_zh})
            db.commit()
        finally:
            db.close()
        return saved

    def _persist_draft(self, event_id: int, draft) -> dict:
        return self._persist_drafts(event_id, [draft])[0]

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
