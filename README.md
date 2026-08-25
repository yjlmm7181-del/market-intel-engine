# Market Intel Engine

美股市场热点情报引擎。每天自动回答三个问题：

1. 今天市场什么最热？
2. 哪些股票 / 指数在跟着这个热点动？
3. 怎么把这个热点压成一条美国用户愿意回复的短信？

最终输出：**Market Event + Related Stocks + Related Indexes + News Context + AI Summary + SMS Hook + CTA**（每条短信带一个 `MORE / LIST / WATCH / FULL / BULL` 行动指令）。

## 技术栈

- 后端：Python + FastAPI + SQLAlchemy + APScheduler
- 前端：React (Vite) + react-router，深色金融风
- 行情：Moomoo OpenAPI（OpenD 本地网关）→ **yfinance 兜底**
- 资讯：Moomoo 公开 HTTP 端点 `GET /news_search`（`ai-news-search.futunn.com`，免 Key）
- AI：任意 OpenAI 兼容端点（OpenAI / DeepSeek / Moonshot …），**无 Key 时自动降级为模板**

## 快速开始（Docker）

```bash
cp .env.example .env      # 可选：填 AI_API_KEY 等
docker compose up --build
```

打开 **http://localhost:3000** —— 即可看到 S&P 500 / NASDAQ / Dow、今日上涨股票、相关新闻、TOP 3 热点事件，点击 **GENERATE SMS** 得到 Version A/B/C（各带 CTA）。

> 无需本地 OpenD / 无需 AI Key 也能跑：行情自动落到 yfinance，摘要和短信自动落到模板。

## 本地开发

```bash
# 后端（:8000）
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（:3000，proxy 到 8000）
cd frontend
npm install
npm run dev
```

## 测试

```bash
cd backend
python -m pytest -q ../tests/
```

## 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `MOOMOO_HOST` / `MOOMOO_PORT` | OpenD 网关地址 | `127.0.0.1` / `11111` |
| `AI_API_KEY` | AI Key（OpenAI 兼容），留空走模板 | 空 |
| `AI_BASE_URL` / `AI_MODEL` | AI 端点与模型 | OpenAI / `gpt-4o-mini` |
| `DATABASE_URL` | 数据库，默认 SQLite，可换 Postgres | `sqlite:///./market_intel.db` |
| `REDIS_URL` | 去重缓存（可选，挂了自动降级内存） | `redis://localhost:6379/0` |
| `NEWS_BASE_URL` / `NEWS_LANG` / `NEWS_SIZE` | 资讯端点 | Moomoo 公开端点 / `en` / `20` |

## API

```
GET  /api/market/overview            # Dashboard 聚合（指数+涨幅榜+新闻+事件）
GET  /api/market/indexes
GET  /api/stocks/movers
GET  /api/news
GET  /api/events
GET  /api/events/{event_id}
POST /api/events/{event_id}/analyze
POST /api/events/{event_id}/generate-sms
GET  /api/sms
POST /api/sms/{id}/regenerate
```

## Moomoo 能力核实结论（2026-08）

- **个股/ETF/期权/期货行情**：能拿（`get_market_snapshot` / `get_stock_quote`，需本地 OpenD 登录）。
- **美股三大指数**：OpenAPI 行情权限表**不含美股指数** → 用 yfinance 兜底。
- **涨幅榜**：**无 screener 接口** → 自建股票池（~64 只大盘股）快照排序。
- **新闻**：SDK 里**没有**，走独立公开 HTTP 端点（免 Key，`sort_type` 仅 1=阅读量/2=最新）。
- **快照限频**：60 次 / 30 秒。后端对 OpenD 做了快速 TCP 探活 + 熔断，OpenD 不在时毫秒级失败并自动切 yfinance。

## 架构

```
Market Data (Moomoo→yfinance / News endpoint)
        ↓
Market Intelligence (Event Engine + Heat Score)
        ↓
Content Generation (AI Analyst + SMS Generator)
        ↓
API / Dashboard (React)
```

关键模块（`backend/app/`）：

- `providers/` — 数据源适配层：`moomoo/`（OpenD）、`fallback/`（yfinance）、`news/`（资讯）、`ai/`（LLM）、`circuit_breaker.py`
- `collectors/` — `index_collector`（指数）、`mover_collector`（异动）、`news_collector`（新闻+去重）
- `analyzers/` — `event_engine`（主题聚类）、`heat_score`（热度）、`ai_analyst`（摘要）
- `generators/sms_generator.py` — 3 版短信 + CTA
- `services/market_pipeline.py` — 全流程编排（API 与定时任务共用）
- `tasks/scheduler.py` — APScheduler 定时刷新

## 设计说明

- **Provider 抽象**：所有数据源实现 `MarketDataProvider` 接口，未来接新数据源只需加一个实现。
- **优雅降级**：Moomoo 挂了→yfinance；AI 没 Key→模板；资讯挂了→空列表；Redis 挂了→内存去重。任何单一故障都不影响页面打开。
- **去重**：新闻按 `news_id` 在 Redis（可选）+ 内存去重，DB 唯一索引兜底。
- **热度评分**：基线 30 + 平均涨幅×3（±20）+ 指数×2（±15）+ 新闻×8（≤24）+ 前三涨幅 +15，映射到 0–100。
