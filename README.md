# Investment Agent

Multi-agent AI system for analyzing Seed-to-Series B AI startups. Three specialized agents (Search, Sentiment, Valuation) run sequentially to produce a GO / NOGO verdict with full supporting analysis.

## How it works

**Phase 1 — Analysis** *(primary)*: Each agent runs once in sequence (Search → Sentiment → Valuation), building on the prior agent's findings. This produces the final verdict.

**Phase 2 — Debate** *(future enhancement)*: Agents debate in round-robin until all agree on GO or NOGO. If `max_rounds` is exceeded without consensus, the result is NO_CONSENSUS.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

## API keys required

| Key | Required | Where to get it |
|-----|----------|----------------|
| `ANTHROPIC_API_KEY` | Yes | [console.anthropic.com](https://console.anthropic.com) |
| `TAVILY_API_KEY` | Yes | [app.tavily.com](https://app.tavily.com) |
| `CRUNCHBASE_API_KEY` | No | [data.crunchbase.com](https://data.crunchbase.com/docs/using-the-api) |
| `REDDIT_CLIENT_ID` | No | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) |
| `REDDIT_CLIENT_SECRET` | No | Same as above |
| `TWITTER_BEARER_TOKEN` | No | [developer.twitter.com](https://developer.twitter.com/en/portal/dashboard) |

Only `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` are needed to run the app.

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/investment-agent.git
cd investment-agent
```

### 2. Install dependencies

```bash
# With uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"
```

### 3. Add your API keys

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys, or create `.streamlit/secrets.toml`:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
TAVILY_API_KEY = "tvly-..."

# Optional
CRUNCHBASE_API_KEY = ""
REDDIT_CLIENT_ID = ""
REDDIT_CLIENT_SECRET = ""
TWITTER_BEARER_TOKEN = ""
```

The app checks secrets in this order: `st.secrets` → environment variables → `.env` file.

### 4. Verify setup

```bash
uv run python -c "from config import settings; print('✓ Config loaded')"
```

### 5. Run the app

```bash
streamlit run app.py
```

The app opens at [http://localhost:8501](http://localhost:8501).

## Usage

1. Select **Risk Tolerance** in the sidebar — Balanced (Risk Neutral) or Conservative (Risk Averse)
2. Enter a company name or description (e.g. `Anthropic`, `Harvey AI`, or `AI startup building medical imaging tools`)
3. Click **Analyze**
4. View the verdict and per-agent analysis
5. Download the full report as Markdown

## Cost estimates (per analysis)

| API | Approx. cost | Notes |
|-----|--------------|-------|
| Anthropic Claude | $0.10 – $0.50 | 3–5 LLM calls per analysis |
| Tavily Search | $0.01 – $0.05 | ~10–15 searches, cached for reuse |
| Crunchbase | optional | Not required for MVP |

**Total (MVP)**: ~$0.15 – $0.60 per startup analysis

## Project structure

```
investment-agent/
├── app.py                     # Streamlit entry point
├── config.py                  # Secrets loading and validation
├── models.py                  # AgentMessage, DebateResult dataclasses
├── agents/
│   ├── search_agent.py        # Founder and market gap analysis via Tavily
│   ├── sentiment_agent.py     # Press, community, and momentum analysis via Tavily
│   └── valuation_agent.py     # TAM, comparables, and return potential via Tavily
├── orchestrator/
│   └── orchestrator.py        # Phase 1 sequential analysis pipeline; Phase 2 debate (future)
├── tools/
│   ├── anthropic.py           # Anthropic Claude client with retry
│   └── tavily.py              # Tavily web search client with caching and retry
├── ui/
│   ├── components.py          # Reusable Streamlit components
│   └── styles.py              # Custom CSS
└── tests/
    ├── conftest.py
    ├── agents/
    ├── orchestrator/
    └── tools/
```

## Development

```bash
# Run all tests
pytest

# Run tests for a specific module
pytest tests/agents/
pytest tests/orchestrator/

# Lint and format
ruff check .
ruff format .

# Type check
mypy .
```

## Troubleshooting

**`RuntimeError: Missing ANTHROPIC_API_KEY`** — `.env` is missing or the key is empty. Confirm `.env` exists at the project root with a real value.

**Keys not loading** — Streamlit Cloud uses `st.secrets` instead of `.env`. Locally the app falls back to `.env` automatically via `load_dotenv()`.
