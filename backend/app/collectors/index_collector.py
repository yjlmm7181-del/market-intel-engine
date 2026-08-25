"""Index quote collection with primary → fallback failover."""

from dataclasses import dataclass
from typing import Optional

from app.providers.base import MarketDataProvider, ProviderError


@dataclass(frozen=True)
class IndexDef:
    key: str
    name: str
    moomoo_code: str
    yf_symbol: str


DEFAULT_INDICES: list[IndexDef] = [
    IndexDef("sp500", "S&P 500", "US.SPX", "^GSPC"),
    IndexDef("nasdaq", "NASDAQ Composite", "US.IXIC", "^IXIC"),
    IndexDef("dow", "Dow Jones Industrial Average", "US.DJI", "^DJI"),
]


@dataclass
class IndexQuote:
    key: str
    name: str
    symbol: str
    last_price: Optional[float] = None
    prev_close: Optional[float] = None
    change_rate: Optional[float] = None
    source: str = ""  # "moomoo" | "yfinance"


class IndexCollector:
    """Collect configured indices, failing over from Moomoo to yfinance.

    Moomoo US index quotes are likely unavailable (see note in the connector),
    so each index is tried on the primary provider first and only falls back
    to the secondary provider when the primary raises or returns nothing.
    """

    def __init__(
        self,
        primary: MarketDataProvider,
        fallback: MarketDataProvider,
        indices: Optional[list[IndexDef]] = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.indices = indices if indices is not None else DEFAULT_INDICES

    def collect(self) -> list[IndexQuote]:
        out: list[IndexQuote] = []
        for idx in self.indices:
            quote = self._from_provider(idx, self.primary, idx.moomoo_code, "moomoo") or \
                self._from_provider(idx, self.fallback, idx.yf_symbol, "yfinance")
            if quote is not None:
                out.append(quote)
        return out

    def _from_provider(
        self,
        idx: IndexDef,
        provider: MarketDataProvider,
        symbol: str,
        source: str,
    ) -> Optional[IndexQuote]:
        try:
            snaps = provider.get_snapshot([symbol])
        except ProviderError:
            return None
        if not snaps:
            return None
        s = snaps[0]
        return IndexQuote(
            key=idx.key,
            name=idx.name,
            symbol=symbol,
            last_price=s.last_price,
            prev_close=s.prev_close,
            change_rate=s.change_rate,
            source=source,
        )
