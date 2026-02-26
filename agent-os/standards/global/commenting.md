## Code Commenting

- **Self-documenting code:** Clear naming over comments; avoid restating what the code does
- **Agent system prompts:** Add a one-line comment above each system prompt constant explaining the agent's role and risk posture
- **Orchestrator logic:** Comment the debate round-robin loop and consensus check — these are non-obvious control flows
- **Tool wrappers:** Comment any non-obvious API quirks (e.g., Crunchbase pagination, Reddit rate limits)
- **No change comments:** Do not leave comments like "# fixed bug" or "# updated 2025-02" — comments are evergreen documentation only
