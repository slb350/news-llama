"""
Base aggregator interface
"""
from abc import ABC, abstractmethod
from typing import List
from src.utils.models import Article


class BaseAggregator(ABC):
    """Base class for content aggregators"""
    
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    async def collect(self) -> List[Article]:
        """Collect articles from the source"""
        pass
    
    @abstractmethod
    def _is_valid_article(self, article: Article) -> bool:
        """Validate if article meets quality criteria"""
        pass