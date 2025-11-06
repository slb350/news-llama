"""
LLM-powered source discovery system with cache-optimized prompts
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from open_agent import TextBlock, ToolUseBlock, ToolUseError, Client  # type: ignore
from open_agent.types import AgentOptions  # type: ignore
from open_agent.tools import Tool  # type: ignore

from src.utils.config import Config, DiscoveredSource
from src.utils.logger import logger


class SourceDiscoveryEngine:
    """Discovers relevant news sources using LLM reasoning"""

    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.llm

        # Predefined source patterns for different topics
        self.source_patterns = {
            "technology": {
                "reddit_subreddits": [
                    "technology",
                    "programming",
                    "MachineLearning",
                    "LocalLLaMA",
                    "LocalLLM",
                    "OpenAI",
                    "singularity",
                    "artificial",
                    "futurology",
                ],
                "twitter_accounts": [
                    "elonmusk",
                    "sama",
                    "ylecun",
                    "karpathy",
                    "fchollet",
                    "verge",
                    "techcrunch",
                    "wired",
                    "arstechnica",
                    "slashdot",
                ],
                "rss_feeds": [
                    "arstechnica.com",
                    "theverge.com",
                    "techcrunch.com",
                    "wired.com",
                ],
            },
            "ai": {
                "reddit_subreddits": [
                    "MachineLearning",
                    "LocalLLaMA",
                    "OpenAI",
                    "ClaudeAI",
                    "singularity",
                    "artificial",
                    "deeplearning",
                    "computervision",
                    "nlp",
                    "Robotics",
                ],
                "twitter_accounts": [
                    "sama",
                    "ylecun",
                    "karpathy",
                    "fchollet",
                    " AndrewYNg",
                    "hardmaru",
                    "openai",
                    "anthropicai",
                    "googleai",
                    "deepmind",
                ],
                "rss_feeds": [
                    "openai.com/blog",
                    "anthropic.com/news",
                    "deepmind.google/blog",
                ],
            },
            "programming": {
                "reddit_subreddits": [
                    "programming",
                    "learnprogramming",
                    "python",
                    "javascript",
                    "golang",
                    "rust",
                    "cpp",
                    "webdev",
                    "devops",
                ],
                "twitter_accounts": [
                    "github",
                    "gitlab",
                    "thepracticaldev",
                    "code",
                    "hackernewsbot",
                ],
                "rss_feeds": [
                    "github.blog",
                    "stackoverflow.blog",
                    "dev.to",
                    "medium.com/tag/programming",
                ],
            },
            "localllm": {
                "reddit_subreddits": [
                    "LocalLLaMA",
                    "LocalLLM",
                    "ollama",
                    "MachineLearning",
                    "selfhosted",
                ],
                "rss_feeds": ["ollama.com/blog"],
            },
            "localllama": {
                "reddit_subreddits": [
                    "LocalLLaMA",
                    "LocalLLM",
                    "ollama",
                    "MachineLearning",
                ]
            },
            "rust": {
                "reddit_subreddits": [
                    "rust",
                    "learnrust",
                    "rust_gamedev",
                    "programming",
                ],
                "rss_feeds": ["this-week-in-rust.org/rss.xml"],
            },
        }

    async def discover_sources(
        self, user_interests: List[str]
    ) -> List[DiscoveredSource]:
        """Discover relevant sources based on user interests"""
        if not self.config.source_discovery.enabled:
            logger.info("Source discovery is disabled")
            return []

        logger.info(f"Discovering sources for interests: {user_interests}")

        discovered = []

        for interest in user_interests:
            interest_sources = await self._discover_sources_for_interest(interest)
            discovered.extend(interest_sources)

        # Remove duplicates and sort by confidence
        unique_sources = self._deduplicate_sources(discovered)
        unique_sources.sort(key=lambda x: x.confidence_score, reverse=True)

        # Limit to max sources per category
        max_sources = self.config.source_discovery.max_sources_per_category
        limited_sources = unique_sources[:max_sources]

        logger.info(f"Discovered {len(limited_sources)} unique sources")
        return limited_sources

    async def _discover_sources_for_interest(
        self, interest: str
    ) -> List[DiscoveredSource]:
        """Discover sources for a specific interest using multi-tier strategy"""
        # Tier 1: Check predefined patterns first (curated, high quality)
        pattern_sources = self._check_predefined_patterns(interest)
        logger.info(f"Found {len(pattern_sources)} predefined sources for '{interest}'")

        # Tier 2: LLM-powered subreddit name matching (fast, focused)
        subreddit_sources = await self._llm_discover_subreddits(interest)
        logger.info(
            f"LLM discovered {len(subreddit_sources)} subreddit matches for '{interest}'"
        )

        # Tier 3: Broad LLM discovery (multi-source: Twitter, RSS, etc.)
        llm_sources = await self._llm_discovery(interest)
        logger.info(
            f"LLM discovered {len(llm_sources)} multi-source matches for '{interest}'"
        )

        # Combine all discovered sources
        all_sources = pattern_sources + subreddit_sources + llm_sources

        # Tier 4: Try exact subreddit name match if still no sources
        if not all_sources:
            logger.info(
                f"No sources found yet for '{interest}', trying exact subreddit name match"
            )
            exact_match = self._try_exact_subreddit_match(interest)
            if exact_match:
                all_sources.append(exact_match)

        # Tier 5: Final fallback - Reddit search across all subreddits
        if not all_sources:
            logger.info(
                f"No sources found for '{interest}', adding Reddit search fallback"
            )
            search_source = DiscoveredSource(
                name=f"Reddit search: {interest}",
                url=None,
                username=None,
                subreddit=None,
                source_type="reddit_search",
                category=interest,
                confidence_score=0.95,  # High confidence so it doesn't get filtered out
                reason=f"Search Reddit for posts about {interest}",
            )
            all_sources.append(search_source)

        # Log details of discovered sources
        if all_sources:
            source_summary = ", ".join(
                [f"{s.name} ({s.source_type})" for s in all_sources[:5]]
            )
            logger.info(
                f"Sources for '{interest}': {source_summary}{'...' if len(all_sources) > 5 else ''}"
            )
        else:
            logger.warning(f"No sources found for '{interest}'")

        return all_sources

    def _check_predefined_patterns(self, interest: str) -> List[DiscoveredSource]:
        """Check predefined patterns for known interests"""
        interest_lower = interest.lower()
        sources = []

        # Direct match
        if interest_lower in self.source_patterns:
            patterns = self.source_patterns[interest_lower]
            sources.extend(self._create_sources_from_patterns(patterns, interest, 0.9))

        # Partial matches
        for key, patterns in self.source_patterns.items():
            if interest_lower in key or key in interest_lower:
                confidence = 0.7 if interest_lower != key else 0.8
                sources.extend(
                    self._create_sources_from_patterns(patterns, interest, confidence)
                )

        return sources

    def _create_sources_from_patterns(
        self, patterns: Dict[str, List[str]], interest: str, base_confidence: float
    ) -> List[DiscoveredSource]:
        """Create DiscoveredSource objects from patterns"""
        sources = []

        # Reddit subreddits
        if "reddit_subreddits" in patterns:
            for subreddit in patterns["reddit_subreddits"]:
                sources.append(
                    DiscoveredSource(
                        name=f"r/{subreddit}",
                        subreddit=subreddit,
                        source_type="reddit",
                        category=interest,
                        confidence_score=base_confidence,
                        reason=f"Known {interest} subreddit",
                    )
                )

        # Twitter accounts
        if "twitter_accounts" in patterns:
            for account in patterns["twitter_accounts"]:
                sources.append(
                    DiscoveredSource(
                        name=f"@{account}",
                        username=account,
                        source_type="twitter",
                        category=interest,
                        confidence_score=base_confidence,
                        reason=f"Known {interest} Twitter account",
                    )
                )

        # RSS feeds
        if "rss_feeds" in patterns:
            for feed_domain in patterns["rss_feeds"]:
                sources.append(
                    DiscoveredSource(
                        name=feed_domain,
                        url=f"https://{feed_domain}/feed/",
                        source_type="rss",
                        category=interest,
                        confidence_score=base_confidence,
                        reason=f"Known {interest} RSS feed",
                    )
                )

        return sources

    async def _llm_discover_subreddits(self, interest: str) -> List[DiscoveredSource]:
        """
        Use LLM to discover relevant subreddit names with short system prompt.

        NOTE: Reverted from cache-optimized prompts due to ROCm/AMD GPU memory issues.
        Long system prompts trigger prompt caching which causes memory allocation errors.
        """
        try:
            # Short system prompt to avoid triggering prompt caching issues
            system_prompt = (
                "You are an expert Reddit source discovery assistant. "
                "You MUST respond ONLY with valid JSON. No other text, no explanations."
            )

            # User prompt with all instructions embedded
            user_prompt = f"""For the interest "{interest}", suggest 3-7 highly relevant Reddit subreddit names. Consider:

1. **Exact name match**: e.g., "rust" → r/rust
2. **Capitalization variants**: e.g., "ai" → r/MachineLearning, r/ArtificialIntelligence
3. **Learning-focused variants**: e.g., "python" → r/learnpython
4. **Specialized communities**: e.g., "rust" → r/rust_gamedev, r/learnrust
5. **News/discussion subs**: e.g., "technology" → r/technews, r/tech

IMPORTANT GUIDELINES:
- AVOID unrelated subs with similar names (e.g., "rust" should NOT suggest r/RustBelt or r/rust_irl)
- Focus on active, content-rich communities
- Include both general and specialized subreddits
- Prioritize quality over quantity
- Consider niche communities for specific interests

Return ONLY valid JSON. No markdown code blocks, no explanations.

Required JSON format:
{{
    "subreddits": [
        {{
            "name": "r/rust",
            "subreddit": "rust",
            "reason": "Main Rust programming community with active discussions",
            "confidence_score": 0.95
        }},
        {{
            "name": "r/learnrust",
            "subreddit": "learnrust",
            "reason": "Learning-focused Rust community for beginners and intermediate users",
            "confidence_score": 0.85
        }}
    ]
}}

CRITICAL REQUIREMENTS:
- Return ONLY the JSON object
- No text before or after the JSON
- No markdown (no ```json```)
- Each subreddit must have: name, subreddit (without r/), reason, confidence_score
- confidence_score must be a number between 0.0 and 1.0
- Suggest 3-7 subreddits (quality over quantity)"""

            options = AgentOptions(
                system_prompt=system_prompt,
                model=self.llm_config.model,
                base_url=self.llm_config.api_url,
                temperature=0.3,  # Lower temperature for more focused results
                max_tokens=2000,
                api_key="not-needed",
                tools=[],
                auto_execute_tools=False,
                timeout=self.llm_config.timeout,
                max_turns=1,
            )

            parts: List[str] = []

            try:
                async with asyncio.timeout(self.llm_config.timeout):
                    client = Client(options)
                    await client.query(user_prompt)

                    async for block in client.receive_messages():
                        if isinstance(block, TextBlock):
                            parts.append(block.text)

                    await client.close()
            except asyncio.TimeoutError:
                logger.warning(
                    f"Subreddit discovery timed out for interest: {interest}"
                )
                return []

            llm_response = "".join(parts).strip()

            if not llm_response:
                logger.warning(
                    f"Empty LLM response for subreddit discovery: {interest}"
                )
                return []

            logger.debug(
                f"LLM subreddit response for '{interest}': {llm_response[:200]}..."
            )

            return self._parse_subreddit_response(llm_response, interest)

        except Exception as e:
            logger.error(f"Error in LLM subreddit discovery for '{interest}': {e}")
            return []

    def _parse_subreddit_response(
        self, response: str, interest: str
    ) -> List[DiscoveredSource]:
        """Parse LLM subreddit response into DiscoveredSource objects"""
        try:
            # Strip markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response = "\n".join(lines).strip()

            # Try to find JSON if LLM added text before/after
            if not response.startswith("{"):
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end > start:
                    response = response[start:end]

            data = json.loads(response)
            sources = []

            for sub_data in data.get("subreddits", []):
                subreddit_name = sub_data.get("subreddit", "")
                if subreddit_name:
                    source = DiscoveredSource(
                        name=f"r/{subreddit_name}",
                        subreddit=subreddit_name,
                        source_type="reddit",
                        category=interest,
                        confidence_score=sub_data.get("confidence_score", 0.7),
                        reason=sub_data.get("reason", "LLM-discovered subreddit"),
                    )
                    sources.append(source)

            return sources

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse LLM subreddit response for '{interest}': {e}"
            )
            logger.error(f"Response was: {response[:500]}")
            return []

    def _try_exact_subreddit_match(self, interest: str) -> Optional[DiscoveredSource]:
        """Try creating a subreddit source with exact name match as fallback"""
        # Clean the interest string (remove spaces, special chars for subreddit name)
        subreddit_name = interest.strip().replace(" ", "").replace("-", "")

        # Skip if too short or obviously not a subreddit name
        if len(subreddit_name) < 3 or any(char.isspace() for char in subreddit_name):
            return None

        logger.info(f"Trying exact subreddit match: r/{subreddit_name}")

        return DiscoveredSource(
            name=f"r/{subreddit_name}",
            subreddit=subreddit_name,
            source_type="reddit",
            category=interest,
            confidence_score=0.8,  # Moderate confidence for exact match
            reason=f"Exact name match for '{interest}'",
        )

    async def _llm_discovery(self, interest: str) -> List[DiscoveredSource]:
        """
        Use LLM to discover sources with short system prompt.

        NOTE: Reverted from cache-optimized prompts due to ROCm/AMD GPU memory issues.
        Long system prompts trigger prompt caching which causes memory allocation errors.
        """
        try:
            # Short system prompt to avoid triggering prompt caching issues
            system_prompt = (
                "You are an expert source discovery assistant. "
                "You MUST respond ONLY with valid JSON. No other text, no explanations."
            )

            # User prompt with all instructions embedded
            user_prompt = f"""For the interest "{interest}", find 5-8 popular sources across multiple platforms:
- **Reddit communities** (subreddits)
- **RSS feeds** from authoritative sites
- **Twitter accounts** (if applicable)

Return a JSON object with a "sources" array containing:

**Required fields for ALL sources:**
- type: Must be "reddit", "rss", or "twitter"
- name: Human-readable name
- confidence: Number between 0.0-1.0 (how confident you are this source is relevant)
- reasoning: Brief explanation of why this source is relevant

**Type-specific fields:**
- For reddit: include "subreddit" field (just name, no r/ prefix)
- For rss: include "url" field with full RSS feed URL
- For twitter: include "username" field (no @ symbol)

CRITICAL REQUIREMENTS:
- Return ONLY valid JSON, no other text
- No markdown code blocks (no ```json```)
- Only include high-quality, active sources
- Prioritize authoritative and well-known sources
- Aim for 5-8 sources total (balanced across types)
- After any tool use, return ONLY the JSON (no explanations about what you found)

Required JSON format:
{{
    "sources": [
        {{
            "type": "reddit",
            "name": "r/example",
            "subreddit": "example",
            "confidence": 0.9,
            "reasoning": "Primary community for this topic with 500K+ subscribers"
        }},
        {{
            "type": "rss",
            "name": "Example News Feed",
            "url": "https://example.com/feed.xml",
            "confidence": 0.8,
            "reasoning": "Official news feed from authoritative source"
        }},
        {{
            "type": "twitter",
            "name": "Example Expert",
            "username": "example_expert",
            "confidence": 0.7,
            "reasoning": "Leading voice in the field with regular updates"
        }}
    ]
}}

IMPORTANT: Even if you use web search or other tools, return ONLY the final JSON object with no additional commentary."""

            # Define a simple web_search tool to showcase tool-use
            async def web_search_handler(params: Dict[str, Any]) -> Any:
                query = params.get("query") or interest
                max_results = int(params.get("max_results", 5))
                try:
                    from ddgs import DDGS  # type: ignore

                    results = []
                    with DDGS() as ddgs:
                        for r in ddgs.text(query, max_results=max_results):
                            results.append(
                                {"title": r.get("title"), "url": r.get("href")}
                            )
                    return {"results": results}
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")
                    return {"results": []}

            web_search_tool = Tool(
                name="web_search",
                description="Search the web for recent sources related to a topic",
                input_schema={"query": str, "max_results": int},
                handler=web_search_handler,
            )

            options = AgentOptions(
                system_prompt=system_prompt,
                model=self.llm_config.model,
                base_url=self.llm_config.api_url,
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens,
                api_key="not-needed",
                tools=[],  # Disable web search - LLM gets confused after tool use
                auto_execute_tools=False,
                timeout=self.llm_config.timeout,
                max_turns=1,  # Single turn for direct JSON response
            )

            parts: List[str] = []

            # Wrap with asyncio timeout for additional safety
            try:
                async with asyncio.timeout(self.llm_config.timeout):
                    client = Client(options)
                    await client.query(user_prompt)

                    async for block in client.receive_messages():
                        if isinstance(block, TextBlock):
                            parts.append(block.text)
                        elif isinstance(block, ToolUseBlock):
                            # Execute tool and send result back
                            try:
                                result = await web_search_handler(block.input)
                                await client.add_tool_result(
                                    block.id, result, name=block.name
                                )
                            except Exception as e:
                                await client.add_tool_result(
                                    block.id, {"error": str(e)}, name=block.name
                                )
                        elif isinstance(block, ToolUseError):
                            logger.warning(f"Tool error: {block.error}")

                    await client.close()
            except asyncio.TimeoutError:
                logger.warning(
                    f"Source discovery timed out after {self.llm_config.timeout}s for interest: {interest}"
                )
                return []

            llm_response = "".join(parts).strip()

            # Log the response for debugging
            if not llm_response:
                logger.warning(f"Empty LLM response for interest: {interest}")
                return []

            logger.debug(f"LLM response for '{interest}': {llm_response[:200]}...")

            return self._parse_llm_response(llm_response, interest)

        except Exception as e:
            logger.error(f"Error in LLM discovery for '{interest}': {e}")
            return []

    async def _placeholder_llm_call(self, prompt: str) -> str:
        """Deprecated placeholder, retained for tests if needed."""
        await asyncio.sleep(0.01)
        return json.dumps({"sources": []})

    def _parse_llm_response(
        self, response: str, interest: str
    ) -> List[DiscoveredSource]:
        """Parse LLM response into DiscoveredSource objects"""
        try:
            # Strip markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                # Remove code block markers
                lines = response.split("\n")
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response = "\n".join(lines).strip()

            # Try to find JSON if LLM added text before/after
            if not response.startswith("{"):
                # Try to extract JSON from the response
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end > start:
                    response = response[start:end]

            data = json.loads(response)
            sources = []

            for source_data in data.get("sources", []):
                source = DiscoveredSource(
                    name=source_data.get("name", ""),
                    url=source_data.get("url"),
                    username=source_data.get("username"),
                    subreddit=source_data.get("subreddit"),
                    source_type=source_data.get("source_type", "web_search"),
                    category=interest,
                    confidence_score=source_data.get("confidence_score", 0.5),
                    reason=source_data.get("reason", "LLM discovered"),
                )
                sources.append(source)

            return sources

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response for '{interest}': {e}")
            logger.error(f"Response was: {response[:500]}")
            return []

    def _deduplicate_sources(
        self, sources: List[DiscoveredSource]
    ) -> List[DiscoveredSource]:
        """Remove duplicate sources, keeping highest confidence"""
        seen = set()
        unique = []

        for source in sources:
            # Create a unique key based on name and type
            key = (source.name.lower(), source.source_type)

            if key not in seen:
                seen.add(key)
                unique.append(source)
            else:
                # Update existing source if this has higher confidence
                for i, existing in enumerate(unique):
                    if (existing.name.lower(), existing.source_type) == key:
                        if source.confidence_score > existing.confidence_score:
                            unique[i] = source
                        break

        return unique
