# Context Management and Interim Storage Strategy

## Overview

This document clarifies how interim outputs from tool calls and agent pipelines are stored and managed in the multi-agent investment debate system, with specific focus on the Search Agent's dual-pipeline architecture (Founder Analysis + Market Gap Validation).

## Architecture Principles

1. **Session-scoped statelessness**: All agents are stateless between `run()` calls; context is passed explicitly
2. **Streamlit session state for UI persistence**: `st.session_state` stores results for the current user's browser session
3. **No persistent storage**: No database; all data is ephemeral within a session
4. **API result caching**: Cache external API calls to reduce cost and improve performance

## Storage Layers

### Layer 1: Tool-Level Caching (In-Memory)

**Purpose**: Avoid redundant external API calls within a single agent run

**Implementation**:
```python
# tools/tavily.py
from functools import lru_cache

class TavilyClient:
    def __init__(self, api_key: str):
        self.client = Client(api_key=api_key)
        self._cache: dict[str, list[dict]] = {}

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        cache_key = self._make_cache_key(query, max_results)
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self.client.search(query, max_results=max_results)
        self._cache[cache_key] = result
        return result
```

**Cache scope**:
- Persists across multiple `run()` calls within a single Streamlit session
- Shared across all agents (Search, Sentiment, Valuation) that use Tavily
- Useful for: competitor research by sector (reuse across startups in same sector)

**What gets cached**:
- Tavily search results by query hash
- Crunchbase organization lookups by UUID
- Reddit/Twitter search results by query

**Cache invalidation**:
- Automatic on session refresh (user closes browser tab)
- Manual via `clear_cache()` method for testing

### Layer 2: Pipeline-Level State (Within Agent Run)

**Purpose**: Pass interim outputs between pipeline stages within a single agent run

**Implementation**: Use local variables and intermediate data structures
```python
# agents/search_agent.py
def run(self, context: str, risk_tolerance: str) -> AgentMessage:
    # Stage 1: Discover company
    company_data = self._discover_company(context)

    # Stage 2: Founder analysis pipeline
    founder_data = self._collect_founder_data(company_data)
    founder_analysis = self._analyze_founders(founder_data, risk_tolerance)

    # Stage 3: Market gap validation pipeline
    market_data = self._collect_market_data(company_data)
    market_analysis = self._analyze_market_gap(market_data, risk_tolerance)

    # Stage 4: Synthesize
    final_output = self._synthesize_output(
        company_data, founder_analysis, market_analysis
    )

    return AgentMessage(
        agent_name="Search Agent",
        content=json.dumps(final_output),
        role="analyst"
    )
```

**What flows through pipeline state**:
- Raw tool outputs (Crunchbase responses, Tavily search results)
- LLM intermediate results (per-founder relevance scores, competitor lists)
- Partially assembled structures (founder_profiles array, competitors array)

**Storage mechanism**: Python local variables, method arguments, return values
- **NOT** stored in `st.session_state` during pipeline execution
- Cleared after `run()` returns (agent is stateless)

### Layer 3: Session State for UI and Debate (Cross-Agent)

**Purpose**: Store results that need to persist across the two-phase debate pipeline

**Implementation**: `st.session_state` keys defined in standards

```python
# In Streamlit app or orchestrator
import streamlit as st

# After Phase 1 (all agents speak once)
st.session_state["agent_messages"] = [
    search_message,
    sentiment_message,
    valuation_message
]

# After Phase 2 (debate until consensus)
st.session_state["debate_result"] = DebateResult(
    verdict="GO",
    rounds=4,
    messages=all_messages,
    consensus_reached=True
)

# Run configuration for reproducibility
st.session_state["run_config"] = {
    "company": "Anthropic",
    "risk_tolerance": "risk_neutral",
    "mode": "debate"
}
```

**Session state keys**:
| Key | Type | Purpose |
|-----|------|---------|
| `agent_messages` | `list[AgentMessage]` | All messages from Phase 1 + Phase 2 debate |
| `debate_result` | `DebateResult` | Final GO/NOGO verdict with metadata |
| `run_config` | `dict` | Input parameters for current run |

**When session state is cleared**:
- User starts a new company analysis
- User explicitly clicks "Clear" / "New Debate" button
- Browser session ends (automatic)

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Streamlit Session                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    st.session_state                           │  │
│  │  - agent_messages: list[AgentMessage]                        │  │
│  │  - debate_result: DebateResult                               │  │
│  │  - run_config: dict                                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Stores final results
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                     Orchestrator (Two-Phase Pipeline)               │
│  Phase 1: Search Agent → Sentiment Agent → Valuation Agent          │
│  Phase 2: Round-robin debate until consensus                        │
└─────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Returns AgentMessage
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                    Search Agent Internal Pipeline                    │
│  ┌─────────────┐    ┌─────────────────┐    ┌────────────────────┐  │
│  │ Tool Layer  │───▶│ Pipeline State  │───▶│   LLM Synthesis    │  │
│  │             │    │ (local vars)    │    │                    │  │
│  │ - Tavily    │    │ - company_data  │    │ - Founder scores   │  │
│  │ - Crunchbase│    │ - founder_data  │    │ - Market scores    │  │
│  │ (cached)    │    │ - market_data   │    │ - Final JSON       │  │
│  └─────────────┘    └─────────────────┘    └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Search Agent: Specific Interim State Management

The Search Agent has **two parallel analysis pipelines** that converge at synthesis:

### Founder Analysis Pipeline Interim State
```python
@dataclass
class FounderAnalysisState:
    company_data: dict  # From Crunchbase
    founder_profiles: list[dict]  # Raw data from Tavily searches
    relevance_scores: dict[str, int]  # Per-founder LLM outputs
    complementarity_score: int | None  # LLM output
    commitment_levels: dict[str, str]  # Per-founder analysis
    founder_quality_score: int  # Final composite
```

### Market Gap Validation Pipeline Interim State
```python
@dataclass
class MarketAnalysisState:
    company_data: dict  # Shared with founder pipeline
    product_description: str  # From Tavily
    bandwagon_risk_score: int  # LLM output
    competitors: list[dict]  # From Tavily + LLM extraction
    defensibility_score: int  # LLM output
    market_gap_score: int  # Final composite
```

### Final Synthesis
Both pipelines' interim states feed into the final JSON output embedded in `AgentMessage.content`.

## Why Not Use Streamlit Session State for Interim Pipeline Outputs?

### Problems with `st.session_state` for pipeline internals:

1. **Breaks agent statelessness**: Agents should be reusable with different contexts
2. **Unnecessary persistence**: Pipeline intermediates don't need to survive past the `run()` call
3. **Complex key management**: Would need namespaced keys like `search_agent_founder_step_2_temp`
4. **Memory bloat**: Storing raw LLM responses and tool outputs unnecessarily

### When to use `st.session_state`:

✅ **Use** for:
- Final agent outputs that Phase 2 debate needs to reference
- Debate results for UI display and report export
- Run configuration for "Analyze Again" functionality
- User preferences (risk tolerance, mode selection)

❌ **Don't use** for:
- Pipeline intermediate variables
- Tool wrapper internal caches
- LLM request/response pairs (unless debugging)
- Temporary data structures within a single `run()` call

## Caching Strategy for Cost Optimization

### Tavily Search Caching by Sector

For competitor research, cache by sector to reuse across startups:

```python
# tools/tavily.py
class TavilyClient:
    def __init__(self):
        self._cache: dict[str, list[dict]] = {}

    def search_sector_competitors(self, sector: str) -> list[dict]:
        """Cached competitor search by sector for reuse"""
        cache_key = f"sector_competitors:{sector.lower()}"
        if cache_key not in self._cache:
            self._cache[cache_key] = self.search(
                f"{sector} AI startups competitors alternatives",
                max_results=15
            )
        return self._cache[cache_key]
```

**Example**: When analyzing three different medical imaging AI startups, the competitor search for "medical imaging AI" runs once and is reused.

### Cache Warming Strategy

```python
# Optional: Pre-warm cache when user selects sector
def warm_sector_cache(sector: str):
    tavily = TavilyClient(settings.TAVILY_API_KEY)
    tavily.search_sector_competitors(sector)
    # Also cache common patterns
    tavily.search(f"{sector} market trends 2026")
```

## Testing and Debugging

### Accessing Interim State for Testing

During development, you may want to inspect pipeline internals:

```python
# In tests, expose interim state via optional parameter
def run(
    self,
    context: str,
    risk_tolerance: str,
    debug: bool = False  # For testing
) -> AgentMessage | tuple[AgentMessage, FounderAnalysisState, MarketAnalysisState]:

    founder_state = FounderAnalysisState(...)
    market_state = MarketAnalysisState(...)

    result = self._synthesize(founder_state, market_state)

    if debug:
        return result, founder_state, market_state
    return result
```

### Production Logging

Log key interim values without storing full state:

```python
import logging

logger = logging.getLogger(__name__)

# In pipeline
logger.info(
    f"Founder analysis complete: "
    f"quality_score={founder_quality_score}, "
    f"num_founders={len(founder_profiles)}, "
    f"complementarity_score={complementarity_score}"
)
```

## Session Persistence Limitations

### Current Behavior (Streamlit Default)

| Event | What Happens | Data Lost |
|-------|--------------|-----------|
| Browser refresh/reload | `st.session_state` is wiped | All agent outputs, debate results, run config |
| Close browser tab | `st.session_state` is wiped | All data |
| Browser back button | May trigger re-run | Partial data loss |
| New tab to same URL | New session | No data carried over |
| 1 hour idle | No automatic TTL | Session persists until browser close |

**There is NO built-in TTL**. Streamlit sessions persist until:
1. User closes the browser tab
2. User refreshes the page
3. Server restarts (Streamlit Community Cloud may restart containers)

### Implications

**Problem for investment workflow**:
- User spends 10 minutes running a full debate on "Anthropic"
- User accidentally refreshes browser
- **Entire analysis is lost** - must re-run all agents (costing more API calls)

**Problem for research continuity**:
- User analyzes 3 startups in a session
- User wants to compare them side-by-side next day
- **Not possible** - previous day's results are gone

### Potential Solutions (Future Enhancements)

If session persistence becomes a requirement, here are options:

#### Option 1: Client-Side Persistence (Simplest)
```python
# Export debate results as JSON file
import streamlit as st

if st.session_state.get("debate_result"):
    st.download_button(
        "Save Analysis",
        data=json.dumps(st.session_state["debate_result"]),
        file_name=f"analysis_{company_name}_{timestamp}.json",
        mime="application/json"
    )

# Load saved analysis
uploaded = st.file_uploader("Load Previous Analysis", type=["json"])
if uploaded:
    st.session_state["debate_result"] = json.load(uploaded)
```

**Pros**: Simple, no backend, user controls data
**Cons**: Manual save/load required, not seamless

#### Option 2: Streamlit File-Based Session State (Medium Complexity)
```python
import hashlib
import json
from pathlib import Path

# Save session state to disk
def save_session(company: str):
    session_id = hashlib.md5(company.encode()).hexdigest()[:8]
    path = Path(f".sessions/{session_id}.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(dict(st.session_state)))

# Load session state from disk
def load_session(company: str) -> bool:
    session_id = hashlib.md5(company.encode()).hexdigest()[:8]
    path = Path(f".sessions/{session_id}.json")
    if path.exists():
        data = json.loads(path.read_text())
        for key, value in data.items():
            st.session_state[key] = value
        return True
    return False
```

**Add to `.gitignore`**: `.sessions/`

**Pros**: Automatic persistence across refreshes, TTL can be added
**Cons**: Only works on single server, doesn't scale to multi-user deployment

#### Option 3: Redis/Database Backing (Full Solution)
```python
# Requires Streamlit Enterprise or custom deployment
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def save_to_redis(session_id: str, ttl_seconds: int = 3600):
    redis_client.setex(
        f"session:{session_id}",
        ttl_seconds,
        json.dumps(dict(st.session_state))
    )

def load_from_redis(session_id: str):
    data = redis_client.get(f"session:{session_id}")
    if data:
        for key, value in json.loads(data).items():
            st.session_state[key] = value
```

**Pros**: TTL support, scales to multi-user, survives server restarts
**Cons**: Requires infrastructure, adds cost/complexity

### Recommended Approach for MVP

**Accept Streamlit's default ephemeral behavior** and:
1. Provide prominent "Export Report" button (markdown download already planned)
2. Show warning before user navigates away: "Your analysis will be lost if you refresh - export first!"
3. Consider adding file-based session storage (Option 2) in V2 if users report pain

**Rationale**: This is a pre-Series A investment tool, not a production SaaS. Users are likely running individual analyses and exporting results, not maintaining persistent dashboards.

## Summary

| Concern | Solution |
|---------|----------|
| API call deduplication | Tool-level in-memory cache (per session) |
| Pipeline data flow | Local variables and return values |
| Cross-agent communication | `AgentMessage` passed via orchestrator |
| UI persistence | `st.session_state` for final results |
| Session refresh handling | **Data lost** - ephemeral by design (export recommended) |
| TTL | **None** - session persists until browser close or refresh |
| Cost optimization | Sector-based caching for competitor research |
| Debugging | Optional debug mode to expose interim state |
| Long-term storage | None by design (ephemeral sessions) |
| Post-MVP enhancement | File-based session storage or Redis backing |

This layered approach keeps agents stateless and testable while providing efficient caching for expensive operations and proper persistence for UI requirements. The ephemeral nature is a conscious trade-off: simplicity over persistence.
