"""Background scheduler (APScheduler) for periodic market refresh."""

from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = None


def _refresh() -> None:
    from app.services.market_pipeline import pipeline

    try:
        pipeline.refresh()
    except Exception:
        pass


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    from app.core.config import settings

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _refresh,
        "interval",
        minutes=settings.refresh_interval_minutes,
        id="market_refresh",
    )
    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
