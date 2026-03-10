"""Debate Orchestrator: runs round-robin adversarial debate after Phase 1 analysis.

Extends the base Orchestrator to add:
- Round-robin debate loop (Search → Sentiment → Valuation, repeat)
- Consensus detection after each full round
- Majority vote fallback when max_rounds exceeded
- Progress callbacks for UI integration
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeAlias

from models import AgentMessage, DebateResult
from orchestrator.orchestrator import Orchestrator

from .agents.search_debate_agent import SearchDebateAgent
from .agents.sentiment_debate_agent import SentimentDebateAgent
from .agents.valuation_debate_agent import ValuationDebateAgent
from .models import DebatePosition, DebateRound

logger = logging.getLogger(__name__)

StatusCallback: TypeAlias = "Callable[[str], None] | None"


class DebateOrchestrator:
    """Wraps base Orchestrator with adversarial debate capability.

    Usage:
        orchestrator = DebateOrchestrator(risk_tolerance="risk_neutral", max_rounds=3)
        result = orchestrator.run("Anthropic", "risk_neutral")
    """

    def __init__(self, risk_tolerance: str = "risk_neutral", max_rounds: int = 3) -> None:
        """Initialize the debate orchestrator.

        Args:
            risk_tolerance: Risk tolerance setting for agent prompts.
            max_rounds: Maximum number of debate rounds before majority vote.
        """
        self.risk_tolerance = risk_tolerance
        self.max_rounds = max_rounds
        self._base_orchestrator = Orchestrator(risk_tolerance)

        # Initialize debate agents
        self._search_debate = SearchDebateAgent(risk_tolerance)
        self._sentiment_debate = SentimentDebateAgent(risk_tolerance)
        self._valuation_debate = ValuationDebateAgent(risk_tolerance)

    def eligibility_check(self, company: str) -> tuple[bool, str]:
        """Check eligibility using live search results.

        Delegates to base orchestrator, which performs a single comprehensive
        search covering both listing status and product information. This ensures
        identical results for proper A/B testing between base and debate modes.

        Only blocks if confidence > 80 on either criterion.

        Args:
            company: Company name to check.

        Returns:
            Tuple of (is_eligible, reason). reason is empty string if eligible.
        """
        # Use the base orchestrator's eligibility check with all criteria applied
        return self._base_orchestrator.eligibility_check(company)

    def _check_consensus(self, positions: list[DebatePosition]) -> tuple[bool, str | None]:
        """Check if all positions agree on GO or NOGO.

        Args:
            positions: List of DebatePosition objects from the current round.

        Returns:
            Tuple of (consensus_reached, consensus_position). Consensus position
            is "GO" or "NOGO" if consensus reached, else None.
        """
        if not positions:
            return False, None

        unique_positions = set(p.position for p in positions)
        if len(unique_positions) == 1:
            return True, unique_positions.pop()
        return False, None

    def _majority_vote(self, debate_rounds: list[DebateRound]) -> str:
        """Calculate majority vote across all debate rounds.

        Tally all positions from all rounds and return the majority position.
        Defaults to "NOGO" on a tie.

        Args:
            debate_rounds: List of all DebateRound objects in the debate.

        Returns:
            "GO" or "NOGO" — the majority position.
        """
        all_positions: list[str] = []
        for debate_round in debate_rounds:
            for pos in debate_round.positions:
                all_positions.append(pos.position)

        if not all_positions:
            return "NOGO"

        counts = Counter(all_positions)
        go_count = counts.get("GO", 0)
        nogo_count = counts.get("NOGO", 0)

        # Default to NOGO on tie
        if go_count > nogo_count:
            return "GO"
        return "NOGO"

    def _run_debate(
        self,
        company: str,
        risk_tolerance: str,
        phase1_map: dict[str, AgentMessage],
        status_callback: StatusCallback = None,
    ) -> tuple[list[DebateRound], str, bool]:
        """Run the round-robin adversarial debate.

        Args:
            company: Company being analyzed.
            risk_tolerance: Risk tolerance setting.
            phase1_map: Dict mapping agent names to their Phase 1 AgentMessage objects.
            status_callback: Optional callback for progress updates (e.g., st.write).

        Returns:
            Tuple of (debate_rounds, final_verdict, consensus_reached).
        """
        debate_rounds: list[DebateRound] = []
        debate_history: list[dict] = []
        round_number = 1

        while round_number <= self.max_rounds:
            round_positions: list[DebatePosition] = []

            # Round-robin: Search → Sentiment → Valuation
            agents = [
                ("Search Agent", self._search_debate),
                ("Sentiment Agent", self._sentiment_debate),
                ("Valuation Agent", self._valuation_debate),
            ]

            for agent_name, agent in agents:
                # Get this agent's Phase 1 analysis for context
                phase1_analysis = phase1_map.get(agent_name)
                if not phase1_analysis:
                    logger.warning(f"Phase 1 analysis not found for {agent_name}")
                    phase1_analysis = AgentMessage(
                        agent_name=agent_name, content="No Phase 1 analysis available.", role="analyst"
                    )

                # Extract JSON content if available
                try:
                    analysis_json = json.loads(phase1_analysis.content)
                    phase1_text = json.dumps(analysis_json, indent=2)
                except json.JSONDecodeError:
                    phase1_text = phase1_analysis.content

                # Take debate turn
                position = agent.debate_turn(
                    company=company,
                    phase1_analysis=phase1_text,
                    debate_history=debate_history,
                    round_number=round_number,
                    risk_tolerance=risk_tolerance,
                )
                round_positions.append(position)

                # Add to history for next agents
                debate_history.append(
                    {
                        "agent_name": position.agent_name,
                        "position": position.position,
                        "confidence": position.confidence,
                        "rationale": position.rationale,
                        "challenges": position.challenges,
                        "round_number": position.round_number,
                    }
                )

            # Check for consensus
            consensus_reached, consensus_position = self._check_consensus(round_positions)

            # Record the round
            debate_round = DebateRound(
                round_number=round_number,
                positions=round_positions,
                consensus_reached=consensus_reached,
                consensus_position=consensus_position,
            )
            debate_rounds.append(debate_round)

            # Build status message
            pos_summary = ", ".join(
                [f"{p.agent_name}: {p.position} ({p.confidence:.1f})" for p in round_positions]
            )
            if consensus_reached:
                status_msg = f"Round {round_number}: {pos_summary} — consensus reached: {consensus_position}"
            else:
                status_msg = f"Round {round_number}: {pos_summary} — no consensus"

            if status_callback:
                status_callback(status_msg)
            logger.info(status_msg)

            # Exit early if consensus reached
            if consensus_reached:
                final_verdict = consensus_position or "NOGO"
                return debate_rounds, final_verdict, True

            round_number += 1

        # Max rounds exceeded — use majority vote
        final_verdict = self._majority_vote(debate_rounds)
        if status_callback:
            status_callback(f"Max rounds ({self.max_rounds}) exceeded — majority vote: {final_verdict}")
        logger.info(f"Max rounds exceeded, majority vote: {final_verdict}")

        return debate_rounds, final_verdict, False

    def run(self, company: str, risk_tolerance: str | None = None, status_callback: StatusCallback = None) -> DebateResult:
        """Run full analysis: Phase 1 (independent agents) → Phase 2 (debate).

        Args:
            company: Company name or description to analyze.
            risk_tolerance: Optional override of instance default.
            status_callback: Optional callback for progress updates.

        Returns:
            DebateResult with final verdict and all messages including debate rounds.
        """
        rt = risk_tolerance or self.risk_tolerance

        # Phase 1: Run independent agents (reuse base orchestrator)
        logger.info(f"DebateOrchestrator starting Phase 1: {company}")
        if status_callback:
            status_callback("Running Phase 1: independent agent analysis...")

        # Get Phase 1 messages from base agents — run in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            f_search = executor.submit(self._search_debate.base_agent.run, company, rt)
            f_sentiment = executor.submit(self._sentiment_debate.base_agent.run, company, rt)
            f_valuation = executor.submit(self._valuation_debate.base_agent.run, company, rt)
            search_msg = f_search.result()
            sentiment_msg = f_sentiment.result()
            valuation_msg = f_valuation.result()

        phase1_messages = [search_msg, sentiment_msg, valuation_msg]
        phase1_map = {msg.agent_name: msg for msg in phase1_messages}

        if status_callback:
            status_callback("Phase 1 complete — starting debate...")

        # Phase 2: Run debate
        logger.info(f"DebateOrchestrator starting Phase 2 debate (max_rounds={self.max_rounds})")
        debate_rounds, final_verdict, consensus_reached = self._run_debate(
            company=company,
            risk_tolerance=rt,
            phase1_map=phase1_map,
            status_callback=status_callback,
        )

        # Build messages list (Phase 1 + debate positions)
        all_messages = phase1_messages.copy()

        # Add debate positions as AgentMessage objects
        for debate_round in debate_rounds:
            for pos in debate_round.positions:
                # Create a readable message for the UI
                content = json.dumps(
                    {
                        "round_number": pos.round_number,
                        "position": pos.position,
                        "confidence": pos.confidence,
                        "rationale": pos.rationale,
                        "challenges": pos.challenges,
                    },
                    indent=2,
                )
                all_messages.append(
                    AgentMessage(agent_name=pos.agent_name, content=content, role="debate")
                )

        # Generate recommendations if GO verdict
        recommendations = None
        if final_verdict == "GO":
            phase1_summary = self._base_orchestrator._format_phase1_summary(phase1_messages)
            recommendations = self._base_orchestrator._recommend_companies(company, phase1_summary)
            logger.info(f"Recommendations generated: {recommendations}")

        logger.info(f"DebateOrchestrator complete: {final_verdict} (consensus={consensus_reached})")

        return DebateResult(
            verdict=final_verdict,
            rounds=len(debate_rounds),
            messages=all_messages,
            consensus_reached=consensus_reached,
            recommendations=recommendations,
        )

    @property
    def base_orchestrator(self) -> Orchestrator:
        """Access the underlying Orchestrator for Phase 1 methods."""
        return self._base_orchestrator
