"""Moomoo OpenD connector.

Wraps the ``moomoo-api`` SDK (the international brand of Futu OpenAPI) behind
the ``MarketDataProvider`` interface.

Key facts (verified against official docs, 2026-08):
- SDK: ``pip install moomoo-api``, ``import moomoo``.
- OpenD is a *local* gateway; default address ``127.0.0.1:11111``.
- OpenD handles login itself — the backend only connects over TCP, it does
  NOT send account credentials.
- ``get_market_snapshot`` requires an explicit code list (there is no
  screener / top-gainers endpoint).
- Snapshot rate limit: 60 requests / 30 seconds.
- US indices are NOT in the OpenAPI quote-permission table — handled by a
  fallback provider in STEP 4.
"""

from typing import Any, Optional

from app.providers.base import (
    MarketDataProvider,
    ProviderAPIError,
    ProviderConnectionError,
    Snapshot,
)

# moomoo.RET_OK == 0. Duplicated here so this module can be imported and unit
# tested without the moomoo SDK installed (the SDK is only needed at runtime).
RET_OK = 0


def moomoo_code(market: str, code: str) -> str:
    """Build a Moomoo symbol such as 'US.AAPL'."""
    return f"{market.upper()}.{code.upper()}"


class MoomooOpenDConnector(MarketDataProvider):
    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        self.host = host
        self.port = port
        self._ctx: Any = None  # moomoo.OpenQuoteContext; injected in tests

    # -- lifecycle ---------------------------------------------------------
    def connect(self) -> None:
        if self._ctx is not None:
            return
        # Fast pre-check: the SDK otherwise retries ~forever when OpenD is down,
        # which would hang the whole pipeline. Fail fast so the caller can fall
        # back to the secondary provider.
        self._check_reachable()
        from moomoo import OpenQuoteContext  # lazy import (runtime only)

        self._ctx = OpenQuoteContext(host=self.host, port=self.port)

    def _check_reachable(self) -> None:
        import socket

        try:
            with socket.create_connection((self.host, self.port), timeout=2):
                pass
        except OSError as exc:
            raise ProviderConnectionError(
                f"OpenD not reachable at {self.host}:{self.port}: {exc}"
            ) from exc

    def close(self) -> None:
        if self._ctx is not None:
            try:
                self._ctx.close()
            finally:
                self._ctx = None

    def is_connected(self) -> bool:
        return self._ctx is not None

    def _require_ctx(self) -> Any:
        self.connect()
        if self._ctx is None:
            raise ProviderConnectionError(
                f"OpenD not reachable at {self.host}:{self.port} — "
                "is OpenD running and logged in?"
            )
        return self._ctx

    # -- data --------------------------------------------------------------
    def get_snapshot(self, codes: list[str]) -> list[Snapshot]:
        ctx = self._require_ctx()
        data = self._call("get_market_snapshot", ctx.get_market_snapshot, list(codes))
        return self._normalize(data)

    def get_quote(self, codes: list[str]) -> list[Snapshot]:
        ctx = self._require_ctx()
        data = self._call("get_stock_quote", ctx.get_stock_quote, list(codes))
        return self._normalize(data)

    # -- helpers -----------------------------------------------------------
    def _call(self, name: str, fn, *args) -> Any:
        """Run a moomoo SDK call and translate its (ret, data) convention."""
        try:
            ret, data = fn(*args)
        except Exception as exc:  # socket errors when OpenD is down, etc.
            raise ProviderAPIError(
                f"{name} failed — OpenD unreachable at {self.host}:{self.port}? {exc}"
            ) from exc
        if ret != RET_OK:
            raise ProviderAPIError(f"{name} returned ret={ret}: {data}")
        return data

    @staticmethod
    def _normalize(data: Any) -> list[Snapshot]:
        """Convert a moomoo DataFrame (or list-of-dicts in tests) to Snapshot."""
        if data is None:
            return []
        records = data.to_dict("records") if hasattr(data, "to_dict") else list(data)
        out: list[Snapshot] = []
        for r in records:
            last = _to_float(r.get("last_price"))
            prev = _to_float(r.get("prev_close_price"))
            change: Optional[float] = None
            if last is not None and prev:
                change = round((last - prev) / prev * 100, 4)
            out.append(
                Snapshot(
                    code=r.get("code", ""),
                    name=r.get("name", ""),
                    last_price=last,
                    prev_close=prev,
                    open_price=_to_float(r.get("open_price")),
                    high=_to_float(r.get("high_price")),
                    low=_to_float(r.get("low_price")),
                    volume=_to_float(r.get("volume")),
                    turnover=_to_float(r.get("turnover")),
                    change_rate=change,
                    update_time=str(r.get("update_time", "")),
                )
            )
        return out


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None
