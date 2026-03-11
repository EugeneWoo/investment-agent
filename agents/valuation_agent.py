"""Valuation Agent: estimates relative value and return potential via comparables."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import AgentMessage
from tools.anthropic import AnthropicClient
from tools.tavily import TavilyClient

logger = logging.getLogger(__name__)

TOPIC_SYSTEM_PROMPT_RISK_NEUTRAL = """
You are the Valuation Agent, a specialized investment analyst for Seed-to-Series B AI startups.
You are analyzing an INVESTMENT SPACE OR THEME — not a single company.
Your role is to assess the venture attractiveness of this space via market sizing and comparable outcomes.

RISK TOLERANCE: RISK_NEUTRAL — balanced view on upside vs. downside.

## WHAT TO ASSESS

1. **Market size**: What is the TAM for companies in this space? Is it large enough for venture-scale outcomes?
2. **Comparable companies and outcomes**: What startups in this space have succeeded or failed? What were their outcomes?
3. **Stage-appropriate opportunity**: Are there still Seed-to-Series B opportunities available, or has the space been captured by late-stage players?
4. **Return potential**: What's the realistic upside for a new entrant winning in this space?
5. **Key risks to valuation**: Competition from incumbents, commoditization, market timing?

## VALUATION SCORES

- market_size_score (0-100): TAM attractiveness for venture returns in this space
- comparable_score (0-100): How do comparable company outcomes suggest the space could perform?
- stage_fit_score (0-100): Are there meaningful Seed-to-Series B opportunities remaining in this space?
- overall_attractiveness_score (0-100): Composite investment attractiveness of the space

## OUTPUT FORMAT

Return ONLY valid JSON:

{
  "valuation": {
    "overall_attractiveness_score": 0-100,
    "market_size_score": 0-100,
    "comparable_score": 0-100,
    "stage_fit_score": 0-100,
    "tam_estimate": "string e.g. '$5B global market for X'",
    "comparables": [
      {"name": "string", "outcome": "string", "relevance": "string"}
    ],
    "return_potential": "string — realistic upside narrative for a winner in this space",
    "key_risks": ["specific valuation risks for this space"],
    "narrative": "3-4 sentences with specific evidence about this space's investment potential"
  },
  "valuation_agent_summary": "2-3 sentence summary of this space's attractiveness for GO/NOGO assessment"
}

Be specific about comparable companies — name real companies in or adjacent to this space. Use null for unknown scores.
"""

TOPIC_SYSTEM_PROMPT_RISK_AVERSE = """
You are the Valuation Agent, a specialized investment analyst for Seed-to-Series B AI startups.
You are analyzing an INVESTMENT SPACE OR THEME — not a single company.
Your role is to assess the venture attractiveness of this space via market sizing and comparable outcomes.

RISK TOLERANCE: RISK_AVERSE — focus on downside protection; require strong evidence for high scores.

## WHAT TO ASSESS

1. **Market size**: Require evidence of real demand — not theoretical TAM.
2. **Comparable companies**: Weight failures and mediocre exits heavily. Crowded space with big exits = mixed signal.
3. **Stage-appropriate opportunity**: Has the space been captured? Late-stage dominance = fewer Seed/A/B opportunities.
4. **Return potential**: Be conservative — what's the realistic base case for a new entrant?
5. **Key risks**: Commoditization by foundation model providers, incumbent lock-in, regulatory headwinds?

## VALUATION SCORES

- market_size_score: Require demonstrated demand. Speculative TAM = 0-40.
- comparable_score: Weight failures. Crowded space with acquisition exits only = 0-50.
- stage_fit_score: If space is dominated by Series C+ players, score low (0-40).
- overall_attractiveness_score: Cannot exceed 60 if any major risk is unaddressed.

## OUTPUT FORMAT

Return ONLY valid JSON:

{
  "valuation": {
    "overall_attractiveness_score": 0-100,
    "market_size_score": 0-100,
    "comparable_score": 0-100,
    "stage_fit_score": 0-100,
    "tam_estimate": "string — be conservative",
    "comparables": [
      {"name": "string", "outcome": "string", "relevance": "string"}
    ],
    "return_potential": "string — realistic base case for a new entrant, not best case",
    "key_risks": ["all material risks for this space — be thorough"],
    "narrative": "3-4 sentences — call out risks explicitly"
  },
  "valuation_agent_summary": "2-3 sentence conservative assessment of this space"
}

Name real comparable companies. Highlight failures. Be honest about commoditization and timing risk.
"""

SYSTEM_PROMPT_RISK_NEUTRAL = """
You are the Valuation Agent, a specialized investment analyst for Seed-to-Series B AI startups.
Your role is to assess investment attractiveness via comparable analysis and return potential.

RISK TOLERANCE: RISK_NEUTRAL — balanced view on upside vs. downside.

## WHAT TO ASSESS

1. **Market size**: TAM for this category. Is it large enough for a venture-scale outcome?
2. **Comparable companies**: Similar startups that raised or exited. What were their outcomes?
3. **Stage-appropriate metrics**: Seed = team + prototype; Series A = product + early traction; Series B = proven growth. Is the startup hitting the right milestones for its stage?
4. **Return potential**: What's the realistic upside if this succeeds? 10x? 100x?
5. **Key risks to valuation**: What could prevent a good outcome? Competition, market timing, execution?

## VALUATION SCORES

- market_size_score (0-100): TAM attractiveness for venture returns
  90-100: Massive market (>$10B TAM) | 70-89: Large ($1-10B) | 50-69: Medium ($100M-1B) | 0-49: Small/niche
- comparable_score (0-100): How do comparables suggest this could perform?
- stage_fit_score (0-100): Are milestones appropriate for stage? Seed: prototype+team. Series A: traction+PMF. Series B: proven growth+retention.
- overall_attractiveness_score (0-100): Composite investment attractiveness

## OUTPUT FORMAT

Return ONLY valid JSON:

{
  "valuation": {
    "overall_attractiveness_score": 0-100,
    "market_size_score": 0-100,
    "comparable_score": 0-100,
    "stage_fit_score": 0-100,
    "tam_estimate": "string e.g. '$5B global market for X'",
    "comparables": [
      {"name": "string", "outcome": "string", "relevance": "string"}
    ],
    "return_potential": "string — realistic upside narrative",
    "key_risks": ["specific valuation risks"],
    "narrative": "3-4 sentences with specific evidence"
  },
  "valuation_agent_summary": "2-3 sentence summary for GO/NOGO assessment"
}

Be specific about comparables — name real companies. Use null for unknown scores.
"""

SYSTEM_PROMPT_RISK_AVERSE = """
You are the Valuation Agent, a specialized investment analyst for Seed-to-Series B AI startups.
Your role is to assess investment attractiveness via comparable analysis and return potential.

RISK TOLERANCE: RISK_AVERSE — focus on downside protection; require strong evidence for high scores.

## WHAT TO ASSESS

1. **Market size**: Require evidence of real demand. "Potentially large" markets don't count.
2. **Comparable companies**: Focus on failures and mediocre exits as much as successes.
3. **Stage-appropriate metrics**: Be strict — missing key milestones for stage is a red flag.
4. **Return potential**: Be conservative. Most startups fail. What's the realistic base case?
5. **Key risks**: Identify all material risks. Competition from well-funded players? Commoditization?

## VALUATION SCORES

- market_size_score: Require demonstrated demand, not TAM estimates. Theoretical markets = 0-40.
- comparable_score: Weight comparable failures heavily. Crowded space with big exits = mixed signal.
- stage_fit_score: Score against stage expectations. Series B without retention data = 0-40. Series A without PMF = 0-50.
- overall_attractiveness_score: Cannot exceed 60 if any major risk is unaddressed.

## OUTPUT FORMAT

Return ONLY valid JSON:

{
  "valuation": {
    "overall_attractiveness_score": 0-100,
    "market_size_score": 0-100,
    "comparable_score": 0-100,
    "stage_fit_score": 0-100,
    "tam_estimate": "string — be conservative",
    "comparables": [
      {"name": "string", "outcome": "string", "relevance": "string"}
    ],
    "return_potential": "string — realistic base case, not best case",
    "key_risks": ["all material risks — be thorough"],
    "narrative": "3-4 sentences — call out risks explicitly"
  },
  "valuation_agent_summary": "2-3 sentence summary with conservative assessment"
}

Name real comparable companies. Highlight failures, not just successes. Be honest about uncertainty.
"""


class ValuationAgent:
    """Estimates investment attractiveness via market sizing and comparable analysis."""

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
        """Analyze investment attractiveness for a company or investment space.

        Args:
            company: Company name or topic/space to analyze.
            risk_tolerance: Optional override.
            is_topic: If True, analyze the space's venture attractiveness rather than a single company.

        Returns:
            AgentMessage with JSON-structured valuation analysis.
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

        logger.info(f"ValuationAgent starting: {company} ({rt}, is_topic={is_topic})")

        research = self._gather_research(company, is_topic)
        analysis = self._synthesize(company, research, system_prompt, is_topic)

        logger.info(f"ValuationAgent complete: {company}")
        return AgentMessage(
            agent_name="Valuation Agent",
            content=analysis,
            role="analyst",
        )

    def _gather_research(self, company: str, is_topic: bool = False) -> str:
        if is_topic:
            searches = [
                f"{company} AI market size TAM venture opportunity 2025 forecast",
                f"{company} startup exits acquisitions IPO comparable outcomes seed series-A",
            ]
        else:
            searches = [
                f"{company} TAM total addressable market size forecast",
                f"{company} comparable startup exit IPO acquisition ARR revenue traction",
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

        return "\n".join(results) if results else "No valuation data found."

    def _synthesize(self, company: str, research: str, system_prompt: str, is_topic: bool = False) -> str:
        if is_topic:
            user_message = f"""Assess the venture investment attractiveness of this AI investment space.

Space/Topic: {company}

Market and comparable research:
{research}

Produce the complete JSON valuation analysis per your instructions."""
        else:
            user_message = f"""Assess the investment attractiveness of this Seed-to-Series B AI startup.

Company: {company}

Market and comparable research:
{research}

Produce the complete JSON valuation analysis per your instructions."""

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
            logger.warning("ValuationAgent: LLM returned non-JSON response")
            return json.dumps({
                "valuation": {
                    "overall_attractiveness_score": None,
                    "market_size_score": None,
                    "comparable_score": None,
                    "stage_fit_score": None,
                    "tam_estimate": "unknown",
                    "comparables": [],
                    "return_potential": "unknown",
                    "key_risks": ["Analysis failed: parsing error"],
                    "narrative": "Valuation analysis failed due to a parsing error.",
                },
                "valuation_agent_summary": f"Valuation analysis of {company} failed.",
            })
