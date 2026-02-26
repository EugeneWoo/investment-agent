# Tech Stack

## Language and Runtime

| Choice | Detail |
|---|---|
| Language | Python 3.11+ |
| Package manager | `uv` (preferred); `pip` with `pyproject.toml` as fallback |

---

## LLM Provider

| Choice | Detail |
|---|---|
| Model | `claude-sonnet-4-6` |
| SDK | `anthropic` Python SDK (official) |
| Notes | No AutoGen, no LangChain, no LlamaIndex — raw SDK only |

---

## Multi-Agent Orchestration

| Choice | Detail |
|---|---|
| Framework | Custom Python orchestrator |
| Approach | Pure `anthropic` SDK; agents are Python classes/functions coordinated by a hand-written orchestrator |
| Notes | No third-party agent frameworks (AutoGen, CrewAI, LangGraph, etc.) |

---

## Data Sources

| Source | Purpose | Library / API |
|---|---|---|
| Tavily | Web search for startup discovery and news aggregation | `tavily-python` SDK / REST API |
| Crunchbase | Firmographic data, funding rounds, investor info | Crunchbase REST API |
| Reddit | Community sentiment and discussion signals | `praw` (Python Reddit API Wrapper) |
| Twitter / X | Social sentiment and founder/investor signals | `tweepy` |

---

## UI

| Choice | Detail |
|---|---|
| Framework | Streamlit |
| Version target | Latest stable Streamlit compatible with Python 3.11+ |

---

## Hosting

| Choice | Detail |
|---|---|
| Platform | Streamlit Community Cloud (`share.streamlit.io`) |
| Repository | Public GitHub repository (required by Streamlit Community Cloud) |
| URL | Shareable public URL, no authentication required for viewers |

---

## Secrets Management

| Environment | Method |
|---|---|
| Local development | `.streamlit/secrets.toml` (gitignored) |
| Production | Streamlit Cloud secrets manager (configured via the Streamlit Cloud dashboard) |

Secrets include: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `CRUNCHBASE_API_KEY`,
`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`,
`TWITTER_BEARER_TOKEN`.

---

## Testing

| Choice | Detail |
|---|---|
| Framework | `pytest` |
| Approach | Unit tests with mocked API responses for agents; integration/smoke tests for orchestrator and report output |

---

## Linting and Formatting

| Tool | Purpose |
|---|---|
| `ruff` | Linting and auto-formatting (replaces flake8 + isort + black) |
| `mypy` | Static type checking |

---

## Project Configuration

| File | Purpose |
|---|---|
| `pyproject.toml` | Project metadata, dependencies, `ruff` and `mypy` configuration |
| `.streamlit/secrets.toml` | Local API key secrets (gitignored) |
| `.gitignore` | Excludes `.streamlit/secrets.toml`, `__pycache__`, `.mypy_cache`, `.ruff_cache`, `.venv` |
