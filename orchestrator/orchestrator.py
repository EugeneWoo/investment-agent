"""Orchestrator: runs 3 independent agents then a Judge for a decisive GO/NOGO verdict."""

from __future__ import annotations

import json
import logging

from agents.search_agent import SearchAgent
from agents.sentiment_agent import SentimentAgent
from agents.valuation_agent import ValuationAgent
from models import AgentMessage, DebateResult
from tools.anthropic import AnthropicClient
from tools.tavily import TavilyClient

logger = logging.getLogger(__name__)

ELIGIBILITY_SYSTEM_PROMPT = """
You are a pre-screening filter for an investment analysis system focused on Seed-to-Series B AI-native startups.

You will be given a company name and web search results from Yahoo Finance and MarketWatch.
Use the search results as ground truth. Score your confidence (0–100) on each criterion.

CRITERION 1 — PUBLIC LISTING:
Is the company publicly traded on any stock exchange?
- Look for ticker symbols, stock price data, or exchange names in the search results.
- A result like "WISE stock" or "NYSE: XYZ" is definitive evidence of listing.
- If search results show a stock page for this company, it is listed.

CRITERION 2 — AI-NATIVE:
Is AI core to the company's product? A bank, payments processor, pharma, retailer, or manufacturer that uses AI as a tool does NOT qualify. The product itself must be AI-driven.

Rules:
- Only block if confidence > 80 for that criterion.
- If search results are inconclusive, score confidence below 80 and allow through.

Respond with ONLY a valid JSON object — no markdown, no text outside the JSON:
{
  "listed_confidence": <0-100>,
  "not_ai_native_confidence": <0-100>,
  "eligible": <true|false>,
  "reason": "<one sentence if ineligible, empty string if eligible>"
}
"""

JUDGE_SYSTEM_PROMPT = """
You are an investment Judge for Seed-to-Series B AI startups.

Three independent analysts have each researched the same startup separately:
- Search Agent: evaluated founder quality and market gap
- Sentiment Agent: evaluated press coverage and community sentiment
- Valuation Agent: evaluated market size, comparables, and return potential

Your task: read all three reports and issue a single, decisive investment verdict.

Rules:
1. Start your response with exactly "GO" or "NOGO" — nothing else on the first line
2. On the second line, write 3-4 sentences citing specific evidence from the reports
3. Weigh all three dimensions: founder quality, sentiment, and valuation
4. Be decisive — no hedging, no "it depends"

Format:
GO|NOGO
[Your rationale citing specific evidence from the three reports]
"""


class Orchestrator:
    """Runs 3 independent agents then a Judge for a decisive GO/NOGO verdict."""

    def __init__(self, risk_tolerance: str = "risk_neutral") -> None:
        self.risk_tolerance = risk_tolerance
        self._search = SearchAgent(risk_tolerance)
        self._sentiment = SentimentAgent(risk_tolerance)
        self._valuation = ValuationAgent(risk_tolerance)
        self._llm = AnthropicClient()

    def eligibility_check(self, company: str) -> tuple[bool, str]:
        """Check eligibility using live search results from Yahoo Finance / MarketWatch.

        Fetches real listing data before asking the LLM, so it can't hallucinate.
        Only blocks if confidence > 80 on either criterion.

        Returns:
            Tuple of (is_eligible, reason). reason is empty string if eligible.
        """
        try:
            tavily = TavilyClient()
            results = tavily.search(
                f'"{company}" stock ticker site:finance.yahoo.com OR site:marketwatch.com',
                max_results=3,
            )
            snippets = "\n\n".join(
                f"[{r['title']}] ({r['url']})\n{r['content'][:300]}"
                for r in results
            ) or "No results found."

            user_message = f"""Company: {company}

Web search results from Yahoo Finance / MarketWatch:
{snippets}"""

            response = self._llm.messages_create(
                system_prompt=ELIGIBILITY_SYSTEM_PROMPT,
                user_message=user_message,
                max_tokens=256,
            )
            raw = response.strip()
            json_start = raw.rfind("{")
            json_end = raw.rfind("}") + 1
            data = json.loads(raw[json_start:json_end])

            listed_conf = int(data.get("listed_confidence", 0))
            not_ai_conf = int(data.get("not_ai_native_confidence", 0))
            logger.info(
                f"Eligibility check for '{company}': "
                f"listed_confidence={listed_conf}, not_ai_native_confidence={not_ai_conf}"
            )

            if listed_conf > 80 or not_ai_conf > 80:
                reason = data.get("reason", "Company does not meet eligibility criteria.")
                return False, reason
            return True, ""
        except Exception as e:
            logger.warning(f"Eligibility check failed, proceeding anyway: {e}")
            return True, ""

    def run(self, company: str, risk_tolerance: str | None = None) -> DebateResult:
        """Run independent agent analysis then Judge verdict.

        Each agent researches the company independently with no shared context.
        The Judge reads all three reports and issues a single GO/NOGO decision.

        Args:
            company: Company name or description to analyze.
            risk_tolerance: Optional override of instance default.

        Returns:
            DebateResult with final verdict and all messages.
        """
        rt = risk_tolerance or self.risk_tolerance
        all_messages: list[AgentMessage] = []

        # --- Independent agent analysis (no context sharing) ---
        logger.info(f"Analysis starting: {company}")

        search_msg = self._search.run(company, rt)
        all_messages.append(search_msg)
        logger.info("Search Agent complete")

        sentiment_msg = self._sentiment.run(company, rt)
        all_messages.append(sentiment_msg)
        logger.info("Sentiment Agent complete")

        valuation_msg = self._valuation.run(company, rt)
        all_messages.append(valuation_msg)
        logger.info("Valuation Agent complete")

        # --- Judge: single LLM call over all three reports ---
        full_analysis = self._format_phase1_summary(all_messages)
        judge_msg, verdict = self._judge_reports(company, full_analysis, rt)
        all_messages.append(judge_msg)
        logger.info(f"Judge verdict: {verdict}")

        recommendations = None
        if verdict == "GO":
            recommendations = self._recommend_companies(company, full_analysis)
            logger.info(f"Recommendations generated: {recommendations}")

        return DebateResult(
            verdict=verdict,
            rounds=0,
            messages=all_messages,
            consensus_reached=True,
            recommendations=recommendations,
        )

    def _judge_reports(
        self, company: str, analysis: str, risk_tolerance: str
    ) -> tuple[AgentMessage, str]:
        """Read all three independent agent reports and issue a GO/NOGO verdict.

        Args:
            company: Company being evaluated.
            analysis: Formatted summary of all three agent reports.
            risk_tolerance: Risk tolerance setting for context.

        Returns:
            Tuple of (AgentMessage with role='judge', verdict string).
        """
        user_message = f"""Company: {company}
Risk tolerance: {risk_tolerance}

Independent analyst reports:
{analysis}

Issue your GO or NOGO verdict with rationale."""

        try:
            response = self._llm.messages_create(
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_message=user_message,
                max_tokens=512,
            )
        except RuntimeError as e:
            logger.error(f"Judge LLM call failed: {e}")
            response = "NOGO\nUnable to complete analysis due to API error."

        first_line = response.strip().split("\n")[0].strip().upper()
        if "NOGO" in first_line or "NO GO" in first_line:
            verdict = "NOGO"
        else:
            verdict = "GO"

        return AgentMessage(agent_name="Judge", content=response, role="judge"), verdict

    def _extract_summary(self, msg: AgentMessage) -> str:
        """Extract the summary field from an agent's JSON content."""
        try:
            data = json.loads(msg.content)
            for key in ("search_agent_summary", "sentiment_agent_summary", "valuation_agent_summary"):
                if key in data:
                    return f"{msg.agent_name}: {data[key]}"
        except (json.JSONDecodeError, KeyError):
            pass
        return f"{msg.agent_name}: {msg.content[:200]}"

    def _format_phase1_summary(self, messages: list[AgentMessage]) -> str:
        """Format all agent outputs into a readable summary for the Judge."""
        parts = []
        for msg in messages:
            try:
                data = json.loads(msg.content)
                parts.append(f"### {msg.agent_name}\n{json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                parts.append(f"### {msg.agent_name}\n{msg.content[:500]}")
        return "\n\n".join(parts)

    def _recommend_companies(self, topic: str, analysis: str) -> list[str]:
        """Generate 3 specific company recommendations based on the GO verdict and analysis.

        Args:
            topic: The company name or topic the user entered.
            analysis: Phase 1 analysis summary used as context.

        Returns:
            List of 3 recommendation strings, each naming a company and a one-line rationale.
        """
        user_message = f"""The investment analysis for "{topic}" returned a GO verdict.

Based on this analysis:
{analysis[:2000]}

Name exactly 3 specific Seed-to-Series B AI startups operating in this space that an investor should look at next. For each, provide:
- Company name
- One sentence on why it's worth investigating

Return ONLY a JSON array of 3 strings, each formatted as "Company Name — rationale sentence."
Example: ["Acme AI — building proprietary data moats in the legal vertical.", ...]

No markdown, no preamble, just the JSON array."""

        try:
            response = self._llm.messages_create(
                system_prompt="You are an expert venture capital analyst. Return only valid JSON.",
                user_message=user_message,
                max_tokens=512,
            )
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0].strip()
            result = json.loads(cleaned)
            if isinstance(result, list) and len(result) >= 3:
                return [str(r) for r in result[:3]]
        except Exception as e:
            logger.warning(f"Failed to generate recommendations: {e}")
        return []
