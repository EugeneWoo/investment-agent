# Spec Requirements: Search Agent with Founder Analysis and Market Gap Validation

## Initial Description
The Search Agent discovers pre-Series A AI startups via Tavily and Crunchbase APIs, and performs comprehensive founder profile analysis plus market gap validation. This is part of the multi-agent investment debate system where three specialized agents (Search, Sentiment, Valuation) run in a unified two-phase pipeline.

## Requirements Discussion

### First Round Questions

**Q1:** Should we use Crunchbase API's `/organizations/{uuid}/people` endpoint for basic founder data, then supplement with Tavily web search for richer background information?
**Answer:** Yes, use Crunchbase for structured data (names, roles) and Tavily for deeper background research (LinkedIn, bios, interviews, previous companies).

**Q2:** Should we use LLM analysis for experience relevance rather than keyword matching, and produce both qualitative assessment and numerical scores?
**Answer:** Yes, use Claude LLM analysis with both qualitative narrative and numerical `relevance_score` (0-100) for each founder.

**Q3:** Should team complementarity be LLM-generated qualitative analysis or a structured skill matrix?
**Answer:** Use LLM-generated qualitative analysis that considers skill domains (technical, business, AI expertise, industry domain knowledge) with a `complementarity_score` (0-100).

**Q4:** Should full-time commitment verification detect concurrent employment as a binary red flag or nuanced commitment level?
**Answer:** Use nuanced approach: Tavily search for founder names + current roles, LinkedIn profile analysis, recent activity checks (GitHub, blogs, Twitter). Output as `commitment_level` (full-time / part-time / unknown) with evidence.

**Q5:** How should the agent detect "LLM wrapper" signals vs genuine innovation?
**Answer:** Look for red flags: generic marketing copy ("AI-powered"), shallow tech descriptions, no proprietary data/fine-tuning mentioned, single-provider dependency, basic chat interfaces. Output `bandwagon_risk_score` (0-100, 100 = definite wrapper) with supporting evidence.

**Q6:** Should competitive landscape analysis include structured competitor data or qualitative narrative?
**Answer:** Use Tavily to search for competitors, then have Claude analyze differentiation. Output structured `competitors` array + qualitative `competitive_positioning` narrative.

**Q7:** Should defensibility assessment be a score or narrative?
**Answer:** Produce `defensibility_score` (0-100) with qualitative narrative covering moats: proprietary data, network effects, switching costs, regulatory barriers, domain expertise.

**Q8:** What data sources beyond Crunchbase and Tavily for market gap validation?
**Answer:** Tavily's broad web search is sufficient to capture signals indirectly (product reviews, technical blogs, patents, GitHub repos). No additional APIs needed.

**Q9:** Should AgentMessage be extended with new fields or keep JSON-structured content?
**Answer:** Keep `AgentMessage` dataclass as-is with JSON-structured `content` field to maintain debate pipeline compatibility.

**Q10:** How should founder and market analyses factor into GO/NOGO decision?
**Answer:** Produce separate scores for transparency:
- `founder_quality_score` (0-100)
- `market_gap_score` (0-100)
- `bandwagon_risk_score` (0-100)
- `defensibility_score` (0-100)
Plus composite `search_agent_summary` for quick comparison.

**Q11:** How should edge cases be handled (single founders, stealth startups, missing data, pre-launch products)?
**Answer:** Set scores to `None` or "unknown" with clear caveats in narrative rather than failing. Use uncertainty signaling explicitly.

**Q12:** Should we implement tiered research approach or comprehensive analysis with caching?
**Answer:** Comprehensive analysis with caching. Cache competitor research across startups in same sector to reduce redundant Tavily API calls.

**Q13:** Founder analysis scope - what to exclude?
**Answer:** Out of scope: Founder equity distribution, governance structure, board composition. Also exclude founder social sentiment (Sentiment Agent territory) and founder network quality (VC connections, alma mater prestige).

**Q14:** Market analysis scope - what to exclude?
**Answer:** Out of scope: TAM/SAM/SOM market sizing (too complex), financial projections/revenue modeling (Valuation Agent), technical architecture evaluation (too deep), user experience assessment (subjective).

### Existing Code to Reference

**Current State:**
- `agents/` directory exists but is empty except for `__init__.py`
- `tools/` directory exists but is empty except for `__init__.py`
- `models.py` defines `AgentMessage` and `DebateResult` dataclasses
- This is a greenfield implementation following established patterns

**Architecture Patterns to Follow:**
- Agent pattern: Python class with `__init__(risk_tolerance)` and `run(context, risk_tolerance) -> AgentMessage`
- Risk tolerance injected into system prompts at instantiation (`risk_neutral` | `risk_averse`)
- Structured output via dataclasses (`AgentMessage`, `DebateResult`)
- Two-phase pipeline: Phase 1 (each agent speaks once) → Phase 2 (round-robin debate)

### Follow-up Questions

No follow-up questions were needed. User provided comprehensive decisions on scoring, wrapper detection, API strategy, and scope boundaries.

## Visual Assets

### Files Provided:
No visual assets were provided.

### Visual Insights:
N/A - No visual files to analyze.

## Requirements Summary

### Functional Requirements

**Core Capabilities:**
1. Discover pre-Series A AI startups via Tavily web search and Crunchbase API
2. Perform comprehensive founder profile analysis:
   - Experience relevance to startup's product/domain
   - Team complementarity (co-founder skill coverage)
   - Full-time commitment verification (no concurrent employment)
3. Conduct market gap validation:
   - Product differentiation assessment (beyond generic LLM wrappers)
   - Competitive landscape analysis
   - Defensibility evaluation (moats, barriers to entry)
   - Bandwagon detection (LLM wrapper risk signals)
4. Output structured `AgentMessage` with both quantitative scores and qualitative narratives

**Data Sources:**
- Crunchbase API: `/organizations/{uuid}/people` endpoint for founder names/roles
- Tavily API: Web search for founder backgrounds, competitor research, technical validation
- Cached research results across companies in same sector

**Scoring Output (all 0-100 scale):**
- `founder_quality_score`: Overall assessment of founder team strength
- `market_gap_score`: Validation that product addresses real market need
- `bandwagon_risk_score`: 100 = definite LLM wrapper, 0 = genuine innovation
- `defensibility_score`: Strength of competitive moats
- `relevance_score`: Per-founder experience relevance
- `complementarity_score`: Team skill coverage assessment
- `commitment_level`: full-time / part-time / unknown per founder

### Reusability Opportunities

**Components to Investigate:**
- Tavily API client wrapper pattern (to be created in `tools/tavily.py`)
- Crunchbase API client wrapper pattern (to be created in `tools/crunchbase.py`)
- LLM prompt construction for structured analysis (may inform future agents)
- Caching layer for competitor research (reusable across analysis phases)

**Backend Patterns:**
- Risk tolerance injection into agent system prompts
- JSON-structured content in `AgentMessage` for complex outputs
- Error handling for missing/uncertain data (None values with caveats)

### Scope Boundaries

**In Scope:**
- Founder background research via LinkedIn, bios, interviews
- Founder experience relevance and complementarity analysis
- Founder full-time commitment verification
- Product differentiation assessment vs LLM wrappers
- Competitive landscape identification
- Defensibility evaluation (data moats, network effects, switching costs, regulatory barriers)
- Bandwagon risk detection (generic marketing, shallow tech, single-provider dependency)
- Quantitative scoring (0-100) with qualitative supporting narratives
- Result caching across companies in same sector

**Out of Scope:**
- Founder equity distribution, governance structure, board composition
- Founder social media sentiment (Sentiment Agent responsibility)
- Founder network quality (VC connections, alumni prestige)
- TAM/SAM/SOM market sizing (too complex for this phase)
- Financial projections, revenue modeling (Valuation Agent responsibility)
- Technical architecture evaluation (too deep)
- User experience assessment (subjective, hard to automate)
- Founder track record (previous exits, failed startups) - future enhancement

### Technical Considerations

**API Strategy:**
- Comprehensive analysis per company (2-3 Tavily searches per founder, 3-5 for competitors, 2-3 for product validation)
- Implement caching layer to reuse competitor research across startups in same sector
- Handle Crunchbase rate limits gracefully
- Cost-conscious Tavily usage through smart caching

**LLM Integration:**
- Use Claude (`claude-sonnet-4-6`) for qualitative analysis
- Construct system prompts to produce both scores and narratives
- Handle missing/uncertain data with explicit uncertainty signaling

**Error Handling:**
- Missing founder data: Set scores to None, include caveats
- Stealth startups with limited info: Note data limitations explicitly
- Single-founder teams: Skip complementarity analysis, note as limitation
- Pre-launch products: Note lack of competitive/Market data

**Data Structures:**
```python
@dataclass
class AgentMessage:
    agent_name: str
    content: str  # JSON-structured with all scores and narratives
    role: str

# Content JSON structure:
{
    "company": {...},
    "founders": [
        {
            "name": str,
            "role": str,
            "background": str,
            "relevance_score": int | None,
            "commitment_level": "full-time" | "part-time" | "unknown",
            "evidence": [...]
        }
    ],
    "founder_analysis": {
        "founder_quality_score": int,
        "complementarity_score": int | None,
        "narrative": str
    },
    "market_analysis": {
        "market_gap_score": int,
        "bandwagon_risk_score": int,
        "defensibility_score": int,
        "differentiation": str,
        "competitors": [...],
        "competitive_positioning": str,
        "defensibility_narrative": str
    },
    "search_agent_summary": str
}
```

**Testing Requirements:**
- Unit tests for founder analysis logic with mocked API responses
- Unit tests for market gap validation with mock competitor data
- Integration tests for full Search Agent run with mocked Crunchbase/Tavily
- Edge case tests: single founders, stealth startups, missing data
- Verify caching behavior for competitor research reuse

**Integration Points:**
- Phase 1 pipeline: Search Agent output consumed by Sentiment and Valuation agents
- Phase 2 debate: Scores and narratives used as evidence in GO/NOGO arguments
- Streamlit UI: Display structured scores and expandable narratives
