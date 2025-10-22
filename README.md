# News Llama 🦙📰

AI-powered news curation engine that aggregates content from RSS, Twitter/X, Hacker News, Reddit, and web search, then summarizes the most relevant articles using local LLM.

## ✨ Features

- **🤖 AI-Powered Source Discovery**: Five-tier progressive discovery strategy with intelligent subreddit matching
- **📡 Multi-Source Aggregation**: RSS, Twitter/X, Reddit (with smart time filtering for 24h top posts)
- **🧠 Smart Content Processing**: Duplicate detection, sentiment analysis, keyword extraction
- **⚡ Performance Optimized**: Pre-filters articles before LLM summarization (saves ~90% of LLM time!)
- **📝 AI Summarization**: Local LLM-powered summarization via open-agent-sdk
- **🎯 Personalized Curation**: Discovery-only mode when interests provided (skips default sources)
- **📊 Rich Output Formats**: Beautiful HTML, RSS, and JSON outputs
- **🔧 Environment-Based Config**: Secure dotenv configuration for easy deployment

## 🚀 Quick Start

### 1. Setup the project

```bash
# Clone and setup
git clone <your-repo>
cd news-llama
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

## 🎯 AI Source Discovery

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

## 🏗️ Project Structure

```
news-llama/
├── src/
│   ├── aggregators/         # Source-specific aggregators
│   │   ├── rss_aggregator.py
│   │   ├── twitter_aggregator.py
│   │   ├── reddit_aggregator.py
│   │   ├── hackernews_aggregator.py
│   │   └── dynamic_aggregator.py  # AI-discovered sources
│   ├── processors/          # Content processing
│   │   ├── content_processor.py
│   │   ├── duplicate_detector.py
│   │   └── source_discovery.py   # LLM source discovery
│   ├── summarizers/         # LLM summarization
│   ├── generators/          # Output generation
│   └── utils/              # Configuration and models
├── config/                 # Configuration templates
├── output/                 # Generated content
├── templates/              # HTML templates
├── tests/                  # Test suite
├── .env.example           # Environment variables template
└── setup.py               # Automated setup script
```

## ⚡ Performance

News Llama is optimized for speed with **intelligent pre-filtering**:

### Real Performance Example

**10 interests** (AI, rust, LocalLLM, boxoffice, television, movies, etc.):

```
📊 Collection:    678 total articles
🔍 Deduplication: 661 unique articles
⚡ Pre-filtering: 100 articles (10 per category)
🤖 Summarized:    100 articles
✅ Valid output:  78 articles
⏱️  LLM time:     ~21 minutes
```

**Without pre-filtering**: Would have taken ~2 hours to summarize all 661 articles!

### How It Works

1. **Smart Scoring**: Ranks articles by recency + content quality + Reddit score
2. **Category Limits**: Keeps top N articles per category (default: 10)
3. **LLM Efficiency**: Only summarizes articles that will be displayed
4. **Result**: ~90% reduction in LLM processing time

## ⚙️ Configuration

### Key Environment Variables

```bash
# LLM Configuration
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=llama-3.1-8b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000

# Reddit API (required for Reddit sources)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password

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

## 🔧 Development

### Development Commands

```bash
# Install development dependencies
./dev.sh install

# Run tests
./dev.sh test

# Run with coverage
./dev.sh test-coverage

# Lint code
./dev.sh lint

# Format code
./dev.sh format

# Run the application
./dev.sh run
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_models.py
```

## 📊 Output Examples

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

## 🤖 LLM Integration

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
LLM_MAX_TOKENS=4000
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

## 🔒 Security & Privacy

- **Local Processing**: All processing happens locally
- **No Data Sharing**: Your interests and reading habits stay private
- **Environment Variables**: Secure API key management
- **Open Source**: Transparent and auditable code

## ⚠️ Known Limitations

- **Failed Content Extraction**: ~20-25% of articles fail extraction (paywalls, dead links, image-only posts). These are automatically filtered out.
- **RSS Feed Errors**: Some discovered RSS feeds may return 404s (sites change URLs over time). This is normal and logged as warnings.
- **Reddit Time Window**: Uses 24-hour `time_filter='day'` for top posts. Very low-activity subreddits may return 0 posts.
- **No NSFW Support**: Intentionally excluded due to Reddit API limitations on restricted/quarantined subreddit access.

## 🤝 Contributing

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

## 📝 License

This project is open source. See LICENSE file for details.

## 🙏 Acknowledgments

- **open-agent-sdk**: Local LLM integration with tool use
- **asyncpraw**: Async Reddit API client
- **Feedparser**: RSS feed parsing
- **TextBlob**: Sentiment analysis and keyword extraction
- **Pydantic**: Data validation and settings management
- **Jinja2**: Beautiful HTML template rendering