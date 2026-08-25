"""AI market analyst — English summary for a market event (AI if key, else template)."""

from app.analyzers.event_engine import MarketEventData
from app.providers.ai.openai_provider import AIProvider

SYSTEM_PROMPT = (
    "You are a concise US stock-market analyst. Write a 2-3 sentence English summary "
    "of a market theme for retail investors. Mention the leading stocks and the index "
    "move. No markdown, no disclaimers."
)


def _template(event: MarketEventData) -> str:
    lead = event.stocks[0] if event.stocks else None
    if lead and lead.change_rate is not None:
        if lead.change_rate >= 0:
            head = f"{lead.name} ({lead.symbol}) is up {lead.change_rate:.1f}%"
        else:
            head = f"{lead.name} ({lead.symbol}) is down {abs(lead.change_rate):.1f}%"
    else:
        head = f"{event.title} stocks are active"

    idx = ""
    if event.index_change is not None:
        direction = "up" if event.index_change >= 0 else "down"
        idx = f", with the {event.index_key.upper()} {direction} {abs(event.index_change):.2f}%"

    news = f" {len(event.news)} related headlines" if event.news else ""
    return f"{event.title} is leading today's market move: {head}{idx}.{news} are driving the theme."


def _build_prompt(event: MarketEventData) -> str:
    stocks = ", ".join(
        f"{s.symbol} {s.change_rate:+.1f}%"
        for s in event.stocks[:6]
        if s.change_rate is not None
    )
    idx = f"{event.index_key} {event.index_change:+.2f}%" if event.index_change is not None else "n/a"
    headlines = "; ".join(n.get("title", "")[:120] for n in event.news[:3])
    return (
        f"Theme: {event.title}\n"
        f"Index: {idx}\n"
        f"Leading stocks: {stocks}\n"
        f"Headlines: {headlines}\n"
        "Summarize why this theme is hot today in 2-3 sentences."
    )


class AIAnalyst:
    def __init__(self, ai: AIProvider):
        self.ai = ai

    def summarize(self, event: MarketEventData):
        if self.ai.available:
            user = _build_prompt(event)
            text = self.ai.complete(SYSTEM_PROMPT, user)
            if text and text.strip():
                return text.strip(), "ai"
        return _template(event), "template"
