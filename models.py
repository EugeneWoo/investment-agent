from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentMessage:
    agent_name: str
    content: str
    role: str


@dataclass
class DebateResult:
    verdict: str
    rounds: int
    messages: list[AgentMessage]
    consensus_reached: bool
    recommendations: list[str] | None = None
