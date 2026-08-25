"""Market Event Engine: cluster movers + news into themed events.

A theme (e.g. "AI / Semiconductor") becomes a Market Event when any of its
stocks appear in today's movers OR any headline matches its keywords. Heat
score comes from the composite in ``heat_score.py``.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.analyzers.heat_score import compute_heat_score
from app.collectors.mover_collector import StockMover
from app.core.universe import SYMBOL_NAMES, THEMES, Theme


@dataclass
class EventStock:
    symbol: str
    name: str
    change_rate: Optional[float]


@dataclass
class MarketEventData:
    theme: str
    title: str
    heat_score: int
    id: Optional[int] = None
    index_key: str = ""
    index_change: Optional[float] = None
    stocks: list[EventStock] = field(default_factory=list)
    news: list[dict] = field(default_factory=list)  # [{title, url}]
    ai_summary: str = ""
    summary_source: str = "template"


def _matches(text: str, keywords) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


class EventEngine:
    def __init__(self, themes: Optional[list[Theme]] = None):
        self.themes = themes if themes is not None else THEMES

    def build(
        self,
        movers: list[StockMover],
        news: list[dict],
        index_quotes,
    ) -> list[MarketEventData]:
        index_map = {q.key: q for q in index_quotes}
        ranked = sorted(
            movers,
            key=lambda m: m.change_rate if m.change_rate is not None else -1e9,
            reverse=True,
        )
        rank_of = {m.symbol: i + 1 for i, m in enumerate(ranked)}

        events: list[MarketEventData] = []
        for th in self.themes:
            matched_stocks = [m for m in movers if m.symbol in th.stocks]
            matched_news = [n for n in news if _matches(n.get("title", ""), th.keywords)]
            if not matched_stocks and not matched_news:
                continue

            index_change: Optional[float] = None
            iq = index_map.get(th.index_key)
            if iq is not None:
                index_change = iq.change_rate

            has_top = any(rank_of.get(s.symbol, 999) <= 3 for s in matched_stocks)
            changes = [s.change_rate for s in matched_stocks if s.change_rate is not None]
            heat = compute_heat_score(changes, index_change, len(matched_news), has_top)

            stocks = [
                EventStock(s.symbol, s.name or SYMBOL_NAMES.get(s.symbol, s.symbol), s.change_rate)
                for s in matched_stocks
            ]
            stocks.sort(
                key=lambda s: s.change_rate if s.change_rate is not None else -1e9,
                reverse=True,
            )

            events.append(
                MarketEventData(
                    theme=th.key,
                    title=th.title,
                    heat_score=heat,
                    index_key=th.index_key,
                    index_change=index_change,
                    stocks=stocks,
                    news=[{"title": n.get("title", ""), "url": n.get("url", "")}
                          for n in matched_news],
                )
            )

        events.sort(key=lambda e: e.heat_score, reverse=True)
        return events
