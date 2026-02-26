# Product Mission

## Pitch

Investment Agent is a multi-agent AI debate system that helps angel investors, early-stage VCs,
and investment analysts evaluate pre-Series A AI startup opportunities by providing structured,
multi-perspective analysis — combining automated discovery, sentiment signals, valuation estimates,
and a debate-driven GO/NOGO recommendation.

---

## Users

### Primary Customers

- **Angel investors** evaluating early-stage AI companies before committing capital
- **Early-stage VCs** running initial due diligence screens on pre-Series A deals
- **Investment analysts** who want AI-assisted research to augment their own judgment
- **Retail investors** exploring startup and early-stage AI investment opportunities

### User Personas

**Dana — Angel Investor**
Dana reviews 20–30 startup pitches per month. She needs a fast, structured way to separate
signal from noise before spending time on deeper due diligence. She trusts data-backed
perspectives but wants to see multiple viewpoints, not just a single AI verdict.

**Marcus — Early-Stage VC Analyst**
Marcus is responsible for sourcing and screening deals at a seed-stage fund. He spends hours
manually aggregating news, social sentiment, and comparable funding data. He wants tooling that
compresses hours of research into a structured report he can present to partners.

**Priya — Retail Investor / Startup Enthusiast**
Priya follows AI startup news closely and occasionally invests through syndicates. She lacks
access to institutional research and wants a public, easy-to-use tool that gives her professional-
grade analysis without requiring a Bloomberg terminal.

---

## The Problem

### Information Overload in Early-Stage Startup Evaluation

Pre-Series A startup research is fragmented across news articles, fundraising databases, social
media, and founder blogs. Analysts must manually synthesize dozens of disparate sources to form
an investment view — a process that takes hours per company and is highly prone to confirmation
bias. Research shows that individual analysts miss 40–60% of relevant signals when working
without structured frameworks.

**Our Solution:** Three specialized AI agents independently analyze a company from different
angles (discovery, sentiment, valuation), then debate their findings in a structured round-robin
until they reach a GO/NOGO consensus — surfacing disagreements that a single model or analyst
would suppress.

### Bias and Blind Spots in Solo Analysis

A single analyst — human or AI — tends to anchor on the first signal encountered and discount
contradictory evidence. This is especially dangerous in early-stage investing, where the
available data is sparse and ambiguous.

**Our Solution:** The debate mode forces each agent to argue its position, challenge others, and
update its view based on counterarguments — mimicking the dynamics of an investment committee
and reducing single-point-of-failure bias.

### Slow, Expensive Due Diligence Pipelines

Traditional due diligence on a single startup can take 1–2 weeks of analyst time. For angel
investors and retail investors without large research teams, this cost is prohibitive.

**Our Solution:** Automated discovery, sentiment summarization, and comparable valuation are
delivered in minutes via a public Streamlit dashboard — democratizing access to structured
investment analysis.

---

## Differentiators

### Multi-Agent Debate with Structured Consensus Logic

Unlike single-model AI research tools (e.g., Perplexity, ChatGPT research mode), Investment
Agent runs a true multi-agent debate where three specialized agents argue, challenge, and
converge on a GO/NOGO recommendation. If consensus cannot be reached within a maximum number
of rounds, the system explicitly surfaces NO_CONSENSUS — making uncertainty visible rather
than hiding it behind a false confidence score.

### Reflection-Enhanced Sentiment Across Multiple Social Channels

Unlike tools that pull a single news feed, the Sentiment Agent applies reflection-enhanced
LLM summarization over fundraising news, product launches, Reddit, and Twitter/X — iteratively
refining its own summary before committing to a final signal. This reduces hallucination and
increases coverage of weak but important signals.

### Computational Valuation via Comparable Company Analysis

Unlike qualitative-only AI research tools, the Valuation Agent provides a quantitative estimate
of annualized return and volatility using comparable company data — grounding the debate in
numbers, not just narrative.

### Risk Tolerance Personalization

Users select their risk profile (risk_neutral or risk_averse) before analysis begins. This
preference is injected directly into each agent's system prompt, ensuring that the entire
debate — from framing to final recommendation — is calibrated to the investor's actual
risk appetite.

### Fully Public, No-Login Dashboard

Investment Agent is hosted on Streamlit Community Cloud with a shareable public URL. No
account creation, no paywall for basic analysis — making it accessible to retail investors
and analysts who want to demo or share results with partners.

---

## Key Features

### Core Features

- **Search Agent** — Discovers pre-Series A and early-stage AI startup investment ideas by
  querying Tavily web search and the Crunchbase API. Users select their preferred data sources
  from a checkbox list (Crunchbase, TechCrunch, Product Hunt) with an "Others" free-text
  option for custom sources. Returns a structured list of candidate companies with basic
  firmographic data.

- **Sentiment Agent** — Aggregates fundraising news, product launch announcements, Reddit
  discussions, and Twitter/X posts for a given company. Applies reflection-enhanced LLM
  summarization to produce a calibrated sentiment signal (positive / neutral / negative)
  with key supporting evidence.

- **Valuation Agent** — Estimates annualized return potential and volatility using a
  comparable company analysis framework. Produces a quantitative score alongside qualitative
  commentary on key value drivers and risk factors.

- **Two-Phase Pipeline** — Phase 1 runs each agent once in sequence (Search → Sentiment → Valuation) to produce independent analyses. Phase 2 immediately follows with a round-robin debate where agents challenge each other's positions until GO/NOGO consensus is reached or a maximum round limit is exceeded (resulting in NO_CONSENSUS).

- **Risk Tolerance Selection** — Users choose between `risk_neutral` and `risk_averse` before
  initiating analysis. This setting is injected into every agent's system prompt to ensure
  recommendations are aligned with the user's investment philosophy.

### Advanced Features

- **Consolidated Investment Report** — A structured markdown report generated at the end of
  each session covering company overview, sentiment summary, valuation estimate, debate
  transcript highlights, and the final GO/NOGO (or NO_CONSENSUS) outcome.

- **Public Streamlit Dashboard** — A clean, interactive UI hosted on Streamlit Community Cloud
  with a shareable public URL. Enables third parties (LPs, co-investors, colleagues) to view
  and reproduce analyses without any setup.

- **Transparent Debate Transcript** — Users can read the full turn-by-turn agent debate,
  understanding exactly why each agent argued for or against investment — building trust in
  the recommendation through explainability.
