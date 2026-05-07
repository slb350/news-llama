# News Llama

## Project Description

An AI-powered news curation engine that aggregates content from RSS, Twitter/X, Hacker News, Reddit, and web search, then summarizes the most relevant articles using a local LLM via **open-agent-sdk**. Runs in CLI batch mode or as a persistent web application.

## Repository Structure

```
news-llama/
├── main.py                    # CLI entry point
├── src/
│   ├── aggregators/           # Source-specific aggregators
│   │   ├── rss_aggregator.py
│   │   ├── twitter_aggregator.py
│   │   ├── reddit_aggregator.py
│   │   ├── hackernews_aggregator.py
│   │   └── dynamic_aggregator.py  # AI-discovered sources
│   ├── processors/            # Content processing
│   │   ├── content_processor.py
│   │   ├── duplicate_detector.py
│   │   └── source_discovery.py    # LLM-powered source discovery
│   ├── summarizers/           # LLM summarization via open-agent-sdk
│   ├── generators/            # Output generation (HTML, JSON, RSS)
│   ├── utils/                 # Config and data models
│   └── web/                   # FastAPI web application
│       ├── app.py             # FastAPI app, route registration
│       ├── api/               # RESTful JSON API (v1)
│       │   └── v1/            # v1 routes: users.py, interests.py, newsletters.py
│       ├── services/          # 15 service modules: core (user, interest, newsletter, generation, scheduler) + discovery (autonomous_discovery, direct_search, list_mining, discovery_metrics) + AI (tier1, llama_wrapper, llama_wrapper_tier1) + support (blacklist, health_check, quality_scoring)
│       ├── models.py          # SQLAlchemy ORM models (Users, UserInterests, Newsletters)
│       ├── schemas.py         # Pydantic request/response schemas
│       ├── database.py        # SQLite WAL mode + Alembic integration
│       ├── config.py          # Web app configuration
│       ├── dependencies.py    # FastAPI dependency injection
│       ├── error_handlers.py  # Global error handling
│       ├── rate_limiter.py
│       └── file_cache.py      # LRU file cache
├── NewsLlama/                 # Native macOS SwiftUI app (XcodeGen project)
├── tests/
│   ├── unit/                  # CLI/batch mode tests
│   └── web/unit/              # Web application tests (500+ tests)
├── docs/                      # Architecture, deployment, user guide
├── config/                    # Configuration templates
├── templates/                 # Jinja2 HTML templates
├── output/                    # Generated digests (HTML, JSON, RSS)
├── alembic.ini
├── requirements.txt
├── setup.py                   # Automated setup script
└── dev.sh                     # Development helper script
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **CLI** | Python, asyncio |
| **Web Backend** | FastAPI, SQLAlchemy, SQLite (WAL mode) |
| **Migrations** | Alembic |
| **Scheduler** | APScheduler |
| **LLM** | open-agent-sdk (OpenAI-compatible endpoints) |
| **macOS App** | SwiftUI, XcodeGen |
| **Templates** | Jinja2 |

## Common Commands

```bash
# Setup
python setup.py
# Or manually:
pip install -r requirements.txt
cp .env.example .env

# CLI mode
python main.py
python main.py --interests AI "machine learning" rust startups
python main.py --schedule

# Web server
./venv/bin/uvicorn src.web.app:app --host 0.0.0.0 --port 8000
./venv/bin/uvicorn src.web.app:app --reload --port 8000  # dev mode

# Database migrations
TESTING=true ./venv/bin/alembic upgrade head

# Development
./dev.sh install
./dev.sh test
./dev.sh test-coverage
./dev.sh lint
./dev.sh format
./dev.sh run

# Tests
pytest tests/unit/                                           # CLI tests
TESTING=true PYTHONPATH=. pytest tests/web/unit/             # Web tests
TESTING=true PYTHONPATH=. pytest tests/web/unit/ --cov=src/web --cov-report=html
```

**Always set `TESTING=true` when running tests** to disable the background scheduler.

## Configuration

Key `.env` variables:

```bash
# LLM
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=llama-3.1-8b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000

# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# Output
OUTPUT_FORMATS=html,rss,json
MAX_ARTICLES_PER_CATEGORY=10

# Web/Scheduler
DATABASE_URL=sqlite:///./news_llama.db
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=6
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Los_Angeles

# Enable AI source discovery
ENABLE_LLM_SOURCE_DISCOVERY=true
```

## Architecture

### CLI Mode
`main.py` → aggregators (RSS, Twitter, Reddit, HN, dynamic) → content processor (dedup, filter, score) → LLM summarizer → output generators (HTML/JSON/RSS)

### Web Mode
FastAPI app with 15 service modules. Service layer drives business logic; routes are thin controllers. Core services handle user, interest, newsletter, generation, and scheduling. Extended services cover autonomous source discovery, direct search, list mining, discovery metrics, Tier 1 LLM integration, quality scoring, blacklist management, and health checks. APScheduler runs daily generation per-user. SQLite WAL mode with optimized indexes. LRU file cache for generated newsletters.

### Source Discovery (Five Tiers)
1. Predefined patterns (fast lookup)
2. LLM subreddit matching (temperature 0.3, exact-match focused)
3. Broad LLM discovery (multi-source)
4. Exact match fallback (`r/{interest}`)
5. Reddit search (last resort)

### LLM Integration (open-agent-sdk)
- Streaming JSON-first prompting for summarization
- Tool use (web_search via DuckDuckGo) for source discovery
- `auto_execute_tools=False` — manual tool result loop

### JSON API v1 (macOS app)
| Endpoint | Description |
|----------|-------------|
| `GET/POST /api/v1/users` | User creation/retrieval |
| `GET /api/v1/interests/predefined` | Predefined interests |
| `POST /api/v1/interests` | Add/remove interests |
| `GET /api/v1/newsletters` | List newsletters |
| `POST /api/v1/newsletters/generate` | Trigger generation |

## Development Rules

- TDD: Write failing tests before implementation
- Always run `TESTING=true` in test environments to prevent scheduler startup
- `seed_library` must run before other seeds (calendar, tasks, social depend on it)
- No stack traces exposed in user-facing error responses
- **Coverage target**: 80%+ for `src/web/` (250+ tests, 99%+ pass rate)

## macOS App

```bash
cd NewsLlama
xcodegen generate          # Requires XcodeGen
open "News Llama.xcodeproj"
```

The macOS app requires the web server running locally on port 8000.
