"""
HTML output generator
"""
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from jinja2 import Template, Environment, FileSystemLoader

from src.utils.models import SummarizedArticle, NewsDigest
from src.utils.logger import logger


class HTMLGenerator:
    """Generates HTML output for news summaries"""
    
    def __init__(self, config):
        self.config = config
        self.template_dir = Path(config.output.template_dir)
        self.output_dir = Path(config.output.directory)
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )
    
    def generate(self, articles: List[SummarizedArticle]) -> None:
        """Generate HTML output"""
        if not articles:
            logger.warning("No articles to generate HTML for")
            return
        
        # Group articles by category
        articles_by_category = self._group_by_category(articles)
        
        # Sort articles within each category by importance
        for category in articles_by_category:
            articles_by_category[category].sort(
                key=lambda x: x.importance_score,
                reverse=True
            )
            # Note: No limit here - pre-filtering happens before summarization in main.py
        
        # Create news digest
        digest = NewsDigest(
            date=datetime.now(),
            articles_by_category=articles_by_category,
            total_articles=len(articles),
            processing_time_seconds=0.0,  # TODO: Add timing
            sources_used=list(set(article.source for article in articles)),
            discovered_sources_count=len(getattr(self.config, 'discovered_sources', [])),
            user_interests=getattr(self.config, 'user_interests', [])
        )
        
        # Generate HTML file
        self._generate_html_page(digest)
        
        total_categories = len(articles_by_category)
        total_articles = sum(len(articles) for articles in articles_by_category.values())
        logger.info(f"Generated HTML with {total_categories} categories and {total_articles} articles")
    
    def _group_by_category(self, articles: List[SummarizedArticle]) -> Dict[str, List[SummarizedArticle]]:
        """Group articles by category"""
        grouped = {}
        for article in articles:
            category = article.category
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(article)
        return grouped
    
    def _generate_html_page(self, digest: NewsDigest) -> None:
        """Generate the main HTML page"""
        # Create default template if it doesn't exist
        self._ensure_template_exists()

        # Copy logo to output directory if it exists
        logo_src = Path(__file__).parent.parent.parent / 'assets' / 'logo.png'
        logo_dest = self.output_dir / 'logo.png'
        has_logo = False
        if logo_src.exists():
            import shutil
            shutil.copy2(logo_src, logo_dest)
            has_logo = True
            logger.info(f"Logo copied to: {logo_dest}")

        # Load template
        template = self.env.get_template('news.html')

        # Render HTML
        html_content = template.render(
            digest=digest,
            config=self.config,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            has_logo=has_logo
        )

        # Write to file
        output_file = self.output_dir / f"news-{digest.date.strftime('%Y-%m-%d')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"HTML generated: {output_file}")
    
    def _ensure_template_exists(self) -> None:
        """Create default HTML template if it doesn't exist"""
        template_path = self.template_dir / 'news.html'
        
        if not template_path.exists():
            default_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily News Digest - {{ digest.date.strftime('%B %d, %Y') }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'JetBrains Mono', monospace;
            background: #F5F1EA;
        }
        .article-card {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-radius: 12px;
        }
        .article-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.08), 0 8px 10px -6px rgb(0 0 0 / 0.08);
        }
        .coral-accent {
            color: #E85D4A;
        }
        .coral-bg {
            background-color: #E85D4A;
        }
        .coral-bg-light {
            background-color: #FEE9E7;
        }
    </style>
</head>
<body class="min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">

        <!-- Header -->
        <header class="bg-white rounded-lg shadow-lg p-8 mb-8">
            <!-- Logo and Title -->
            <div class="text-center mb-6">
                {% if has_logo %}
                <div class="flex justify-center mb-6">
                    <img src="/static/logo.png" alt="" class="h-64 w-auto">
                </div>
                {% endif %}
                <h1 class="text-5xl font-bold text-gray-900 mb-3">Daily News Digest</h1>
                <p class="text-base text-gray-500 uppercase tracking-wide mb-3">AI-Powered Curation</p>
                <div class="text-sm text-gray-400">
                    Generated <span class="coral-accent font-semibold">{{ digest.date.strftime('%H:%M:%S') }}</span> on {{ digest.date.strftime('%Y-%m-%d') }}
                </div>
            </div>

            <!-- Stats Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="text-2xl font-bold text-gray-900">{{ digest.total_articles }}</div>
                    <div class="text-xs text-gray-500 uppercase tracking-wide">Articles</div>
                </div>
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="text-2xl font-bold text-gray-900">{{ digest.sources_used|length }}</div>
                    <div class="text-xs text-gray-500 uppercase tracking-wide">Sources</div>
                </div>
                {% if digest.discovered_sources_count > 0 %}
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="text-2xl font-bold coral-accent">{{ digest.discovered_sources_count }}</div>
                    <div class="text-xs text-gray-500 uppercase tracking-wide">Discovered</div>
                </div>
                {% endif %}
                <div class="bg-gray-50 rounded-lg p-4">
                    <div class="text-2xl font-bold text-gray-900">{{ digest.articles_by_category|length }}</div>
                    <div class="text-xs text-gray-500 uppercase tracking-wide">Categories</div>
                </div>
            </div>

            <!-- Interests Tags -->
            {% if digest.user_interests %}
            <div class="coral-bg-light rounded-lg p-4">
                <div class="text-xs text-gray-600 uppercase tracking-wide font-semibold mb-2 text-center">Your Interests</div>
                <div class="flex flex-wrap gap-2 justify-center">
                    {% for interest in digest.user_interests %}
                    <span class="inline-block coral-bg text-white px-3 py-1 rounded-md text-xs font-medium">{{ interest }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </header>

        <!-- Articles by Category -->
        {% for category, articles in digest.articles_by_category.items() %}
        <div class="mb-8">
            <h2 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 text-center">{{ category.upper() }}</h2>

            {% for article in articles %}
            <div class="article-card bg-white shadow-lg mb-4">
                <a href="{{ article.url }}" target="_blank" class="block p-6">
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex-1">
                            <h3 class="text-lg font-semibold text-gray-900 mb-1">{{ article.title }}</h3>
                            <div class="flex items-center gap-3 text-xs text-gray-500 mb-3">
                                <span class="font-medium text-gray-700">{{ article.source }}</span>
                                <span>{{ article.published_at.strftime('%H:%M') }}</span>
                                <span>{{ article.reading_time_minutes }} min read</span>
                                {% if 'discovery_reason' in article.metadata %}
                                <span class="coral-bg-light coral-accent px-2 py-0.5 rounded font-medium">AI Discovered</span>
                                {% endif %}
                            </div>
                        </div>
                        <div class="ml-4">
                            {% if article.importance_score > 0.7 %}
                            <span class="inline-block coral-bg text-white px-2 py-1 rounded text-xs font-bold uppercase">High</span>
                            {% elif article.importance_score > 0.4 %}
                            <span class="inline-block bg-orange-500 text-white px-2 py-1 rounded text-xs font-bold uppercase">Medium</span>
                            {% else %}
                            <span class="inline-block bg-gray-400 text-white px-2 py-1 rounded text-xs font-bold uppercase">Low</span>
                            {% endif %}
                        </div>
                    </div>

                    <div class="text-sm text-gray-700 leading-relaxed mb-4">
                        {{ article.ai_summary }}
                    </div>

                    {% if article.key_points %}
                    <div class="bg-gray-50 rounded-lg p-4 mb-3">
                        <div class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Key Points</div>
                        <ul class="space-y-1 text-xs text-gray-700">
                            {% for point in article.key_points %}
                            <li class="flex items-start">
                                <span class="coral-accent mr-2">•</span>
                                <span>{{ point }}</span>
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}

                    <div class="flex items-center gap-2 text-xs flex-wrap">
                        {% if article.sentiment_score %}
                        <span class="bg-gray-100 text-gray-600 px-2 py-1 rounded">Sentiment: {{ "%.1f"|format(article.sentiment_score * 100) }}%</span>
                        {% endif %}
                        {% if 'discovery_reason' in article.metadata and 'confidence_score' in article.metadata %}
                        <span class="bg-purple-50 text-purple-700 px-2 py-1 rounded font-medium">Confidence: {{ "%.0f"|format(article.metadata.confidence_score * 100) }}%</span>
                        {% endif %}
                    </div>
                </a>
            </div>
            {% endfor %}
        </div>
        {% endfor %}

        <!-- Footer -->
        <footer class="bg-white rounded-lg shadow-lg p-6 text-center">
            <div class="text-xs text-gray-500 uppercase tracking-wide mb-2">Generated by News Llama</div>
            <div class="text-xs text-gray-400">AI-Powered News Curation Engine</div>
            <div class="text-xs text-gray-400 mt-3">
                Sources: {{ digest.sources_used|join(' • ') }}
                {% if digest.discovered_sources_count > 0 %}
                • Plus {{ digest.discovered_sources_count }} AI-discovered sources
                {% endif %}
            </div>
        </footer>

    </div>
</body>
</html>'''
            
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(default_template)
            
            logger.info(f"Created default HTML template: {template_path}")