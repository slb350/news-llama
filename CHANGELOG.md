# Changelog

All notable changes to News Llama will be documented in this file.

## 2026-10-04 (branch `fix/source-discovery-and-test-rot`, not merged)

Repair pass, stopped partway because the project is no longer in use.

### Fixed
- LLM source discovery read `source_type`/`confidence_score`/`reason` while the prompt asks for `type`/`confidence`/`reasoning`, so every discovered source was routed as `web_search`
- `your_*` placeholder API keys from `.env.example` passed validation
- RSS and Hacker News publication times were naive and mixed local and UTC; both now emit timezone-aware UTC
- Duplicate detection scores content-word Dice overlap with a 0.6 threshold; the same-domain bonus is gone
- Placeholder `example.com` articles for web-search sources and the unreachable tool-use path in discovery are removed
- Calendar grid aligns with real weekdays, and the "first newsletter" empty state shows only for users with no newsletters
- `pytest.ini` used a `[tool:pytest]` header, so pytest ignored it; the 80% coverage gate and strict markers now apply
- 19 stale or broken tests repaired; suite is 616 passed at 83% coverage

### Remaining
- `ruff check .` reports 236 findings under ruff 0.16.10's default rules, mostly naive `datetime.now()`/`date.today()` (DTZ, 143) and blind `except Exception` (BLE001, 53)

## [0.1.0] - 2024-XX-XX

### Added
- Initial release of News Llama
- AI-powered source discovery using LLM reasoning
- Multi-source aggregation (RSS, Twitter, Reddit, Hacker News, Web Search)
- Environment-based configuration with dotenv
- Local LLM integration via open-agent-sdk
- Content processing with duplicate detection and sentiment analysis
- Beautiful HTML output generation with responsive design
- Automated setup script and development tools
- Comprehensive test suite with pytest
- Support for personalized user interests
- Dynamic source discovery and aggregation

### Features
- **AI Source Discovery**: Automatically discovers relevant sources based on user interests
- **Smart Curation**: AI-powered ranking and importance scoring
- **Multiple Output Formats**: HTML, RSS, JSON (extensible)
- **Privacy-First**: Local processing with no data sharing
- **Modular Architecture**: Easy to extend with new sources and processors
- **Developer-Friendly**: Full testing suite, linting, and development tools

### Technical Details
- Built with Python 3.8+
- Uses Pydantic for type safety and validation
- Async/await for concurrent processing
- Modular aggregators for each source type
- Configurable processing pipelines
- Comprehensive logging and error handling