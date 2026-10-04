"""
JSON output generator
"""
import json
from pathlib import Path
from typing import List

from src.generators.digest import build_digest
from src.utils.models import SummarizedArticle, NewsDigest
from src.utils.logger import logger


class JSONGenerator:
    """Generates JSON output for news summaries"""

    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.output.directory)

    def generate(self, articles: List[SummarizedArticle]) -> None:
        """Generate JSON output"""
        if not articles:
            logger.warning("No articles to generate JSON for")
            return

        digest = build_digest(articles, self.config)

        # Generate JSON file
        self._generate_json_file(digest)

        logger.info(f"Generated JSON with {len(articles)} articles")

    def _generate_json_file(self, digest: NewsDigest) -> None:
        """Generate the JSON output file"""
        # Convert digest to dict using Pydantic's model_dump
        digest_dict = digest.model_dump(mode='json')

        # Write to file with pretty formatting
        output_file = self.output_dir / f"news-{digest.date.strftime('%Y-%m-%d')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(digest_dict, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"JSON generated: {output_file}")
