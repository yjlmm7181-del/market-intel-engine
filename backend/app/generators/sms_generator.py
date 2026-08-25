"""SMS generator — 3 versions, each ending with a CTA (MORE/LIST/WATCH/FULL/BULL)."""

import json
import re
from dataclasses import dataclass

from app.analyzers.event_engine import MarketEventData
from app.providers.ai.openai_provider import AIProvider

CTAS = ["MORE", "LIST", "WATCH", "FULL", "BULL"]


@dataclass
class SmsDraft:
    version: str
    body: str
    cta: str


SYSTEM_PROMPT = (
    "You write punchy US stock-market SMS alerts for retail investors. "
    "Keep each message under 160 characters. Always end with exactly one call-to-action "
    "keyword chosen from: MORE, LIST, WATCH, FULL, BULL (e.g. 'Reply MORE for details'). "
    "Return JSON only: {\"messages\": [{\"version\": \"A\", \"body\": \"...\", \"cta\": \"MORE\"}, ...]} "
    "with exactly three messages (versions A, B, C), each with a different CTA."
)


def _fmt_change(change) -> str:
    if change is None:
        return "moving"
    return f"{change:+.1f}%"


def _template(event: MarketEventData) -> list[SmsDraft]:
    lead = event.stocks[0] if event.stocks else None
    second = event.stocks[1] if len(event.stocks) > 1 else None
    theme = event.title

    idx = ""
    if event.index_change is not None:
        idx = f"{event.index_key.upper()} {event.index_change:+.2f}%"

    out: list[SmsDraft] = []
    if lead:
        out.append(SmsDraft(
            "A",
            f"\U0001F525 {theme}: {lead.symbol} {_fmt_change(lead.change_rate)} leading today. Reply MORE for the story.",
            "MORE",
        ))
        if second:
            out.append(SmsDraft(
                "B",
                f"{idx} as {theme} pops. {lead.symbol} {_fmt_change(lead.change_rate)}, {second.symbol} {_fmt_change(second.change_rate)}. Text LIST for the names.",
                "LIST",
            ))
        else:
            out.append(SmsDraft(
                "B",
                f"{idx} as {theme} moves. {lead.symbol} {_fmt_change(lead.change_rate)}. Text LIST for the names.",
                "LIST",
            ))
    else:
        out.append(SmsDraft("A", f"\U0001F525 {theme} is today's hot theme. Reply MORE.", "MORE"))
        out.append(SmsDraft("B", f"{theme} trending. Text LIST for the tickers.", "LIST"))

    out.append(SmsDraft(
        "C",
        f"Market watch: {theme} moving fast. Reply BULL to get every ticker before the close.",
        "BULL",
    ))
    return out


class SmsGenerator:
    def __init__(self, ai: AIProvider):
        self.ai = ai

    def generate(self, event: MarketEventData) -> list[SmsDraft]:
        if self.ai.available:
            drafts = self._ai_generate(event)
            if drafts:
                return drafts
        return _template(event)

    def _ai_generate(self, event: MarketEventData) -> list[SmsDraft]:
        text = self.ai.complete(SYSTEM_PROMPT, _build_prompt(event), max_tokens=600)
        if not text:
            return []
        msgs = _parse_messages(text)
        if not msgs:
            return []
        drafts: list[SmsDraft] = []
        for m in msgs:
            cta = str(m.get("cta", "")).upper()
            if cta not in CTAS:
                cta = "MORE"
            drafts.append(SmsDraft(str(m.get("version", "?")), str(m.get("body", "")), cta))
        return drafts[:3]


def _parse_messages(text: str) -> list[dict]:
    try:
        return json.loads(text).get("messages", [])
    except Exception:
        pass
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0)).get("messages", [])
    except Exception:
        return []
    return []


def _build_prompt(event: MarketEventData) -> str:
    stocks = ", ".join(f"{s.symbol} {_fmt_change(s.change_rate)}" for s in event.stocks[:5])
    idx = f"{event.index_key} {event.index_change:+.2f}%" if event.index_change is not None else "n/a"
    return (
        f"Theme: {event.title}\nIndex: {idx}\nStocks: {stocks}\n"
        "Write 3 SMS variants (A, B, C) under 160 chars, each ending with a different CTA."
    )
