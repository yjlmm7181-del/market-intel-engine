"""News collection with dedup across a few broad search terms."""

from typing import Optional

from app.providers.news.moomoo_news import MoomooNewsProvider
from app.services.dedup import Dedup

NEWS_SEARCH_TERMS = ["US stocks market", "artificial intelligence semiconductor", "earnings"]


class NewsCollector:
    def __init__(self, provider: MoomooNewsProvider, dedup: Dedup, size: int = 20):
        self.provider = provider
        self.dedup = dedup
        self.size = size

    def collect(self, terms: Optional[list[str]] = None) -> list[dict]:
        terms = terms or NEWS_SEARCH_TERMS
        seen: dict[str, dict] = {}
        for term in terms:
            for item in self.provider.search(keyword=term, size=self.size):
                nid = item.get("news_id") or ""
                if not nid or nid in seen:
                    continue
                if self.dedup.is_seen(nid):
                    continue
                seen[nid] = item
                self.dedup.mark(nid)
        return list(seen.values())
