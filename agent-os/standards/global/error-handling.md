## Error Handling

- **API failures:** Wrap all external API calls (Anthropic, Tavily, Crunchbase, Reddit, Twitter/X) in try/except with specific exception types; surface clear errors to Streamlit UI via `st.error()`
- **Rate limits:** Implement exponential backoff with jitter for all third-party API calls; use `tenacity` library
- **LLM errors:** Catch `anthropic.APIError`, `anthropic.RateLimitError`, and `anthropic.APITimeoutError` separately
- **Debate deadlock:** If the debate orchestrator exceeds `max_rounds` without consensus, return a `NO_CONSENSUS` result rather than looping indefinitely
- **Partial failures:** If one agent fails mid-debate, surface the error but preserve results from agents that succeeded
- **Streamlit:** Never let unhandled exceptions crash the app; catch at the top-level UI call and display `st.error()` with actionable message
- **Logging:** Use Python `logging` module (not `print`); log agent inputs/outputs at DEBUG level, errors at ERROR level
