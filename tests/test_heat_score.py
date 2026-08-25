import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.analyzers.heat_score import compute_heat_score


def test_baseline():
    assert compute_heat_score([]) == 30


def test_flat_stocks_stay_near_baseline():
    assert compute_heat_score([0.0, 0.0]) == 30


def test_strong_stocks_push_high():
    s = compute_heat_score([5.0, 4.0, 6.0], index_change=1.5, news_count=3, has_top_gainer=True)
    # avg=5.0 -> +15; index +3; news +24; top +15; base 30 = 87
    assert s == 87


def test_caps_at_100():
    s = compute_heat_score([20.0, 20.0], index_change=20.0, news_count=10, has_top_gainer=True)
    assert s == 100


def test_negative_moves_reduce_score():
    s = compute_heat_score([-5.0, -4.0], index_change=-2.0)
    # base 30 + (-4.5*3=-13.5->-13.5) + (-4) = 12.5 -> 13
    assert s < 30
