## Tech Stack

### Language & Runtime
- **Language:** Python 3.11+
- **Package Manager:** `uv` (preferred) or `pip` with `pyproject.toml`

### Multi-Agent Framework
- **Orchestration:** Custom Python orchestrator using the `anthropic` SDK directly (no AutoGen, no LangChain)
- **LLM:** Claude via `anthropic` Python SDK (`claude-sonnet-4-6` default model)
- **Agent pattern:** Each agent is a Python class with a system prompt, tool list, and `run()` method that calls `client.messages.create()`

### Agents
- **Search Agent:** Discovers pre-Series A / early-stage AI startup investment ideas
- **Sentiment Agent:** Reflection-enhanced LLM summarization over fundraising news, product launches, events, and social media
- **Valuation Agent:** Computational tool estimating annualized return and volatility using comparable company analysis
- **Orchestrator:** Group Chat controller supporting two modes:
  - `collaboration` — each agent speaks twice, outputs consolidated report
  - `debate` — round-robin until consensus GO/NOGO decision

### Data Sources & APIs
- **Web Search:** Tavily API (`tavily-python`)
- **Startup Data:** Crunchbase API
- **Social Sentiment:** Reddit via PRAW (`praw`), Twitter/X via `tweepy`
- **LLM:** Anthropic API (`anthropic`)

### Frontend
- **UI Framework:** Streamlit
- **Hosting:** Streamlit Community Cloud (share.streamlit.io) — public GitHub repo required
- **Secrets:** `.streamlit/secrets.toml` (local), Streamlit Cloud secrets manager (production)

### Testing & Quality
- **Test Framework:** `pytest`
- **Linting/Formatting:** `ruff` (lint + format)
- **Type Checking:** `mypy`

### Environment
- **Config:** Environment variables via `.env` (local), `st.secrets` (Streamlit Cloud)
- **Secrets never committed:** API keys for Anthropic, Tavily, Crunchbase, Reddit, Twitter/X
