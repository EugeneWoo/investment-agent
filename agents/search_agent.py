"""Search Agent: discovers Seed-to-Series B AI startups and analyzes founder quality + market gap."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import AgentMessage
from tools.anthropic import AnthropicClient
from tools.tavily import TavilyClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_RISK_NEUTRAL = """
You are the Search Agent, a specialized investment analyst for Seed-to-Series B AI startups.
Analyze TWO dimensions: (1) Founder Quality and (2) Market Gap Validation.

ELIGIBLE STAGES: pre-seed, seed, Series A, Series B. If the company is Series C or later, set funding_stage accordingly and note it is outside the eligible investment scope.

RISK TOLERANCE: RISK_NEUTRAL — give the startup the benefit of the doubt on ambiguous signals.

## PART 1: FOUNDER QUALITY

For each founder evaluate:
- Experience relevance (0-100): Does their background match the startup's domain?
  90-100: Senior leader in exact domain | 70-89: Strong adjacent experience | 50-69: Some relevance | 0-49: Weak/none
- Team complementarity (0-100, null if solo): Do skills cover tech + business + domain?
- Commitment: "full-time" | "part-time" | "unknown"
  Green flags: left previous job, sole LinkedIn role, active GitHub/blog
  Red flags: currently employed elsewhere, "side project" language
  Ambiguous = "unknown" (neutral signal)

Synthesize into founder_quality_score (relevance 40%, complementarity 30%, commitment 30%).

## PART 2: MARKET GAP VALIDATION

- bandwagon_risk_score (0-100, 100=definite LLM wrapper):
  Red flags: "AI-powered X" with no specifics, thin API wrapper, GPT-4 as product not infra, no proprietary data/fine-tuning
  Green flags: proprietary data, domain expertise embedded, custom models, workflow integration
- defensibility_score (0-100): Moats today — exclusive data, network effects, switching costs, regulatory barriers
- market_gap_score = weighted synthesis (defensibility 40%, inverse bandwagon risk 30%, competitive differentiation 30%)

## OUTPUT FORMAT

Return ONLY valid JSON — no markdown, no preamble:

{
  "company": {
    "name": "string",
    "description": "string",
    "funding_stage": "seed|pre-seed|series-a|series-b|unknown",
    "source_urls": ["string"]
  },
  "founders": [
    {
      "name": "string",
      "role": "string",
      "background": "2-3 sentence summary",
      "relevance_score": 0-100,
      "commitment_level": "full-time|part-time|unknown",
      "evidence": ["specific evidence items"]
    }
  ],
  "founder_analysis": {
    "founder_quality_score": 0-100,
    "complementarity_score": "0-100 or null",
    "narrative": "3-4 sentences with specific evidence"
  },
  "market_analysis": {
    "market_gap_score": 0-100,
    "bandwagon_risk_score": 0-100,
    "defensibility_score": 0-100,
    "differentiation": "2-3 sentences",
    "competitors": [{"name": "string", "differentiation": "string"}],
    "bandwagon_evidence": ["specific signals found"],
    "defensibility_narrative": "2-3 sentences"
  },
  "search_agent_summary": "2-3 sentence executive summary for GO/NOGO assessment"
}

Cite specific evidence — never generic claims. Use null for unknown numeric fields.
"""

SYSTEM_PROMPT_RISK_AVERSE = """
You are the Search Agent, a specialized investment analyst for Seed-to-Series B AI startups.
Analyze TWO dimensions: (1) Founder Quality and (2) Market Gap Validation.

ELIGIBLE STAGES: pre-seed, seed, Series A, Series B. If the company is Series C or later, set funding_stage accordingly and note it is outside the eligible investment scope.

RISK TOLERANCE: RISK_AVERSE — require strong evidence for positive signals; treat ambiguity as risk.

## PART 1: FOUNDER QUALITY

For each founder evaluate:
- Experience relevance (0-100): Require DIRECT proven experience in exact domain.
  90-100: Proven track record | 70-89: Strong direct experience | 50-69: Adjacent only | 0-49: Weak/none — major red flag
- Team complementarity (0-100, null if solo): Require coverage across tech + business + domain. Solo founder = significant risk.
- Commitment: "full-time" | "part-time" | "unknown"
  Green flags: left previous job, sole LinkedIn role
  Red flags: employed elsewhere, student, "side project"
  Ambiguous = treat "unknown" as a NEGATIVE signal (50 score)

Synthesize into founder_quality_score. No single weak dimension should allow score >70.

## PART 2: MARKET GAP VALIDATION

- bandwagon_risk_score (0-100, 100=definite LLM wrapper):
  Low threshold — if technical differentiation is unclear, score above 40.
  One red flag is enough to score 50+. Scrutinize "AI-powered" marketing claims heavily.
- defensibility_score (0-100): Only existing moats count — future plans don't.
  Pre-revenue with no moats = 0-30.
- market_gap_score = weighted synthesis. Wrapper OR no defensibility = cap at 50.

## OUTPUT FORMAT

Return ONLY valid JSON — no markdown, no preamble:

{
  "company": {
    "name": "string",
    "description": "string",
    "funding_stage": "seed|pre-seed|series-a|series-b|unknown",
    "source_urls": ["string"]
  },
  "founders": [
    {
      "name": "string",
      "role": "string",
      "background": "2-3 sentence summary",
      "relevance_score": 0-100,
      "commitment_level": "full-time|part-time|unknown",
      "evidence": ["specific evidence items"]
    }
  ],
  "founder_analysis": {
    "founder_quality_score": 0-100,
    "complementarity_score": "0-100 or null",
    "narrative": "3-4 sentences — highlight concerns explicitly"
  },
  "market_analysis": {
    "market_gap_score": 0-100,
    "bandwagon_risk_score": 0-100,
    "defensibility_score": 0-100,
    "differentiation": "2-3 sentences — be honest if weak",
    "competitors": [{"name": "string", "differentiation": "string"}],
    "bandwagon_evidence": ["specific red flags found"],
    "defensibility_narrative": "2-3 sentences — call out lack of moats clearly"
  },
  "search_agent_summary": "2-3 sentence summary with clear risk assessment"
}

Cite specific evidence. Flag concerns explicitly. Use null for unknown numeric fields.
"""


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response, stripping markdown fences and surrounding text."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    # If still not starting with {, find the first { and last }
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return text


class SearchAgent:
    """Discovers and analyzes Seed-to-Series B AI startups via web search and LLM reasoning."""

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
        """Run full analysis: discover company → research founders → validate market gap → synthesize.

        Args:
            company: Company name or description to analyze.
            risk_tolerance: Optional override; uses instance default if not provided.

        Returns:
            AgentMessage with JSON-structured analysis in content field.
        """
        rt = risk_tolerance or self.risk_tolerance
        system_prompt = (
            SYSTEM_PROMPT_RISK_AVERSE if rt == "risk_averse" else SYSTEM_PROMPT_RISK_NEUTRAL
        )

        logger.info(f"SearchAgent starting analysis: {company} ({rt})")

        research = self._gather_research(company)
        analysis = self._synthesize(company, research, system_prompt)

        logger.info(f"SearchAgent complete: {company}")
        return AgentMessage(
            agent_name="Search Agent",
            content=analysis,
            role="analyst",
        )

    def _gather_research(self, company: str) -> str:
        """Run Tavily searches in parallel to gather company, founder, and competitor data."""
        searches = [
            f"{company} product technology use case competitors differentiation",
            f"{company} funding round seed investors announced",
            f"{company} CEO CTO founder LinkedIn biography background",
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

        return "\n".join(results) if results else "No search results found."

    def _synthesize(self, company: str, research: str, system_prompt: str) -> str:
        """Send research to Claude for structured analysis."""
        user_message = f"""Analyze this Seed-to-Series B AI startup for investment potential.

Company: {company}

Research gathered:
{research}

Produce the complete JSON analysis per your instructions."""

        try:
            response = self._llm.messages_create(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=4096,
            )
            cleaned = _extract_json(response)
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON response, wrapping in error structure")
            return json.dumps({
                "company": {"name": company, "description": "", "funding_stage": "unknown", "source_urls": []},
                "founders": [],
                "founder_analysis": {"founder_quality_score": None, "complementarity_score": None, "narrative": "Analysis failed: LLM returned invalid JSON."},
                "market_analysis": {"market_gap_score": None, "bandwagon_risk_score": None, "defensibility_score": None, "differentiation": "", "competitors": [], "bandwagon_evidence": [], "defensibility_narrative": ""},
                "search_agent_summary": f"Analysis of {company} failed due to a parsing error.",
            })
