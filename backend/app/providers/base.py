"""Data-source provider abstractions.

Every external data source (Moomoo OpenD, a fallback market-data API, a news
endpoint, ...) is wrapped behind a Provider interface so the rest of the app
never depends on a concrete SDK. This is the seam where future data sources
get plugged in.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class ProviderError(Exception):
    """Base error for provider failures."""


class ProviderConnectionError(ProviderError):
    """Could not reach / connect to the underlying data source."""


class ProviderAPIError(ProviderError):
    """The data source returned an error response."""


@dataclass
class Snapshot:
    """Normalized market snapshot, independent of any specific SDK."""

    code: str
    name: str = ""
    last_price: Optional[float] = None
    prev_close: Optional[float] = None
    open_price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    turnover: Optional[float] = None
    change_rate: Optional[float] = None  # percent, e.g. 1.86 means +1.86%
    update_time: str = ""


class MarketDataProvider(ABC):
    """Interface for a source of market quotes / snapshots."""

    @abstractmethod
    def connect(self) -> None:
        """Establish / prepare the underlying connection."""

    @abstractmethod
    def close(self) -> None:
        """Tear down the underlying connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the underlying connection is currently established."""

    @abstractmethod
    def get_snapshot(self, codes: list[str]) -> list[Snapshot]:
        """Batch snapshot for one or more symbols (e.g. ['US.AAPL', 'US.NVDA'])."""

    @abstractmethod
    def get_quote(self, codes: list[str]) -> list[Snapshot]:
        """Real-time quote for one or more symbols."""
