"""Top-level API router.

Endpoints are mounted here module by module as they are built, e.g.:

    from app.api.endpoints import market, stocks, news, events, sms
    api_router.include_router(market.router, prefix="/market", tags=["market"])

Final surface (per spec):
    GET  /api/market/overview
    GET  /api/market/indexes
    GET  /api/stocks/movers
    GET  /api/news
    GET  /api/events
    GET  /api/events/{event_id}
    POST /api/events/{event_id}/analyze
    POST /api/events/{event_id}/generate-sms
    GET  /api/sms
    POST /api/sms/{id}/regenerate
"""

from fastapi import APIRouter

from app.api.endpoints import events, market, news, sms, stocks

api_router = APIRouter()
api_router.include_router(market.router)
api_router.include_router(stocks.router)
api_router.include_router(news.router)
api_router.include_router(events.router)
api_router.include_router(sms.router)
