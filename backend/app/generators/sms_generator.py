"""SMS generator — natural-language market alerts.

Every draft is built from a curated combination of a theme subject, a natural
sentence template (signal + hook woven together), a reply CTA, and a STOP
opt-out. No percentages, no profit guarantees. Wording is randomized on every
call and de-duplicated (against the current deck and against history) so cards
don't repeat phrasing or structure.

Every draft carries an English `body` and a Chinese `body_zh` with the same
meaning — the Chinese is written naturally, not word-for-word translated.
"""

import json
import random
import re
from dataclasses import dataclass

from app.analyzers.event_engine import MarketEventData

VERSIONS = ["A", "B", "C", "D", "E", "F", "G", "H"]
VERSION_CTA = {"A": "MORE", "B": "LIST", "C": "WATCH", "D": "FULL", "E": "BULL", "F": "OK", "G": "Yes", "H": "START"}
CTA_SET = {"MORE", "LIST", "WATCH", "FULL", "BULL", "OK", "Yes", "START"}
STYLES = ["standard", "hook", "urgent"]
DEFAULT_STYLE = "hook"

FORBIDDEN = [
    "guaranteed", "risk-free", "risk free", "easy money", "guaranteed winner",
    "will explode", "100%", "no-risk", "no risk", "you will make money",
    "buy now", "guaranteed profit", "guarantee", "sure win", "sure thing",
    "can't lose", "cannot lose", "double your money", "get rich",
]

STOP_EN = "Reply STOP to opt out."
STOP_ZH = "回复 STOP 取消订阅。"

START_STOP_LINES = [
    ("Reply START to subscribe; reply STOP to cancel.", "回复 START 加入订阅；回复 STOP 取消订阅。"),
    ("Reply START to join; reply STOP to cancel.", "回复 START 加入参与；回复 STOP 取消参与。"),
    ("Reply START to get updates; reply STOP to opt out.", "回复 START 接收更新；回复 STOP 退订。"),
    ("Reply START to continue; reply STOP to stop.", "回复 START 继续接收；回复 STOP 停止。"),
    ("Reply START to keep getting these; reply STOP to cancel.", "回复 START 继续接收通知；回复 STOP 取消。"),
]

# Event theme -> natural market-subject phrases (English, Chinese). Kept bare
# (no "the"/"group") because templates append their own nouns.
THEME_SUBJECTS = {
    "ai_semiconductor": [
        ("AI and semiconductor", "AI与半导体"),
        ("AI, semiconductor, and cloud", "AI、半导体和云计算"),
        ("AI and chip", "AI与芯片"),
        ("semiconductor and cloud", "半导体与云计算"),
    ],
    "big_tech": [
        ("big tech", "大型科技"),
        ("mega-cap tech", "超大盘科技"),
        ("mega-cap", "超大盘"),
    ],
    "ev_clean_energy": [
        ("EV and clean energy", "电动车与清洁能源"),
        ("EV", "电动车"),
    ],
    "financials": [
        ("financials", "金融"),
        ("banks and financials", "银行与金融"),
    ],
    "crypto": [
        ("crypto and blockchain", "加密货币与区块链"),
        ("bitcoin and crypto", "比特币与加密货币"),
        ("crypto", "加密货币"),
    ],
    "healthcare": [
        ("healthcare and biotech", "医疗与生物科技"),
        ("biotech", "生物科技"),
    ],
    "consumer": [
        ("consumer", "消费"),
        ("retail", "零售"),
    ],
    "energy": [
        ("energy", "能源"),
        ("oil and energy", "石油与能源"),
    ],
    "industrials": [
        ("industrials", "工业"),
        ("defense and industrials", "国防与工业"),
    ],
}
DEFAULT_SUBJECTS = [("the market", "大盘")]

# Chinese display names for basket symbols (used by the hook style).
SYMBOL_ZH_NAMES = {
    "NVDA": "英伟达", "AMD": "超威半导体", "AVGO": "博通",
    "TSM": "台积电", "INTC": "英特尔", "MU": "美光",
    "MRVL": "美满电子", "AMAT": "应用材料", "ASML": "阿斯麦",
    "SMCI": "超微电脑", "QCOM": "高通", "ARM": "安谋",
    "AAPL": "苹果", "MSFT": "微软", "GOOGL": "谷歌",
    "AMZN": "亚马逊", "META": "Meta", "NFLX": "奈飞",
    "TSLA": "特斯拉", "RIVN": "Rivian", "LCID": "Lucid",
    "FSLR": "第一太阳能", "ENPH": "Enphase", "PLUG": "普拉格能源",
    "JPM": "摩根大通", "BAC": "美国银行", "GS": "高盛",
    "MS": "摩根士丹利", "WFC": "富国银行", "C": "花旗",
    "V": "Visa", "MA": "万事达",
    "COIN": "Coinbase", "MSTR": "微策略", "MARA": "马拉松数字",
    "RIOT": "Riot", "HOOD": "Robinhood",
    "LLY": "礼来", "UNH": "联合健康", "JNJ": "强生",
    "PFE": "辉瑞", "MRK": "默沙东", "ABBV": "艾伯维", "MRNA": "莫德纳",
    "WMT": "沃尔玛", "COST": "开市客", "TGT": "塔吉特", "HD": "家得宝",
    "NKE": "耐克", "SBUX": "星巴克", "MCD": "麦当劳", "DIS": "迪士尼",
    "ABNB": "爱彼迎",
    "XOM": "埃克森美孚", "CVX": "雪佛龙", "COP": "康菲石油",
    "SLB": "斯伦贝谢", "OXY": "西方石油",
    "BA": "波音", "CAT": "卡特彼勒", "GE": "通用电气",
    "HON": "霍尼韦尔", "LMT": "洛克希德马丁", "RTX": "雷神",
}

# Hook style = "AI agent" voice. {AGENT}/{AGENT_ZH} = agent name,
# {STOCK}/{STOCK_ZH} = a concrete stock, {SIGNAL}/{SIGNAL_ZH} = a technical signal.
AGENT_NAMES = [
    ("Momentum Scout", "动量侦察员"),
    ("Alpha Screener", "阿尔法筛选器"),
    ("Signal Watch", "信号观察员"),
]

SIGNALS = [
    ("broke above its 20-day moving average", "股价突破了 20 天平均价格线"),
    ("reached a one-year high on above-average volume", "股价以高于平常的幅度达到了一年来的最高价"),
    ("saw a pickup in buying activity", "购买活动有所增加"),
    ("broke out on above-average volume", "放量突破"),
    ("reached a fresh 52-week high", "创下 52 周新高"),
    ("climbed for a third straight session", "连续第三个交易日上涨"),
    ("cleared a key resistance level", "突破了关键阻力位"),
    ("showed unusual accumulation", "出现异常吸筹"),
]

HOOK_TEMPLATES = [
    ("AI agent \"{AGENT}\" spotted {STOCK} {SIGNAL}.",
     "AI 代理「{AGENT_ZH}」发现 {STOCK_ZH}{SIGNAL_ZH}。"),
    ("Your AI agent finished its daily scan: {STOCK} {SIGNAL}.",
     "您的 AI 代理完成每日扫描：{STOCK_ZH}{SIGNAL_ZH}。"),
    ("AI performance review complete — {STOCK} {SIGNAL}.",
     "人工智能评估已完成——{STOCK_ZH}{SIGNAL_ZH}。"),
    ("Your AI agent just flagged {STOCK}, which {SIGNAL}.",
     "您的 AI 代理刚标记了 {STOCK_ZH}，该股{SIGNAL_ZH}。"),
    ("Scan complete — {STOCK} {SIGNAL}, per your AI agent.",
     "扫描完成——据您的 AI 代理，{STOCK_ZH}{SIGNAL_ZH}。"),
    ("AI alert: {STOCK} {SIGNAL}.",
     "AI 提醒：{STOCK_ZH}{SIGNAL_ZH}。"),
    ("Daily AI scan found {STOCK} {SIGNAL}.",
     "每日 AI 扫描发现 {STOCK_ZH}{SIGNAL_ZH}。"),
]

STANDARD_TEMPLATES = [
    ("{S} names are moving higher today.",
     "{Z}板块今天走高。"),
    ("Trading is picking up across the {S} group.",
     "{Z}板块成交活跃度在提升。"),
    ("The {S} group is drawing interest this session.",
     "{Z}板块今天吸引了资金关注。"),
    ("Several {S} names are climbing on solid volume.",
     "几只{Z}标的在放量上涨。"),
    ("The {S} group is holding steady near recent levels.",
     "{Z}板块在近期点位附近企稳。"),
    ("Money is rotating toward {S} today.",
     "资金今天在轮动流入{Z}板块。"),
    ("The {S} complex is outperforming the tape.",
     "{Z}板块跑赢大盘。"),
    ("A few {S} names are standing out this session.",
     "今天{Z}板块里有几只标的尤为突出。"),
    ("The {S} group is firm into midday.",
     "{Z}板块在午盘前保持坚挺。"),
    ("Sentiment is improving across {S}.",
     "{Z}板块情绪正在好转。"),
    ("The {S} trade is steady, with volume confirming.",
     "{Z}行情稳中有升，成交量予以确认。"),
    ("There is a clear bid under the {S} group today.",
     "今天{Z}板块下方有明显的买盘支撑。"),
]

URGENT_TEMPLATES = [
    ("The {S} move is happening now — the window is closing fast.", "{Z}这波正在进行——时间窗口正在快速关闭。"),
    ("Don't wait too long on {S}. The leaders are already running.", "别在{Z}上等太久，龙头已经在跑了。"),
    ("The {S} setup is live right now. Every minute counts.", "{Z}的结构现在就在成形，每一分钟都重要。"),
    ("This {S} move won't wait for you. Acting now?", "{Z}这波不会等你。现在行动？"),
    ("The {S} leaders are moving into the close — little time left.", "{Z}龙头正在冲收盘——时间不多了。"),
    ("Right now is the window on {S}. It's tightening fast.", "{Z}的机会就是现在，窗口正在快速收窄。"),
    ("The {S} trade is heating up as we speak.", "{Z}行情正在实时升温。"),
    ("Minutes matter in {S} today. The setup is now.", "{Z}今天分秒必争，结构就是现在。"),
    ("The {S} move is breaking as I write this.", "{Z}这波行情在我写下这行字时正在突破。"),
    ("Don't be the last one to see the {S} move.", "别做最后一个看到{Z}这波的人。"),
    ("The {S} window is open now — it could close by the bell.", "{Z}的窗口现在开着——收盘前可能就关了。"),
    ("This is the moment for {S}. Are you in time?", "现在就是{Z}的时刻，你赶得上吗？"),
]

TEMPLATES_BY_STYLE = {
    "hook": HOOK_TEMPLATES,
    "standard": STANDARD_TEMPLATES,
    "urgent": URGENT_TEMPLATES,
}

CTA_LINES = {
    "MORE": ("Reply MORE for the names.", "回复 MORE 获取名单。"),
    "LIST": ("Reply LIST for the full list.", "回复 LIST 获取完整名单。"),
    "WATCH": ("Reply WATCH and I'll keep you posted.", "回复 WATCH，我实时提醒你。"),
    "FULL": ("Reply FULL for the complete picture.", "回复 FULL 获取完整版。"),
    "BULL": ("Reply BULL for the leaders before the close.", "回复 BULL，收盘前发你龙头名单。"),
    "OK": ("Reply OK to subscribe to the daily note.", "回复 OK 订阅每日简报。"),
    "Yes": ("Reply Yes if you want today's top plays.", "回复 Yes 获取今日最强标的。"),
}


@dataclass
class SmsDraft:
    version: str
    body: str
    cta: str
    body_zh: str = ""


def _hook_ctx(event, subject) -> dict:
    stocks = sorted(event.stocks, key=lambda s: abs(s.change_rate or 0), reverse=True)
    if not stocks:
        return {}
    stock = stocks[0]
    agent_en, agent_zh = random.choice(AGENT_NAMES)
    signal_en, signal_zh = random.choice(SIGNALS)
    return {
        "AGENT": agent_en, "AGENT_ZH": agent_zh,
        "STOCK": stock.name or stock.symbol,
        "STOCK_ZH": SYMBOL_ZH_NAMES.get(stock.symbol, stock.name or stock.symbol),
        "SIGNAL": signal_en, "SIGNAL_ZH": signal_zh,
    }


def _render(template, ctx, cta, style) -> tuple[str, str]:
    en_t, zh_t = template
    en_sent = en_t
    zh_sent = zh_t
    for key, val in ctx.items():
        en_sent = en_sent.replace('{' + key + '}', val)
        zh_sent = zh_sent.replace('{' + key + '}', val)
    if cta == "START":
        # H card (any style): randomized START/STOP line
        start_en, start_zh = random.choice(START_STOP_LINES)
        body = f"{en_sent} {start_en}"
        body_zh = f"{zh_sent}{start_zh}"
    elif style == "hook":
        # hook A-G: concrete names + original CTA + STOP
        cta_en, cta_zh = CTA_LINES[cta]
        body = f"{en_sent} {cta_en} {STOP_EN}"
        body_zh = f"{zh_sent}{cta_zh}{STOP_ZH}"
    else:
        # standard & urgent: CTA + disclaimer
        cta_en, cta_zh = CTA_LINES[cta]
        body = f"{en_sent} {cta_en}"
        body_zh = f"{zh_sent}{cta_zh}"
        # "仅限数据" disclaimer on standard & urgent (not hook), random position
        body, body_zh = _add_disclaimer(body, body_zh)
    return body, body_zh


def _add_disclaimer(body: str, body_zh: str) -> tuple[str, str]:
    pos = random.choice(["start", "middle", "end"])
    if pos == "start":
        return "Data only. " + body, "仅限数据。" + body_zh
    if pos == "end":
        return body + " Data only.", body_zh + "仅限数据。"
    en_parts = body.split(". ", 1)
    zh_parts = body_zh.split("。", 1)
    if len(en_parts) == 2:
        body = en_parts[0] + ". Data only. " + en_parts[1]
    else:
        body = body + " Data only."
    if len(zh_parts) == 2:
        body_zh = zh_parts[0] + "。仅限数据。" + zh_parts[1]
    else:
        body_zh = body_zh + "仅限数据。"
    return body, body_zh


class SmsGenerator:
    def __init__(self, ai=None):
        self.ai = ai  # reserved; generation is deterministic/combinatorial
        self._history: set[str] = set()

    def seed_bodies(self, bodies) -> None:
        for b in bodies:
            if b:
                self._history.add(b)

    def generate_deck(self, event: MarketEventData, style: str = DEFAULT_STYLE) -> list[SmsDraft]:
        templates = TEMPLATES_BY_STYLE.get(style, HOOK_TEMPLATES)
        subjects = THEME_SUBJECTS.get(event.theme, DEFAULT_SUBJECTS)
        drafts: list[SmsDraft] = []
        used_templates: set[int] = set()
        used_subjects: set[int] = set()
        for version in VERSIONS:
            drafts.append(self._build_fresh(templates, subjects, event, style, version, used_templates, used_subjects, set()))
        return drafts

    def generate_one(self, event: MarketEventData, version: str, style: str = DEFAULT_STYLE, avoid=()) -> SmsDraft:
        if version not in VERSION_CTA:
            version = "A"
        templates = TEMPLATES_BY_STYLE.get(style, HOOK_TEMPLATES)
        subjects = THEME_SUBJECTS.get(event.theme, DEFAULT_SUBJECTS)
        return self._build_fresh(templates, subjects, event, style, version, set(), set(), set(avoid))

    def _build_fresh(self, templates, subjects, event, style, version, used_templates, used_subjects, avoid) -> SmsDraft:
        cta = VERSION_CTA[version]
        tidxs = list(range(len(templates)))
        random.shuffle(tidxs)
        sidxs = list(range(len(subjects)))
        random.shuffle(sidxs)

        def _ctx(sidx):
            subject = subjects[sidx]
            return _hook_ctx(event, subject) if style == "hook" else {"S": subject[0], "Z": subject[1]}

        # first pass: fully fresh (unused template, unused subject, not in history/avoid)
        for tidx in tidxs:
            if tidx in used_templates:
                continue
            for sidx in sidxs:
                if sidx in used_subjects:
                    continue
                body, body_zh = _render(templates[tidx], _ctx(sidx), cta, style)
                if body in self._history or body in avoid or _forbidden(body):
                    continue
                used_templates.add(tidx)
                used_subjects.add(sidx)
                self._history.add(body)
                return SmsDraft(version, body, cta, body_zh)

        # second pass: relax subject uniqueness, still avoid history/avoid
        for tidx in tidxs:
            if tidx in used_templates:
                continue
            for sidx in sidxs:
                body, body_zh = _render(templates[tidx], _ctx(sidx), cta, style)
                if body in self._history or body in avoid or _forbidden(body):
                    continue
                used_templates.add(tidx)
                self._history.add(body)
                return SmsDraft(version, body, cta, body_zh)

        # fallback (should be rare)
        body, body_zh = _render(templates[tidxs[0]], _ctx(sidxs[0]), cta, style)
        self._history.add(body)
        return SmsDraft(version, body, cta, body_zh)


def _forbidden(body: str) -> bool:
    low = body.lower()
    return any(w in low for w in FORBIDDEN)
