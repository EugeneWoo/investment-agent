# Tasks: Search Agent with Founder Analysis and Market Gap Validation

## Overview

Total task groups: 8
Total tasks: 40

The Search Agent is one of three **independent analysts** in the Phase 1 pipeline. It runs once and produces a structured `AgentMessage`. The agents do not share context — all three outputs are fed to a Judge LLM which issues the final GO/NOGO verdict. Phase 2 debate is out of scope here.

**Group dependencies:**
- Group 0 (Environment Setup) — must be completed first; required before any development
- Group 1 (Tool Wrappers - Tavily) — depends on Group 0 (requires API keys)
- Group 2 (Tool Wrappers - Crunchbase, optional) — depends on Group 0; skip for MVP
- Group 3 (Search Agent Skeleton) — depends on Group 1 (agent uses Tavily as primary source)
- Group 4 (Founder Analysis Pipeline) — depends on Group 3 (builds on agent skeleton)
- Group 5 (Market Gap Validation Pipeline) — depends on Group 3 (builds on agent skeleton)
- Group 6 (Integration and Error Handling) — depends on Groups 4-5 (requires both pipelines)
- Group 7 (Testing) — depends on Group 6 (tests validate complete implementation)

---

## Group 0: Environment Setup

**Goal:** Configure local development environment with API keys and verify configuration loading works correctly.

**Acceptance criteria:**
- `.env` file exists at project root with **required** API keys populated (not placeholders)
- `python -c "from config import settings; print(settings.ANTHROPIC_API_KEY[:10])"` works without error
- Required keys validate as non-empty strings: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`
- Optional keys can be empty: `CRUNCHBASE_API_KEY`, `REDDIT_*`, `TWITTER_*`
- `uv run pytest tests/test_config.py` passes (existing tests from scaffold spec)

### Tasks

**0.1** Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

**0.2** Populate `.env` with actual API keys:
   - **Required**: `ANTHROPIC_API_KEY` — Get from https://console.anthropic.com/
   - **Required**: `TAVILY_API_KEY` — Get from https://tavily.com/
   - **Optional**: `CRUNCHBASE_API_KEY` — Skip for MVP, can add later for enrichment
   - **Optional**: `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` — For Sentiment Agent (later)
   - **Optional**: `TWITTER_BEARER_TOKEN` — For Sentiment Agent (later)

**0.3** Verify configuration loads correctly:
   ```bash
   uv run python -c "from config import settings; print('✓ Config loaded'); print(f'  Anthropic: {settings.ANTHROPIC_API_KEY[:10]}...'); print(f'  Tavily: {settings.TAVILY_API_KEY[:10]}...')"
   ```

**0.4** Run existing config tests to verify:
   ```bash
   uv run pytest tests/test_config.py -v
   ```

---

## Group 1: Tool Wrapper - Tavily Client

**Goal:** Implement a Tavily web search client with caching layer. This is the primary data source for all company and founder information.

**Acceptance criteria:**
- `tools/tavily.py` exists with `TavilyClient` class
- `search()` method returns list of search results with typed fields
- In-memory cache implemented (dict-based, keyed by query hash)
- Cache persists across multiple calls within a Streamlit session
- `tenacity` retry logic for transient failures
- API failures return empty list and log warning (never raise)
- `uv run pytest tests/tools/test_tavily.py` passes all tests
- `uv run ruff check tools/tavily.py` reports no errors
- `uv run mypy tools/tavily.py` reports no errors

### Tasks

**1.1** Add `tenacity` to `pyproject.toml` dev dependencies if not already present.

**1.2** Create `tools/tavily.py` with module-level imports: `tavily`, `tenacity`, `logging`, `typing` (`TypedDict`, `Any`), `hashlib`. Import `settings` from `config`.

**1.3** Define `TavilySearchResult` TypedDict with fields: `title: str`, `url: str`, `content: str`, `score: float | None`.

**1.4** Implement `TavilyClient` class:
   - `__init__(api_key: str)` — store api_key, initialize empty `_cache: dict[str, list[TavilySearchResult]]`
   - `_make_cache_key(query: str, max_results: int) -> str` — return `hashlib.md5(f"{query}:{max_results}".encode()).hexdigest()`
   - `search(self, query: str, max_results: int = 10) -> list[TavilySearchResult]` — main search method
   - `clear_cache(self)` — clear the in-memory cache (useful for testing)

**1.5** Implement `search()` method body:
   - Check cache using `_make_cache_key()`, return cached results if present
   - Call `tavily.Client.search()` with `query`, `max_results=max_results`, `search_depth="advanced"`
   - Parse response into `list[TavilySearchResult]` (handle tavily response structure)
   - Store in cache before returning
   - Return empty list on any exception and log warning with query context

**1.6** Implement `clear_cache()` method to empty the in-memory cache dict.

**1.7** Add `@tenacity.retry` decorator to `search()` method:
   - Retry on `tavily.errors.TavilyException` with exponential backoff
   - Max 3 attempts with `wait_exponential_multiplier=1000, wait_exponential_max=10000`

**1.8** Create `tests/tools/test_tavily.py` with tests:
   - Test 1: Successful search returns parsed results
   - Test 2: Cache hit returns same results without API call
   - Test 3: Cache miss triggers API call and caches result
   - Test 4: API failure returns empty list and logs warning
   - Test 5: `clear_cache()` empties the cache
   - Test 6: Retry logic works on transient failures

**1.9** Run `uv run pytest tests/tools/test_tavily.py -v` and confirm all tests pass.

---

## Group 2: Tool Wrapper - Crunchbase Client (OPTIONAL)

**Goal:** Implement Crunchbase API wrapper for structured data enrichment. **Skip for MVP** — Tavily is the primary data source. Add later if a Crunchbase key is available.

**Acceptance criteria:**
- `tools/crunchbase.py` exists with `CrunchbaseClient` class (if implementing)
- Gracefully handles missing API key (skip Crunchbase enrichment)
- All methods return empty list if key not configured
- `uv run pytest tests/tools/test_crunchbase.py` passes all tests

### Tasks (OPTIONAL - Skip if no Crunchbase API key)

**2.1** [OPTIONAL] Create `tools/crunchbase.py` with module-level imports: `httpx`, `tenacity`, `logging`, `typing`.

**2.2** [OPTIONAL] Implement `CrunchbaseClient` that checks for API key in `__init__`:
   - If `settings.CRUNCHBASE_API_KEY` is empty or `"YOUR_KEY_HERE"`, log warning and set `self.enabled = False`
   - All methods return empty list if `not self.enabled`

**2.3** [OPTIONAL] If implementing, add methods for organization search and people lookup (see original spec for details).

**2.4** [OPTIONAL] Create tests for graceful degradation when API key missing.

**Note**: For MVP, the Search Agent will work with Tavily-only data. Crunchbase can be added later as an enhancement for better structured data.

---

## Group 3: Tool Wrapper - Anthropic Client (LLM Wrapper)

**Goal:** Implement a lightweight Anthropic Claude client wrapper for LLM calls in founder analysis and market gap validation.

**1.3** Define `CrunchbaseOrganization` TypedDict with fields: `uuid` (str), `name` (str), `short_description` (str | None), `funding_total` (int | None), `employee_count` (int | None), `founded_on` (str | None), `website` (str | None).

**1.4** Define `CrunchbasePerson` TypedDict with fields: `person_uuid` (str), `name` (str), `role` (str), `job_title` (str | None), `started_on` (str | None).

**1.5** Implement `CrunchbaseClient.__init__()` to store `api_key` from `settings.CRUNCHBASE_API_KEY` and set up base URL `https://api.crunchbase.com/api/v4/` and logger.

**1.6** Implement `@tenacity.retry` decorator helper method in `CrunchbaseClient` with: `stop=stop_after_attempt(3)`, `wait=wait_exponential(multiplier=1, max=10)`, `retry=retry_if_exception_type(httpx.HTTPStatusError)` for 429 status codes.

**1.7** Implement `CrunchbaseClient.search_organizations(query: str, funding_stage: str = "seed,series_a") -> list[CrunchbaseOrganization]`:
  - Make GET request to `/entities/organizations` endpoint with query params
  - Use retry decorator for rate limit handling
  - Parse response JSON and extract relevant fields into `CrunchbaseOrganization` dicts
  - Return empty list on any exception and log warning with query context

**1.8** Implement `CrunchbaseClient.get_organization_people(org_uuid: str) -> list[CrunchbasePerson]`:
  - Make GET request to `/entities/organizations/{uuid}/people` endpoint
  - Use retry decorator for rate limit handling
  - Filter results for `role` in `["founder", "co-founder"]`
  - Parse response into `CrunchbasePerson` dicts
  - Return empty list on any exception and log warning with UUID context

**1.9** Write tests in `tests/tools/test_crunchbase.py`:
  - Test 1: `search_organizations()` returns parsed list on successful response
  - Test 2: `search_organizations()` returns empty list on API error and logs warning
  - Test 3: `search_organizations()` applies retry logic on 429 status (mock 3 attempts)
  - Test 4: `get_organization_people()` filters for founders correctly
  - Test 5: `get_organization_people()` returns empty list on API error and logs warning
  - Test 6: TypedDict structures have correct field types (use mypy assertions)

**1.10** Run `uv run pytest tests/tools/test_crunchbase.py -v` and confirm all tests pass.

---

## Group 2: Tool Wrapper - Tavily Client with Caching

**Goal:** Implement a Tavily API client wrapper with web search functionality and session-scoped caching to optimize repeated queries (e.g., competitor research).

**Acceptance criteria:**
- `tools/tavily.py` exists with `TavilyClient` class
- `search()` method returns list of search results with typed fields
- `TypedDict` structure defines response shape (`TavilySearchResult`)
- LRU cache implemented with `@lru_cache` decorator
- Cache hits logged at DEBUG level
- All API calls use `tenacity` for exponential backoff
- API failures return empty list and log warning (never raise)
- `uv run pytest tests/tools/test_tavily.py` passes all tests
- `uv run ruff check tools/tavily.py` reports no errors
- `uv run mypy tools/tavily.py` reports no errors

### Tasks

**2.1** Create `tools/tavily.py` with module-level imports: `tavily`, `functools`, `logging`, `hashlib`, `typing` (`TypedDict`, `Any`). Import `settings` from `config`.

**2.2** Define `TavilySearchResult` TypedDict with fields: `title` (str), `url` (str), `content` (str), `score` (float).

**2.3** Implement `TavilyClient.__init__()` to initialize `tavily.TavilyClient(api_key=settings.TAVILY_API_KEY)` and set up logger.

**2.4** Implement cache key helper function `_make_cache_key(query: str, max_results: int) -> str` that hashes the query string and max_results using `hashlib.sha256` and returns hex digest.

**2.5** Implement `TavilyClient.search()` method:
  - Method signature: `search(self, query: str, max_results: int = 10) -> list[TavilySearchResult]`
  - Check in-memory cache dict (keyed by `_make_cache_key()`)
  - On cache hit: log DEBUG message and return cached results
  - On cache miss: call `self.client.search(query=query, max_results=max_results)`
  - Parse response into `TavilySearchResult` dicts
  - Store in cache before returning
  - Return empty list on any exception and log warning with query context

**2.6** Implement `TavilyClient.clear_cache()` method to empty the in-memory cache dict (useful for testing).

**2.7** Implement `@tenacity.retry` decorator for Tavily API calls with: `stop=stop_after_attempt(3)`, `wait=wait_exponential(multiplier=1, max=10)`, `retry=retry_if_exception_type(tavily.TavilyError)`.

**2.8** Write tests in `tests/tools/test_tavily.py`:
  - Test 1: `search()` returns parsed list on successful response
  - Test 2: `search()` caches results and returns cached data on second call (assert only 1 API call made)
  - Test 3: `search()` cache key different for different queries (same query returns cached, different calls API)
  - Test 4: `search()` returns empty list on API error and logs warning
  - Test 5: `clear_cache()` empties cache and next call hits API again
  - Test 6: TypedDict structure has correct field types (use mypy assertions)

**2.9** Run `uv run pytest tests/tools/test_tavily.py -v` and confirm all tests pass.

**2.10** Run `uv run ruff check tools/tavily.py` and `uv run mypy tools/tavily.py` and resolve any issues.

---

## Group 3: Search Agent Skeleton

**Goal:** Create the `SearchAgent` class with system prompts, basic structure, and `run()` method skeleton. No analysis logic yet—just the framework.

**Acceptance criteria:**
- `agents/search_agent.py` exists with `SearchAgent` class
- `__init__(risk_tolerance: str)` builds and stores system prompt
- Two module-level prompt constants: `SEARCH_AGENT_SYSTEM_PROMPT_RISK_NEUTRAL`, `SEARCH_AGENT_SYSTEM_PROMPT_RISK_AVERSE`
- `run(context: str, risk_tolerance: str) -> AgentMessage` skeleton exists
- Instantiates `CrunchbaseClient` and `TavilyClient` in `__init__`
- `uv run ruff check agents/search_agent.py` reports no errors
- `uv run mypy agents/search_agent.py` reports no errors

### Tasks

**3.1** Create `agents/search_agent.py` with module-level imports: `anthropic`, `logging`, `typing` (`Any`), and import `AgentMessage` from `models`, `CrunchbaseClient` from `tools.crunchbase`, `TavilyClient` from `tools.tavily`, `settings` from `config`.

**3.2** Write `SEARCH_AGENT_SYSTEM_PROMPT_RISK_NEUTRAL` as a module-level constant (multiline f-string or triple-quoted string) with:
  - Agent role definition: "You are the Search Agent, an independent analyst in a multi-agent investment pipeline. You specialize in discovering Seed-to-Series B AI startups and analyzing founder quality and market gaps. Your report will be read by a Judge LLM alongside two other independent agents to produce a GO/NOGO verdict."
  - Scoring rubrics for all scores (0-100 scale) with anchor examples
  - Instructions for balanced assessment, optimistic interpretation of ambiguity
  - JSON output format specification matching the spec structure
  - Evidence citation requirements

**3.3** Write `SEARCH_AGENT_SYSTEM_PROMPT_RISK_AVERSE` as a module-level constant with:
  - Same structure as risk-neutral prompt
  - Stricter scoring requirements: "Require stronger evidence for positive signals"
  - Conservative interpretation: "When uncertain, assume downside risk"
  - Heavier penalties for red flags (part-time commitment, bandwagon risk, weak moats)

**3.4** Implement `SearchAgent.__init__(self, risk_tolerance: str)`:
  - Validate `risk_tolerance` is in `["risk_neutral", "risk_averse"]`, raise `ValueError` if not
  - Store `risk_tolerance` as instance attribute
  - Select appropriate system prompt constant based on risk_tolerance
  - Instantiate `CrunchbaseClient()` and `TavilyClient()` as instance attributes
  - Initialize `anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)` as instance attribute
  - Set up logger instance attribute

**3.5** Implement `SearchAgent.run(self, context: str, risk_tolerance: str) -> AgentMessage` skeleton:
  - Validate `risk_tolerance` matches `self.risk_tolerance`, else raise `ValueError`
  - Log INFO message: "Starting Search Agent analysis for context: {context}"
  - Create placeholder for structured result dict (empty for now)
  - Return `AgentMessage(agent_name="search", content="{}", role="analyst")` for now
  - (Full implementation in Groups 4-6)

**3.6** Run `uv run ruff check agents/search_agent.py` and resolve any lint errors.

**3.7** Run `uv run mypy agents/search_agent.py` and resolve any type errors.

---

## Group 4: Founder Analysis Pipeline

**Goal:** Implement the founder analysis logic within `SearchAgent.run()`: data collection, experience relevance, team complementarity, and full-time commitment verification.

**Acceptance criteria:**
- `SearchAgent.run()` collects founder data via Crunchbase + Tavily
- Experience relevance analysis produces per-founder `relevance_score` (0-100)
- Team complementarity produces `complementarity_score` (0-100 or None for single founder)
- Full-time commitment verification produces `commitment_level` per founder
- Final LLM synthesis produces `founder_quality_score` (0-100) + narrative
- All founder data stored in structured dict matching spec
- Edge cases handled: single founder, missing data, API failures
- `uv run pytest tests/agents/test_search_agent.py::test_founder_analysis*` passes

### Tasks

**4.1** Add helper method `_collect_founder_data(self, company_name: str) -> list[dict]` in `SearchAgent`:
  - Call `self.crunchbase.search_organizations(company_name)` and get first result's UUID
  - Call `self.crunchbase.get_organization_people(org_uuid)` to get founders
  - For each founder, run 3 Tavily searches: LinkedIn, background, current position
  - Extract relevant info into dict: name, role, linkedin_url, background text
  - Return list of founder dicts, log INFO count of founders found

**4.2** Add helper method `_analyze_experience_relevance(self, founder: dict, company_description: str) -> tuple[int | None, str]` in `SearchAgent`:
  - Construct prompt: founder background + company description
  - Call Claude API with system prompt
  - Parse response for relevance score (0-100) and narrative
  - Log DEBUG with score for founder name
  - Return (score, narrative)

**4.3** Add helper method `_analyze_complementarity(self, founders: list[dict], company_description: str) -> tuple[int | None, str]` in `SearchAgent`:
  - If only 1 founder, return (None, "Single-founder team: complementarity not applicable")
  - Construct prompt: all founder backgrounds + company description
  - Call Claude API with system prompt
  - Parse response for complementarity score (0-100) and narrative
  - Log DEBUG with score
  - Return (score, narrative)

**4.4** Add helper method `_verify_commitment(self, founder: dict, company_name: str) -> tuple[str, list[str]]` in `SearchAgent`:
  - Analyze Tavily search results for commitment signals
  - Look for red flags: concurrent employment, "student" status, minimal activity
  - Look for green flags: "left X to found Y", active GitHub/blog, LinkedIn "Founder at {company}"
  - Use Claude to classify commitment level: "full-time", "part-time", "unknown"
  - Extract supporting evidence as list of strings
  - Log INFO with commitment level for founder name
  - Return (commitment_level, evidence_list)

**4.5** Add helper method `_synthesize_founder_analysis(self, founders: list[dict]) -> tuple[int, str]` in `SearchAgent`:
  - Compile all founder relevance scores, complementarity score, commitment levels
  - Construct prompt with all founder data
  - Call Claude API to synthesize into composite score
  - Parse response for `founder_quality_score` (0-100) and narrative summary
  - Log INFO with final score
  - Return (score, narrative)

**4.6** Update `SearchAgent.run()` to call founder analysis pipeline:
  - After basic company info collection, call `_collect_founder_data()`
  - For each founder, call `_analyze_experience_relevance()` and `_verify_commitment()`
  - Call `_analyze_complementarity()` with all founders
  - Call `_synthesize_founder_analysis()` to get final score
  - Store all results in `founders` and `founder_analysis` sections of result dict
  - Handle edge cases: if no founders found, log WARNING and set scores to None with caveat

**4.7** Write tests in `tests/agents/test_search_agent.py` for founder analysis:
  - Test 1: `_collect_founder_data()` with mocked Crunchbase/Tavily returns correct founder dicts
  - Test 2: `_analyze_experience_relevance()` returns score 0-100 and narrative
  - Test 3: `_analyze_complementarity()` returns None for single founder, score for multiple
  - Test 4: `_verify_commitment()` returns valid commitment level and evidence list
  - Test 5: `_synthesize_founder_analysis()` returns composite score 0-100
  - Test 6: Full founder pipeline with all mocks produces correct JSON structure

**4.8** Run `uv run pytest tests/agents/test_search_agent.py::test_founder_analysis -v` and confirm all tests pass.

---

## Group 5: Market Gap Validation Pipeline

**Goal:** Implement the market gap validation logic within `SearchAgent.run()`: bandwagon risk detection, competitive landscape analysis, defensibility assessment, and market gap score synthesis.

**Acceptance criteria:**
- `SearchAgent.run()` collects company product info via Tavily
- Bandwagon risk detection produces `bandwagon_risk_score` (0-100) + evidence
- Competitive analysis identifies competitors + `competitive_positioning` narrative
- Defensibility assessment produces `defensibility_score` (0-100) + narrative
- Final LLM synthesis produces `market_gap_score` (0-100) + narrative
- Competitor research cached by sector for reuse
- All market data stored in structured dict matching spec
- Edge cases handled: stealth startups, pre-launch, no competitors
- `uv run pytest tests/agents/test_search_agent.py::test_market_analysis*` passes

### Tasks

**5.1** Add helper method `_collect_company_product_info(self, company_name: str) -> dict` in `SearchAgent`:
  - Call `self.crunchbase.search_organizations(company_name)` for basic info
  - Call Tavily search: `"{company_name} product features AI"`
  - Extract product description, target market, key features into dict
  - Return dict with company overview fields
  - Log INFO with company name and description

**5.2** Add helper method `_detect_bandwagon_risk(self, company_info: dict) -> tuple[int, list[str]]` in `SearchAgent`:
  - Construct prompt: company description, marketing copy, product info
  - Include bandwagon red flag indicators in prompt (generic marketing, shallow tech, etc.)
  - Call Claude API with system prompt
  - Parse response for `bandwagon_risk_score` (0-100, 100 = definite wrapper)
  - Extract supporting evidence list (red flags found)
  - Log INFO with bandwagon risk score
  - Return (score, evidence_list)

**5.3** Add helper method `_analyze_competitors(self, company_info: dict, sector: str) -> tuple[list[dict], str]` in `SearchAgent`:
  - Generate sector key from company info (e.g., "medical imaging AI")
  - Run 3 Tavily searches: competitors, alternatives, sector startups
  - Use cache (should auto-hit if same sector analyzed previously)
  - Construct prompt: competitor results + company description
  - Call Claude API to identify top 3-5 competitors with differentiation notes
  - Parse response into competitors array and competitive_positioning narrative
  - Log INFO with competitor count and whether cache was used
  - Return (competitors_list, positioning_narrative)

**5.4** Add helper method `_assess_defensibility(self, company_info: dict, competitors: list[dict]) -> tuple[int, str]` in `SearchAgent`:
  - Construct prompt: product description, competitors, funding info
  - Include moat categories in prompt (data, network effects, switching costs, regulatory, expertise)
  - Call Claude API with system prompt
  - Parse response for `defensibility_score` (0-100) and narrative
  - Log INFO with defensibility score
  - Return (score, narrative)

**5.5** Add helper method `_synthesize_market_analysis(self, bandwagon_score: int, defensibility_score: int, competitors: list) -> tuple[int, str]` in `SearchAgent`:
  - Compile all market analysis scores and narratives
  - Construct prompt with all market data
  - Call Claude API to synthesize into composite score
  - Parse response for `market_gap_score` (0-100) and narrative summary
  - Log INFO with final market gap score
  - Return (score, narrative)

**5.6** Update `SearchAgent.run()` to call market analysis pipeline:
  - After founder analysis, call `_collect_company_product_info()`
  - Call `_detect_bandwagon_risk()` and store score + evidence
  - Call `_analyze_competitors()` and store competitors + positioning
  - Call `_assess_defensibility()` and store score + narrative
  - Call `_synthesize_market_analysis()` to get final score
  - Store all results in `market_analysis` section of result dict
  - Handle edge cases: if no competitors found for stealth/pre-launch, note limitation explicitly

**5.7** Write tests in `tests/agents/test_search_agent.py` for market analysis:
  - Test 1: `_collect_company_product_info()` returns correct structure
  - Test 2: `_detect_bandwagon_risk()` returns score 0-100 and evidence list
  - Test 3: `_detect_bandwagon_risk()` flags obvious LLM wrapper (test with "ChatGPT for X" description)
  - Test 4: `_analyze_competitors()` uses cache on second call for same sector (assert API call count)
  - Test 5: `_assess_defensibility()` returns score 0-100 and narrative
  - Test 6: `_synthesize_market_analysis()` returns composite score 0-100
  - Test 7: Full market pipeline with all mocks produces correct JSON structure

**5.8** Run `uv run pytest tests/agents/test_search_agent.py::test_market_analysis -v` and confirm all tests pass.

---

## Group 6: Integration and Error Handling

**Goal:** Integrate founder and market pipelines, add comprehensive error handling, implement final summary generation, and ensure JSON output matches spec structure.

**Acceptance criteria:**
- `SearchAgent.run()` executes full pipeline: discovery → founder analysis → market analysis → summary
- All API calls wrapped in try/except with logging
- Partial results produced on failures (e.g., Crunchbase timeout but Tavily works)
- Final summary generated: `search_agent_summary` (2-3 sentence synthesis)
- Full JSON structure matches spec exactly (all required fields present)
- Risk tolerance correctly influences prompts and scoring
- `uv run pytest tests/agents/test_search_agent.py::test_integration*` passes
- `uv run pytest tests/agents/test_search_agent.py::test_error_handling*` passes

### Tasks

**6.1** Update `SearchAgent.run()` to execute full integrated pipeline:
  - Call company info collection (try/except, log WARNING on failure, continue with partial data)
  - Call founder analysis pipeline (try/except, log ERROR on failure, set founder fields to None)
  - Call market analysis pipeline (try/except, log ERROR on failure, set market fields to None)
  - If both pipelines failed completely, raise exception with context
  - Log INFO: "Search Agent analysis complete: founder_score={X}, market_gap_score={Y}, bandwagon_risk={Z}"

**6.2** Add helper method `_generate_search_summary(self, result: dict) -> str` in `SearchAgent`:
  - Compile key scores: founder_quality, market_gap, bandwagon_risk, defensibility
  - Construct prompt to generate 2-3 sentence executive summary for the Sentiment and Valuation agents to build on
  - Call Claude API with system prompt
  - Parse response summary text
  - Log DEBUG with summary
  - Return summary string

**6.3** Add helper method `_build_final_json(self, company_info: dict, founders: list, founder_analysis: dict, market_analysis: dict, summary: str) -> str` in `SearchAgent`:
  - Construct complete JSON dict matching spec structure exactly
  - Include all fields: company, founders, founder_analysis, market_analysis, search_agent_summary
  - Handle None values appropriately (null in JSON, not missing)
  - Serialize to JSON string with `json.dumps()` and pretty formatting
  - Validate JSON structure (optional: use JSON schema or manual assertion)
  - Return JSON string

**6.4** Update `SearchAgent.run()` final return:
  - Call `_generate_search_summary()` with result dict
  - Call `_build_final_json()` to create JSON content
  - Return `AgentMessage(agent_name="search", content=json_string, role="analyst")`

**6.5** Add error handling wrapper around entire `run()` method:
  - Top-level try/except catching `Exception`
  - On unexpected exception, log ERROR with full context (company, risk_tolerance, traceback)
  - Re-raise with helpful message for orchestrator to handle
  - Never return malformed `AgentMessage`

**6.6** Add risk tolerance influence verification:
  - In `_synthesize_founder_analysis()`, adjust prompt based on `self.risk_tolerance`
  - In `_synthesize_market_analysis()`, adjust prompt based on `self.risk_tolerance`
  - Add logging DEBUG: "Using {risk_tolerance} prompt for founder synthesis"
  - Verify via test that risk_averse produces different (lower) scores than risk_neutral for same input

**6.7** Write integration tests in `tests/agents/test_search_agent.py`:
  - Test 1: Full pipeline with all mocks produces complete JSON matching spec structure
  - Test 2: Full pipeline validates JSON can be parsed and has all required keys
  - Test 3: Crunchbase failure produces partial results with market analysis intact
  - Test 4: Tavily failure produces partial results with Crunchbase data intact
  - Test 5: Both APIs failure raises exception with helpful context message
  - Test 6: Risk tolerance difference: risk_averse produces lower scores than risk_neutral on same input

**6.8** Run `uv run pytest tests/agents/test_search_agent.py::test_integration -v` and `uv run pytest tests/agents/test_search_agent.py::test_error_handling -v` and confirm all tests pass.

**6.9** Run `uv run ruff check agents/search_agent.py` and `uv run mypy agents/search_agent.py` and resolve any issues.

---

## Group 7: Full Quality Pipeline Verification

**Goal:** Confirm all quality checks pass across the complete implementation: linting, type checking, and full test suite.

**Acceptance criteria:**
- `uv run pytest tests/` (all tests) exits with code 0
- `uv run ruff check .` exits with code 0 (no lint violations)
- `uv run ruff format --check .` exits with code 0 (no formatting changes needed)
- `uv run mypy .` exits with code 0 (no type errors)
- All tool wrapper tests pass: `tests/tools/test_crunchbase.py`, `tests/tools/test_tavily.py`
- All agent tests pass: `tests/agents/test_search_agent.py`
- Test coverage is reasonable (no critical untested paths)

### Tasks

**7.1** Run `uv run pytest tests/ -v` and review output. Confirm all tests collected and passed with exit code 0. Fix any failing tests before proceeding.

**7.2** Run `uv run pytest tests/tools/ -v` specifically to confirm tool wrapper tests pass.

**7.3** Run `uv run pytest tests/agents/test_search_agent.py -v` specifically to confirm agent tests pass.

**7.4** Run `uv run ruff check .` and resolve any lint violations in:
  - `tools/tavily.py` (primary)
  - `tools/crunchbase.py` (optional, if implemented)
  - `agents/search_agent.py`
  - Test files

**7.5** Run `uv run ruff format --check .` and if any files need formatting, run `uv run ruff format .` to fix.

**7.6** Run `uv run mypy .` and resolve any type errors:
  - Add `# type: ignore` annotations for third-party library issues if needed
  - Ensure all TypedDicts and dataclasses have correct type annotations
  - Verify function signatures have complete type hints

**7.7** Run `uv run pytest tests/ --cov=agents --cov=tools --cov-report=term-missing` (if `pytest-cov` is installed) to check test coverage. Review any missing critical paths and add tests if needed.

**7.8** Create a manual integration test script (optional but helpful):
  - Create `tests/manual_test_search_agent.py` with example usage
  - Show how to instantiate `SearchAgent` with different risk tolerances
  - Show example input/output (can use with real API keys for manual verification)
  - Document expected JSON structure in comments

**7.9** Final verification: Run `uv run pytest tests/ -v` one more time and confirm clean exit with all tests passing. Log the test count and duration.

---

## Completion Checklist

After completing all task groups, verify:

- [ ] `tools/tavily.py` exists with `TavilyClient` class with caching (REQUIRED)
- [ ] `tools/crunchbase.py` exists (OPTIONAL - if API key available)
- [ ] `agents/search_agent.py` exists with `SearchAgent` class
- [ ] All system prompt constants defined at module level (see `planning/system-prompts.md`)
- [ ] Founder analysis pipeline implemented (Tavily-based)
- [ ] Market gap validation pipeline implemented (Tavily-based)
- [ ] Error handling covers all API failures with partial results
- [ ] Risk tolerance influences prompts and scoring
- [ ] JSON output structure matches spec exactly
- [ ] All unit tests pass (`tests/tools/test_tavily.py`, `tests/agents/`)
- [ ] All integration tests pass
- [ ] `ruff check` passes with no errors
- [ ] `mypy` passes with no errors
- [ ] Code follows project conventions (snake_case, type hints, dataclasses)

**Estimated completion time:** 1-2 weeks (reduced from original - no Crunchbase dependency for MVP)

**API Keys Required for MVP:**
- ✅ `ANTHROPIC_API_KEY` - Required
- ✅ `TAVILY_API_KEY` - Required (primary data source)
- ⚪ `CRUNCHBASE_API_KEY` - Optional (can add later for enrichment)
