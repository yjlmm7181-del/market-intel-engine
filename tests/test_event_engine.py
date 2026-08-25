import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.analyzers.event_engine import EventEngine
from app.collectors.index_collector import IndexQuote
from app.collectors.mover_collector import StockMover


def _movers():
    return [
        StockMover("NVDA", "NVIDIA", 100.0, 6.2, "yfinance"),
        StockMover("AMD", "AMD", 90.0, 5.4, "yfinance"),
        StockMover("AVGO", "Broadcom", 80.0, 4.3, "yfinance"),
        StockMover("TSLA", "Tesla", 70.0, -1.5, "yfinance"),
    ]


def _news():
    return [
        {"title": "NVIDIA chip demand surges", "url": "https://x/1"},
        {"title": "AI semiconductor rally continues", "url": "https://x/2"},
        {"title": "Tesla EV deliveries miss", "url": "https://x/3"},
    ]


def _indexes():
    return [
        IndexQuote("sp500", "S&P 500", "US.SPX", 5000.0, 4990.0, 0.2, "yfinance"),
        IndexQuote("nasdaq", "NASDAQ", "US.IXIC", 18000.0, 17700.0, 1.86, "yfinance"),
        IndexQuote("dow", "Dow", "US.DJI", 40000.0, 40010.0, -0.02, "yfinance"),
    ]


def test_build_events_only_for_matched_themes():
    engine = EventEngine()
    events = engine.build(_movers(), _news(), _indexes())
    themes = {e.theme for e in events}
    assert "ai_semiconductor" in themes   # NVDA/AMD/AVGO + AI news
    assert "ev_clean_energy" in themes    # TSLA + EV news
    # events sorted by heat desc
    scores = [e.heat_score for e in events]
    assert scores == sorted(scores, reverse=True)


def test_event_stocks_are_sorted_desc():
    engine = EventEngine()
    events = engine.build(_movers(), _news(), _indexes())
    ai = next(e for e in events if e.theme == "ai_semiconductor")
    rates = [s.change_rate for s in ai.stocks]
    assert rates == sorted(rates, reverse=True)
    assert ai.stocks[0].symbol == "NVDA"
    assert ai.heat_score > 60


def test_no_matches_produces_no_events():
    engine = EventEngine()
    events = engine.build([StockMover("ZZZ", "Unknown", 10.0, 1.0, "x")], [], _indexes())
    assert events == []
