# Changelog

All notable changes to News Llama will be documented in this file.

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