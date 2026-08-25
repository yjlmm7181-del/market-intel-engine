"""Fallback US market data via yfinance (keyless, Yahoo Finance).

Used where Moomoo OpenAPI has a gap — specifically US index quotes, which are
not in the OpenAPI quote-permission table (see the Moomoo connector docs).

Verified against yfinance 1.6.0: ``Ticker.fast_info`` exposes camelCase keys
``lastPrice``, ``previousClose``, ``open``, ``dayHigh``, ``dayLow``,
``lastVolume`` (note: the key is ``lastVolume``, not ``volume``).
"""

from typing import Any, Optional

from app.providers.base import MarketDataProvider, ProviderAPIError, Snapshot


class YFinanceProvider(MarketDataProvider):
    def __init__(self) -> None:
        self._connected = False

    # -- lifecycle ---------------------------------------------------------
    def connect(self) -> None:
        self._connected = True

    def close(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # -- data --------------------------------------------------------------
    def get_snapshot(self, codes: list[str]) -> list[Snapshot]:
        codes = list(codes)
        if len(codes) == 0:
            return []
        if len(codes) == 1:
            return [self._one(codes[0])]
        return self._batch(codes)

    def get_quote(self, codes: list[str]) -> list[Snapshot]:
        return self.get_snapshot(codes)

    def _batch(self, codes: list[str]) -> list[Snapshot]:
        """Batch daily snapshot via yf.download (single request)."""
        import yfinance as yf

        try:
            df = yf.download(
                codes, period="5d", interval="1d",
                auto_adjust=False, progress=False, group_by="column",
            )
        except Exception as exc:
            raise ProviderAPIError(f"yfinance batch failed: {exc}") from exc
        if df is None or getattr(df, "empty", True):
            return []
        try:
            closes = df["Close"]
        except KeyError:
            return []
        out: list[Snapshot] = []
        for ticker in closes.columns:
            series = closes[ticker].dropna()
            if len(series) < 2:
                continue
            last = float(series.iloc[-1])
            prev = float(series.iloc[-2])
            change: Optional[float] = None
            if prev:
                change = round((last - prev) / prev * 100, 4)
            out.append(
                Snapshot(code=str(ticker), name="", last_price=last,
                         prev_close=prev, change_rate=change)
            )
        return out

    # -- helpers -----------------------------------------------------------
    def _one(self, symbol: str) -> Snapshot:
        import yfinance as yf  # lazy import (runtime only)

        try:
            fi = yf.Ticker(symbol).fast_info
        except Exception as exc:
            raise ProviderAPIError(f"yfinance failed for {symbol}: {exc}") from exc

        last = _get(fi, "lastPrice", "last_price")
        prev = _get(fi, "previousClose", "previous_close")
        change: Optional[float] = None
        if last is not None and prev:
            change = round((last - prev) / prev * 100, 4)

        return Snapshot(
            code=symbol,
            name="",
            last_price=last,
            prev_close=prev,
            open_price=_get(fi, "open"),
            high=_get(fi, "dayHigh", "day_high"),
            low=_get(fi, "dayLow", "day_low"),
            volume=_get(fi, "lastVolume", "volume"),
            turnover=None,
            change_rate=change,
        )


def _get(fi: Any, *keys: str) -> Optional[float]:
    """Return the first present key as a float, else None."""
    for k in keys:
        try:
            v = fi[k]
            if v is None:
                continue
            return float(v)
        except (KeyError, TypeError, ValueError):
            continue
    return None
