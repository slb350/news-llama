# News Llama

## Project Description

An AI-powered news curation engine that aggregates content from RSS, Twitter/X, Reddit, and web search (DuckDuckGo), then summarizes the most relevant articles using a local LLM via **open-agent-sdk**. Runs in CLI batch mode or as a persistent web application with multi-user support and automatic daily newsletter generation. (Hacker News aggregator exists but is disabled due to empty content extraction.)

## Repository Structure

```
news-llama/
├── main.py                    # CLI entry point (NewsLlama class, async orchestration)
├── setup.py                   # Automated setup script
├── take_screenshots.py        # Screenshot helper for macOS app
├── requirements.txt           # 35 Python dependencies
├── alembic.ini                # Database migration configuration
├── pytest.ini                 # Test configuration (80%+ coverage target)
├── CONTRIBUTING.md            # Contribution guidelines
├── CHANGELOG.md               # Project changelog
├── src/
│   ├── aggregators/           # Source-specific aggregators
│   │   ├── base.py            # BaseAggregator abstract class
│   │   ├── rss_aggregator.py
│   │   ├── twitter_aggregator.py
│   │   ├── reddit_aggregator.py # asyncpraw with 24h smart time filtering
│   │   ├── hackernews_aggregator.py  # Disabled: empty content
│   │   └── dynamic_aggregator.py    # AI-discovered sources
│   ├── processors/            # Content processing
│   │   ├── content_processor.py    # Cleaning, filtering, categorization, scoring
│   │   ├── duplicate_detector.py   # Cosine similarity dedup (threshold 0.8)
│   │   └── source_discovery.py     # LLM-powered five-tier source discovery
│   ├── summarizers/           # LLM summarization via open-agent-sdk
│   │   └── llm_summarizer.py       # Batch summarization, streaming JSON-first
│   ├── generators/            # Output generation
│   │   ├── html_generator.py  # Responsive HTML with Jinja2 templates
│   │   ├── json_generator.py
│   │   └── rss_generator.py
│   ├── utils/                 # Configuration, models, utilities
│   │   ├── config.py          # Pydantic-based configuration (LLM, social, processing)
│   │   ├── models.py          # Article, SummarizedArticle dataclasses
│   │   ├── logger.py          # Logging setup (loguru)
│   │   ├── scheduler.py       # CLI mode scheduler
│   │   ├── constants.py       # Predefined interests and source patterns
│   │   ├── llm_prompts.py     # System prompts for LLM
│   │   ├── image_cache.py     # Image caching
│   │   └── security.py        # Security utilities
│   └── web/                   # FastAPI web application
│       ├── app.py             # FastAPI app, route registration, lifespan management
│       ├── models.py          # SQLAlchemy ORM (8 tables: users, newsletters,
│       │                      #   user_interests, tier1_sources, source_blacklist,
│       │                      #   discovered_sources, source_health, source_contributions)
│       ├── schemas.py         # Pydantic request/response schemas
│       ├── database.py        # SQLite WAL mode + connection pooling + Alembic
│       ├── config.py          # Web app configuration
│       ├── dependencies.py    # FastAPI dependency injection (get_db, get_current_user)
│       ├── error_handlers.py  # Global error handling (no stack traces exposed)
│       ├── rate_limiter.py    # Sliding window rate limiter (10 req/min default)
│       ├── file_cache.py      # LRU cache for newsletter HTML (100 files, ~10MB cap)
│       ├── static/            # Static assets (CSS, JS, favicon, logo)
│       │   ├── styles.css
│       │   ├── avatar-manager.js
│       │   ├── interest-manager.js
│       │   └── form-accessibility.js
│       ├── templates/         # Jinja2 HTML templates
│       │   ├── base.html
│       │   ├── profile_select.html
│       │   ├── profile_create.html
│       │   ├── profile_settings.html
│       │   ├── calendar.html
│       │   └── metrics.html
│       ├── api/               # RESTful JSON API (v1)
│       │   └── v1/            # v1 routes: users.py, interests.py, newsletters.py
│       └── services/          # 15 service modules: core (user, interest, newsletter,
│                              #   generation, scheduler) + discovery (autonomous_discovery,
│                              #   direct_search, list_mining, discovery_metrics) +
│                              #   AI (tier1, llama_wrapper, llama_wrapper_tier1) +
│                              #   support (blacklist, health_check, quality_scoring)
├── NewsLlama/                 # Native macOS SwiftUI app (XcodeGen project)
├── tests/
│   ├── test_*.py              # Root-level CLI tests (5 files: models, content_processor,
│   │                          #   duplicate_detector, security, integration)
│   ├── unit/                  # Additional CLI/batch mode tests (4 files: llm_prompts,
│   │                          #   llm_summarizer_caching, main_tier1_integration, models)
│   └── web/unit/              # Web application tests (27 files, 416 test functions)
│       ├── conftest.py        # Shared fixtures (in-memory SQLite for isolation)
│       ├── api/               # API v1 endpoint tests (3 files)
│       │   ├── test_api_users.py
│       │   ├── test_api_interests.py
│       │   └── test_api_newsletters.py
│       ├── test_user_service.py
│       ├── test_interest_service.py
│       ├── test_newsletter_service.py
│       ├── test_generation_service.py  # Newsletter generation orchestration
│       ├── test_scheduler_service.py
│       ├── test_llama_wrapper.py
│       ├── test_llama_wrapper_tier1.py
│       ├── test_autonomous_discovery_service.py
│       ├── test_direct_search_service.py
│       ├── test_list_mining_service.py
│       ├── test_discovery_metrics.py
│       ├── test_tier1_service.py
│       ├── test_blacklist_service.py
│       ├── test_quality_scoring.py
│       ├── test_health_check_service.py
│       ├── test_routes_profile.py      # Profile creation/selection/deletion routes
│       ├── test_routes_calendar.py     # Calendar view routes
│       ├── test_routes_settings.py     # Profile settings routes
│       ├── test_routes_newsletter.py   # Newsletter view/generate/retry routes
│       ├── test_routes_health.py       # Health check routes
│       ├── test_error_handlers.py      # Error handling (user-friendly messages)
│       ├── test_performance.py         # Indexes, rate limiting, LRU caching
│       ├── test_ui_states.py           # Empty/loading/error UI states
│       └── test_source_discovery_models.py
├── docs/                      # Architecture, deployment, user guide
├── config/                    # Configuration templates (config.example.yaml)
├── assets/                    # Static assets (logo.png)
├── screenshots/               # Demo screenshots and GIFs
├── db/                        # Alembic migration files
└── .env.example               # Environment variables template
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **CLI** | Python 3.8+, asyncio |
| **Web Backend** | FastAPI 0.109+, SQLAlchemy 2.0+, SQLite (WAL mode) |
| **Migrations** | Alembic |
| **Scheduler** | APScheduler 3.10+ |
| **LLM** | open-agent-sdk (OpenAI-compatible endpoints) with tool use |
| **Content Sources** | RSS (feedparser), asyncpraw (Reddit), tweepy (Twitter), newspaper3k, BeautifulSoup4, ddgs (DuckDuckGo) |
| **Text Processing** | NLTK, TextBlob (sentiment), newspaper3k (article extraction) |
| **macOS App** | SwiftUI, XcodeGen |
| **Templates** | Jinja2 |
| **Logging** | loguru |
| **Validation** | pydantic 2.0+ |
| **Linting** | ruff, black, flake8, mypy |
| **Testing** | pytest 7.4+, pytest-asyncio, pytest-cov |

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

# Tests
pytest tests/                                                # All tests
pytest tests/test_*.py tests/unit/                          # CLI tests only
TESTING=true PYTHONPATH=. pytest tests/web/unit/             # Web tests
TESTING=true PYTHONPATH=. pytest tests/web/unit/ --cov=src/web --cov-report=html
TESTING=true PYTHONPATH=. pytest tests/web/unit/test_user_service.py  # Specific file
```

**Always set `TESTING=true` when running tests** to disable the background scheduler.

## Configuration

Key `.env` variables (see `.env.example` for the full list):

```bash
# LLM
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=llama-3.1-8b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
LLM_TIMEOUT=300

# Twitter/X
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret

# Reddit
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=news-llama/1.0

# Output
OUTPUT_FORMATS=html,rss,json
OUTPUT_DIRECTORY=output
MAX_ARTICLES_PER_CATEGORY=10
DUPLICATE_THRESHOLD=0.8
MIN_ARTICLE_LENGTH=200
MAX_ARTICLE_AGE_HOURS=24

# Processing
ENABLE_SENTIMENT_ANALYSIS=true
ENABLE_LLM_SOURCE_DISCOVERY=true

# Web/Scheduler
DATABASE_URL=sqlite:///data/news_llama.db
SECRET_KEY=your-secret-key-change-in-production
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=6
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Los_Angeles
TESTING=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/news-llama.log
```

## Architecture

### CLI Mode
`main.py` → aggregators (RSS, Twitter, Reddit, dynamic) → content processor (dedup, filter, score) → LLM summarizer → output generators (HTML/JSON/RSS)

**Performance flow**: Articles are scored by recency + content quality + Reddit score, then pre-filtered to top N per category *before* LLM processing. This saves ~90% of LLM processing time (example: 661 raw articles → 100 pre-filtered → 78 valid LLM-summarized).

### Web Mode
FastAPI app with 15 service modules. Service layer drives all business logic; routes are thin controllers. APScheduler runs 4 scheduled jobs: daily newsletter generation (6 AM Pacific), weekly autonomous source discovery (Sunday 3 AM), weekly database VACUUM (Thursday 11 PM), and hourly rate-limiter cleanup. SQLite WAL mode allows concurrent reads. LRU file cache (100 newsletters, ~10MB) avoids re-rendering generated content.

**Request flow**: HTTP Request → FastAPI route → dependency injection (get_db, get_current_user) → service call → SQLAlchemy ORM → SQLite (WAL mode) → response

**Newsletter generation flow**: Trigger (scheduler or manual) → `generation_service.py` orchestrates → `llama_wrapper.py` delegates to CLI `NewsLlama` class → result saved to DB → file cache populated

### Source Discovery (Five Tiers)
1. Predefined patterns (fast lookup for known topics)
2. LLM subreddit matching (temperature 0.3, exact-match focused, avoids false positives)
3. Broad LLM discovery (multi-source: Twitter, RSS)
4. Exact match fallback (`r/{interest}`)
5. Reddit search (last resort across all subreddits)

### LLM Integration (open-agent-sdk)
- **Summarization**: Streaming JSON-first prompting. Model returns `{"summary": ..., "key_points": [...], "importance": 0.0-1.0}`. Parsed from streamed text after completion.
- **Source discovery**: Tool use pattern with `web_search` (DuckDuckGo). `auto_execute_tools=False` — manual tool execution loop so we can inject custom search logic.
- **Error handling**: LLM timeout/failure on any article → that article skipped (not fatal). Generation failure → retry up to 3 times.

### Database Schema (Web Mode)
8 tables with optimized indexes:
- `users` — id (Integer PK), first_name, avatar_path, created_at
- `user_interests` — id, user_id (FK), interest_name, is_predefined, added_at; unique on (user_id, interest_name), index on user_id
- `newsletters` — id (Integer PK), user_id (FK), date, guid (unique), file_path, status, generated_at, retry_count; indexes on (user_id, date), (status), (user_id)
- `tier1_sources` — auto-populated dynamic Tier 1 sources via weekly discovery
- `source_blacklist` — sources auto-blacklisted on repeated failures
- `discovered_sources` — all sources found by weekly discovery job
- `source_health` — health check results per source (updated weekly)
- `source_contributions` — per-newsletter article collection/inclusion tracking

**WAL mode** enables concurrent reads without blocking writes. **Eager loading** via `joinedload` prevents N+1 queries in list views. The `source_contributions` table tracks which sources contributed articles to each generated newsletter for discovery metrics.

### Performance Optimizations
- **Pre-filtering**: Articles ranked and capped per category before LLM (~90% LLM time savings)
- **Database indexes**: 6+ indexes on commonly filtered/sorted columns
- **LRU file cache**: Generated newsletter HTML cached in memory (100 entries max)
- **Rate limiting**: Sliding window limiter (10 req/min default) on API endpoints
- **Eager loading**: `joinedload` on all ORM queries that access related objects

### JSON API v1 (macOS app)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/users` | List all users with interests and newsletter counts |
| `GET` | `/api/v1/users/{user_id}` | Get user with full interest details |
| `GET` | `/api/v1/users/{user_id}/newsletters` | Get newsletters for user (by month) |
| `GET` | `/api/v1/interests/predefined` | Predefined interests (grouped or flat via `?flat=true`) |
| `GET` | `/api/v1/interests/search` | Search predefined interests (`?q=query`) |
| `GET` | `/api/v1/newsletters/{guid}/content` | Get newsletter content (JSON + HTML) |
| `GET` | `/api/v1/newsletters/{guid}/render` | Render newsletter HTML (for WKWebView) |

### Web UI Routes (server-rendered)
| Route | Description |
|-------|-------------|
| `GET /` | Homepage / profile selector |
| `GET /profile/new` | Profile creation page |
| `POST /profile/create` | Submit new profile (JSON, sets cookie) |
| `POST /profile/avatar` | Upload profile avatar image (500KB max, validated) |
| `DELETE /profile/{user_id}` | Delete profile and all associated data |
| `GET /calendar` | Newsletter calendar (current month) |
| `GET /calendar/{year}/{month}` | Newsletter calendar (specific month, HTMX partial) |
| `GET /profile/settings` | Interest management page |
| `POST /profile/settings` | Update name and/or interests |
| `POST /profile/settings/interests/add` | Add single interest |
| `POST /profile/settings/interests/remove` | Remove single interest |
| `GET /newsletters/{guid}` | View a specific newsletter (HTML or status JSON) |
| `POST /newsletters/generate` | Trigger newsletter generation (rate-limited) |
| `POST /newsletters/{guid}/retry` | Retry a failed newsletter |
| `GET /metrics` | Discovery system metrics (public) |
| `GET /health/scheduler` | Scheduler status and jobs |
| `GET /health/generation` | Generation metrics and success rate |

## Service Layer Details

| Service | Responsibility |
|---------|---------------|
| `user_service.py` | User CRUD, profile management |
| `interest_service.py` | Interest add/remove, predefined list (grouped/flat) |
| `newsletter_service.py` | Newsletter CRUD, retrieval, status tracking |
| `generation_service.py` | Generation orchestration, retry logic (max 3), metrics |
| `scheduler_service.py` | APScheduler lifecycle (start/stop/status) |
| `llama_wrapper.py` | Bridge from web to CLI `NewsLlama` class |
| `llama_wrapper_tier1.py` | Tier 1 LLM integration variant |
| `autonomous_discovery_service.py` | Autonomous source discovery |
| `direct_search_service.py` | Direct search without LLM |
| `list_mining_service.py` | Source list mining |
| `discovery_metrics_service.py` | Discovery quality metrics tracking |
| `tier1_service.py` | Tier 1 discovery integration |
| `blacklist_service.py` | Source blacklist management |
| `quality_scoring.py` | Article and source quality scoring |
| `health_check_service.py` | App health and scheduler status |

## Development Rules

- **TDD**: Write failing tests before implementation
- **TESTING=true**: Always set when running tests to prevent scheduler startup
- **No stack traces**: Never expose internal errors in user-facing API responses
- **No 500s**: All routes must handle malformed input gracefully (return 400/404/422)
- **Coverage target**: 80%+ for `src/` (pytest.ini `--cov-fail-under=80` covers all of `src`)
- **Eager loading**: Always use `joinedload`/`contains_eager` for relationships accessed in loops
- **Rate limiting**: All mutating API endpoints should go through the rate limiter

## Test Patterns

```python
# Always use in-memory SQLite for isolation (from conftest.py)
@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

# TESTING=true disables APScheduler — always set in test environments
# Example test structure:
def test_create_user_success(db):
    user = user_service.create_user(db, name="Alice")
    assert user.name == "Alice"
    assert user.id is not None

def test_create_newsletter_retry_on_failure(db, mock_llama):
    mock_llama.side_effect = [Exception("timeout"), "success"]
    result = generation_service.generate(db, user_id="...", date=date.today())
    assert result.status == "completed"  # retried and succeeded
```

## Known Limitations

- **Content extraction failures**: ~20-25% of articles fail extraction (paywalls, dead links, image-only). Filtered out automatically.
- **RSS feed errors**: Discovered feeds may return 404s (sites change URLs). Logged as warnings, not errors.
- **Reddit time window**: Uses 24-hour `time_filter='day'` for top posts. Very low-activity subreddits may return 0 posts.
- **No NSFW support**: Intentionally excluded (Reddit API limitations on restricted/quarantined subreddits).
- **HackerNews aggregator**: Disabled due to empty content extraction (HN uses external links).
- **SQLite only**: Web mode uses SQLite; no PostgreSQL support (sufficient for single-server deployment).

## macOS App

```bash
cd NewsLlama
xcodegen generate          # Requires XcodeGen
open "News Llama.xcodeproj"
```

The macOS app requires the web server running locally on port 8000. It communicates exclusively via the `/api/v1` JSON endpoints.
