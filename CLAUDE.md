# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Multi-agent investment analysis system for Seed-to-Series B AI startups. Three specialized agents (Search, Sentiment, Valuation) run in a two-phase pipeline: **Phase 1** each agent speaks once in sequence (Search → Sentiment → Valuation) to produce a GO/NOGO verdict; **Phase 2** round-robin debate until consensus (future enhancement). Deployed as a public Streamlit dashboard on Streamlit Community Cloud.

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

# Run the app locally
streamlit run app.py

# Run tests
pytest                         # all tests
pytest tests/agents/           # agents only
pytest tests/orchestrator/     # orchestrator only

# Lint & format
ruff check .
ruff format .
mypy .
```

## Architecture

```
investment-agent/
├── app.py                     # Streamlit entry point
├── agents/
│   ├── search_agent.py        # Discovers Seed-to-Series B AI startups via Tavily + Crunchbase
│   ├── sentiment_agent.py     # Reflection-enhanced LLM summarization over Reddit/Twitter/news
│   └── valuation_agent.py     # Estimates annualized return + volatility via comparables
├── orchestrator/
│   └── orchestrator.py        # Two-phase pipeline: analysis (once each) → round-robin debate
├── tools/
│   ├── tavily.py              # Tavily web search wrapper
│   ├── crunchbase.py          # Crunchbase startup data wrapper
│   ├── reddit.py              # Reddit PRAW wrapper
│   └── twitter.py             # Twitter/X tweepy wrapper
├── ui/
│   ├── components.py          # Reusable Streamlit component functions
│   └── styles.py              # Custom CSS injected once at startup
├── models.py                  # AgentMessage, DebateResult, DebateState dataclasses
└── tests/
    ├── conftest.py            # Shared fixtures (AgentMessage, DebateResult)
    ├── agents/
    ├── orchestrator/
    └── tools/
```

### Key Design Decisions

- **Agent pattern:** Each agent is a Python class with `__init__(risk_tolerance)` that builds the system prompt, and `run(context, risk_tolerance) -> AgentMessage`
- **Risk tolerance:** Injected into system prompts at instantiation (`risk_neutral` | `risk_averse`) — not hardcoded
- **Orchestrator pipeline:** Single `Orchestrator.run(company, risk_tolerance)` method — Phase 1 runs each agent once in sequence, Phase 2 runs round-robin debate until consensus
- **Structured output:** All inter-agent data uses `AgentMessage` and `DebateResult` dataclasses — no bare dicts
- **Consensus:** Debate mode requires all agents to agree on GO/NOGO; exceeding `max_rounds` returns `NO_CONSENSUS`
- **Session state keys:** `st.session_state["debate_result"]`, `["agent_messages"]`, `["run_config"]`
