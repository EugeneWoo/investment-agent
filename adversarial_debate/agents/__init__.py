"""Debate agents: wrappers that add debate_turn() capability to base agents.

Each debate agent wraps its parent via composition, extending it with:
- debate_turn() method for participating in adversarial debates
- Debate-specific system prompts (risk_neutral and risk_averse)
- Utilities for formatting debate history for LLM consumption
"""

from __future__ import annotations

__all__ = ["SearchDebateAgent", "SentimentDebateAgent", "ValuationDebateAgent"]
