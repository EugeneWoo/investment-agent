## Test Writing

- **Framework:** `pytest` with `pytest-mock` for mocking
- **What to test:** Agent `run()` methods with mocked LLM responses; orchestrator debate/collaboration logic; tool wrapper parsing functions
- **Mock external calls:** Always mock `anthropic.Client.messages.create`, Tavily, Crunchbase, Reddit, and Twitter/X clients in tests — never make real API calls in tests
- **Fixtures:** Define reusable `AgentMessage` and `DebateResult` fixtures in `conftest.py`
- **Test files:** Mirror source structure — `tests/agents/test_search_agent.py`, `tests/orchestrator/test_debate.py`, `tests/tools/test_tavily.py`
- **Run tests:** `pytest` from project root; `pytest tests/agents/` for a specific module
- **Focus:** Test orchestrator consensus logic, round counting, and NO_CONSENSUS fallback — these are the most critical paths
