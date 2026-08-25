"""SMS generator — 3 versions, each ending with a CTA (MORE/LIST/WATCH/FULL/BULL).

Each draft carries an English `body` and a Chinese `body_zh` (same message,
translated) so the UI can toggle a bilingual view.
"""

import json
import re
from dataclasses import dataclass

from app.analyzers.event_engine import MarketEventData
from app.providers.ai.openai_provider import AIProvider

CTAS = ["MORE", "LIST", "WATCH", "FULL", "BULL"]

THEME_ZH = {
    "ai_semiconductor": "AI/半导体",
    "big_tech": "大型科技",
    "ev_clean_energy": "电动车/清洁能源",
    "financials": "金融/银行",
    "crypto": "加密货币",
    "healthcare": "医疗/制药",
    "consumer": "消费/零售",
    "energy": "能源/石油",
    "industrials": "工业/国防",
}


@dataclass
class SmsDraft:
    version: str
    body: str
    cta: str
    body_zh: str = ""


SYSTEM_PROMPT = (
    "You write punchy US stock-market SMS alerts for retail investors. "
    "Keep each message under 160 characters. Always end with exactly one call-to-action "
    "keyword chosen from: MORE, LIST, WATCH, FULL, BULL (e.g. 'Reply MORE for details'). "
    "Return JSON only: {\"messages\": [{\"version\": \"A\", \"body\": \"<English SMS>\", "
    "\"body_zh\": \"<natural Chinese translation>\", \"cta\": \"MORE\"}, ...]} "
    "with exactly three messages (versions A, B, C), each with a different CTA."
)


def _fmt_change(change) -> str:
    if change is None:
        return "moving"
    return f"{change:+.1f}%"


def _dir_zh(change) -> str:
    if change is None:
        return "表现活跃"
    return "领涨" if change >= 0 else "领跌"


def _theme_zh(event: MarketEventData) -> str:
    return THEME_ZH.get(event.theme, event.title)


def _template(event: MarketEventData) -> list[SmsDraft]:
    lead = event.stocks[0] if event.stocks else None
    second = event.stocks[1] if len(event.stocks) > 1 else None
    theme = event.title
    theme_zh = _theme_zh(event)

    idx = ""
    if event.index_change is not None:
        idx = f"{event.index_key.upper()} {event.index_change:+.2f}%"

    out: list[SmsDraft] = []
    if lead:
        chg = _fmt_change(lead.change_rate)
        out.append(SmsDraft(
            "A",
            f"\U0001F525 {theme}: {lead.symbol} {chg} leading today. Reply MORE for the story.",
            "MORE",
            f"\U0001F525 {theme_zh}：{lead.symbol} {chg} {_dir_zh(lead.change_rate)}今日。回复 MORE 获取详情。",
        ))
        if second:
            out.append(SmsDraft(
                "B",
                f"{idx} as {theme} pops. {lead.symbol} {chg}, {second.symbol} {_fmt_change(second.change_rate)}. Text LIST for the names.",
                "LIST",
                f"{idx}，{theme_zh}走强。{lead.symbol} {chg}、{second.symbol} {_fmt_change(second.change_rate)}。回复 LIST 获取名单。",
            ))
        else:
            out.append(SmsDraft(
                "B",
                f"{idx} as {theme} moves. {lead.symbol} {chg}. Text LIST for the names.",
                "LIST",
                f"{idx}，{theme_zh}活跃。{lead.symbol} {chg}。回复 LIST 获取名单。",
            ))
    else:
        out.append(SmsDraft(
            "A", f"\U0001F525 {theme} is today's hot theme. Reply MORE.", "MORE",
            f"\U0001F525 {theme_zh}是今日热门主题。回复 MORE。",
        ))
        out.append(SmsDraft(
            "B", f"{theme} trending. Text LIST for the tickers.", "LIST",
            f"{theme_zh}热度上升。回复 LIST 获取标的。",
        ))

    out.append(SmsDraft(
        "C",
        f"Market watch: {theme} moving fast. Reply BULL to get every ticker before the close.",
        "BULL",
        f"行情速递：{theme_zh}快速拉升。回复 BULL 收盘前获取全部标的。",
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
        text = self.ai.complete(SYSTEM_PROMPT, _build_prompt(event), max_tokens=700)
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
            drafts.append(SmsDraft(
                str(m.get("version", "?")),
                str(m.get("body", "")),
                cta,
                str(m.get("body_zh", "")),
            ))
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
        "Write 3 SMS variants (A, B, C) under 160 chars, each ending with a different CTA. "
        "Give each an English body and a Chinese body_zh."
    )
