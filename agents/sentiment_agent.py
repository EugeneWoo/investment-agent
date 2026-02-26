"""Sentiment Agent: analyzes social sentiment and news coverage for a startup."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import AgentMessage
from tools.anthropic import AnthropicClient
from tools.tavily import TavilyClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_RISK_NEUTRAL = """
You are the Sentiment Agent, a specialized investment analyst for Seed-to-Series B AI startups.
Your role is to assess public sentiment, press coverage, and community reaction to a startup.

RISK TOLERANCE: RISK_NEUTRAL — weigh positive and negative signals equally.

## WHAT TO ASSESS

1. **Press & media coverage**: Is coverage positive, neutral, or negative? Credible outlets?
2. **Community reaction**: Developer/customer excitement or skepticism? Reddit, HN, Twitter signals?
3. **Founder reputation**: Are founders respected in their field? Any public controversy?
4. **Momentum signals**: Recent launches, partnerships, hiring, awards?
5. **Red flags**: Negative press, controversy, pivot history, failed promises?

## SENTIMENT SCORES

- overall_sentiment_score (0-100): 70+ = positive momentum, 40-69 = mixed, 0-39 = negative/concerning
- press_score (0-100): Quality and volume of press coverage
- community_score (0-100): Developer/customer enthusiasm
- momentum_score (0-100): Recent velocity — launches, hires, partnerships

## OUTPUT FORMAT

Return ONLY valid JSON:

{
  "sentiment": {
    "overall_sentiment_score": 0-100,
    "press_score": 0-100,
    "community_score": 0-100,
    "momentum_score": 0-100,
    "verdict": "positive|mixed|negative",
    "key_signals": ["specific signals found — positive or negative"],
    "red_flags": ["any concerning signals"],
    "narrative": "3-4 sentence summary with specific evidence"
  },
  "sentiment_agent_summary": "2-3 sentence summary for GO/NOGO assessment"
}

Cite specific articles, posts, or quotes. Use null for scores if no data found.
"""

SYSTEM_PROMPT_RISK_AVERSE = """
You are the Sentiment Agent, a specialized investment analyst for Seed-to-Series B AI startups.
Your role is to assess public sentiment, press coverage, and community reaction to a startup.

RISK TOLERANCE: RISK_AVERSE — weight negative signals heavily; treat absence of coverage as a concern.

## WHAT TO ASSESS

1. **Press & media coverage**: Require credible outlet coverage. Absence of coverage is a yellow flag.
2. **Community reaction**: Look for genuine enthusiasm vs. manufactured buzz.
3. **Founder reputation**: Any past controversy, failed ventures, or credibility issues?
4. **Momentum signals**: Verify claims — real partnerships or just announcements?
5. **Red flags**: Negative press, pivot history, overpromising, silent communities.

## SENTIMENT SCORES

- overall_sentiment_score (0-100): Be conservative. Mixed signals = 40-55 max.
- press_score: No coverage from credible outlets = 0-30.
- community_score: Hype without substance = 0-40.
- momentum_score: Announcements without follow-through = 0-40.

## OUTPUT FORMAT

Return ONLY valid JSON:

{
  "sentiment": {
    "overall_sentiment_score": 0-100,
    "press_score": 0-100,
    "community_score": 0-100,
    "momentum_score": 0-100,
    "verdict": "positive|mixed|negative",
    "key_signals": ["specific signals found"],
    "red_flags": ["concerning signals — be explicit"],
    "narrative": "3-4 sentences — highlight risks clearly"
  },
  "sentiment_agent_summary": "2-3 sentence summary with clear risk assessment"
}

Flag every concern. No coverage = flag it. Hype without substance = flag it.
"""


class SentimentAgent:
    """Analyzes public sentiment, press coverage, and community reaction for a startup."""

    def __init__(self, risk_tolerance: str = "risk_neutral") -> None:
        self.risk_tolerance = risk_tolerance
        self.system_prompt = (
            SYSTEM_PROMPT_RISK_AVERSE
            if risk_tolerance == "risk_averse"
            else SYSTEM_PROMPT_RISK_NEUTRAL
        )
        self._tavily = TavilyClient()
        self._llm = AnthropicClient()

    def run(self, company: str, risk_tolerance: str | None = None) -> AgentMessage:
        """Analyze sentiment for a company using web search and LLM reasoning.

        Args:
            company: Company name to analyze.
            risk_tolerance: Optional override.

        Returns:
            AgentMessage with JSON-structured sentiment analysis.
        """
        rt = risk_tolerance or self.risk_tolerance
        system_prompt = (
            SYSTEM_PROMPT_RISK_AVERSE if rt == "risk_averse" else SYSTEM_PROMPT_RISK_NEUTRAL
        )

        logger.info(f"SentimentAgent starting: {company} ({rt})")

        research = self._gather_research(company)
        analysis = self._synthesize(company, research, system_prompt)

        logger.info(f"SentimentAgent complete: {company}")
        return AgentMessage(
            agent_name="Sentiment Agent",
            content=analysis,
            role="analyst",
        )

    def _gather_research(self, company: str) -> str:
        searches = [
            f"{company} TechCrunch Wired Forbes VentureBeat article",
            f"{company} site:reddit.com OR site:news.ycombinator.com discussion",
            f"{company} founder CEO controversy lawsuit negative press",
            f"{company} partnership award hiring milestone 2025 2026",
        ]

        query_results: dict[str, list] = {}
        with ThreadPoolExecutor(max_workers=len(searches)) as executor:
            future_to_query = {executor.submit(self._tavily.search, q, 5): q for q in searches}
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                query_results[query] = future.result()

        results: list[str] = []
        for query in searches:  # preserve original order
            hits = query_results.get(query, [])
            if hits:
                results.append(f"## Search: {query}")
                for h in hits:
                    results.append(f"- [{h['title']}]({h['url']})\n  {h['content'][:300]}")

        return "\n".join(results) if results else "No sentiment data found."

    def _synthesize(self, company: str, research: str, system_prompt: str) -> str:
        user_message = f"""Analyze public sentiment for this Seed-to-Series B AI startup.

Company: {company}

Sentiment research:
{research}

Produce the complete JSON sentiment analysis per your instructions."""

        try:
            response = self._llm.messages_create(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=2048,
            )
            # Strip markdown code fences if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0].strip()
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            logger.warning("SentimentAgent: LLM returned non-JSON response")
            return json.dumps({
                "sentiment": {
                    "overall_sentiment_score": None,
                    "press_score": None,
                    "community_score": None,
                    "momentum_score": None,
                    "verdict": "unknown",
                    "key_signals": [],
                    "red_flags": ["Analysis failed: parsing error"],
                    "narrative": "Sentiment analysis failed due to a parsing error.",
                },
                "sentiment_agent_summary": f"Sentiment analysis of {company} failed.",
            })
