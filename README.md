# News Llama 📰🦙

AI-powered news curation engine that aggregates content from RSS, Twitter/X, Reddit, and web search (DuckDuckGo), then summarizes the most relevant articles using a local LLM via open-agent-sdk.

![News Llama Demo](screenshots/demo.gif)

## Why News Llama?

Tired of doom-scrolling through endless feeds? News Llama curates a personalized daily digest based on *your* interests using AI-powered source discovery. It runs locally, keeps your reading habits private, and cuts through the noise with intelligent summarization. No ads, no tracking, no drama—just news.

## Features

- **AI-Powered Source Discovery**: Five-tier progressive discovery strategy with intelligent subreddit matching
- **Multi-Source Aggregation**: RSS, Twitter/X, Reddit (with smart time filtering for 24h top posts)
- **Smart Content Processing**: Duplicate detection, sentiment analysis, keyword extraction
- **Performance Optimized**: Pre-filters articles before LLM summarization (saves ~90% of LLM time!)
- **AI Summarization**: Local LLM-powered summarization via open-agent-sdk
- **Personalized Curation**: Discovery-only mode when interests provided (skips default sources)
- **Rich Output Formats**: Beautiful HTML, RSS, and JSON outputs
- **Environment-Based Config**: Secure dotenv configuration for easy deployment

## Quick Start

### 1. Setup the project

```bash
# Clone and setup
cd news-llama  # Navigate to your cloned repository
python setup.py

# Or manually:
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
```

### 2. Configure your environment

Edit `.env` file with your settings:

```bash
# LLM Configuration
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=llama-3.1-8b-instruct

# Optional: Social Media API Keys
TWITTER_API_KEY=your_twitter_api_key
REDDIT_CLIENT_ID=your_reddit_client_id

# Enable AI source discovery
ENABLE_LLM_SOURCE_DISCOVERY=true
```

### 3. Run with your interests

```bash
# Run once with default interests
python main.py

# Customize your interests
python main.py --interests AI "machine learning" rust startups

# Run in scheduled mode (uses SCHEDULER_* settings from .env)
python main.py --schedule

# Combine options
python main.py --interests AI programming --schedule
```

### 4. View your curated news

Your news digest will be generated in multiple formats:

- **HTML**: Open `output/news-YYYY-MM-DD.html` in your browser for a beautiful, responsive digest
- **JSON**: `output/news-YYYY-MM-DD.json` for programmatic access
- **RSS**: `output/news-YYYY-MM-DD.xml` for RSS readers

Configure which formats to generate in `.env` with `OUTPUT_FORMATS=html,rss,json`

## AI Source Discovery

News Llama uses a **five-tier progressive discovery strategy** with intelligent LLM-powered matching:

### Discovery Tiers (in order)

1. **Predefined Patterns**: Fast lookup for known topics (AI, rust, technology, etc.)
2. **LLM Subreddit Matching**: Focused discovery with temperature 0.3 to avoid false matches
   - Finds exact matches: "rust" → r/rust (NOT r/RustBelt)
   - Discovers variants: r/learnrust, r/rust_gamedev
   - Identifies specialized communities
3. **Broad LLM Discovery**: Multi-source discovery (Twitter, RSS feeds)
4. **Exact Match Fallback**: Tries r/{interest} directly
5. **Reddit Search**: Last resort across all subreddits

### Example Discoveries

**Interest: "AI"** → Discovers:
- **Reddit**: r/MachineLearning, r/LocalLLaMA, r/OpenAI, r/ClaudeAI, r/singularity
- **Twitter**: @sama, @ylecun, @karpathy, @fchollet, @openai
- **RSS**: OpenAI Blog, Anthropic News, DeepMind Blog

**Interest: "boxoffice"** → Discovers:
- **Reddit**: r/boxoffice, r/movies, r/movienews, r/film

**Interest: "rust"** → Discovers:
- **Reddit**: r/rust, r/learnrust, r/rust_gamedev
- **RSS**: This Week in Rust

## Project Structure

```
news-llama/
├── main.py                      # CLI entry point (NewsLlama class, async orchestration)
├── setup.py                     # Automated setup script
├── take_screenshots.py          # Screenshot helper for macOS app
├── requirements.txt             # Python dependencies (35 packages)
├── alembic.ini                  # Database migration configuration
├── CONTRIBUTING.md              # Contribution guidelines
├── CHANGELOG.md                 # Project changelog
├── src/
│   ├── aggregators/             # Source-specific aggregators
│   │   ├── base.py              # BaseAggregator abstract class
│   │   ├── rss_aggregator.py
│   │   ├── twitter_aggregator.py
│   │   ├── reddit_aggregator.py # asyncpraw with 24h smart time filtering
│   │   ├── hackernews_aggregator.py  # Disabled: empty content
│   │   └── dynamic_aggregator.py  # AI-discovered sources
│   ├── processors/              # Content processing
│   │   ├── content_processor.py # Cleaning, filtering, categorization, scoring
│   │   ├── duplicate_detector.py # Cosine similarity deduplication (threshold 0.8)
│   │   └── source_discovery.py  # LLM-powered five-tier source discovery
│   ├── summarizers/             # LLM summarization via open-agent-sdk
│   │   └── llm_summarizer.py    # Batch summarization, streaming JSON-first prompting
│   ├── generators/              # Output generation (HTML, JSON, RSS)
│   │   ├── html_generator.py    # Responsive HTML with Jinja2 templates
│   │   ├── json_generator.py
│   │   └── rss_generator.py
│   ├── utils/                   # Configuration and utilities
│   │   ├── config.py            # Pydantic-based configuration
│   │   ├── models.py            # Article, SummarizedArticle dataclasses
│   │   ├── logger.py            # Logging setup (loguru)
│   │   ├── scheduler.py         # CLI mode scheduler
│   │   ├── llm_prompts.py       # System prompts for LLM
│   │   ├── constants.py         # Predefined interests and source patterns
│   │   ├── image_cache.py       # Image caching utilities
│   │   └── security.py          # Security utilities
│   └── web/                     # FastAPI web application
│       ├── app.py               # FastAPI app, route registration, lifespan management
│       ├── models.py            # SQLAlchemy ORM (8 tables)
│       ├── schemas.py           # Pydantic request/response schemas
│       ├── database.py          # SQLite WAL mode + connection pooling
│       ├── config.py            # Web app configuration
│       ├── dependencies.py      # FastAPI dependency injection
│       ├── error_handlers.py    # Global error handling (no stack traces exposed)
│       ├── rate_limiter.py      # Sliding window rate limiter (10 req/min default)
│       ├── file_cache.py        # LRU cache for newsletter HTML (100 files, ~10MB)
│       ├── static/              # Static assets (CSS, JS, favicon, logo)
│       ├── templates/           # Jinja2 HTML templates (base, profile, calendar, metrics)
│       ├── api/                 # RESTful JSON API v1 (macOS client)
│       │   └── v1/
│       │       ├── users.py
│       │       ├── interests.py
│       │       └── newsletters.py
│       └── services/            # 15 service modules (business logic layer)
│           ├── user_service.py
│           ├── interest_service.py
│           ├── newsletter_service.py
│           ├── generation_service.py
│           ├── scheduler_service.py
│           ├── llama_wrapper.py
│           ├── autonomous_discovery_service.py
│           ├── direct_search_service.py
│           ├── list_mining_service.py
│           ├── discovery_metrics_service.py
│           ├── tier1_service.py
│           ├── llama_wrapper_tier1.py
│           ├── blacklist_service.py
│           ├── quality_scoring.py
│           └── health_check_service.py
├── NewsLlama/                   # Native macOS SwiftUI app (XcodeGen project)
├── tests/
│   ├── test_*.py                # Root-level CLI tests (5 files)
│   ├── unit/                    # Additional CLI/batch mode tests (4 files)
│   └── web/unit/                # Web application tests (26 files + api/ subdir, 416 functions)
├── docs/                        # Architecture, deployment, user guide
├── config/                      # Configuration templates (config.example.yaml)
├── assets/                      # Static assets (logo.png)
├── screenshots/                 # Demo screenshots and GIFs
├── db/                          # Alembic migration files
└── .env.example                 # Environment variables template
```

## Performance

News Llama is optimized for speed with **intelligent pre-filtering**:

### Real Performance Example

**10 interests** (AI, rust, LocalLLM, boxoffice, television, movies, etc.):

```
Collection:    678 total articles
Deduplication: 661 unique articles
Pre-filtering: 100 articles (10 per category)
Summarized:    100 articles
Valid output:  78 articles
LLM time:     ~21 minutes
```

**Without pre-filtering**: Would have taken ~2 hours to summarize all 661 articles!

### How It Works

1. **Smart Scoring**: Ranks articles by recency + content quality + Reddit score
2. **Category Limits**: Keeps top N articles per category (default: 10)
3. **LLM Efficiency**: Only summarizes articles that will be displayed
4. **Result**: ~90% reduction in LLM processing time

## Configuration

### Key Environment Variables

```bash
# LLM Configuration
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=llama-3.1-8b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# Reddit API (required for Reddit sources)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Output Settings
MAX_ARTICLES_PER_CATEGORY=10  # Articles to show per category
OUTPUT_FORMATS=html,rss,json
```

See `.env.example` for all available options:

- **LLM Settings**: API URL, model, temperature, tokens
- **Social Media**: Twitter and Reddit API keys
- **Processing**: Duplicate thresholds, sentiment analysis, article age limits
- **Output**: Formats, directories, articles per category
- **Discovery**: AI source discovery settings

### User Interests

Define your interests when initializing News Llama:

```python
interests = [
    "AI", "machine learning", "startups", 
    "python programming", "technology news"
]

news_llama = NewsLlama(user_interests=interests)
```

## macOS Native Client

News Llama ships a native SwiftUI macOS app (`NewsLlama/`) that consumes the JSON API v1.

### Quick Start

```bash
# Generate Xcode project from project.yml (requires XcodeGen)
cd NewsLlama
xcodegen generate
open "News Llama.xcodeproj"
```

The macOS app defaults to `https://news.localbrandonfamily.com` as the server URL. For local development, update the URL in **Settings → General** to `http://localhost:8000`. Requires macOS 14.0+. Includes auto-update support via Sparkle (Check for Updates in Settings). The app communicates with the web server via the `/api/v1` endpoints.

### JSON API v1

The web server exposes a RESTful JSON API at `/api/v1` for use by the macOS client and other native consumers:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/users` | List all users with interests and newsletter counts |
| `GET` | `/api/v1/users/{user_id}` | Get user with full interest details |
| `GET` | `/api/v1/users/{user_id}/newsletters` | Get newsletters for user (optional `?year=&month=`) |
| `GET` | `/api/v1/interests/predefined` | Predefined interests (grouped; add `?flat=true` for flat list) |
| `GET` | `/api/v1/interests/search` | Search predefined interests (`?q=query`) |
| `GET` | `/api/v1/newsletters/{guid}/content` | Get newsletter metadata + HTML content |
| `GET` | `/api/v1/newsletters/{guid}/render` | Render raw newsletter HTML (for WKWebView) |

---

## Web Application

News Llama includes a modern web interface for managing multiple user profiles, interests, and personalized newsletters.

### Features

- **Multi-User Profiles**: Create and manage multiple users with individual interests
- **Newsletter Calendar**: View all your newsletters organized by month
- **Interest Management**: Add/remove interests with instant newsletter regeneration
- **Background Scheduler**: Automatic daily newsletter generation at configured time
- **Performance Optimized**: Database indexes, rate limiting, and LRU file caching
- **Beautiful UI**: Responsive design with warm coral accents and smooth interactions

### Quick Start

#### 1. Install Dependencies

```bash
# Install all dependencies including web requirements
pip install -r requirements.txt
```

#### 2. Initialize Database

```bash
# Run Alembic migrations to create database schema
TESTING=true ./venv/bin/alembic upgrade head
```

#### 3. Configure Environment

Add web-specific settings to your `.env` file:

```bash
# Scheduler Configuration
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=6              # Generate at 6 AM
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Los_Angeles

# Database
DATABASE_URL=sqlite:///data/news_llama.db

# Security
SECRET_KEY=your-secret-key-change-in-production
```

#### 4. Start the Server

```bash
# Production mode
./venv/bin/uvicorn src.web.app:app --host 0.0.0.0 --port 8000

# Development mode (auto-reload)
./venv/bin/uvicorn src.web.app:app --reload --port 8000
```

#### 5. Open in Browser

Navigate to `http://localhost:8000` to access the web interface.

### Usage Guide

#### Creating Your Profile

1. **Visit Homepage**: Select "Create New Profile"
2. **Enter Name**: Provide your first name
3. **Select Interests**: Choose from predefined interests or add custom ones
4. **Submit**: Your first newsletter will be queued for generation (takes 10-15 minutes)

#### Managing Interests

1. **Access Settings**: Click your profile icon → "Profile Settings"
2. **Add Interests**: Type or select from available interests
3. **Remove Interests**: Click the × on any interest tag
4. **Auto-Regeneration**: Today's newsletter automatically regenerates when interests change

#### Viewing Newsletters

1. **Calendar View**: See all newsletters organized by month
2. **Status Indicators**:
   - 🟢 **Completed**: Ready to view
   - 🟡 **Generating**: Processing (may take 10-15 minutes)
   - 🔴 **Failed**: Click to retry
3. **Click Date**: View the newsletter for that day
4. **Generate New**: Click any empty date to queue a newsletter

#### Background Automation

The scheduler automatically generates newsletters daily at your configured time:

- **Default**: 6:00 AM Pacific Time
- **Configurable**: Set `SCHEDULER_HOUR`, `SCHEDULER_MINUTE`, `SCHEDULER_TIMEZONE` in `.env`
- **Per-User**: Generates for all users with interests
- **Retry Logic**: Automatically retries failed generations (max 3 attempts)

Check scheduler status: `http://localhost:8000/health/scheduler`

### Architecture

Built with **FastAPI**, **SQLAlchemy**, **SQLite** (WAL mode), **Alembic** migrations, and **APScheduler** for background jobs.

**Key Components**:
- **Database**: 8 tables with optimized indexes — core (users, user_interests, newsletters) + discovery system (tier1_sources, source_blacklist, discovered_sources, source_health, source_contributions)
- **Service Layer**: 15 service modules — core (user, interest, newsletter, generation, scheduler), discovery (autonomous_discovery, direct_search, list_mining, discovery_metrics), AI integration (tier1, llama_wrapper, llama_wrapper_tier1), and support (blacklist, health_check, quality_scoring)
- **API**: RESTful endpoints with cookie-based sessions
- **Performance**: Database indexes, rate limiting, LRU file caching, eager loading

**Deep dive**: [Why We Over-Engineered Database Indexes for a Family SQLite App](https://open.substack.com/pub/stephenbrandon525517/p/a-love-letter-to-indexes-sqlite-and) - A detailed exploration of our indexing strategy and performance philosophy.

**API Endpoints**:
- **Pages**: `/`, `/profile/new`, `/calendar`, `/calendar/{year}/{month}`, `/profile/settings`, `/newsletters/{guid}`, `/metrics`
- **Actions**: `/profile/create`, `/profile/avatar`, `/profile/settings/interests/add`, `/profile/settings/interests/remove`, `/newsletters/generate`, `/newsletters/{guid}/retry`
- **Health**: `/health/scheduler`, `/health/generation`
- **JSON API v1**: `/api/v1/users`, `/api/v1/users/{id}`, `/api/v1/users/{id}/newsletters`, `/api/v1/interests/predefined`, `/api/v1/interests/search`, `/api/v1/newsletters/{guid}/content`, `/api/v1/newsletters/{guid}/render`

**Error Handling**: User-friendly messages for all scenarios, no stack traces exposed.

For detailed architecture documentation, see [docs/architecture.md](docs/architecture.md).

### Configuration Reference

#### Web-Specific Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///data/news_llama.db

# Security
SECRET_KEY=your-secret-key-change-in-production

# Scheduler
SCHEDULER_ENABLED=true          # Enable/disable background scheduler
SCHEDULER_HOUR=6                # Hour for daily generation (0-23)
SCHEDULER_MINUTE=0              # Minute for daily generation (0-59)
SCHEDULER_TIMEZONE=America/Los_Angeles  # Timezone for scheduler

# Testing (disable scheduler during tests)
TESTING=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/news-llama.log
```

All CLI configuration options (LLM, social media, processing) still apply to web mode.

### Deployment

For production deployment (systemd, nginx, backups), see [docs/deployment.md](docs/deployment.md).

For end-user documentation, see [docs/user-guide.md](docs/user-guide.md).

For technical architecture details, see [docs/architecture.md](docs/architecture.md).

## Development

### Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
./venv/bin/uvicorn src.web.app:app --reload --port 8000

# Lint code
ruff check src/ tests/
flake8 src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/
```

### Testing

#### CLI Tests

```bash
# Run root-level CLI tests
pytest tests/test_*.py

# Run unit/ CLI tests
pytest tests/unit/

# Run specific test
pytest tests/unit/test_models.py
```

#### Web Tests

```bash
# Run all web tests
TESTING=true PYTHONPATH=. pytest tests/web/unit/

# Run with coverage
TESTING=true PYTHONPATH=. pytest tests/web/unit/ --cov=src/web --cov-report=html

# Run specific test file
TESTING=true PYTHONPATH=. pytest tests/web/unit/test_user_service.py
```

**Note**: Set `TESTING=true` to disable background scheduler during tests.

#### Test Structure

```
tests/
├── test_models.py             # CLI model tests
├── test_content_processor.py  # Content processor tests
├── test_duplicate_detector.py # Duplicate detection tests
├── test_security.py           # Security utility tests
├── test_integration.py        # CLI integration tests
├── unit/                      # Additional CLI/batch mode tests
│   ├── test_llm_prompts.py
│   ├── test_llm_summarizer_caching.py
│   ├── test_main_tier1_integration.py
│   └── test_models.py
└── web/
    └── unit/                  # Web application tests (416 functions)
        ├── conftest.py        # Shared fixtures (in-memory SQLite)
        ├── api/               # API v1 endpoint tests
        │   ├── test_api_users.py
        │   ├── test_api_interests.py
        │   └── test_api_newsletters.py
        ├── test_user_service.py
        ├── test_interest_service.py
        ├── test_newsletter_service.py
        ├── test_generation_service.py
        ├── test_scheduler_service.py
        ├── test_llama_wrapper.py
        ├── test_llama_wrapper_tier1.py
        ├── test_autonomous_discovery_service.py
        ├── test_direct_search_service.py
        ├── test_list_mining_service.py
        ├── test_discovery_metrics.py
        ├── test_tier1_service.py
        ├── test_blacklist_service.py
        ├── test_quality_scoring.py
        ├── test_health_check_service.py
        ├── test_routes_profile.py
        ├── test_routes_calendar.py
        ├── test_routes_settings.py
        ├── test_routes_newsletter.py
        ├── test_routes_health.py
        ├── test_error_handlers.py
        ├── test_performance.py
        ├── test_ui_states.py
        └── test_source_discovery_models.py
```

**Coverage Target**: 80%+ for `src/` (enforced via `--cov-fail-under=80` in pytest.ini)

## Output Examples

### HTML Digest Features
- **Personalized Header**: Shows your interests and discovery stats
- **Smart Categories**: Articles grouped by topic with AI ranking
- **Rich Article Cards**: Summaries, key points, sentiment, importance
- **Discovery Badges**: Highlights AI-discovered sources
- **Responsive Design**: Mobile-friendly layout

### Article Information
- **AI-generated summaries**: Concise summaries and 5-7 key bullet points
- **Sentiment analysis**: 0-100% score based on article language tone
  - 0-40%: Negative sentiment
  - 40-60%: Neutral/factual
  - 60-100%: Positive sentiment
- **Importance scoring**: LLM-generated 0.0-1.0 relevance score
- **Reading time estimates**: Based on word count
- **Source attribution**: Shows original source + discovery reasoning
- **Quality indicators**: Reddit scores, upvote ratios for social content

## LLM Integration

News Llama uses the **open-agent-sdk** for local LLM integration:

### Source Discovery
The LLM analyzes your interests and suggests relevant sources across platforms, with confidence scoring and reasoning.

### Content Summarization
Each article is summarized with:
- ~500-word summary
- 5-7 key bullet points
- Importance score (0.1-1.0)

### Smart Reasoning
- Identifies authoritative sources
- Understands topic relationships
- Adapts to current trends

### Open Agent SDK Integration (Showcase)
- Streaming completions with `AgentOptions` (model, base_url, temperature, max_tokens)
- JSON-first prompting: assistants return strictly-JSON payloads that we parse
- Tool use flow in discovery: a `web_search` tool (DuckDuckGo) is available to the agent
- Tool execution is mediated via `ToolUseBlock`/`add_tool_result`, then the agent returns a final JSON result

Minimal configuration (env):
```bash
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=llama-3.1-8b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
```

#### Code excerpts

Summarization (streaming JSON result):
```python
from open_agent.types import AgentOptions
from open_agent import client as oa_client, TextBlock

options = AgentOptions(
    system_prompt=(
        "You are a precise news summarization assistant. "
        "Always return valid JSON exactly matching the requested schema and nothing else."
    ),
    model=config.llm.model,
    base_url=config.llm.api_url,
    temperature=config.llm.temperature,
    max_tokens=config.llm.max_tokens,
    api_key="not-needed",
)

text_parts = []
async for msg in oa_client.query(prompt, options):
    for block in msg.content:
        if isinstance(block, TextBlock):
            text_parts.append(block.text)
```

Tool use (source discovery with `web_search`):
```python
from open_agent import Client, TextBlock, ToolUseBlock, ToolUseError
from open_agent.types import AgentOptions
from open_agent.tools import Tool

async def web_search_handler(params):
    # run DuckDuckGo search and return {"results": [{"title":..., "url":...}, ...]}
    ...

tool = Tool(
    name='web_search',
    description='Search the web for recent sources related to a topic',
    input_schema={'query': str, 'max_results': int},
    handler=web_search_handler,
)

options = AgentOptions(
    system_prompt=(
        "You are an expert source discovery assistant. You can call the web_search tool when needed."
    ),
    model=config.llm.model,
    base_url=config.llm.api_url,
    tools=[tool],
    auto_execute_tools=False,
    api_key="not-needed",
)

client = Client(options)
await client.query(prompt)
async for block in client.receive_messages():
    if isinstance(block, TextBlock):
        ... # collect final JSON
    elif isinstance(block, ToolUseBlock):
        result = await web_search_handler(block.input)
        await client.add_tool_result(block.id, result, name=block.name)
    elif isinstance(block, ToolUseError):
        ... # log tool error
await client.close()
```

## Security & Privacy

- **Local Processing**: All processing happens locally
- **No Data Sharing**: Your interests and reading habits stay private
- **Environment Variables**: Secure API key management
- **Open Source**: Transparent and auditable code

## Known Limitations

- **Failed Content Extraction**: ~20-25% of articles fail extraction (paywalls, dead links, image-only posts). These are automatically filtered out.
- **RSS Feed Errors**: Some discovered RSS feeds may return 404s (sites change URLs over time). This is normal and logged as warnings.
- **Reddit Time Window**: Uses 24-hour `time_filter='day'` for top posts. Very low-activity subreddits may return 0 posts.
- **No NSFW Support**: Intentionally excluded due to Reddit API limitations on restricted/quarantined subreddit access.
- **HackerNews aggregator**: Disabled due to empty content extraction (HN uses external links, not on-site content).
- **SQLite only**: Web mode uses SQLite; no PostgreSQL support (sufficient for single-server deployment).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run linting and tests
6. Submit a pull request

### Adding New Sources

1. Create a new aggregator in `src/aggregators/`
2. Inherit from `BaseAggregator`
3. Implement `collect()` and `_is_valid_article()`
4. Add to the main aggregation loop

## License

This project is open source. See LICENSE file for details.

## Acknowledgments

- **open-agent-sdk**: Local LLM integration with tool use
- **asyncpraw**: Async Reddit API client
- **Feedparser**: RSS feed parsing
- **TextBlob**: Sentiment analysis and keyword extraction
- **Pydantic**: Data validation and settings management
- **Jinja2**: Beautiful HTML template rendering