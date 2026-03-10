# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Multi-agent investment analysis system for Seed-to-Series B AI startups. Two modes, both deployed as public Streamlit dashboards on Streamlit Community Cloud:

- **Judge mode** (`app.py`): Three agents (Search, Sentiment, Valuation) research independently, then a fourth **Judge** LLM synthesizes into a GO/NOGO verdict.
- **Debate mode** (`adversarial_debate/app_debate.py`): Same three agents run Phase 1, then debate in round-robin until consensus or `max_rounds` is exceeded (majority vote fallback).

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
streamlit run app.py                              # Judge mode
streamlit run adversarial_debate/app_debate.py   # Debate mode

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
├── app.py                     # Judge mode Streamlit entry point
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
    ├── app_debate.py          # Debate mode Streamlit entry point
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
- **Eligibility check:** Runs before any agent analysis. Single Tavily search (`"{company}" funding raised private company product AI`, `include_domains=["crunchbase.com"]`) + LLM scoring on three criteria: `listed_confidence` (BLOCK if >80 — publicly traded), `not_ai_native_confidence` (BLOCK if >80 — not AI-native), `late_stage_confidence` (BLOCK if >80 — Series C or later). "Venture - Series Unknown" on Crunchbase is treated as inconclusive and passes through. Both orchestrators share the same eligibility logic for A/B test consistency.
- **Session state keys:** `st.session_state["debate_result"]`, `["agent_messages"]`, `["run_config"]`
