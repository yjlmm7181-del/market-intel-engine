import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.providers.base import ProviderAPIError
from app.providers.moomoo.connector import MoomooOpenDConnector, moomoo_code


class FakeDF:
    """Minimal DataFrame stand-in exposing .to_dict('records')."""

    def __init__(self, records):
        self._records = records

    def to_dict(self, orient="records"):
        assert orient == "records"
        return self._records


class FakeCtx:
    def __init__(self, snapshot_records=None, quote_records=None):
        self.snapshot_records = snapshot_records or []
        self.quote_records = quote_records or []
        self.closed = False

    def get_market_snapshot(self, codes):
        return 0, FakeDF(self.snapshot_records)

    def get_stock_quote(self, codes):
        return 0, FakeDF(self.quote_records)

    def close(self):
        self.closed = True


def _connector():
    c = MoomooOpenDConnector(host="127.0.0.1", port=11111)
    c._ctx = FakeCtx(
        snapshot_records=[
            {
                "code": "US.AAPL",
                "name": "Apple",
                "last_price": 220.0,
                "prev_close_price": 215.0,
                "open_price": 216.0,
                "high_price": 222.0,
                "low_price": 215.5,
                "volume": 5e7,
                "turnover": 1.1e10,
                "update_time": "2026-08-25 16:00:00",
            }
        ]
    )
    return c


def test_moomoo_code():
    assert moomoo_code("us", "aapl") == "US.AAPL"
    assert moomoo_code("US", "NVDA") == "US.NVDA"


def test_snapshot_normalization_and_change_rate():
    c = _connector()
    snaps = c.get_snapshot(["US.AAPL"])
    assert len(snaps) == 1
    s = snaps[0]
    assert s.code == "US.AAPL"
    assert s.name == "Apple"
    assert s.last_price == 220.0
    assert s.prev_close == 215.0
    # (220 - 215) / 215 * 100 = 2.3256
    assert s.change_rate == round((220 - 215) / 215 * 100, 4)


def test_empty_data_returns_empty_list():
    c = MoomooOpenDConnector()
    c._ctx = FakeCtx(snapshot_records=[])
    assert c.get_snapshot(["US.AAPL"]) == []


def test_close_sets_disconnected():
    c = _connector()
    ctx = c._ctx  # hold a reference before close() nulls it
    assert c.is_connected() is True
    c.close()
    assert c.is_connected() is False
    assert ctx.closed is True


def test_api_error_on_nonzero_ret():
    class BadCtx:
        def get_market_snapshot(self, codes):
            return -1, "some error"

    c = MoomooOpenDConnector()
    c._ctx = BadCtx()
    with pytest.raises(ProviderAPIError):
        c.get_snapshot(["US.AAPL"])


def test_api_error_on_exception():
    class BoomCtx:
        def get_stock_quote(self, codes):
            raise ConnectionError("socket refused")

    c = MoomooOpenDConnector()
    c._ctx = BoomCtx()
    with pytest.raises(ProviderAPIError):
        c.get_quote(["US.AAPL"])
