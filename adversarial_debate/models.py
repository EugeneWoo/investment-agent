"""Debate models: extends base models with debate-specific data structures.

The DebatePosition and DebateRound dataclasses capture the state and evolution
of agent positions during an adversarial debate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DebatePosition:
    """A single agent's position in a specific debate round.

    Attributes:
        agent_name: Name of the agent (e.g., "Search Agent", "Sentiment Agent")
        position: The agent's stance — GO or NOGO
        confidence: Confidence level from 0.0 to 1.0
        rationale: Textual explanation for the position
        challenges: List of specific opposing arguments being challenged
        round_number: Which debate round this position is from
    """

    agent_name: str
    position: Literal["GO", "NOGO"]
    confidence: float
    rationale: str
    challenges: list[str] = field(default_factory=list)
    round_number: int = 1


@dataclass
class DebateRound:
    """A complete round of the adversarial debate.

    Each round consists of all three agents (Search, Sentiment, Valuation)
    taking turns to state their positions after reviewing prior rounds.

    Attributes:
        round_number: Which round this is (1-indexed)
        positions: List of DebatePosition objects from all agents in this round
        consensus_reached: Whether all agents reached the same position
        consensus_position: The consensus position ("GO" or "NOGO") if reached, else None
    """

    round_number: int
    positions: list[DebatePosition]
    consensus_reached: bool
    consensus_position: Literal["GO", "NOGO"] | None = None
