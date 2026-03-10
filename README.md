# Investment Agents

Multi-agent AI system for analyzing Seed-to-Series B AI startups. Both modes are available in a single unified app (`app.py`), selectable via a radio toggle at the top.

## How it works

**LLM as CIO** (Judge mode): Three agents (Search, Sentiment, Valuation) each independently research the startup with no shared context. A fourth **Judge** LLM reads all three reports and issues the final GO / NOGO verdict.

**Agentic Round-Robin Debate** (Debate mode): Same three agents run Phase 1, then debate in round-robin (Search → Sentiment → Valuation, repeat) until all agree on GO or NOGO. If `max_rounds` is exceeded without consensus, majority vote across all rounds determines the verdict (ties default to NOGO).

## Quick start

**Live app:** [https://investment-agents.streamlit.app/](https://investment-agents.streamlit.app/)

**Run locally:**

```bash
git clone https://github.com/EugeneWoo/investment-agent.git
cd investment-agent
uv sync
# Add API keys to .streamlit/secrets.toml (see Setup below)
streamlit run app.py
# Opens at http://localhost:8501
```

---

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
# Unified app (both modes)
streamlit run app.py

# Debate mode standalone (optional)
streamlit run adversarial_debate/app_debate.py
```

Opens at [http://localhost:8501](http://localhost:8501).

## Usage

1. Select **LLM as CIO** or **Agentic Round-Robin Debate** at the top
2. Select **Risk Tolerance** in the sidebar — Balanced (Risk Neutral) or Conservative (Risk Averse)
3. *(Debate mode only)* Set **Max debate rounds** (1–5, default 3)
4. Enter a company name or description (e.g. `Anthropic`, `Harvey AI`, or `AI startup building medical imaging tools`)
5. Click **Analyze**
6. View the verdict and per-agent analysis
7. Download the full report as Markdown

## Cost estimates (per analysis)

| API | Approx. cost | Notes |
|-----|--------------|-------|
| Anthropic Claude | $0.10 – $0.50 | 3–5 LLM calls (Judge); up to 3×rounds more in Debate mode |
| Tavily Search | $0.01 – $0.05 | ~10–15 searches, cached for reuse |
| Crunchbase | optional | Not required for MVP |

**Total (MVP)**: ~$0.15 – $0.60 per analysis (Judge); higher in Debate mode depending on rounds

## Project structure

```
investment-agent/
├── app.py                     # Unified Streamlit entry point (LLM as CIO + Agentic Round-Robin Debate)
├── config.py                  # Secrets loading and validation
├── models.py                  # AgentMessage, DebateResult dataclasses
├── agents/
│   ├── search_agent.py        # Founder and market gap analysis via Tavily
│   ├── sentiment_agent.py     # Press, community, and momentum analysis via Tavily
│   └── valuation_agent.py     # TAM, comparables, and return potential via Tavily
├── orchestrator/
│   └── orchestrator.py        # 3 independent agents → Judge verdict; eligibility check
├── tools/
│   ├── anthropic.py           # Anthropic Claude client with retry
│   └── tavily.py              # Tavily web search client with caching and retry
├── ui/
│   ├── components.py          # Reusable Streamlit components
│   └── styles.py              # Custom CSS
├── tests/
│   ├── conftest.py
│   ├── agents/
│   ├── orchestrator/
│   └── tools/
└── adversarial_debate/        # Debate mode (self-contained module)
    ├── app_debate.py          # Debate mode standalone Streamlit entry point
    ├── models.py              # DebatePosition, DebateRound dataclasses
    ├── orchestrator.py        # Phase 1 → round-robin debate → consensus/majority vote
    ├── agents/                # Debate-capable wrappers around base agents
    └── tests/
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

## Eligibility check

Before running any agent analysis, the orchestrator runs a pre-screening check using two Tavily searches and an LLM judge. A company is blocked if any criterion scores above 80:

Two searches are used: (1) Crunchbase-domain search for authoritative funding/product data; (2) broad news search targeting Series C/D/E and IPO keywords — necessary because Crunchbase profile pages are paywalled and Tavily cannot scrape them directly.

| Criterion | Blocks if | Examples |
|-----------|-----------|---------|
| Publicly traded | `listed_confidence > 80` | C3.ai, Palantir, Salesforce |
| Not AI-native | `not_ai_native_confidence > 80` | JPMorgan Chase, Walmart |
| Series C or later | `late_stage_confidence > 80` | Replit, Databricks, Scale AI |

**What counts as confirmed public listing:** active ticker symbol, current stock price, completed IPO.

**What counts as confirmed late stage:** Crunchbase `last_funding_type` of Series C/D/E or later; confirmed round designation in news. "Venture - Series Unknown" is treated as inconclusive and passes through.

**What does NOT trigger a block:** IPO speculation, funding round announcements, valuation estimates, or total funding amount alone.

## Troubleshooting

**`RuntimeError: Missing ANTHROPIC_API_KEY`** — `.env` is missing or the key is empty. Confirm `.env` exists at the project root with a real value.

**Keys not loading** — Streamlit Cloud uses `st.secrets` instead of `.env`. Locally the app falls back to `.env` automatically via `load_dotenv()`.
