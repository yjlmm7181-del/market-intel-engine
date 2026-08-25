import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import yfinance

from app.collectors.index_collector import DEFAULT_INDICES, IndexCollector
from app.providers.base import MarketDataProvider, ProviderAPIError, Snapshot


class StubProvider(MarketDataProvider):
    """Configurable in-memory provider for failover tests."""

    def __init__(self, result=None, error=None):
        self.result = result  # list[Snapshot] to return, or None
        self.error = error    # ProviderError to raise
        self.calls = []

    def connect(self):
        pass

    def close(self):
        pass

    def is_connected(self):
        return True

    def get_snapshot(self, codes):
        self.calls.append(list(codes))
        if self.error:
            raise self.error
        return self.result or []

    def get_quote(self, codes):
        return self.get_snapshot(codes)


def _snap(code, last=100.0, prev=98.0):
    return Snapshot(code=code, last_price=last, prev_close=prev,
                    change_rate=round((last - prev) / prev * 100, 4))


# -- IndexCollector failover ------------------------------------------------

def test_uses_primary_when_available():
    primary = StubProvider(result=[_snap("US.SPX", 5000.0, 4950.0)])
    fallback = StubProvider(result=[_snap("^GSPC", 1.0, 1.0)])
    c = IndexCollector(primary, fallback)
    quotes = c.collect()
    assert len(quotes) == 3
    sp = quotes[0]
    assert sp.key == "sp500"
    assert sp.name == "S&P 500"
    assert sp.source == "moomoo"
    # fallback never called
    assert fallback.calls == []


def test_falls_back_when_primary_raises():
    primary = StubProvider(error=ProviderAPIError("OpenD down"))
    fallback = StubProvider(result=[_snap("^GSPC", 5000.0, 4950.0)])
    c = IndexCollector(primary, fallback)
    quotes = c.collect()
    assert all(q.source == "yfinance" for q in quotes)


def test_falls_back_when_primary_returns_empty():
    primary = StubProvider(result=[])  # e.g. US.SPX unsupported -> empty
    fallback = StubProvider(result=[_snap("^GSPC", 5000.0, 4950.0)])
    c = IndexCollector(primary, fallback)
    quotes = c.collect()
    assert all(q.source == "yfinance" for q in quotes)


def test_skips_index_when_both_fail():
    primary = StubProvider(error=ProviderAPIError("down"))
    fallback = StubProvider(error=ProviderAPIError("down too"))
    c = IndexCollector(primary, fallback)
    assert c.collect() == []


def test_default_indices_have_three_members():
    assert [i.key for i in DEFAULT_INDICES] == ["sp500", "nasdaq", "dow"]


# -- YFinanceProvider normalization (no network) ----------------------------

def test_yfinance_snapshot_normalization(monkeypatch):
    from app.providers.fallback.yfinance_provider import YFinanceProvider

    class FakeFastInfo(dict):
        pass

    class FakeTicker:
        def __init__(self, symbol):
            self.fast_info = FakeFastInfo({
                "lastPrice": 220.0,
                "previousClose": 215.0,
                "open": 216.0,
                "dayHigh": 222.0,
                "dayLow": 214.0,
                "lastVolume": 5e7,
            })

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    p = YFinanceProvider()
    snaps = p.get_snapshot(["^GSPC"])
    assert len(snaps) == 1
    s = snaps[0]
    assert s.code == "^GSPC"
    assert s.last_price == 220.0
    assert s.prev_close == 215.0
    assert s.change_rate == round((220 - 215) / 215 * 100, 4)


def test_yfinance_raises_provider_error_on_failure(monkeypatch):
    from app.providers.fallback.yfinance_provider import YFinanceProvider

    def boom(symbol):
        raise RuntimeError("yahoo unreachable")

    monkeypatch.setattr(yfinance, "Ticker", boom)
    p = YFinanceProvider()
    with pytest.raises(ProviderAPIError):
        p.get_snapshot(["^GSPC"])
