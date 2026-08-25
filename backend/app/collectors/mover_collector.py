"""Stock mover collection via self-built basket + snapshot ranking.

Moomoo has no screener, so we snapshot a fixed watchlist and rank by change.
Primary provider = Moomoo (codes "US.XXX"); fallback = yfinance (plain tickers).
"""

from dataclasses import dataclass
from typing import Optional

from app.core.universe import BASKET, SYMBOL_NAMES
from app.providers.base import MarketDataProvider, ProviderError, Snapshot


@dataclass
class StockMover:
    symbol: str
    name: str = ""
    last_price: Optional[float] = None
    change_rate: Optional[float] = None
    source: str = ""


class MoverCollector:
    def __init__(
        self,
        primary: MarketDataProvider,
        fallback: MarketDataProvider,
        basket: Optional[list[str]] = None,
        top_n: int = 10,
    ):
        self.primary = primary
        self.fallback = fallback
        self.basket = basket if basket is not None else BASKET
        self.top_n = top_n

    def collect_all(self) -> list[StockMover]:
        snaps = self._try(self.primary, [f"US.{s}" for s in self.basket])
        source = "moomoo"
        if snaps is None:
            snaps = self._try(self.fallback, self.basket)
            source = "yfinance"
        if snaps is None:
            return []
        return [self._to_mover(s, source) for s in snaps]

    def collect(self, top_n: Optional[int] = None) -> list[StockMover]:
        n = top_n if top_n is not None else self.top_n
        movers = self.collect_all()
        movers.sort(
            key=lambda m: m.change_rate if m.change_rate is not None else -1e9,
            reverse=True,
        )
        return movers[:n]

    def _try(self, provider: MarketDataProvider, codes: list[str]) -> Optional[list[Snapshot]]:
        try:
            snaps = provider.get_snapshot(codes)
        except ProviderError:
            return None
        return snaps or None

    def _to_mover(self, s: Snapshot, source: str) -> StockMover:
        symbol = s.code.split(".")[-1] if "." in s.code else s.code
        return StockMover(
            symbol=symbol,
            name=s.name or SYMBOL_NAMES.get(symbol, symbol),
            last_price=s.last_price,
            change_rate=s.change_rate,
            source=source,
        )
