## Data Models

This project has no database. "Models" refers to Python dataclasses and TypedDicts used for structured data.

### Core Dataclasses

```python
@dataclass
class AgentMessage:
    agent_name: str        # "search", "sentiment", "valuation", "orchestrator"
    content: str           # The agent's response text
    round: int             # Which debate/collaboration round (1-indexed)
    timestamp: datetime
    verdict: str | None    # "GO", "NOGO", or None if not a final verdict

@dataclass
class DebateResult:
    verdict: str           # "GO", "NOGO", "NO_CONSENSUS"
    rounds: int            # Total rounds completed
    agent_messages: list[AgentMessage]
    report: str            # Consolidated markdown report
    company: str
    risk_tolerance: str
    mode: str              # "collaboration" or "debate"
```

### Conventions
- Use `@dataclass(frozen=True)` for immutable message objects
- Use `TypedDict` for API response shapes from Tavily, Crunchbase, Reddit, Twitter/X
- Never use bare `dict` for structured data passed between agents and orchestrator
