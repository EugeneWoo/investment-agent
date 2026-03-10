# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Multi-agent investment analysis system for Seed-to-Series B AI startups. Both modes are unified in a single Streamlit dashboard (`app.py`) deployed on Streamlit Community Cloud:

- **LLM as CIO** (Judge mode): Three agents (Search, Sentiment, Valuation) research independently, then a fourth **Judge** LLM synthesizes into a GO/NOGO verdict.
- **Agentic Round-Robin Debate** (Debate mode): Same three agents run Phase 1, then debate in round-robin until consensus or `max_rounds` is exceeded (majority vote fallback).

`adversarial_debate/app_debate.py` remains as a standalone entry point for the debate mode only.

## Tech Stack

- **Language:** Python 3.11+
- **LLM:** Claude (`claude-sonnet-4-6`) via `anthropic` SDK — no AutoGen, no LangChain
- **Multi-agent:** Custom Python orchestrator (pure `anthropic` SDK)
- **Data sources:** Tavily API, Crunchbase API, Reddit (PRAW), Twitter/X (tweepy)
- **UI:** Streamlit → deployed to Streamlit Community Cloud (public repo required)
- **Secrets:** `.streamlit/secrets.toml` locally; Streamlit Cloud secrets manager in production
- **Testing:** `pytest`, mocked external APIs
- **Linting:** `ruff` (lint + format), `mypy`

## Commands

```bash
# Install dependencies
uv sync                        # or: pip install -e ".[dev]"

# Run the apps locally
streamlit run app.py                              # Unified app (both modes)
streamlit run adversarial_debate/app_debate.py   # Debate mode standalone

# Run tests
pytest                              # all tests
pytest tests/agents/                # agents only
pytest tests/orchestrator/          # orchestrator only
PYTHONPATH=. pytest adversarial_debate/tests/   # debate module tests

# Lint & format
ruff check .
ruff format .
mypy .
```

## Architecture

```
investment-agent/
├── app.py                     # Unified Streamlit entry point (LLM as CIO + Agentic Round-Robin Debate)
├── agents/
│   ├── search_agent.py        # Discovers Seed-to-Series B AI startups via Tavily + Crunchbase
│   ├── sentiment_agent.py     # Reflection-enhanced LLM summarization over Reddit/Twitter/news
│   └── valuation_agent.py     # Estimates annualized return + volatility via comparables
├── orchestrator/
│   └── orchestrator.py        # Phase 1: 3 independent agents → Judge LLM verdict; eligibility check
├── tools/
│   ├── tavily.py              # Tavily web search wrapper (supports include_domains)
│   ├── crunchbase.py          # Crunchbase startup data wrapper
│   ├── reddit.py              # Reddit PRAW wrapper
│   └── twitter.py             # Twitter/X tweepy wrapper
├── ui/
│   ├── components.py          # Reusable Streamlit component functions
│   └── styles.py              # Custom CSS injected once at startup
├── models.py                  # AgentMessage, DebateResult, DebateState dataclasses
├── tests/
│   ├── conftest.py            # Shared fixtures (AgentMessage, DebateResult)
│   ├── agents/
│   ├── orchestrator/
│   └── tools/
└── adversarial_debate/        # Debate mode (self-contained module)
    ├── app_debate.py          # Debate mode standalone Streamlit entry point
    ├── models.py              # DebatePosition, DebateRound dataclasses
    ├── orchestrator.py        # DebateOrchestrator: Phase 1 → round-robin debate → consensus/majority vote
    ├── agents/
    │   ├── search_debate_agent.py
    │   ├── sentiment_debate_agent.py
    │   └── valuation_debate_agent.py
    └── tests/
```

### Key Design Decisions

- **Agent pattern:** Each agent is a Python class with `__init__(risk_tolerance)` that builds the system prompt, and `run(context, risk_tolerance) -> AgentMessage`
- **Risk tolerance:** Injected into system prompts at instantiation (`risk_neutral` | `risk_averse`) — not hardcoded
- **Orchestrator pipeline:** `Orchestrator.run()` runs each agent independently (no shared context), then a Judge LLM reads all three reports and issues GO/NOGO. `DebateOrchestrator.run()` runs the same Phase 1, then adds a round-robin debate loop.
- **Structured output:** All inter-agent data uses `AgentMessage` and `DebateResult` dataclasses — no bare dicts
- **Debate consensus:** All agents must agree on GO/NOGO. Exceeding `max_rounds` triggers majority vote across all rounds; ties default to NOGO.
- **Eligibility check:** Runs before any agent analysis. Two Tavily searches: (1) Crunchbase-domain search for authoritative funding/product data; (2) broad news search targeting Series C/D/E and IPO keywords (Crunchbase profile pages are paywalled, so news catches late-stage rounds the profile page cannot). LLM scores three criteria: `listed_confidence` (BLOCK if >80 — publicly traded), `not_ai_native_confidence` (BLOCK if >80 — not AI-native), `late_stage_confidence` (BLOCK if >80 — Series C or later). "Venture - Series Unknown" is inconclusive and passes through. Both orchestrators share the same eligibility logic for A/B test consistency.
- **Session state keys:** Judge mode: `st.session_state["judge_result"]`, `["judge_config"]`. Debate mode: `["debate_result"]`, `["debate_config"]`.
- **Unified app:** `app.py` hosts both modes via a top-level radio selector (`"LLM as CIO"` | `"Agentic Round-Robin Debate"`). Each mode renders its own sidebar config, input, run logic, and results section.
