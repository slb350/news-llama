# Contributing to News Llama

We welcome contributions to News Llama! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- A local LLM setup (for testing)

### Setup Development Environment

```bash
# Clone the repository
git clone <your-fork>
cd news-llama

# Setup the project
./dev.sh setup

# Install development dependencies
./dev.sh install

# Run tests to ensure everything works
./dev.sh test
```

## 📝 How to Contribute

### 1. Create an Issue

Before starting work, create an issue to discuss your proposed changes:
- Bug reports with detailed reproduction steps
- Feature requests with use cases
- Documentation improvements
- Performance optimizations

### 2. Fork and Branch

```bash
# Create your fork on GitHub
git clone <your-fork-url>
cd news-llama

# Create a feature branch
git checkout -b feature/your-feature-name
```

### 3. Make Your Changes

#### Code Style
- Follow PEP 8 style guidelines
- Use descriptive variable and function names
- Add type hints where appropriate
- Include docstrings for new functions

#### Testing
- Write tests for new functionality
- Ensure all existing tests pass
- Add integration tests if applicable

```bash
# Run linting
./dev.sh lint

# Run tests
./dev.sh test

# Run coverage
./dev.sh test-coverage
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "feat: add new aggregator for TechCrunch RSS

- Implement TechCrunchRSSAggregator class
- Add configuration options
- Add unit tests
- Update documentation"
```

### 5. Submit a Pull Request

- Push to your fork
- Create a pull request with a clear title and description
- Link to any related issues
- Describe testing done

## 🏗️ Architecture Overview

### Core Components

#### Aggregators (`src/aggregators/`)
- Collect content from various sources
- Each aggregator inherits from `BaseAggregator`
- Implement `collect()` and `_is_valid_article()` methods

#### Processors (`src/processors/`)
- `ContentProcessor`: Clean and analyze content
- `DuplicateDetector`: Remove duplicate articles
- `SourceDiscoveryEngine`: AI-powered source discovery

#### Summarizers (`src/summarizers/`)
- Generate AI-powered summaries using local LLM
- Extract key points and importance scores

#### Generators (`src/generators/`)
- Create output in various formats
- Currently supports HTML, extensible for RSS/JSON

#### Utils (`src/utils/`)
- Configuration management
- Data models
- Logging utilities

### Adding New Sources

1. **Create Aggregator Class**:
```python
# src/aggregators/newsource_aggregator.py
from src.aggregators.base import BaseAggregator
from src.utils.models import Article, SourceType

class NewSourceAggregator(BaseAggregator):
    async def collect(self) -> List[Article]:
        # Implementation here
        pass
    
    def _is_valid_article(self, article: Article) -> bool:
        # Validation logic
        pass
```

2. **Add to Main Application**:
```python
# main.py
from src.aggregators.newsource_aggregator import NewSourceAggregator

def _setup_aggregators(self):
    aggregators = {
        # ... existing aggregators
        'newsource': NewSourceAggregator(self.config),
    }
    return aggregators
```

3. **Add Configuration**:
```python
# src/utils/config.py
class NewSourceConfig(BaseModel):
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("NEWSOURCE_API_KEY"))
    # other config options
```

4. **Write Tests**:
```python
# tests/test_newsource_aggregator.py
import pytest
from src.aggregators.newsource_aggregator import NewSourceAggregator

def test_newsource_aggregator():
    # Test implementation
    pass
```

### Adding New Output Formats

1. **Create Generator Class**:
```python
# src/generators/json_generator.py
from src.generators.base import BaseGenerator

class JSONGenerator(BaseGenerator):
    def generate(self, articles: List[SummarizedArticle]):
        # JSON generation logic
        pass
```

2. **Register Generator**:
```python
# main.py
def _setup_generators(self):
    generators = {
        'html': HTMLGenerator(self.config),
        'json': JSONGenerator(self.config),  # Add this
    }
    return generators
```

## 🧪 Testing

### Test Structure
```
tests/
├── test_aggregators/
│   ├── test_rss_aggregator.py
│   └── test_twitter_aggregator.py
├── test_processors/
│   ├── test_content_processor.py
│   └── test_source_discovery.py
├── test_summarizers/
│   └── test_llm_summarizer.py
├── test_generators/
│   └── test_html_generator.py
└── test_utils/
    ├── test_config.py
    └── test_models.py
```

### Running Tests
```bash
# All tests
./dev.sh test

# Specific test file
pytest tests/test_models.py

# With coverage
./dev.sh test-coverage
```

### Writing Tests
- Use pytest fixtures for common setup
- Mock external API calls
- Test both success and failure cases
- Aim for high test coverage

## 📋 Code Review Process

### What Reviewers Look For
- Code follows project style guidelines
- Tests are comprehensive and pass
- Documentation is updated
- No breaking changes
- Security considerations
- Performance impact

### Review Checklist
- [ ] Code adheres to style guidelines
- [ ] Tests pass and cover new functionality
- [ ] Documentation is updated
- [ ] Changes don't break existing functionality
- [ ] Security implications considered
- [ ] Performance impact assessed

## 🐛 Bug Reports

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages
- Configuration used (redact sensitive info)

## 💡 Feature Requests

For feature requests:
- Describe the problem you're solving
- Explain why this feature is valuable
- Consider edge cases and limitations
- Suggest implementation approach if you have ideas

## 📚 Documentation

- Update README.md for user-facing changes
- Add inline docstrings for new functions
- Update this CONTRIBUTING.md for process changes
- Consider adding examples for complex features

## 🔒 Security

- Never commit API keys or secrets
- Use environment variables for configuration
- Follow security best practices
- Report security issues privately

## 🤝 Community Guidelines

- Be respectful and inclusive
- Help others learn and contribute
- Focus on constructive feedback
- Welcome newcomers and help them get started

## 📞 Getting Help

- Create an issue for questions
- Check existing issues and documentation
- Join discussions in pull requests
- Reach out to maintainers if needed

Thank you for contributing to News Llama! 🦙📰