"""SMS generator — 7 versions with distinct angles, each ending with a CTA
(MORE/LIST/WATCH/FULL/BULL/OK/Yes). Two styles: "standard" (concise) and "hook"
(punchy). Wording is randomized on every call so messages don't feel templated:
the leading stock, the phrasing, and the order of facts all vary.

Every draft carries an English `body` and a Chinese `body_zh` with the same meaning.
"""

import json
import random
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
    "reply keyword from: MORE, LIST, WATCH, FULL, BULL, OK, Yes. Vary your phrasing "
    "and the order of facts so messages don't feel templated. "
    "Return JSON only: {\"messages\": [{\"version\": \"A\", \"body\": \"<English>\", "
    "\"body_zh\": \"<natural Chinese, same meaning>\", \"cta\": \"MORE\"}, ...]} "
    "with exactly seven messages (A-G), each a DIFFERENT angle or fact."
)

SYSTEM_PROMPT_HOOK = (
    "You write engaging US stock-market SMS alerts that sound like a sharp trader "
    "texting a friend. Each message: 1-2 sentences of a hook — a hot move, a big % "
    "number, or a 'don't miss this' tease — then close with exactly one reply keyword "
    "from: MORE, LIST, WATCH, FULL, BULL, OK, Yes. Vary your phrasing and the order of "
    "facts on every message so they don't feel templated. Keep each under 320 characters. "
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


def _lead_second(event: MarketEventData):
    stocks = event.stocks
    if not stocks:
        return None, None
    if len(stocks) == 1:
        return stocks[0], None
    return random.sample(stocks[:3], 2)


def _pick(event: MarketEventData) -> dict:
    """Randomized facts used to fill every template."""
    lead, second = _lead_second(event)
    theme = event.title
    theme_zh = _theme_zh(event)
    lead_en = f"{lead.symbol} {_fmt_change(lead.change_rate)}" if lead else theme
    lead_zh = f"{lead.symbol} {_fmt_change(lead.change_rate)}" if lead else theme_zh
    second_en = f" and {second.symbol} {_fmt_change(second.change_rate)}" if second else ""
    second_zh = f"、{second.symbol} {_fmt_change(second.change_rate)}" if second else ""
    return {
        "theme": theme,
        "theme_zh": theme_zh,
        "lead": lead_en,
        "lead_zh": lead_zh,
        "second": second_en,
        "second_zh": second_zh,
        "idx": _idx(event),
        "n": len(event.stocks),
    }


def _pick_en_zh(variants):
    return random.choice(variants)


# --------------------------------------------------------------------------- #
# STANDARD style — concise, information-forward                               #
# --------------------------------------------------------------------------- #

def _standard_a(c):
    v = [
        (f"\U0001F525 {c['theme']} is on fire today — {c['lead']}{c['second']}. Reply MORE to see what's driving it.",
         f"\U0001F525 {c['theme_zh']}今天火了——{c['lead_zh']}{c['second_zh']}。回复 MORE 看背后原因。"),
        (f"{c['lead']}{c['second']} are leading {c['theme']} today. Reply MORE to see what's driving it.",
         f"{c['lead_zh']}{c['second_zh']}领涨{c['theme_zh']}今天。回复 MORE 看背后原因。"),
    ]
    return _pick_en_zh(v)


def _standard_b(c):
    v = [
        (f"{c['lead']}{c['second']} are leading {c['theme']}, with {c['n']} names moving. Reply LIST for the full list.",
         f"{c['lead_zh']}{c['second_zh']}领涨{c['theme_zh']}，共 {c['n']} 只异动。回复 LIST 拿完整名单。"),
        (f"{c['n']} names are moving in {c['theme']} — {c['lead']}{c['second']} out front. Reply LIST for the full list.",
         f"{c['theme_zh']}有 {c['n']} 只异动——{c['lead_zh']}{c['second_zh']}领涨。回复 LIST 拿完整名单。"),
    ]
    return _pick_en_zh(v)


def _standard_c(c):
    if c["idx"]:
        v = [
            (f"Watch {c['theme']} today — {c['n']} stocks moving, {c['idx']} behind them. Reply WATCH and I'll ping you live.",
             f"盯紧{c['theme_zh']}——{c['n']} 只异动，{c['idx']} 在背后推动。回复 WATCH，我实时提醒你。"),
            (f"{c['idx']} is behind today's {c['theme']} move — {c['n']} stocks on the go. Reply WATCH and I'll ping you live.",
             f"{c['idx']} 在推动今天{c['theme_zh']}的行情——{c['n']} 只异动。回复 WATCH，我实时提醒你。"),
        ]
    else:
        v = [
            (f"Watch {c['theme']} today — {c['n']} stocks moving. Reply WATCH and I'll ping you live.",
             f"盯紧{c['theme_zh']}——{c['n']} 只异动。回复 WATCH，我实时提醒你。"),
            (f"{c['n']} stocks are moving in {c['theme']} today. Reply WATCH and I'll ping you live.",
             f"今天{c['theme_zh']}有 {c['n']} 只异动。回复 WATCH，我实时提醒你。"),
        ]
    return _pick_en_zh(v)


def _standard_d(c):
    v = [
        (f"Want the whole {c['theme']} story? {c['lead']}{c['second']} and the rest — plus why they're moving. Reply FULL.",
         f"想看{c['theme_zh']}完整版？{c['lead_zh']}{c['second_zh']}和其余标的，加上它们为什么动。回复 FULL。"),
        (f"The full {c['theme']} picture: every ticker + the reason behind the move. Reply FULL.",
         f"{c['theme_zh']}全貌：每只标的 + 这波行情的原因。回复 FULL。"),
    ]
    return _pick_en_zh(v)


def _standard_e(c):
    v = [
        (f"{c['theme']} momentum is building — {c['lead']} leading the charge. Reply BULL for every ticker before the close.",
         f"{c['theme_zh']}动能正在累积——{c['lead_zh']}打头阵。回复 BULL，收盘前发你全部标的。"),
        (f"{c['lead']} is leading the {c['theme']} charge. Reply BULL for every ticker before the close.",
         f"{c['lead_zh']}带头冲锋{c['theme_zh']}。回复 BULL，收盘前发你全部标的。"),
    ]
    return _pick_en_zh(v)


def _standard_f(c):
    v = [
        (f"{c['lead']} this morning. Want a briefing on {c['theme']} every day? Reply OK to subscribe.",
         f"{c['lead_zh']}，今早表现不错。想每天收一份{c['theme_zh']}简报？回复 OK 订阅。"),
        (f"A daily {c['theme']} briefing, direction + tickers spelled out. Reply OK to subscribe.",
         f"每天一份{c['theme_zh']}简报，方向加标的都点清楚。回复 OK 订阅。"),
    ]
    return _pick_en_zh(v)


def _standard_g(c):
    if c["idx"]:
        v = [
            (f"{c['theme']} just popped with {c['idx']}. Want today's top {c['theme']} plays? Reply Yes.",
             f"{c['theme_zh']}刚拉升，{c['idx']}。想要今天{c['theme_zh']}最强标的吗？回复 Yes。"),
            (f"Today's top {c['theme']} plays are ready — {c['idx']} on the move. Reply Yes and I'll send them.",
             f"今天{c['theme_zh']}的最强标的已就绪——{c['idx']}在动。回复 Yes，我发你。"),
        ]
    else:
        v = [
            (f"{c['theme']} just popped. Want today's top {c['theme']} plays? Reply Yes.",
             f"{c['theme_zh']}刚拉升。想要今天{c['theme_zh']}最强标的吗？回复 Yes。"),
            (f"Today's top {c['theme']} plays are ready. Reply Yes and I'll send them.",
             f"今天{c['theme_zh']}的最强标的已就绪。回复 Yes，我发你。"),
        ]
    return _pick_en_zh(v)


# --------------------------------------------------------------------------- #
# HOOK style — punchy, reply-driven                                           #
# --------------------------------------------------------------------------- #

def _hook_a(c):
    v = [
        (f"\U0001F525 {c['theme']} is ripping today — {c['lead']}{c['second']}. Want to know where the money's flowing? Reply MORE and I'll break it down.",
         f"\U0001F525 {c['theme_zh']}今天彻底爆发了——{c['lead_zh']}{c['second_zh']}。想知道资金在往哪冲？回复 MORE，我把关键逻辑发你。"),
        (f"Where's the money going today? {c['theme']} is on a tear — {c['lead']}{c['second']}. Reply MORE and I'll break it down.",
         f"今天资金在往哪走？{c['theme_zh']}正在狂飙——{c['lead_zh']}{c['second_zh']}。回复 MORE，我把关键逻辑发你。"),
        (f"{c['lead']}{c['second']} just blew up on {c['theme']}. Want to know why? Reply MORE and I'll break it down.",
         f"{c['lead_zh']}{c['second_zh']}在{c['theme_zh']}上刚爆发。想知道为什么？回复 MORE，我把关键逻辑发你。"),
    ]
    return _pick_en_zh(v)


def _hook_b(c):
    v = [
        (f"{c['theme']} has {c['n']} names leading today — {c['lead']}{c['second']} out front. Don't miss the leaders. Reply LIST for the full list.",
         f"{c['theme_zh']}今天有 {c['n']} 只票带头冲，{c['lead_zh']}{c['second_zh']}领涨。错过龙头就晚了。回复 LIST，我把完整名单发你。"),
        (f"Don't chase the laggards. {c['lead']}{c['second']} are the real {c['theme']} leaders. Reply LIST for the full list.",
         f"别追弱势股。{c['lead_zh']}{c['second_zh']}才是{c['theme_zh']}的真龙头。回复 LIST，我把完整名单发你。"),
    ]
    return _pick_en_zh(v)


def _hook_c(c):
    if c["idx"]:
        v = [
            (f"Watch {c['theme']} today — {c['n']} movers with {c['idx']} behind them. Moves like this usually aren't a one-day thing. Reply WATCH and I'll keep you posted live.",
             f"盯紧{c['theme_zh']}，今天 {c['n']} 只异动，{c['idx']} 在背后撑。这种联动通常不是一天行情。回复 WATCH，我盯盘实时提醒你。"),
            (f"{c['idx']} is backing {c['n']} movers in {c['theme']}. This kind of move usually isn't a one-day thing. Reply WATCH and I'll keep you posted live.",
             f"{c['idx']} 在给{c['theme_zh']}的 {c['n']} 只异动股撑腰。这种行情通常不是一天的事。回复 WATCH，我盯盘实时提醒你。"),
        ]
    else:
        v = [
            (f"Watch {c['theme']} today — {c['n']} movers. Moves like this usually aren't a one-day thing. Reply WATCH and I'll keep you posted live.",
             f"盯紧{c['theme_zh']}，今天 {c['n']} 只异动。这种联动通常不是一天行情。回复 WATCH，我盯盘实时提醒你。"),
        ]
    return _pick_en_zh(v)


def _hook_d(c):
    v = [
        (f"How did this {c['theme']} move start? {c['lead']}{c['second']} lead — but who's following? I've put together the full picture. Reply FULL and it's yours.",
         f"{c['theme_zh']}这波怎么起来的？{c['lead_zh']}{c['second_zh']}领涨，还有谁在跟？我整理了完整版。回复 FULL，发你。"),
        (f"{c['lead']}{c['second']} lead {c['theme']} — but the smart money is already rotating. I've mapped the whole move. Reply FULL and it's yours.",
         f"{c['lead_zh']}{c['second_zh']}领涨{c['theme_zh']}——但聪明钱已经在轮动了。我把整波行情都画出来了。回复 FULL，发你。"),
    ]
    return _pick_en_zh(v)


def _hook_e(c):
    v = [
        (f"{c['theme']} momentum is accelerating — {c['lead']} leading the charge, and there could be another leg before the close. Want in before everyone else? Reply BULL for the tickers.",
         f"{c['theme_zh']}动能正在加速，{c['lead_zh']}打头阵，收盘前可能还有一波。想抄在别人前面？回复 BULL，我把标的发你，别等收盘。"),
        (f"There's still time to get in — {c['lead']} is running and {c['theme']} hasn't topped yet. Reply BULL for the tickers before the close.",
         f"还有时间上车——{c['lead_zh']}在冲，{c['theme_zh']}还没见顶。回复 BULL，收盘前把标的发你。"),
    ]
    return _pick_en_zh(v)


def _hook_f(c):
    v = [
        (f"{c['lead']} — {c['theme']} is the story today, no question. I send a briefing like this every morning. Want it? Reply OK to subscribe, it's free.",
         f"{c['lead_zh']}——{c['theme_zh']}今天没得说。我每天早上都发一份这种热点简报。想收的话回复 OK 订阅，免费的。"),
        (f"I call {c['theme']} every morning before the open — direction + tickers. Reply OK to subscribe, it's free.",
         f"我每天早上开盘前都会点评{c['theme_zh']}——方向加标的。回复 OK 订阅，免费的。"),
    ]
    return _pick_en_zh(v)


def _hook_g(c):
    if c["idx"]:
        v = [
            (f"{c['theme']} just popped with {c['idx']}. Still sitting on the sidelines? I've already lined up today's top plays. Reply Yes and I'll send them over.",
             f"{c['theme_zh']}刚拉升，{c['idx']}。你还在观望吗？我今天最看好的几只已经整理好了。回复 Yes，发你手上。"),
            (f"Are you in or are you watching? {c['theme']} is running — {c['idx']}. I've lined up today's top plays. Reply Yes and I'll send them.",
             f"你是上车了还是还在看？{c['theme_zh']}在涨——{c['idx']}。今天最看好的几只已整理好。回复 Yes，我发你。"),
        ]
    else:
        v = [
            (f"{c['theme']} just popped. Still sitting on the sidelines? I've already lined up today's top plays. Reply Yes and I'll send them over.",
             f"{c['theme_zh']}刚拉升。你还在观望吗？我今天最看好的几只已经整理好了。回复 Yes，发你手上。"),
        ]
    return _pick_en_zh(v)


_STANDARD = {"A": _standard_a, "B": _standard_b, "C": _standard_c, "D": _standard_d,
             "E": _standard_e, "F": _standard_f, "G": _standard_g}
_HOOK = {"A": _hook_a, "B": _hook_b, "C": _hook_c, "D": _hook_d,
         "E": _hook_e, "F": _hook_f, "G": _hook_g}


def _template(event: MarketEventData, style: str) -> list[SmsDraft]:
    builders = _HOOK if style == "hook" else _STANDARD
    c = _pick(event)
    out: list[SmsDraft] = []
    for version in ["A", "B", "C", "D", "E", "F", "G"]:
        body, body_zh = builders[version](c)
        cta = {"A": "MORE", "B": "LIST", "C": "WATCH", "D": "FULL",
               "E": "BULL", "F": "OK", "G": "Yes"}[version]
        out.append(SmsDraft(version, body, cta, body_zh))
    return out


class SmsGenerator:
    def __init__(self, ai: AIProvider):
        self.ai = ai

    def generate(self, event: MarketEventData, style: str = DEFAULT_STYLE) -> list[SmsDraft]:
        if self.ai.available:
            drafts = self._ai_generate(event, style)
            if drafts:
                return drafts
        return _template(event, style)

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
