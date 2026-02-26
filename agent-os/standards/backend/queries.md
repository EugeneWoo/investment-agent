## External Data Queries

This project queries external APIs rather than a database. These conventions apply to all tool wrapper functions in `tools/`.

### Tavily (Web Search)
- Use `tavily-python` client; always set `search_depth="advanced"` for investment research queries
- Limit to 10 results per query; filter to last 90 days for recency
- Cache results in session state (`st.session_state`) to avoid redundant API calls within a single run

### Crunchbase
- Query by company name or domain; always request funding rounds, investors, and founding date fields
- Handle 429 rate limits with exponential backoff (`tenacity`)
- Normalize funding amounts to USD millions in the tool wrapper, not in agent logic

### Reddit (PRAW)
- Search `r/investing`, `r/stocks`, `r/startups`, `r/venturecapital` subreddits
- Limit to top 25 posts by relevance; include comments up to depth 2
- Strip HTML and normalize whitespace before passing to Sentiment Agent

### Twitter/X (tweepy)
- Search recent tweets (last 7 days) with company name + funding/launch keywords
- Filter to verified accounts and accounts with >1000 followers to reduce noise
- Deduplicate by tweet ID before passing to Sentiment Agent

### General
- All query functions are synchronous; use `asyncio.gather` in orchestrator if parallelism is needed
- Log query params and result counts at DEBUG level for each external call
