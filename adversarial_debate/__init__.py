"""Adversarial Debate: round-robin multi-agent debate for investment analysis.

This subfolder extends the base investment-agent system with adversarial debate functionality.
The existing codebase (agents/, orchestrator/, app.py) remains unmodified.

Usage:
    streamlit run adversarial-debate/app_debate.py
"""

from __future__ import annotations

__all__ = ["DebatePosition", "DebateRound", "DebateOrchestrator"]
