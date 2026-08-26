import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.analyzers.ai_analyst import AIAnalyst
from app.analyzers.event_engine import EventStock, MarketEventData
from app.generators.sms_generator import CTA_SET, FORBIDDEN, SmsGenerator, VERSIONS
from app.providers.ai.openai_provider import AIProvider


def _event():
    return MarketEventData(
        theme="ai_semiconductor",
        title="AI / Semiconductor",
        heat_score=94,
        index_key="nasdaq",
        index_change=1.86,
        stocks=[
            EventStock("NVDA", "NVIDIA", 6.2),
            EventStock("AMD", "AMD", 5.4),
            EventStock("AVGO", "Broadcom", 4.3),
        ],
        news=[{"title": "AI chip rally", "url": "https://x/1"}],
    )


def test_template_analyst_falls_back_without_key():
    analyst = AIAnalyst(AIProvider(api_key=""))
    text, source = analyst.summarize(_event())
    assert source == "template"
    assert "AI / Semiconductor" in text
    assert "NVDA" in text


def test_sms_deck_distinct_natural():
    gen = SmsGenerator()
    drafts = gen.generate_deck(_event())
    assert len(drafts) == 7
    bodies = [d.body for d in drafts]
    assert len(set(bodies)) == 7  # no duplicated content
    for d in drafts:
        assert d.version in VERSIONS
        assert d.cta in CTA_SET
        assert d.body and d.body_zh
        assert '%' not in d.body          # no percentages
        assert 'STOP' in d.body           # STOP opt-out preserved
        low = d.body.lower()
        assert not any(w in low for w in FORBIDDEN)


def test_sms_refresh_one_avoids_history():
    gen = SmsGenerator()
    event = _event()
    deck = gen.generate_deck(event)
    others = [d.body for d in deck if d.version != "A"]
    fresh = gen.generate_one(event, "A", avoid=others)
    assert fresh.body not in others
    assert fresh.cta == "MORE"
    assert 'STOP' in fresh.body


def test_ai_analyst_uses_ai_when_available():
    class FakeAI(AIProvider):
        @property
        def available(self):
            return True

        def complete(self, system, user, max_tokens=500):
            return "AI and semiconductor stocks lead today's session."

    analyst = AIAnalyst(FakeAI(api_key="k"))
    text, source = analyst.summarize(_event())
    assert source == "ai"
    assert text == "AI and semiconductor stocks lead today's session."
