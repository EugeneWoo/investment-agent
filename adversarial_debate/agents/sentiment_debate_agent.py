"""Sentiment Debate Agent: wraps SentimentAgent with adversarial debate capability.

Extends the base SentimentAgent to participate in round-robin debates by:
- Reading prior round positions from other agents
- Challenging the weakest opposing argument
- Updating GO/NOGO stance with new confidence and rationale
"""

from __future__ import annotations

import json
import logging

from agents.sentiment_agent import SentimentAgent
from models import AgentMessage
from tools.anthropic import AnthropicClient

from ..models import DebatePosition

logger = logging.getLogger(__name__)

DEBATE_SYSTEM_PROMPT_RISK_NEUTRAL = """
You are the Sentiment Agent in an adversarial investment debate for Seed-to-Series C AI startups.
Your domain expertise: PUBLIC SENTIMENT, PRESS COVERAGE, and COMMUNITY REACTION.

RISK TOLERANCE: RISK_NEUTRAL — weigh positive and negative signals equally.

## YOUR ROLE

You have already completed your initial analysis. Now you must debate with the Search Agent and Valuation Agent.

Read the prior round positions. Identify the WEAKEST opposing argument — one that:
- Contradicts your findings on press coverage, community sentiment, or momentum
- Misinterprets sentiment signals or founder reputation
- Overlooks red flags you identified

Then update your stance. You may:
- STAND FIRM: Keep your position if confident, strengthen rationale
- CONCEDE: Change position if the opposing argument is compelling

## OUTPUT FORMAT

Return ONLY valid JSON — no markdown, no preamble:

{
  "position": "GO|NOGO",
  "confidence": 0.0-1.0,
  "rationale": "2-3 sentences explaining your stance and challenging the weakest opposing argument",
  "challenges": [
    "specific opposing argument you are challenging",
    "another weak argument you are addressing"
  ]
}

Be specific. Cite the agent and argument you're challenging. Use sentiment and momentum evidence from your Phase 1 analysis.
"""

DEBATE_SYSTEM_PROMPT_RISK_AVERSE = """
You are the Sentiment Agent in an adversarial investment debate for Seed-to-Series C AI startups.
Your domain expertise: PUBLIC SENTIMENT, PRESS COVERAGE, and COMMUNITY REACTION.

RISK TOLERANCE: RISK_AVERSE — weight negative signals heavily; treat absence of coverage as a concern.

## YOUR ROLE

You have already completed your initial analysis. Now you must debate with the Search Agent and Valuation Agent.

Read the prior round positions. Identify the WEAKEST opposing argument — one that:
- Downplays negative sentiment or red flags you identified
- Overstates community enthusiasm without evidence
- Ignores lack of credible press coverage or founder reputation issues

Then update your stance. You may:
- STAND FIRM: Keep your position if confident, especially if red flags remain unaddressed
- CONCEDE: Change position only if opposing arguments present strong counterevidence

## OUTPUT FORMAT

Return ONLY valid JSON — no markdown, no preamble:

{
  "position": "GO|NOGO",
  "confidence": 0.0-1.0,
  "rationale": "2-3 sentences explaining your stance and challenging the weakest opposing argument",
  "challenges": [
    "specific opposing argument you are challenging",
    "another weak argument you are addressing"
  ]
}

Be conservative. Highlight negative sentiment and red flags. Challenge arguments that gloss over lack of coverage or community concerns.
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


class SentimentDebateAgent:
    """Wraps SentimentAgent with adversarial debate capability."""

    agent_name: str = "Sentiment Agent"

    def __init__(self, risk_tolerance: str = "risk_neutral") -> None:
        """Initialize with a base SentimentAgent instance.

        Args:
            risk_tolerance: Risk tolerance setting for system prompt selection.
        """
        self.risk_tolerance = risk_tolerance
        self._base_agent = SentimentAgent(risk_tolerance)
        self._llm = AnthropicClient()

    def _debate_system_prompt(self, risk_tolerance: str) -> str:
        """Select the appropriate debate system prompt based on risk tolerance.

        Args:
            risk_tolerance: Either "risk_neutral" or "risk_averse".

        Returns:
            The debate system prompt string.
        """
        return (
            DEBATE_SYSTEM_PROMPT_RISK_AVERSE if risk_tolerance == "risk_averse" else DEBATE_SYSTEM_PROMPT_RISK_NEUTRAL
        )

    def _format_debate_history(self, debate_history: list[dict]) -> str:
        """Format accumulated debate history into a readable string for the LLM.

        Args:
            debate_history: List of prior debate position dicts, each containing
                agent_name, position, confidence, rationale, challenges, round_number.

        Returns:
            Formatted string with one entry per prior position.
        """
        if not debate_history:
            return "No prior positions."

        lines = []
        for entry in debate_history:
            round_num = entry.get("round_number", "?")
            agent = entry.get("agent_name", "Unknown")
            position = entry.get("position", "?")
            conf = entry.get("confidence", 0.0)
            rationale = entry.get("rationale", "")
            challenges = entry.get("challenges", [])

            lines.append(f"Round {round_num} — {agent}: {position} (confidence: {conf:.2f})")
            lines.append(f"  Rationale: {rationale}")

            if challenges:
                lines.append(f"  Challenges:")
                for c in challenges:
                    lines.append(f"    - {c}")
            lines.append("")

        return "\n".join(lines)

    def debate_turn(
        self,
        company: str,
        phase1_analysis: str,
        debate_history: list[dict],
        round_number: int,
        risk_tolerance: str,
        is_topic: bool = False,
    ) -> DebatePosition:
        """Take a debate turn after reviewing prior positions.

        Args:
            company: Company or topic/space being analyzed.
            phase1_analysis: The agent's Phase 1 analysis (truncated to ~2000 chars).
            debate_history: Accumulated positions from all prior rounds.
            round_number: Current debate round number (1-indexed).
            risk_tolerance: Risk tolerance setting for prompt selection.
            is_topic: If True, frame the debate around the space rather than a single company.

        Returns:
            DebatePosition with the agent's updated stance.
        """
        system_prompt = self._debate_system_prompt(risk_tolerance)
        history_text = self._format_debate_history(debate_history)

        prior_entries = [e for e in debate_history if e.get("agent_name") == self.agent_name]
        prior_confidence_line = (
            f"Your previous confidence: {prior_entries[-1]['confidence']:.2f}"
            if prior_entries
            else "Your previous confidence: N/A (this is your first round)"
        )

        subject_label = "Space/Topic" if is_topic else "Company"
        user_message = f"""{subject_label}: {company}
Risk tolerance: {risk_tolerance}
Round: {round_number}
{prior_confidence_line}

## Your Phase 1 Analysis (sentiment, press, community reaction across this space):
{phase1_analysis[:2000]}

## Prior Debate Positions:
{history_text}

## Your Turn:
Review the prior positions. Identify the weakest opposing argument and challenge it.
Update your position (GO/NOGO), confidence, rationale, and challenges.

CONFIDENCE RULE: Your confidence score MUST change from your previous value unless you can state a specific, compelling reason in your rationale for why the debate has added nothing new. Adjust up if arguments strengthen your case; adjust down if opposing arguments raised valid concerns. Do not anchor to your prior score.

Return JSON in the specified format."""

        try:
            response = self._llm.messages_create(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=1024,
            )
            cleaned = _extract_json(response)
            data = json.loads(cleaned)

            return DebatePosition(
                agent_name=self.agent_name,
                position=data.get("position", "NOGO"),
                confidence=float(data.get("confidence", 0.0)),
                rationale=data.get("rationale", ""),
                challenges=data.get("challenges", []),
                round_number=round_number,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"SentimentDebateAgent: Failed to parse debate response: {e}")
            # Return safe fallback
            return DebatePosition(
                agent_name=self.agent_name,
                position="NOGO",
                confidence=0.0,
                rationale=f"Parse error: {e}",
                challenges=[],
                round_number=round_number,
            )

    @property
    def base_agent(self) -> SentimentAgent:
        """Access the underlying SentimentAgent for Phase 1 analysis."""
        return self._base_agent
