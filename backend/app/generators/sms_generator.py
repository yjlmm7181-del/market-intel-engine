"""SMS generator — multiple versions with distinct content, each ending with a
CTA (MORE/LIST/WATCH/FULL/BULL/OK/Yes). Two styles are supported:

- "standard": concise, information-forward wording.
- "hook": longer, punchier, hook + reply-driven wording.

Every draft carries an English `body` and a Chinese `body_zh` with the same meaning.
"""

import json
import re
from dataclasses import dataclass

from app.analyzers.event_engine import MarketEventData
from app.providers.ai.openai_provider import AIProvider

CTAS = ["MORE", "LIST", "WATCH", "FULL", "BULL", "OK", "YES"]
STYLES = ["standard", "hook"]
DEFAULT_STYLE = "hook"

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


SYSTEM_PROMPT_STANDARD = (
    "You write natural US stock-market SMS alerts that sound like a sharp trader "
    "texting a friend. Keep each message under 320 characters. End with exactly one "
    "reply keyword from: MORE, LIST, WATCH, FULL, BULL, OK, Yes. "
    "Return JSON only: {\"messages\": [{\"version\": \"A\", \"body\": \"<English>\", "
    "\"body_zh\": \"<natural Chinese, same meaning>\", \"cta\": \"MORE\"}, ...]} "
    "with exactly seven messages (A-G), each a DIFFERENT angle or fact."
)

SYSTEM_PROMPT_HOOK = (
    "You write engaging US stock-market SMS alerts that sound like a sharp trader "
    "texting a friend. Each message: 1-2 sentences of a hook — a hot move, a big % "
    "number, or a 'don't miss this' tease — then close with exactly one reply keyword "
    "from: MORE, LIST, WATCH, FULL, BULL, OK, Yes (e.g. 'Reply MORE and I'll break it down'). "
    "Keep each message under 320 characters. "
    "Return JSON only: {\"messages\": [{\"version\": \"A\", \"body\": \"<English SMS>\", "
    "\"body_zh\": \"<natural Chinese translation, same meaning>\", \"cta\": \"MORE\"}, ...]} "
    "with exactly seven messages (versions A-G), each with a DIFFERENT angle or fact."
)


def _fmt_change(change) -> str:
    if change is None:
        return "moving"
    return f"{change:+.1f}%"


def _theme_zh(event: MarketEventData) -> str:
    return THEME_ZH.get(event.theme, event.title)


def _idx(event: MarketEventData) -> str:
    if event.index_change is None:
        return ""
    return f"{event.index_key.upper()} {event.index_change:+.2f}%"


def _ctx(event: MarketEventData):
    """Common data pulled from the event, used by both styles."""
    stocks = event.stocks
    lead = stocks[0] if stocks else None
    second = stocks[1] if len(stocks) > 1 else None
    lead_en = f"{lead.symbol} {_fmt_change(lead.change_rate)}" if lead else event.title
    lead_zh = f"{lead.symbol} {_fmt_change(lead.change_rate)}" if lead else _theme_zh(event)
    second_en = f"{second.symbol} {_fmt_change(second.change_rate)}" if second else ""
    second_zh = f"{second.symbol} {_fmt_change(second.change_rate)}" if second else ""
    return {
        "lead_en": lead_en,
        "lead_zh": lead_zh,
        "second_en": second_en,
        "second_zh": second_zh,
        "idx": _idx(event),
        "n_stocks": len(stocks),
    }


def _template_standard(event: MarketEventData) -> list[SmsDraft]:
    theme = event.title
    theme_zh = _theme_zh(event)
    c = _ctx(event)
    lead_en, lead_zh = c["lead_en"], c["lead_zh"]
    second_en, second_zh = c["second_en"], c["second_zh"]
    idx, n = c["idx"], c["n_stocks"]

    out: list[SmsDraft] = []

    # A — lead move
    if second_en:
        out.append(SmsDraft("A",
            f"\U0001F525 {theme} is on fire today — {lead_en} and {second_en}. Reply MORE to see what's driving it.",
            "MORE",
            f"\U0001F525 {theme_zh}今天火了——{lead_zh}、{second_zh}。回复 MORE 看背后原因。"))
    else:
        out.append(SmsDraft("A",
            f"\U0001F525 {theme} is on fire today — {lead_en}. Reply MORE to see what's driving it.",
            "MORE",
            f"\U0001F525 {theme_zh}今天火了——{lead_zh}。回复 MORE 看背后原因。"))

    # B — leaders + breadth
    if second_en:
        out.append(SmsDraft("B",
            f"{lead_en} and {second_en} are leading {theme}, with {n} names moving. Reply LIST for the full list.",
            "LIST",
            f"{lead_zh}、{second_zh}领涨{theme_zh}，共 {n} 只异动。回复 LIST 拿完整名单。"))
    else:
        out.append(SmsDraft("B",
            f"{lead_en} is leading {theme}, with {n} names moving. Reply LIST for the full list.",
            "LIST",
            f"{lead_zh}领涨{theme_zh}，共 {n} 只异动。回复 LIST 拿完整名单。"))

    # C — watch
    if idx:
        out.append(SmsDraft("C",
            f"Watch {theme} today — {n} stocks moving, {idx} behind them. Reply WATCH and I'll ping you live.",
            "WATCH",
            f"盯紧{theme_zh}——{n} 只异动，{idx} 在背后推动。回复 WATCH，我实时提醒你。"))
    else:
        out.append(SmsDraft("C",
            f"Watch {theme} today — {n} stocks moving. Reply WATCH and I'll ping you live.",
            "WATCH",
            f"盯紧{theme_zh}——{n} 只异动。回复 WATCH，我实时提醒你。"))

    # D — full story
    if second_en:
        out.append(SmsDraft("D",
            f"Want the whole {theme} story? {lead_en}, {second_en} and the rest — plus why they're moving. Reply FULL.",
            "FULL",
            f"想看{theme_zh}完整版？{lead_zh}、{second_zh}和其余标的，加上它们为什么动。回复 FULL。"))
    else:
        out.append(SmsDraft("D",
            f"Want the whole {theme} story? {lead_en} and the rest — plus why it's moving. Reply FULL.",
            "FULL",
            f"想看{theme_zh}完整版？{lead_zh}和其余标的，加上为什么动。回复 FULL。"))

    # E — momentum
    out.append(SmsDraft("E",
        f"{theme} momentum is building — {lead_en} leading the charge. Reply BULL for every ticker before the close.",
        "BULL",
        f"{theme_zh}动能正在累积——{lead_zh}打头阵。回复 BULL，收盘前发你全部标的。"))

    # F — daily briefing
    out.append(SmsDraft("F",
        f"{lead_en} this morning. Want a briefing on {theme} every day? Reply OK to subscribe.",
        "OK",
        f"{lead_zh}，今早表现不错。想每天收一份{theme_zh}简报？回复 OK 订阅。"))

    # G — question
    if idx:
        out.append(SmsDraft("G",
            f"{theme} just popped with {idx}. Want today's top {theme} plays sent to you? Reply Yes.",
            "Yes",
            f"{theme_zh}刚拉升，{idx}。想把今天{theme_zh}最强标的发到你手上吗？回复 Yes。"))
    else:
        out.append(SmsDraft("G",
            f"{theme} just popped. Want today's top {theme} plays sent to you? Reply Yes.",
            "Yes",
            f"{theme_zh}刚拉升。想把今天{theme_zh}最强标的发到你手上吗？回复 Yes。"))

    return out


def _template_hook(event: MarketEventData) -> list[SmsDraft]:
    theme = event.title
    theme_zh = _theme_zh(event)
    c = _ctx(event)
    lead_en, lead_zh = c["lead_en"], c["lead_zh"]
    second_en, second_zh = c["second_en"], c["second_zh"]
    idx, n = c["idx"], c["n_stocks"]

    out: list[SmsDraft] = []

    # A — ripping move + "where's the money" hook
    if second_en:
        out.append(SmsDraft("A",
            f"\U0001F525 {theme} is ripping today — {lead_en}, {second_en}. Want to know where the money's flowing? Reply MORE and I'll break it down.",
            "MORE",
            f"\U0001F525 {theme_zh}今天彻底爆发了——{lead_zh}、{second_zh}。想知道资金在往哪冲？回复 MORE，我把关键逻辑发你。"))
    else:
        out.append(SmsDraft("A",
            f"\U0001F525 {theme} is ripping today — {lead_en}. Want to know where the money's flowing? Reply MORE and I'll break it down.",
            "MORE",
            f"\U0001F525 {theme_zh}今天彻底爆发了——{lead_zh}。想知道资金在往哪冲？回复 MORE，我把关键逻辑发你。"))

    # B — leaders + "don't miss" hook
    if second_en:
        out.append(SmsDraft("B",
            f"{theme} has {n} names leading today — {lead_en} and {second_en} out front. Don't miss the leaders. Reply LIST for the full list.",
            "LIST",
            f"{theme_zh}今天有 {n} 只票带头冲，{lead_zh}、{second_zh}领涨。错过龙头就晚了。回复 LIST，我把完整名单发你。"))
    else:
        out.append(SmsDraft("B",
            f"{theme} has {n} names leading today — {lead_en} out front. Don't miss the leaders. Reply LIST for the full list.",
            "LIST",
            f"{theme_zh}今天有 {n} 只票带头冲，{lead_zh}领涨。错过龙头就晚了。回复 LIST，我把完整名单发你。"))

    # C — watch + "not one-day" hook
    if idx:
        out.append(SmsDraft("C",
            f"Watch {theme} today — {n} movers with {idx} behind them. Moves like this usually aren't a one-day thing. Reply WATCH and I'll keep you posted live.",
            "WATCH",
            f"盯紧{theme_zh}，今天 {n} 只异动，{idx} 在背后撑。这种联动通常不是一天行情。回复 WATCH，我盯盘实时提醒你。"))
    else:
        out.append(SmsDraft("C",
            f"Watch {theme} today — {n} movers. Moves like this usually aren't a one-day thing. Reply WATCH and I'll keep you posted live.",
            "WATCH",
            f"盯紧{theme_zh}，今天 {n} 只异动。这种联动通常不是一天行情。回复 WATCH，我盯盘实时提醒你。"))

    # D — the story + "who's following" hook
    if second_en:
        out.append(SmsDraft("D",
            f"How did this {theme} move start? {lead_en} and {second_en} lead — but who's following? I've put together the full picture: every ticker + the money flow. Reply FULL and it's yours.",
            "FULL",
            f"{theme_zh}这波怎么起来的？{lead_zh}、{second_zh}领涨，还有谁在跟？我整理了完整版：每只标的加资金逻辑。回复 FULL，发你。"))
    else:
        out.append(SmsDraft("D",
            f"How did this {theme} move start? {lead_en} leads — but who's following? I've put together the full picture: every ticker + the money flow. Reply FULL and it's yours.",
            "FULL",
            f"{theme_zh}这波怎么起来的？{lead_zh}领涨，还有谁在跟？我整理了完整版：每只标的加资金逻辑。回复 FULL，发你。"))

    # E — momentum + "get in early" hook
    out.append(SmsDraft("E",
        f"{theme} momentum is accelerating — {lead_en} leading the charge, and there could be another leg before the close. Want in before everyone else? Reply BULL for the tickers.",
        "BULL",
        f"{theme_zh}动能正在加速，{lead_zh}打头阵，收盘前可能还有一波。想抄在别人前面？回复 BULL，我把标的发你，别等收盘。"))

    # F — daily briefing + "free" hook
    out.append(SmsDraft("F",
        f"{lead_en} — {theme} is the story today, no question. I send a briefing like this every morning: direction + tickers, all spelled out. Want it? Reply OK to subscribe, it's free.",
        "OK",
        f"{lead_zh}——{theme_zh}今天没得说。我每天早上都发一份这种热点简报，方向加标的都点清楚。想收的话回复 OK 订阅，免费的。"))

    # G — "sidelines" hook
    if idx:
        out.append(SmsDraft("G",
            f"{theme} just popped with {idx}. Still sitting on the sidelines? I've already lined up today's top plays. Want them? Reply Yes and I'll send them over.",
            "Yes",
            f"{theme_zh}刚拉升，{idx}。你还在观望吗？我今天最看好的几只已经整理好了。想要的话回复 Yes，发你手上。"))
    else:
        out.append(SmsDraft("G",
            f"{theme} just popped. Still sitting on the sidelines? I've already lined up today's top plays. Want them? Reply Yes and I'll send them over.",
            "Yes",
            f"{theme_zh}刚拉升。你还在观望吗？我今天最看好的几只已经整理好了。想要的话回复 Yes，发你手上。"))

    return out


class SmsGenerator:
    def __init__(self, ai: AIProvider):
        self.ai = ai

    def generate(self, event: MarketEventData, style: str = DEFAULT_STYLE) -> list[SmsDraft]:
        if self.ai.available:
            drafts = self._ai_generate(event, style)
            if drafts:
                return drafts
        return (_template_hook if style == "hook" else _template_standard)(event)

    def _ai_generate(self, event: MarketEventData, style: str) -> list[SmsDraft]:
        prompt = SYSTEM_PROMPT_HOOK if style == "hook" else SYSTEM_PROMPT_STANDARD
        text = self.ai.complete(prompt, _build_prompt(event, style), max_tokens=900)
        if not text:
            return []
        msgs = _parse_messages(text)
        if not msgs:
            return []
        drafts: list[SmsDraft] = []
        for m in msgs:
            cta = str(m.get("cta", "")).upper()
            if cta == "YES":
                cta = "Yes"
            if cta not in CTAS and cta != "Yes":
                cta = "MORE"
            drafts.append(SmsDraft(
                str(m.get("version", "?")),
                str(m.get("body", "")),
                cta,
                str(m.get("body_zh", "")),
            ))
        return drafts[:7]


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


def _build_prompt(event: MarketEventData, style: str) -> str:
    stocks = ", ".join(f"{s.symbol} {_fmt_change(s.change_rate)}" for s in event.stocks[:5])
    idx = f"{event.index_key} {event.index_change:+.2f}%" if event.index_change is not None else "n/a"
    style_note = (
        "use punchy hook + reply-driven wording"
        if style == "hook"
        else "use concise, information-forward wording"
    )
    return (
        f"Theme: {event.title}\nIndex: {idx}\nStocks: {stocks}\n"
        f"Write 7 natural SMS variants (A-G) under 320 chars, each with a different angle "
        f"and a different CTA ({style_note}). Give each an English body and a Chinese body_zh "
        "with the same meaning."
    )
