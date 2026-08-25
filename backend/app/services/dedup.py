"""Deduplication helper.

Uses Redis (optional) as a fast short-term set, with a local in-memory set as
a fallback when Redis is unavailable. The database unique index on
``news.news_id`` remains the source of truth.
"""

import hashlib

from app.core.config import settings


class Dedup:
    def __init__(self) -> None:
        self._mem: set[str] = set()
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            import redis

            r = redis.Redis.from_url(
                settings.redis_url, socket_connect_timeout=1, socket_timeout=1
            )
            r.ping()
            self._redis = r
        except Exception:
            self._redis = None
        return self._redis

    @staticmethod
    def _key(identifier: str) -> str:
        return "news_seen:" + hashlib.sha1(identifier.encode()).hexdigest()

    def is_seen(self, identifier: str) -> bool:
        r = self._get_redis()
        if r is not None:
            try:
                return bool(r.exists(self._key(identifier)))
            except Exception:
                pass
        return identifier in self._mem

    def mark(self, identifier: str) -> None:
        r = self._get_redis()
        if r is not None:
            try:
                r.set(self._key(identifier), "1", ex=86400 * 7)
            except Exception:
                pass
        self._mem.add(identifier)
