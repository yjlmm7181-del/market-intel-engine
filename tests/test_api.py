import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest
from fastapi.testclient import TestClient

from app.collectors.index_collector import IndexQuote
from app.collectors.mover_collector import StockMover
from app.core.config import settings
from app.db.session import Base, engine, init_db
from app.main import app
from app.services import market_pipeline as mp


class StubIndexCollector:
    def collect(self):
        return [
            IndexQuote("sp500", "S&P 500", "US.SPX", 5000.0, 4990.0, 0.2, "yfinance"),
            IndexQuote("nasdaq", "NASDAQ", "US.IXIC", 18000.0, 17700.0, 1.86, "yfinance"),
            IndexQuote("dow", "Dow", "US.DJI", 40000.0, 40010.0, -0.02, "yfinance"),
        ]


class StubMoverCollector:
    def collect_all(self):
        return [
            StockMover("NVDA", "NVIDIA", 100.0, 6.2, "yfinance"),
            StockMover("AMD", "AMD", 90.0, 5.4, "yfinance"),
            StockMover("AVGO", "Broadcom", 80.0, 4.3, "yfinance"),
            StockMover("TSLA", "Tesla", 70.0, -1.5, "yfinance"),
        ]


class StubNewsCollector:
    def collect(self, terms=None):
        return [
            {"news_id": "n1", "title": "NVIDIA chip demand surges", "url": "https://x/1",
             "publish_time": 1787606631, "news_type": 1},
            {"news_id": "n2", "title": "AI semiconductor rally", "url": "https://x/2",
             "publish_time": 1787606631, "news_type": 1},
            {"news_id": "n3", "title": "Tesla EV deliveries miss", "url": "https://x/3",
             "publish_time": 1787606631, "news_type": 1},
        ]


@pytest.fixture()
def client(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    init_db()
    # remove any on-disk snapshot cache so stale event ids don't leak between tests
    if os.path.exists(settings.cache_file):
        os.remove(settings.cache_file)
    monkeypatch.setattr(mp.pipeline, "index_collector", StubIndexCollector())
    monkeypatch.setattr(mp.pipeline, "mover_collector", StubMoverCollector())
    monkeypatch.setattr(mp.pipeline, "news_collector", StubNewsCollector())
    mp.pipeline.clear_cache()
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_overview_shape(client):
    r = client.get("/api/market/overview")
    assert r.status_code == 200
    data = r.json()
    assert len(data["indexes"]) == 3
    assert len(data["movers"]) == 4
    assert len(data["news"]) == 3
    assert len(data["events"]) >= 1
    # events are persisted, so they carry ids
    for e in data["events"]:
        assert e["id"] is not None
        assert 0 <= e["heat_score"] <= 100
        assert e["ai_summary"]
        assert e["summary_source"] == "template"


def test_indexes_and_movers(client):
    assert len(client.get("/api/market/indexes").json()) == 3
    movers = client.get("/api/stocks/movers").json()
    assert movers[0]["symbol"] == "NVDA"
    assert movers[0]["change_rate"] == 6.2


def test_news(client):
    news = client.get("/api/news").json()
    assert len(news) == 3


def test_event_detail_and_generate_sms(client):
    events = client.get("/api/events").json()
    ev = events[0]
    detail = client.get(f"/api/events/{ev['id']}")
    assert detail.status_code == 200
    assert detail.json()["theme"] == ev["theme"]

    sms = client.post(f"/api/events/{ev['id']}/generate-sms")
    assert sms.status_code == 200
    messages = sms.json()
    assert len(messages) == 7
    assert len({m["body"] for m in messages}) == 7

    all_sms = client.get("/api/sms").json()
    assert len(all_sms) == 7

    regen = client.post(f"/api/sms/{messages[0]['id']}/regenerate")
    assert regen.status_code == 200
    assert regen.json()["version"] == "R"


def test_event_404(client):
    assert client.get("/api/events/99999").status_code == 404
