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
You are a pre-screening filter for an investment analysis system focused on Seed-to-Series B AI startups and companies that have meaningfully integrated AI/LLMs into their products.

You will be given a company name and web search results (which may include Crunchbase data). Use the search results as ground truth.
Score your confidence (0–100) on each criterion.

IMPORTANT: If search results describe a completely different company (e.g., different industry, wrong names),
treat this as inconclusive information and score confidence LOW (<80) to allow through for manual review.

CRITERION 1 — PUBLIC LISTING (BLOCK if >80):
We ONLY invest in private companies (Seed-to-Series B). Publicly traded companies should be BLOCKED.
- Score listed_confidence HIGH (>80) ONLY if search results CONFIRM the company is currently publicly traded
- CONFIRMED evidence: active ticker symbol (e.g., $PLTR), current stock price, confirmed completed IPO
- Score listed_confidence LOW (0-20) if the company is private, pre-IPO, venture-backed, or has raised funding rounds
- Do NOT score high for: IPO speculation/rumours, comparisons to public companies, valuation estimates, or funding announcements
- "Series A/B/C funding", "valued at $Xbn", "raised $X" = PRIVATE company signals → score LOW

CRITERION 2 — AI-NATIVE (BLOCK if >80):
We ONLY invest in AI-native companies. Non-AI companies should be BLOCKED.
- Score not_ai_native_confidence HIGH (>80) ONLY if the company clearly does NOT meet AI-native definitions
- Score not_ai_native_confidence LOW (0-20) if the company IS AI-native

AI-NATIVE DEFINITIONS (company qualifies if ANY apply):
- Product itself is AI-driven (LLM assistant, AI coding tool, AI image generator)
- Launched LLM-powered product/feature from 2025+ that is central to offering
- Heavily integrated LLMs into core product (AI workflows, LLM-driven automation)

DOES NOT QUALIFY:
- Bank, marketplace, payments, pharma, retailer, manufacturer using AI peripherally
- Traditional cybersecurity, IoT, or infrastructure companies using AI as one feature
- Energy, oil & gas, utilities, or other non-tech industries

CRITERION 3 — FUNDING STAGE (BLOCK if >80):
We ONLY invest in Seed-to-Series B companies. Series C and beyond should be BLOCKED.
Crunchbase is the authoritative source for funding stage. If Crunchbase data is absent or inconclusive, default to score 0 — do NOT infer stage from funding amount, valuation, or company size.
- Score late_stage_confidence 90-100 if Crunchbase explicitly states last_funding_type is "series_c", "series_d", "series_e", or later
- Score late_stage_confidence 90-100 if at least one credible source (news outlet, press release, or Crunchbase) reports a confirmed closed Series C, D, or E round with a specific dollar amount and round label (e.g. "Company X closes $Xm Series C") — Crunchbase profile pages are paywalled, so news is a valid fallback
- Score late_stage_confidence 0-20 if last funding is Seed, Series A, or Series B
- Score late_stage_confidence 0 if Crunchbase data is missing or ambiguous AND news only speculates without a confirmed close
- Score late_stage_confidence 0 if Crunchbase says "Venture - Series Unknown" and news provides no confirmed round label
- Do NOT score above 0 based on funding amount, valuation, or company size alone — only the confirmed round label matters

Rules:
- listed_confidence > 80: BLOCK (company is publicly traded, we only want private)
- not_ai_native_confidence > 80: BLOCK (company is not AI-native)
- late_stage_confidence > 80: BLOCK (company is Series C or later, outside our investment stage)
- When in doubt on any criterion, score LOW and allow through for manual review
- The "reason" field must mention ONLY the criterion that caused the block

Respond with ONLY a valid JSON object — no markdown, no text outside the JSON:
{
  "listed_confidence": <0-100>,
  "not_ai_native_confidence": <0-100>,
  "late_stage_confidence": <0-100>,
  "eligible": <true|false>,
  "reason": "<one sentence citing only the blocking criterion if ineligible, empty string if eligible>"
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

JUDGE_TOPIC_SYSTEM_PROMPT = """
You are an investment Judge evaluating an INVESTMENT SPACE OR THEME for Seed-to-Series B AI startups.

Three independent analysts have each researched this investment space separately:
- Search Agent: evaluated the winning founder archetype and market gap / defensibility in this space
- Sentiment Agent: evaluated press coverage, community reaction, and momentum across this space
- Valuation Agent: evaluated market size, comparable outcomes, and return potential for new entrants

Your task: read all three reports and issue a single, decisive verdict on whether this space is worth investing in now.

Rules:
1. Start your response with exactly "GO" or "NOGO" — nothing else on the first line
2. On the second line, write 3-4 sentences citing specific evidence from the reports
3. Weigh all three dimensions: founder archetype quality, space sentiment, and space valuation
4. Be decisive — no hedging, no "it depends"

A GO verdict means: this space has strong structural opportunity for new Seed-to-Series B investments right now.
A NOGO verdict means: the space is too crowded, too early, too late, or lacks defensibility.

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

    @staticmethod
    def detect_input_type(text: str) -> str | None:
        """Heuristically detect whether input looks like a company name or a topic/space.

        Returns "company" if input looks like a specific company name when set to topic mode,
        "topic" if input looks like a space/theme when set to company mode, or None if unclear.

        Used to show a corrective warning in the UI — does not block execution.
        """
        if not text or not text.strip():
            return None

        t = text.strip()
        lower = t.lower()

        # URLs are always company inputs
        if lower.startswith(("http://", "https://", "www.")) or (
            "." in t and " " not in t and len(t) < 60
        ):
            return "company"

        words = t.split()
        word_count = len(words)

        # Strong topic signals
        topic_keywords = {
            "startups", "companies", "space", "sector", "industry", "market",
            "tools", "software", "platforms", "solutions", "systems",
            "for ", "in ", "using ", "with ai", "ai for", "ai in",
            "vertical", "applications", "landscape",
        }
        has_topic_keyword = any(kw in lower for kw in topic_keywords)

        # Strong company signals: short, title-cased or ends with known company suffixes
        company_suffixes = (".ai", " ai", "inc", "corp", "labs", "hq", ".io", "llc")
        has_company_suffix = any(lower.endswith(s) or lower.startswith(s.strip()) for s in company_suffixes)
        is_short = word_count <= 3
        is_title_case = all(w[0].isupper() for w in words if w and w[0].isalpha())

        looks_like_company = is_short and (is_title_case or has_company_suffix)
        looks_like_topic = has_topic_keyword or word_count >= 4

        if looks_like_company and not has_topic_keyword:
            return "company"
        if looks_like_topic and not has_company_suffix:
            return "topic"
        return None

    def eligibility_check(self, company: str) -> tuple[bool, str]:
        """Check eligibility using two complementary web searches.

        Search 1: Crunchbase-focused for authoritative funding/product data.
        Search 2: Broad news search targeting Series C+ and IPO keywords, since
        Crunchbase profile pages are paywalled and Tavily cannot scrape them.
        Only blocks if confidence > 80 on any criterion.

        Returns:
            Tuple of (is_eligible, reason). reason is empty string if eligible.
        """
        try:
            tavily = TavilyClient()

            # Search 1: Crunchbase-focused for authoritative funding stage data
            crunchbase_results = tavily.search(
                f'"{company}" funding raised private company product AI',
                max_results=5,
                include_domains=["crunchbase.com"],
            )

            # Search 2: Broad news search for latest funding round — catches Series C+ that Crunchbase paywalls
            news_results = tavily.search(
                f'"{company}" "Series C" OR "Series D" OR "Series E" OR IPO OR "went public" funding round',
                max_results=5,
            )

            all_results = crunchbase_results + news_results

            # Format all search results together
            snippets = "\n\n".join(
                f"[{r['title']}] ({r['url']})\n{r['content'][:400]}"
                for r in all_results
            ) or "No results found."

            user_message = f"""Company: {company}

Web search results:
{snippets}"""

            logger.info(f"Eligibility search results for '{company}': {snippets[:500]}...")

            response = self._llm.messages_create(
                system_prompt=ELIGIBILITY_SYSTEM_PROMPT,
                user_message=user_message,
                max_tokens=256,
                temperature=0,
            )
            logger.info(f"Eligibility LLM response for '{company}': {response}")
            raw = response.strip()
            json_start = raw.rfind("{")
            json_end = raw.rfind("}") + 1
            data = json.loads(raw[json_start:json_end])

            def _safe_conf(key: str) -> int:
                val = data.get(key, 0)
                try:
                    return int(val)
                except (TypeError, ValueError):
                    logger.warning(f"Eligibility field '{key}' has unexpected value {val!r}, defaulting to 0")
                    return 0

            listed_conf = _safe_conf("listed_confidence")
            not_ai_conf = _safe_conf("not_ai_native_confidence")
            late_stage_conf = _safe_conf("late_stage_confidence")
            logger.info(
                f"Eligibility check for '{company}': "
                f"listed_confidence={listed_conf}, not_ai_native_confidence={not_ai_conf}, "
                f"late_stage_confidence={late_stage_conf}"
            )

            if listed_conf > 80 or not_ai_conf > 80 or late_stage_conf > 80:
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
        self, company: str, analysis: str, risk_tolerance: str, is_topic: bool = False
    ) -> tuple[AgentMessage, str]:
        """Read all three independent agent reports and issue a GO/NOGO verdict.

        Args:
            company: Company or topic/space being evaluated.
            analysis: Formatted summary of all three agent reports.
            risk_tolerance: Risk tolerance setting for context.
            is_topic: If True, use the topic-aware judge prompt.

        Returns:
            Tuple of (AgentMessage with role='judge', verdict string).
        """
        subject_label = "Space/Topic" if is_topic else "Company"
        user_message = f"""{subject_label}: {company}
Risk tolerance: {risk_tolerance}

Independent analyst reports:
{analysis}

Issue your GO or NOGO verdict with rationale."""

        judge_prompt = JUDGE_TOPIC_SYSTEM_PROMPT if is_topic else JUDGE_SYSTEM_PROMPT
        try:
            response = self._llm.messages_create(
                system_prompt=judge_prompt,
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
