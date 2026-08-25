"""Static market universe: watchlist basket, display names, and themes.

Curated, deterministic lists used to (a) build the "movers" list (Moomoo has
no screener, so we snapshot a fixed basket and rank by change), and (b) cluster
movers + news into themes (Market Events).
"""

from dataclasses import dataclass

# Symbol -> display name, for the watchlist basket.
SYMBOL_NAMES: dict[str, str] = {
    "NVDA": "NVIDIA", "AMD": "Advanced Micro Devices", "AVGO": "Broadcom",
    "TSM": "Taiwan Semiconductor", "INTC": "Intel", "MU": "Micron",
    "MRVL": "Marvell", "AMAT": "Applied Materials", "ASML": "ASML",
    "SMCI": "Super Micro", "QCOM": "Qualcomm", "ARM": "Arm Holdings",
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "META": "Meta Platforms", "NFLX": "Netflix",
    "TSLA": "Tesla", "RIVN": "Rivian", "LCID": "Lucid",
    "FSLR": "First Solar", "ENPH": "Enphase", "PLUG": "Plug Power",
    "JPM": "JPMorgan Chase", "BAC": "Bank of America", "GS": "Goldman Sachs",
    "MS": "Morgan Stanley", "WFC": "Wells Fargo", "C": "Citigroup",
    "V": "Visa", "MA": "Mastercard",
    "COIN": "Coinbase", "MSTR": "MicroStrategy", "MARA": "Marathon Digital",
    "RIOT": "Riot Platforms", "HOOD": "Robinhood",
    "LLY": "Eli Lilly", "UNH": "UnitedHealth", "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer", "MRK": "Merck", "ABBV": "AbbVie", "MRNA": "Moderna",
    "WMT": "Walmart", "COST": "Costco", "TGT": "Target", "HD": "Home Depot",
    "NKE": "Nike", "SBUX": "Starbucks", "MCD": "McDonald's", "DIS": "Disney",
    "ABNB": "Airbnb",
    "XOM": "Exxon Mobil", "CVX": "Chevron", "COP": "ConocoPhillips",
    "SLB": "Schlumberger", "OXY": "Occidental",
    "BA": "Boeing", "CAT": "Caterpillar", "GE": "GE Aerospace",
    "HON": "Honeywell", "LMT": "Lockheed Martin", "RTX": "RTX",
}

BASKET: list[str] = list(SYMBOL_NAMES.keys())


@dataclass(frozen=True)
class Theme:
    key: str
    title: str
    stocks: tuple[str, ...]
    index_key: str  # one of "sp500" | "nasdaq" | "dow"
    keywords: tuple[str, ...]


THEMES: list[Theme] = [
    Theme("ai_semiconductor", "AI / Semiconductor",
          ("NVDA", "AMD", "AVGO", "TSM", "INTC", "MU", "MRVL", "AMAT", "ASML", "SMCI", "QCOM", "ARM"),
          "nasdaq",
          ("ai", "artificial intelligence", "semiconductor", "chip", "nvidia", "gpu", "amd",
           "broadcom", "tsmc", "taiwan semiconductor", "foundry", "memory", "micron", "data center")),
    Theme("big_tech", "Big Tech / Mega Cap",
          ("AAPL", "MSFT", "GOOGL", "AMZN", "META", "NFLX"),
          "nasdaq",
          ("apple", "microsoft", "google", "alphabet", "amazon", "meta", "netflix", "big tech", "iphone", "cloud")),
    Theme("ev_clean_energy", "EV / Clean Energy",
          ("TSLA", "RIVN", "LCID", "FSLR", "ENPH", "PLUG"),
          "nasdaq",
          ("electric vehicle", "ev", "tesla", "clean energy", "solar", "battery", "lithium", "rivian")),
    Theme("financials", "Financials / Banks",
          ("JPM", "BAC", "GS", "MS", "WFC", "C", "V", "MA"),
          "dow",
          ("bank", "banking", "financial", "fed", "federal reserve", "interest rate",
           "jpmorgan", "goldman", "visa", "mastercard")),
    Theme("crypto", "Crypto / Blockchain",
          ("COIN", "MSTR", "MARA", "RIOT", "HOOD"),
          "nasdaq",
          ("bitcoin", "btc", "crypto", "cryptocurrency", "blockchain", "ethereum", "coinbase", "mining")),
    Theme("healthcare", "Healthcare / Pharma",
          ("LLY", "UNH", "JNJ", "PFE", "MRK", "ABBV", "MRNA"),
          "sp500",
          ("healthcare", "pharma", "drug", "fda", "weight loss", "glp", "vaccine", "biotech", "medical", "ozempic")),
    Theme("consumer", "Consumer / Retail",
          ("WMT", "COST", "TGT", "HD", "NKE", "SBUX", "MCD", "DIS", "ABNB"),
          "sp500",
          ("retail", "consumer", "walmart", "costco", "target", "earnings", "holiday", "spending", "starbucks")),
    Theme("energy", "Energy / Oil",
          ("XOM", "CVX", "COP", "SLB", "OXY"),
          "dow",
          ("oil", "energy", "crude", "opec", "exxon", "chevron", "natural gas")),
    Theme("industrials", "Industrials / Defense",
          ("BA", "CAT", "GE", "HON", "LMT", "RTX"),
          "dow",
          ("boeing", "defense", "aerospace", "industrial", "caterpillar", "lockheed")),
]
