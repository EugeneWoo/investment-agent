# Specification: Search Agent with Founder Analysis and Market Gap Validation

## Goal

Implement the Search Agent as the first agent in the Phase 1 sequential analysis pipeline. The Search Agent discovers pre-Series A AI startups via Tavily web search and Crunchbase API, then performs comprehensive analysis on two critical dimensions: **founder quality** (experience relevance, team complementarity, full-time commitment) and **market gap validation** (product differentiation, competitive landscape, defensibility, bandwagon risk detection). The agent outputs structured scores and qualitative narratives as an `AgentMessage` that feeds into the next agent in the pipeline (Sentiment Agent).

## User Stories

- As an investor, I want the Search Agent to evaluate founder backgrounds so that I can assess whether the team has relevant experience and is committed full-time.
- As an investor, I want the Search Agent to detect LLM wrapper startups so that I can avoid "me-too" products that lack genuine innovation.
- As an investor, I want the Search Agent to assess competitive moats so that I can understand if the startup has defensible differentiation.
- As a system user, I want quantitative scores (0-100) alongside qualitative narratives so that I can quickly compare startups and dive deep when needed.
- As a developer, I want the Search Agent output to be a well-structured `AgentMessage` that the Sentiment Agent and Valuation Agent can build on in Phase 1.
- As a developer, I want competitor research cached across startups in the same sector so that Tavily API costs are controlled.

## Specific Requirements

### Agent Architecture

**Search Agent Class (`agents/search_agent.py`)**
- Follow the standard agent pattern: `class SearchAgent` with `__init__(risk_tolerance: str)` and `run(context: str, risk_tolerance: str) -> AgentMessage`
- `__init__` builds the system prompt with risk tolerance injection (`risk_neutral` | `risk_averse`)
- `run` method orchestrates the full pipeline: startup discovery → founder analysis → market validation → LLM synthesis → structured output
- Use module-level constants for system prompts (e.g., `SEARCH_AGENT_SYSTEM_PROMPT_RISK_NEUTRAL`, `SEARCH_AGENT_SYSTEM_PROMPT_RISK_AVERSE`)
- All LLM calls use `claude-sonnet-4-6` via the `anthropic` SDK

**Context Input**
- `context` is a free-text query describing the company or sector (e.g., "AI-powered medical imaging for radiology" or specific company name "Anthropic")
- The agent should handle both direct company lookups and sector-wide searches
- Risk tolerance modifies analysis depth: `risk_averse` applies stricter scrutiny on commitment signals and bandwagon risks

### Data Source Integration

**Tavily API (`tools/tavily.py`) - PRIMARY DATA SOURCE**
- Implement a Tavily client wrapper with caching layer:
  - `search(query: str, max_results: int = 10) → list[dict]` — standard web search returning `title`, `url`, `content`, `score`
  - Cache results using in-memory dict keyed by query hash
  - Cache should persist across multiple `run()` calls within a single Streamlit session
- Use `tavily-python` SDK with `TAVILY_API_KEY` from settings
- Implement `tenacity` retry logic for transient failures
- Parse responses into `TypedDict` structures (e.g., `TavilySearchResult`)
- Return empty list and log warning on API failures

**Crunchbase API (`tools/crunchbase.py`) - OPTIONAL ENHANCEMENT**
- **Status**: DEPRIORITIZED - not required for MVP
- If implemented later, would provide structured data for:
  - Organization search: `search_organizations(query, funding_stage)` → org list with uuid, name, description, funding
  - People lookup: `get_organization_people(org_uuid)` → founders with names and roles
- For MVP: Use Tavily searches instead:
  - `"{company_name} founders co-founders team"` for founder names
  - `"{company_name} seed funding series A"` for funding stage verification
  - `"{company_name} startup description"` for company overview
- LLM can extract structured data from unstructured Tavily results

### Founder Analysis Pipeline

**1. Founder Data Collection (Tavily-First Approach)**
- Run Tavily search to discover founder names:
  - `"{company_name} founders co-founders"` — get founder names
  - `"{company_name} team leadership"` — backup search
- For each founder discovered, run 2-3 Tavily searches:
  - `"{founder_name} {company_name} LinkedIn"` — find LinkedIn profile
  - `"{founder_name} background experience"` — general background
  - `"{founder_name} current position 2026"` — verify full-time status
- Extract relevant info from search results (LinkedIn URL, previous companies, education, current roles)
- **Optional**: If Crunchbase key is available, use it to validate/enrich founder data
- **Fallback**: If no founder names found, note limitation in output and proceed with available company info

**2. Experience Relevance Analysis**
- For each founder, use Claude LLM to analyze background relevance to the startup's product:
  - Input: founder background text + startup product description
  - Output: qualitative narrative + `relevance_score` (0-100)
  - Risk tolerance adjustment: `risk_averse` penalizes irrelevant prior experience more heavily
- Store results in structured format per founder

**3. Team Complementarity Assessment**
- If multiple founders, use Claude LLM to analyze skill coverage:
  - Input: all founder backgrounds + startup product description
  - Output: qualitative narrative + `complementarity_score` (0-100)
  - Consider domains: technical, business, AI/ML expertise, industry domain knowledge, operations
- If single founder, set `complementarity_score = None` and note limitation in narrative

**4. Full-Time Commitment Verification**
- For each founder, analyze Tavily search results for commitment signals:
  - Red flags: concurrent full-time employment at another company, recent graduation without clear startup focus, minimal recent activity
  - Green flags: left previous job to start this, GitHub commits/blog posts showing active work, LinkedIn status "Founder at [company]"
  - Output: `commitment_level` enum (`"full-time" | "part-time" | "unknown"`) + supporting evidence list
- Risk tolerance adjustment: `risk_averse` treats "unknown" as weaker signal

**5. Founder Quality Score Synthesis**
- Use Claude LLM to synthesize founder analysis into composite score:
  - Input: per-founder relevance scores, complementarity score, commitment levels
  - Output: `founder_quality_score` (0-100) + narrative summary
  - Weighting: relevance 40%, complementarity 30%, commitment 30% (adjustable in system prompt)

### Market Gap Validation Pipeline

**1. Company Overview Collection**
- Use Tavily searches for company information:
  - `"{company_name} startup description product"` — get company overview
  - `"{company_name} funding seed series A"` — verify funding stage
  - `"{company_name} team employees size"` — get company size (if available)
- Extract product description, target market, key features from search results
- **Optional**: If Crunchbase key available, use to enrich structured data (funding amounts, exact employee count)
- **Note**: LLM will extract structured fields from unstructured search results

**2. Bandwagon Risk Detection**
- Use Claude LLM to detect LLM wrapper signals:
  - Input: company description, marketing copy, product information
  - Output: `bandwagon_risk_score` (0-100, where 100 = definite wrapper) + evidence list
  - Red flags to detect:
    - Generic marketing: "AI-powered", "ChatGPT for X", "harnessing LLMs" without specifics
    - Shallow tech: basic chat interface, simple API integration mentioned as key feature
    - No differentiation: product description sounds like OpenAI API wrapper
    - Single-provider dependency: "built on GPT-4" as primary differentiator
    - Lack of proprietary components: no mention of fine-tuning, proprietary data, domain expertise
  - Risk tolerance adjustment: `risk_averse` has lower threshold for flagging wrappers

**3. Competitive Landscape Analysis**
- Use Tavily searches to find competitors:
  - `"{company_name} competitors alternatives"`
  - `"{sector} AI startups"`
  - `"{use_case} software tools"`
- Cache competitor research results by sector (e.g., "medical imaging AI") to reuse across companies
- Use Claude LLM to analyze:
  - Input: competitor search results + company product description
  - Output: structured `competitors` array (name, description, differentiation) + `competitive_positioning` narrative
- If stealth/pre-launch with no public competitors, note limitation explicitly

**4. Defensibility Assessment**
- Use Claude LLM to evaluate moats:
  - Input: product description, competitor analysis, funding info
  - Output: `defensibility_score` (0-100) + narrative covering:
    - Proprietary data access (exclusive partnerships, unique datasets)
    - Network effects (user-generated data improving product)
    - Switching costs (workflow integration, data lock-in)
    - Regulatory barriers (compliance, certifications required)
    - Domain expertise (deep industry knowledge not easily replicated)
  - Risk tolerance adjustment: `risk_averse` requires stronger moat signals

**5. Market Gap Score Synthesis**
- Use Claude LLM to synthesize market analysis:
  - Input: bandwagon risk score, defensibility score, competitive positioning
  - Output: `market_gap_score` (0-100) + narrative summary
  - Weighting: defensibility 40%, bandwagon risk (inverse) 30%, competitive differentiation 30%
  - Higher score = addresses real market gap with defensible position

### Structured Output Format

**AgentMessage Content Structure**
The `content` field of `AgentMessage` should contain JSON-structured data:

```json
{
  "company": {
    "name": "string",
    "description": "string",
    "funding_stage": "string",
    "founded_on": "string | null",
    "employee_count": "int | null",
    "crunchbase_url": "string",
    "source_urls": ["string"]
  },
  "founders": [
    {
      "name": "string",
      "role": "string",
      "linkedin_url": "string | null",
      "background": "string",
      "relevance_score": "int | null",
      "commitment_level": "full-time | part-time | unknown",
      "evidence": ["string"]
    }
  ],
  "founder_analysis": {
    "founder_quality_score": "int",
    "complementarity_score": "int | null",
    "narrative": "string"
  },
  "market_analysis": {
    "market_gap_score": "int",
    "bandwagon_risk_score": "int",
    "defensibility_score": "int",
    "product_description": "string",
    "differentiation": "string",
    "competitors": [
      {
        "name": "string",
        "description": "string",
        "differentiation": "string"
      }
    ],
    "competitive_positioning": "string",
    "defensibility_narrative": "string",
    "bandwagon_evidence": ["string"]
  },
  "search_agent_summary": "string"
}
```

**Field Definitions**
- All scores are integers 0-100, or `null` if unable to determine
- `search_agent_summary` is a concise 2-3 sentence synthesis for the Sentiment and Valuation agents to build on
- All narratives should cite specific evidence (e.g., "Founder X previously led ML at Google" not "founder has good experience")

### System Prompts

**Explicit Prompts Document**
- Full system prompts are defined in `planning/system-prompts.md`
- Include specific founder analysis logic (relevance scoring, complementarity assessment, commitment verification)
- Include LLM-wrapper detection logic (bandwagon risk signals, competitive positioning, defensibility assessment)
- Risk tolerance variants (`SEARCH_AGENT_SYSTEM_PROMPT_RISK_NEUTRAL` and `SEARCH_AGENT_SYSTEM_PROMPT_RISK_AVERSE`) with clear behavioral differences

**Prompt Implementation**
- Module-level constants in `agents/search_agent.py`
- `__init__` selects appropriate prompt based on `risk_tolerance` parameter
- Both prompts include:
  - Founder quality analysis instructions with scoring rubrics
  - Market gap validation instructions with bandwagon detection
  - Structured JSON output format specification
  - Evidence citation requirements
  - Risk tolerance behavioral guidance

**Key Prompt Differences**
| Dimension | Risk Neutral | Risk Averse |
|-----------|--------------|-------------|
| Ambiguity | Benefit of doubt | Treat as risk |
| Commitment unknown | Neutral | Negative signal |
| Wrapper threshold | Multiple red flags | Single red flag |
| Single founder | Note limitation | Major concern |

### Error Handling and Edge Cases

**API Failures**
- All Crunchbase/Tavily calls wrapped in try/except
- On failure, log error with context and return empty list
- Agent should still produce partial results with caveats (e.g., "Founder analysis limited: Crunchbase API timeout")

**Missing Data Scenarios**
- Single-founder teams: Set `complementarity_score = null`, note limitation in narrative
- Stealth startups: Note limited public information, set defensibility score conservatively
- Pre-launch products: Note lack of competitor validation, set `market_gap_score` with uncertainty caveat
- No Crunchbase match: Fall back to Tavily-only search, note data limitations
- No LinkedIn profiles: Use other sources (personal sites, interviews), note reduced confidence

**Scoring with Uncertainty**
- Use `null` for scores when data is completely unavailable
- In narratives, explicitly state uncertainty (e.g., "Unable to verify full-time commitment: no recent LinkedIn activity found")
- Search Agent Summary should flag high-uncertainty analyses

**LLM Errors**
- Catch `anthropic.APIError`, `anthropic.RateLimitError`, `anthropic.APITimeoutError`
- Log error details, re-raise with context message
- Orchestrator should handle Search Agent failures gracefully (preserve other agents' work)

### Caching and Context Management

**Tavily Result Cache**
- Use in-memory dict cache (class-level, not `@lru_cache`) for better control
- Cache key: hash of query string
- Cache persists during single Streamlit session
- Benefits: Competitor research reused across startups in same sector, founder lookups deduplicated
- Sector-based caching: `f"sector:{sector_name}"` key for competitor searches

**Session State and Interim Storage**
- Tool-level caching: In-memory cache within TavilyClient/CrunchbaseClient (per session)
- Pipeline-level state: Local variables within `SearchAgent.run()` (cleared after return)
- Cross-agent persistence: `st.session_state["agent_messages"]`, `["debate_result"]`, `["run_config"]`
- **Important**: Browser refresh wipes all session state - no TTL, ephemeral by design
- See `planning/context-management-strategy.md` for detailed architecture and persistence options

**Cache Invalidation**
- No time-based invalidation needed (session-scoped)
- Cache clears automatically on browser refresh or tab close
- Optional: add `clear_cache()` method for testing

**Cache Logging**
- Log cache hits at DEBUG level to monitor effectiveness
- Include cache stats in agent output for transparency

### Testing Requirements

**Unit Tests (`tests/tools/test_crunchbase.py`, `tests/tools/test_tavily.py`)**
- Test successful API responses with mocked data
- Test rate limit handling with retry assertions
- Test error responses (404, 500, timeout) return empty list + log
- Test parsing logic for response TypedDicts
- Test Tavily cache behavior (miss, hit, key hash)

**Unit Tests (`tests/agents/test_search_agent.py`)**
- Test `run()` method with mocked Crunchbase/Tavily/Anthropic APIs
- Test founder analysis logic with mock founder data
- Test market gap validation with mock competitor data
- Test single-founder edge case (complementarity = None)
- Test stealth startup handling (limited data caveats)
- Test risk tolerance prompt injection (verify different prompts used)
- Test error handling: Crunchbase failure produces partial results

**Integration Tests**
- Test end-to-end agent flow with all APIs mocked
- Verify JSON structure matches expected schema
- Verify all required fields present or null (not missing)
- Verify scores in valid 0-100 range

**Fixtures (`tests/conftest.py`)**
- Add `mock_crunchbase_response` fixture with sample org/people data
- Add `mock_tavily_response` fixture with sample search results
- Add `mock_anthropic_response` fixture with sample founder analysis

### Logging and Observability

**Log Levels**
- DEBUG: Full LLM prompts and responses, Tavily cache hits
- INFO: Agent start/completion, scores produced, API call counts
- WARNING: API failures, missing data, uncertain results
- ERROR: LLM errors, configuration errors

**Log Messages**
- Include context: company name, risk tolerance, search queries
- Include counts: number of founders, competitors searched, API calls made
- Include timing: duration of each analysis phase (optional but helpful)

## Visual Design

No visual mockups provided. The Search Agent is backend-only; UI will be implemented separately in Streamlit dashboard spec.

## Existing Code to Leverage

**Current State:**
- `models.py` defines `AgentMessage` dataclass with `agent_name`, `content`, `role` fields
- `config.py` provides `settings` singleton with all API keys
- `agents/` and `tools/` directories exist but are empty (greenfield implementation)

**Patterns to Follow:**
- Agent class pattern: `__init__(risk_tolerance)` + `run(context, risk_tolerance) -> AgentMessage`
- Risk tolerance injection into system prompts at instantiation
- Dataclass usage for structured data (`AgentMessage`, `DebateResult`)
- Error handling with specific exception types and logging
- TypedDict for API response shapes

**Dependencies:**
- `anthropic` SDK (already in `pyproject.toml`)
- `tavily-python` (already in `pyproject.toml`)
- `tenacity` for retry logic (add to dependencies if not present)
- `functools` for caching (stdlib)

## Out of Scope

- Founder equity distribution, governance structure, board composition analysis
- Founder social media sentiment analysis (deferred to Sentiment Agent)
- Founder network quality (VC connections, alumni prestige, previous exits)
- TAM/SAM/SOM market sizing calculations (too complex for this phase)
- Financial projections or revenue modeling (Valuation Agent responsibility)
- Deep technical architecture evaluation (code quality assessment)
- User experience or UI assessment (subjective, deferred to future)
- Streamlit UI implementation (separate spec)
- Orchestrator Phase 1 pipeline wiring (separate spec)
- Orchestrator Phase 2 debate logic (future spec, deprioritized)
- Sentiment Agent and Valuation Agent implementations (separate specs)
- Persistent cache across Streamlit sessions (session-scoped only)
- Crunchbase advanced fields (investors, acquisitions, IPO status) — basic org data only

## Implementation Notes

**Order of Operations (Task Suggested):**
1. Implement Crunchbase and Tavily tool wrappers first (test in isolation)
2. Implement basic Search Agent skeleton with system prompts
3. Implement founder analysis pipeline (founders → relevance → complementarity → commitment)
4. Implement market gap validation pipeline (bandwagon → competitors → defensibility)
5. Integrate both pipelines with final LLM synthesis
6. Add comprehensive error handling and edge case handling
7. Write unit tests for each component
8. Integration test with full mocked pipeline

**Dependencies to Add:**
- `tenacity` for retry logic (if not already in `pyproject.toml`)

**Type Hints:**
- All function signatures must have complete type hints
- Use `TypedDict` for structured API responses
- Use `| None` for optional fields (Python 3.11+ syntax)

**Risk Tolerance Impact:**
- `risk_neutral`: Balanced scoring, optimistic interpretation of ambiguity
- `risk_averse`: Stricter scoring, penalizes ambiguity, requires stronger evidence
- System prompts should be significantly different, not just minor tweaks
