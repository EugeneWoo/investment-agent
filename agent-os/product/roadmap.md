# Product Roadmap

Items are ordered by technical dependency — foundational infrastructure first, UI and
deployment last. Each item represents an end-to-end testable feature slice.

Effort scale: XS = 1 day, S = 2–3 days, M = 1 week, L = 2 weeks, XL = 3+ weeks

---

1. [ ] **Project Scaffold and Secrets Management** — Set up the Python 3.11+ project
   with `pyproject.toml`, `uv` package management, `ruff`/`mypy` linting, `pytest`
   test structure, and `.streamlit/secrets.toml` local secrets wiring. Verify all API
   keys (Anthropic, Tavily, Crunchbase, Reddit, Twitter/X) are loadable and validated
   at startup. `XS`

2. [ ] **Search Agent — Startup Discovery** — Implement the Search Agent using Tavily
   web search and the Crunchbase API to discover pre-Series A AI startup candidates
   given a user-supplied query or sector. Users select their preferred data sources
   from a checkbox list (Crunchbase, TechCrunch, Product Hunt) with an "Others" free-text
   option for custom sources. Returns a structured list of companies with name, description,
   funding stage, and source URLs. `S`

3. [ ] **Social and News Data Ingestion** — Build data-fetching modules for Reddit
   (via PRAW) and Twitter/X (via tweepy), plus a news/fundraising fetcher using
   Tavily. Each module returns normalized, timestamped text records for a given
   company name. `S`

4. [ ] **Sentiment Agent with Reflection-Enhanced Summarization** — Implement the
   Sentiment Agent that consumes ingested news, Reddit, and Twitter/X data, applies
   iterative LLM reflection (using claude-sonnet-4-6) to refine its summary, and
   outputs a calibrated sentiment signal (positive / neutral / negative) with
   supporting evidence citations. `M`

5. [ ] **Valuation Agent — Comparable Company Analysis** — Implement the Valuation
   Agent that fetches comparable company funding and growth data, computes an estimated
   annualized return and volatility score, and produces a structured valuation output
   with key assumptions and risk flags. `M`

6. [ ] **Risk Tolerance System Prompt Injection** — Add user-selectable risk tolerance
   (`risk_neutral` / `risk_averse`) that is injected into the system prompt of every
   agent before any analysis begins. Verify that agent outputs shift meaningfully
   between the two modes on the same input company. `S`

7. [ ] **Multi-Agent Orchestrator — Analysis + Debate Pipeline** — Build the custom Python orchestrator that runs a single unified pipeline: Phase 1 runs each agent once in sequence (Search → Sentiment → Valuation) to produce independent analyses, then Phase 2 runs a round-robin debate loop where agents challenge each other's positions until GO/NOGO consensus is reached or a maximum-rounds exit condition surfaces NO_CONSENSUS. `M`

9. [ ] **Consolidated Investment Report Generation** — Implement a report renderer that
   takes the full agent outputs and debate transcript and produces a structured markdown
   report covering company overview, sentiment summary, valuation estimate, debate
   highlights, and the final GO/NOGO or NO_CONSENSUS outcome. `S`

10. [ ] **Streamlit Dashboard UI** — Build the Streamlit frontend with company/topic text input, search source selector (checkboxes: Crunchbase, TechCrunch, Product Hunt, Others + custom text input), risk tolerance selector, Run button, live agent output streaming per phase, debate transcript viewer, and rendered final report. `M`

11. [ ] **Streamlit Community Cloud Deployment** — Configure the public GitHub repository,
    set all secrets in the Streamlit Cloud secrets manager, and deploy the app to
    share.streamlit.io with a stable public URL. Verify end-to-end functionality on
    the live deployment. `S`

12. [ ] **End-to-End pytest Suite** — Write pytest tests covering agent unit behavior
    (mocked API responses), orchestrator collaboration and debate logic (including
    NO_CONSENSUS path), report generation output structure, and a smoke test against
    the live Streamlit app. `M`
