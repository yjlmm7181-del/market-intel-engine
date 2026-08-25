"""Heat score — deterministic 0-100 composite for a market theme."""

from typing import Optional, Sequence


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def compute_heat_score(
    stock_changes: Sequence[float],
    index_change: Optional[float] = None,
    news_count: int = 0,
    has_top_gainer: bool = False,
) -> int:
    """Composite heat:
    - baseline 30
    - avg stock move (weight 3, capped ±20)
    - index move (weight 2, capped ±15)
    - news count (8 each, capped +24)
    - top-gainer bonus +15
    Clamped to [0, 100].
    """
    score = 30.0
    if stock_changes:
        avg = sum(stock_changes) / len(stock_changes)
        score += _clamp(avg * 3.0, -20.0, 30.0)
    if index_change is not None:
        score += _clamp(index_change * 2.0, -15.0, 15.0)
    score += min(news_count * 8.0, 24.0)
    if has_top_gainer:
        score += 15.0
    return int(round(_clamp(score, 0.0, 100.0)))
