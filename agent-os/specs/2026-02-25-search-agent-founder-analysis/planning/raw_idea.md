# Raw Idea: Search Agent with Founder Analysis and Market Gap Validation

**Core capability**: The Search Agent discovers pre-Series A AI startups via Tavily and Crunchbase APIs, and performs comprehensive founder profile analysis AND validates whether the product solves a real market gap (vs. being another LLM wrapper).

## Founder analysis requirements

1. **Experience relevance**: Analyze whether each founder's background/experience is directly relevant to the startup's product/domain
2. **Team complementarity**: Assess whether founders' skills and backgrounds complement each other (e.g., technical + business, or industry expertise + operational experience)
3. **Full-time commitment**: Verify whether founders are working on this startup full-time (no part-time, side-project, or concurrent employment signals)

## Market gap validation requirements

1. **Product differentiation**: Determine if the startup's product offers unique value beyond generic LLM API calls (e.g., proprietary data, unique workflow, domain-specific fine-tuning, industry expertise)
2. **Competitive landscape**: Research existing solutions in the same space - is this product differentiated or a "me-too" LLM wrapper?
3. **Defensibility assessment**: Evaluate if there are moats (data network effects, switching costs, proprietary tech, regulatory barriers, domain expertise)
4. **Bandwagon detection**: Identify signals of opportunistic LLM wrapping (e.g., generic ChatGPT wrapper, no unique tech stack, shallow integration, "AI-powered" marketing with basic prompting)

## Data sources

- Tavily API for web search (company + founder names)
- Crunchbase API for structured startup data (founders list, funding stage, team size)
- Potential web scraping/search to validate full-time status (LinkedIn profiles, recent activity, concurrent roles)

## Output

The Search Agent should produce an AgentMessage that includes:

- Company overview
- Founder profiles (names, roles, backgrounds)
- Founder analysis scores (relevance, complementarity, commitment)
- Overall assessment summary

## Context

This is part of the multi-agent investment debate system. The Search Agent's output will be consumed by the Sentiment and Valuation agents in Phase 1, then used in the Phase 2 debate.
