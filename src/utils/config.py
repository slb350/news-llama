"""
Configuration management for News Llama using environment variables
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class RSSSource(BaseModel):
    url: str
    name: str
    category: str


class TwitterSource(BaseModel):
    username: str
    category: str


class RedditSource(BaseModel):
    subreddit: str
    category: str
    limit: int = 50


class DiscoveredSource(BaseModel):
    name: str
    url: Optional[str] = None
    username: Optional[str] = None
    subreddit: Optional[str] = None
    source_type: str  # rss, twitter, reddit, web_search
    category: str
    confidence_score: float
    reason: str


class Category(BaseModel):
    keywords: List[str]
    priority: str = "medium"  # high, medium, low


class LLMConfig(BaseModel):
    api_url: str = Field(default_factory=lambda: os.getenv("LLM_API_URL", "http://localhost:8000/v1"))
    model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "llama-3.1-8b-instruct"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.7")))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "4000")))
    timeout: int = Field(default_factory=lambda: int(os.getenv("LLM_TIMEOUT", "300")))


class OutputConfig(BaseModel):
    formats: List[str] = Field(default_factory=lambda: os.getenv("OUTPUT_FORMATS", "html,rss,json").split(","))
    directory: str = Field(default_factory=lambda: os.getenv("OUTPUT_DIRECTORY", "output"))
    template_dir: str = Field(default_factory=lambda: os.getenv("TEMPLATE_DIRECTORY", "templates"))
    max_articles_per_category: int = Field(default_factory=lambda: int(os.getenv("MAX_ARTICLES_PER_CATEGORY", "5")))
    include_images: bool = Field(default_factory=lambda: os.getenv("INCLUDE_IMAGES", "true").lower() == "true")


class ProcessingConfig(BaseModel):
    duplicate_threshold: float = Field(default_factory=lambda: float(os.getenv("DUPLICATE_THRESHOLD", "0.8")))
    min_article_length: int = Field(default_factory=lambda: int(os.getenv("MIN_ARTICLE_LENGTH", "200")))
    max_article_age: int = Field(default_factory=lambda: int(os.getenv("MAX_ARTICLE_AGE_HOURS", "24")))
    sentiment_analysis: bool = Field(default_factory=lambda: os.getenv("ENABLE_SENTIMENT_ANALYSIS", "true").lower() == "true")


class SchedulerConfig(BaseModel):
    enabled: bool = Field(default_factory=lambda: os.getenv("SCHEDULER_ENABLED", "true").lower() == "true")
    frequency: str = Field(default_factory=lambda: os.getenv("SCHEDULER_FREQUENCY", "daily"))
    time: str = Field(default_factory=lambda: os.getenv("SCHEDULER_TIME", "09:00"))


class LoggingConfig(BaseModel):
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    file: str = Field(default_factory=lambda: os.getenv("LOG_FILE", "logs/news-llama.log"))


class SocialMediaConfig(BaseModel):
    twitter_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("TWITTER_API_KEY"))
    twitter_api_secret: Optional[str] = Field(default_factory=lambda: os.getenv("TWITTER_API_SECRET"))
    twitter_access_token: Optional[str] = Field(default_factory=lambda: os.getenv("TWITTER_ACCESS_TOKEN"))
    twitter_access_token_secret: Optional[str] = Field(default_factory=lambda: os.getenv("TWITTER_ACCESS_TOKEN_SECRET"))

    reddit_client_id: Optional[str] = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID"))
    reddit_client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET"))
    reddit_username: Optional[str] = Field(default_factory=lambda: os.getenv("REDDIT_USERNAME"))
    reddit_password: Optional[str] = Field(default_factory=lambda: os.getenv("REDDIT_PASSWORD"))
    reddit_user_agent: Optional[str] = Field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "news-llama/1.0"))

    @field_validator('twitter_api_key', 'twitter_api_secret', 'twitter_access_token', 'twitter_access_token_secret')
    @classmethod
    def validate_twitter_keys(cls, v):
        if v:
            # Simple validation without importing to avoid circular dependency
            if len(v) < 20 or any(indicator in v.lower() for indicator in ['your_', 'example_', 'test_', 'xxx', '123']):
                try:
                    from src.utils.logger import logger
                    logger.warning(f"Twitter API key appears invalid: {v[:10]}...")
                except Exception:
                    # Fallback to print only if logger is unavailable
                    print(f"Warning: Twitter API key appears invalid: {v[:10]}...")
        return v

    @field_validator('reddit_client_id', 'reddit_client_secret')
    @classmethod
    def validate_reddit_keys(cls, v):
        if v and len(v) < 10:
            try:
                from src.utils.logger import logger
                logger.warning(f"Reddit credential appears too short: {len(v)} characters")
            except Exception:
                print(f"Warning: Reddit credential appears too short: {len(v)} characters")
        return v

    def validate_twitter_credentials(self) -> bool:
        """Validate all Twitter credentials are present and valid"""
        required_keys = [
            self.twitter_api_key, self.twitter_api_secret,
            self.twitter_access_token, self.twitter_access_token_secret
        ]

        if not all(required_keys):
            return False

        # Import here to avoid circular import
        try:
            from src.utils.security import APIKeyValidator
            return APIKeyValidator.validate_twitter_credentials(self)
        except ImportError:
            # Fallback validation
            return all(len(key) >= 20 for key in required_keys if key)

    def validate_reddit_credentials(self) -> bool:
        """Validate Reddit credentials are present and valid"""
        if not self.reddit_client_id or not self.reddit_client_secret:
            return False

        # Import here to avoid circular import
        try:
            from src.utils.security import APIKeyValidator
            return APIKeyValidator.validate_reddit_credentials(self)
        except ImportError:
            # Fallback validation
            base_ok = len(self.reddit_client_id) >= 10 and len(self.reddit_client_secret) >= 10
            return bool(base_ok)


class SourceDiscoveryConfig(BaseModel):
    enabled: bool = Field(default_factory=lambda: os.getenv("ENABLE_LLM_SOURCE_DISCOVERY", "true").lower() == "true")
    web_search_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("WEB_SEARCH_API_KEY"))
    max_sources_per_category: int = 100  # Allow many sources across all interests


class Config(BaseModel):
    sources: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    categories: Dict[str, Category] = Field(default_factory=dict)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    social_media: SocialMediaConfig = Field(default_factory=SocialMediaConfig)
    source_discovery: SourceDiscoveryConfig = Field(default_factory=SourceDiscoveryConfig)
    
    discovered_sources: List[DiscoveredSource] = Field(default_factory=list)
    # Propagated user preferences for generators
    user_interests: List[str] = Field(default_factory=list)

    def __init__(self, config_path: Optional[str] = None, skip_default_sources: bool = False):
        # Initialize with environment variables (Pydantic handles this via Field defaults)
        super().__init__()

        # Setup default sources only if not skipping (RSS feeds, categories, etc.)
        if not skip_default_sources:
            self._setup_default_sources()
        else:
            # Initialize empty sources when skipping defaults
            self.sources = {}
            self.categories = {}

        # Optionally load additional sources/categories from YAML if provided
        if config_path and Path(config_path).exists():
            config_data = self._load_config(config_path)
            # Only override sources and categories from YAML, not the Pydantic config models
            if 'sources' in config_data:
                self.sources = config_data['sources']
            if 'categories' in config_data:
                self.categories = {k: Category(**v) if isinstance(v, dict) else v
                                   for k, v in config_data['categories'].items()}

        # Ensure directories exist
        Path(self.output.directory).mkdir(parents=True, exist_ok=True)
        Path(self.output.template_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logging.file).parent.mkdir(parents=True, exist_ok=True)

        # Validate API keys
        self._validate_api_keys()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _setup_default_sources(self):
        """Setup default sources if no config file exists"""
        self.sources = {
            'rss': [
                {
                    'url': 'https://feeds.bbci.co.uk/news/rss.xml',
                    'name': 'BBC News',
                    'category': 'general'
                },
                {
                    'url': 'https://techcrunch.com/feed/',
                    'name': 'TechCrunch',
                    'category': 'technology'
                }
            ],
            'hackernews': {
                'enabled': True,
                'limit': 100,
                'categories': ['top', 'best', 'new']
            }
        }
        
        self.categories = {
            'technology': Category(keywords=['AI', 'machine learning', 'python', 'programming', 'startup', 'tech']),
            'programming': Category(keywords=['code', 'development', 'software', 'github', 'open source']),
            'general': Category(keywords=['news', 'world', 'politics', 'economy'])
        }

    def _validate_api_keys(self):
        """Validate API keys on initialization"""
        try:
            # Import here to avoid circular import
            from src.utils.logger import logger

            # Validate Twitter credentials if present
            if any([self.social_media.twitter_api_key, self.social_media.twitter_api_secret]):
                if not self.social_media.validate_twitter_credentials():
                    logger.warning("Twitter API credentials validation failed")

            # Validate Reddit credentials if present
            if any([self.social_media.reddit_client_id, self.social_media.reddit_client_secret]):
                if not self.social_media.validate_reddit_credentials():
                    logger.warning("Reddit API credentials validation failed")

        except Exception as e:
            # Fallback if logger import fails
            print(f"Warning: API key validation error: {e}")