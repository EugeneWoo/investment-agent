## General Conventions

- **Project structure:** `agents/` for agent classes, `orchestrator/` for debate/collaboration logic, `tools/` for external API wrappers, `ui/` for Streamlit pages/components
- **Agent classes:** Each agent lives in its own file (`agents/search_agent.py`, `agents/sentiment_agent.py`, `agents/valuation_agent.py`)
- **Tool wrappers:** Each external API (Tavily, Crunchbase, Reddit, Twitter/X) has its own module in `tools/` with a clean interface; agents import tools, not raw API clients
- **Debate state:** Pass a shared `DebateState` dataclass through the orchestrator rather than mutable global state
- **Risk tolerance:** Injected into each agent's system prompt at instantiation time (`risk_neutral` or `risk_averse`), not hardcoded
- **Pipeline:** The orchestrator runs a single unified pipeline — Phase 1 (each agent speaks once: Search → Sentiment → Valuation) followed immediately by Phase 2 (round-robin debate until GO/NOGO consensus or NO_CONSENSUS). No mode toggle.
- **Secrets:** Load from `st.secrets` in Streamlit context; fall back to `os.environ` for CLI/test context
- **Output format:** All agent responses return structured `AgentMessage` dataclasses with `agent_name`, `content`, `round`, and `timestamp` fields
