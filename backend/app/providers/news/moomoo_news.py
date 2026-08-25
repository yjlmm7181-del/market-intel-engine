"""Moomoo public news search endpoint.

Verified live (2026-08-25): ``GET /news_search`` on ai-news-search.futunn.com.
Required param: ``size``; ``sort_type`` must be 1 (views) or 2 (latest);
optional ``keyword``, ``lang`` (en / zh-CN / zh-HK), ``news_type``
(1=news, 2=notices, 3=research). Returns
``{"code": 0, "data": [{"news_id","news_type","title","publish_time"(unix sec),"url","img_url"}]}``.
"""

import html as _html
import re

import httpx


def _clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", _html.unescape(str(text))).strip()


class MoomooNewsProvider:
    def __init__(
        self,
        base_url: str = "https://ai-news-search.futunn.com",
        lang: str = "en",
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.timeout = timeout

    def search(self, keyword: str = "", size: int = 20, sort_type: int = 2) -> list[dict]:
        params: dict = {"lang": self.lang, "size": size, "sort_type": sort_type}
        if keyword:
            params["keyword"] = keyword
        try:
            r = httpx.get(f"{self.base_url}/news_search", params=params, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return []
        if data.get("code") != 0:
            return []
        items = data.get("data") or []
        for it in items:
            it["title"] = _clean(it.get("title", ""))
        return items
