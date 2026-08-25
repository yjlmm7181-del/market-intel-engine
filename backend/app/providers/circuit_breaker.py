"""Circuit-breaker wrapper for a data provider.

If the inner provider fails (e.g. OpenD is down), we open the circuit for a
cooldown window so every request doesn't re-attempt a slow connection, and the
collector falls back to its secondary provider immediately.
"""

import time

from app.providers.base import MarketDataProvider, ProviderConnectionError


class CircuitBreakerProvider(MarketDataProvider):
    def __init__(self, inner: MarketDataProvider, cooldown_seconds: int = 300):
        self.inner = inner
        self.cooldown_seconds = cooldown_seconds
        self._open_until = 0.0

    def _check(self) -> None:
        if time.time() < self._open_until:
            raise ProviderConnectionError("provider circuit open (previous failure)")

    def _guard(self, fn, *args):
        self._check()
        try:
            return fn(*args)
        except Exception:
            self._open_until = time.time() + self.cooldown_seconds
            raise

    def connect(self) -> None:
        self.inner.connect()

    def close(self) -> None:
        self.inner.close()

    def is_connected(self) -> bool:
        return self.inner.is_connected()

    def get_snapshot(self, codes: list[str]):
        return self._guard(self.inner.get_snapshot, codes)

    def get_quote(self, codes: list[str]):
        return self._guard(self.inner.get_quote, codes)
