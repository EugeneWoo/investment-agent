"""Sentiment Agent: analyzes social sentiment and news coverage for a startup."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import AgentMessage
from tools.anthropic import AnthropicClient
from tools.tavily import TavilyClient

logger = logging.getLogger(__name__)

TOPIC_SYSTEM_PROMPT_RISK_NEUTRAL = """
You are the Sentiment Agent, a specialized investment analyst for Seed-to-Series C AI startups.
You are analyzing an INVESTMENT SPACE OR THEME — not a single company.
Your role is to assess public sentiment, press coverage, and community reaction ACROSS this space.

RISK TOLERANCE: RISK_NEUTRAL — weigh positive and negative signals equally.

## WHAT TO ASSESS

1. **Press & media coverage of the space**: Is the space getting credible coverage? Positive, neutral, or overhyped?
2. **Community reaction**: Developer/investor/customer excitement or skepticism about this space on Reddit, HN, Twitter?
3. **Momentum signals**: Is the space heating up or cooling down? Recent funding announcements, new entrants, notable exits?
4. **Red flags**: Backlash, regulatory concerns, over-saturation, disappointment with existing players?
5. **Investor sentiment**: Are top VCs publicly backing this space or pulling back?

## SENTIMENT SCORES

- overall_sentiment_score (0-100): 70+ = strong interest, 40-69 = mixed/cautious, 0-39 = skeptical/declining
- press_score (0-100): Quality and volume of press coverage for the space
- community_score (0-100): Developer/customer/investor community enthusiasm
- momentum_score (0-100): Recent velocity — new startups, funding activity, notable hires in the space

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
    "red_flags": ["any concerning signals about the space"],
    "narrative": "3-4 sentence summary of overall sentiment toward this investment space"
  },
  "sentiment_agent_summary": "2-3 sentence summary of space sentiment for GO/NOGO assessment"
}

Cite specific articles, posts, or data points. Use null for scores if no data found.
"""

TOPIC_SYSTEM_PROMPT_RISK_AVERSE = """
You are the Sentiment Agent, a specialized investment analyst for Seed-to-Series C AI startups.
You are analyzing an INVESTMENT SPACE OR THEME — not a single company.
Your role is to assess public sentiment, press coverage, and community reaction ACROSS this space.

RISK TOLERANCE: RISK_AVERSE — weight negative signals heavily; treat hype without substance as a red flag.

## WHAT TO ASSESS

1. **Press & media coverage of the space**: Require credible, substantive coverage — not just hype cycles.
2. **Community reaction**: Look for genuine enthusiasm vs. manufactured buzz. Skepticism is informative.
3. **Momentum signals**: Verify — are funding announcements real or just pre-announcements?
4. **Red flags**: Over-saturation, regulatory risk, community backlash, pivot fatigue from prior wave.
5. **Investor sentiment**: VCs pulling back or being silent is a yellow flag.

## SENTIMENT SCORES

- overall_sentiment_score: Be conservative. Hype cycle without substance = 40-55 max.
- press_score: Sensational coverage without depth = 0-30.
- community_score: "This is the future" posts without real usage = 0-40.
- momentum_score: New entrants flooding a space can signal commoditization risk.

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
    "red_flags": ["concerning signals about the space — be explicit"],
    "narrative": "3-4 sentences — highlight risks and hype clearly"
  },
  "sentiment_agent_summary": "2-3 sentence summary with clear risk assessment for this space"
}

Flag every concern. Hype without substance = flag it. Over-saturation = flag it.
"""

SYSTEM_PROMPT_RISK_NEUTRAL = """
You are the Sentiment Agent, a specialized investment analyst for Seed-to-Series C AI startups.
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
You are the Sentiment Agent, a specialized investment analyst for Seed-to-Series C AI startups.
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

    def run(self, company: str, risk_tolerance: str | None = None, is_topic: bool = False) -> AgentMessage:
        """Analyze sentiment for a company or investment space using web search and LLM reasoning.

        Args:
            company: Company name or topic/space to analyze.
            risk_tolerance: Optional override.
            is_topic: If True, analyze sentiment across the space rather than a single company.

        Returns:
            AgentMessage with JSON-structured sentiment analysis.
        """
        rt = risk_tolerance or self.risk_tolerance
        if is_topic:
            system_prompt = (
                TOPIC_SYSTEM_PROMPT_RISK_AVERSE if rt == "risk_averse" else TOPIC_SYSTEM_PROMPT_RISK_NEUTRAL
            )
        else:
            system_prompt = (
                SYSTEM_PROMPT_RISK_AVERSE if rt == "risk_averse" else SYSTEM_PROMPT_RISK_NEUTRAL
            )

        logger.info(f"SentimentAgent starting: {company} ({rt}, is_topic={is_topic})")

        research = self._gather_research(company, is_topic)
        analysis = self._synthesize(company, research, system_prompt, is_topic)

        logger.info(f"SentimentAgent complete: {company}")
        return AgentMessage(
            agent_name="Sentiment Agent",
            content=analysis,
            role="analyst",
        )

    def _gather_research(self, company: str, is_topic: bool = False) -> str:
        if is_topic:
            searches = [
                f"{company} AI startups investor sentiment venture capital 2025 2026",
                f"{company} site:reddit.com OR site:news.ycombinator.com discussion hype backlash",
            ]
        else:
            searches = [
                f"{company} press coverage news review partnership milestone 2025 2026",
                f"{company} site:reddit.com OR site:news.ycombinator.com discussion",
            ]

        query_results: dict[str, list] = {}
        with ThreadPoolExecutor(max_workers=len(searches)) as executor:
            future_to_query = {executor.submit(self._tavily.search, q, 3): q for q in searches}
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

    def _synthesize(self, company: str, research: str, system_prompt: str, is_topic: bool = False) -> str:
        if is_topic:
            user_message = f"""Analyze public sentiment for this investment space.

Space/Topic: {company}

Sentiment research:
{research}

Produce the complete JSON sentiment analysis per your instructions."""
        else:
            user_message = f"""Analyze public sentiment for this Seed-to-Series C AI startup.

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
