"""SMS generator — multiple versions with distinct content, each ending with a
CTA (MORE/LIST/WATCH/FULL/BULL). Every draft carries an English `body` and a
Chinese `body_zh` with the same meaning.
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
    "\"body_zh\": \"<Chinese translation with the same meaning>\", \"cta\": \"MORE\"}, ...]} "
    "with exactly six messages (versions A-F). Each message must have DIFFERENT content "
    "(a different angle or fact), not just reworded duplicates."
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


def _idx(event: MarketEventData) -> str:
    if event.index_change is None:
        return ""
    return f"{event.index_key.upper()} {event.index_change:+.2f}%"


def _template(event: MarketEventData) -> list[SmsDraft]:
    theme = event.title
    theme_zh = _theme_zh(event)
    stocks = event.stocks
    lead = stocks[0] if stocks else None
    second = stocks[1] if len(stocks) > 1 else None
    idx = _idx(event)
    n_stocks = len(stocks)
    n_news = len(event.news)

    lead_en = f"{lead.symbol} {_fmt_change(lead.change_rate)}" if lead else theme
    lead_zh = f"{lead.symbol} {_fmt_change(lead.change_rate)} {_dir_zh(lead.change_rate)}" if lead else theme_zh

    out: list[SmsDraft] = []

    # A — headline / lead mover
    out.append(SmsDraft(
        "A",
        f"\U0001F525 {theme}: {lead_en} leading today. Reply MORE for the story.",
        "MORE",
        f"\U0001F525 {theme_zh}：{lead_zh}今日。回复 MORE 获取详情。",
    ))

    # B — names / top movers
    if second:
        second_en = f"{second.symbol} {_fmt_change(second.change_rate)}"
        second_zh = f"{second.symbol} {_fmt_change(second.change_rate)}"
        out.append(SmsDraft(
            "B",
            f"{idx} as {theme} pops. {lead_en}, {second_en}. Text LIST for the names.",
            "LIST",
            f"{idx}，{theme_zh}走强。{lead_zh}、{second_zh}。回复 LIST 获取名单。",
        ))
    else:
        out.append(SmsDraft(
            "B",
            f"{theme} movers to watch: {lead_en}. Text LIST for the names.",
            "LIST",
            f"{theme_zh}异动股：{lead_zh}。回复 LIST 获取名单。",
        ))

    # C — watchlist breadth
    out.append(SmsDraft(
        "C",
        f"Watchlist: {theme} has {n_stocks} movers right now. Reply WATCH for live updates.",
        "WATCH",
        f"自选提醒：{theme_zh}现有 {n_stocks} 只异动股。回复 WATCH 获取实时更新。",
    ))

    # D — full report
    out.append(SmsDraft(
        "D",
        f"Full rundown: {theme} — {n_stocks} movers, {n_news} headlines. Reply FULL for the complete report.",
        "FULL",
        f"完整报告：{theme_zh} —— {n_stocks} 只异动股、{n_news} 条新闻。回复 FULL 获取完整报告。",
    ))

    # E — momentum
    out.append(SmsDraft(
        "E",
        f"Momentum alert: {theme} moving fast. Reply BULL to get every ticker before the close.",
        "BULL",
        f"动量提醒：{theme_zh}快速拉升。回复 BULL 收盘前获取全部标的。",
    ))

    # F — news-driven
    out.append(SmsDraft(
        "F",
        f"News-driven: {n_news} headlines behind the {theme} move today. Reply MORE.",
        "MORE",
        f"新闻驱动：{n_news} 条新闻推动{theme_zh}今日行情。回复 MORE。",
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
        text = self.ai.complete(SYSTEM_PROMPT, _build_prompt(event), max_tokens=900)
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
        return drafts[:6]


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
        "Write 6 SMS variants (A-F) under 160 chars, each with a different angle and a different CTA. "
        "Give each an English body and a Chinese body_zh with the same meaning."
    )
