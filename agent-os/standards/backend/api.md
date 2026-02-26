## Agent & Tool API Standards

This project has no REST API server. "Backend API" refers to the interfaces between agents, the orchestrator, and external tool wrappers.

### Agent Interface
- Each agent exposes a single `run(context: list[AgentMessage], risk_tolerance: str) -> AgentMessage` method
- Agents are stateless between calls; all context is passed in via the `context` argument
- System prompts are constructed in `__init__` based on `risk_tolerance` (`risk_neutral` | `risk_averse`)

### Agent Implementation Pattern

```python
from anthropic import Anthropic

class SearchAgent:
    def __init__(self, risk_tolerance: str):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.risk_tolerance = risk_tolerance
        self.system_prompt = f"""You are a Search Agent for pre-Series A AI startup discovery.
Risk tolerance: {risk_tolerance}
Your role: Find promising AI startups using web search and funding data."""

    def run(self, company: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=self.system_prompt,
            messages=[{"role": "user", "content": f"Find investment opportunities for: {company}"}]
        )
        return response.content[0].text
```

### Orchestrator Debate Pattern

```python
class DebateOrchestrator:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.agents = {
            "search": SearchAgent("risk_neutral"),
            "sentiment": SentimentAgent("risk_neutral"),
            "valuation": ValuationAgent("risk_neutral")
        }

    def run(self, company: str, risk_tolerance: str) -> DebateResult:
        # Phase 1: Each agent speaks once
        phase1_outputs = {}
        for name, agent in self.agents.items():
            phase1_outputs[name] = agent.run(company)

        # Phase 2: Round-robin debate until consensus
        debate_history = list(phase1_outputs.values())
        max_rounds = 5
        consensus = None

        for round_num in range(max_rounds):
            for name, agent in self.agents.items():
                prompt = f"""Debate round {round_num + 1}
Company: {company}

Previous arguments:
{chr(10).join(f'{n}: {a}' for n, a in zip(phase1_outputs.keys(), debate_history))}

Your task: Challenge or support the above positions. State your GO/NOGO recommendation clearly at the end."""

                response = agent.run(prompt)
                debate_history.append(f"{name}: {response}")

            # Check consensus after each full round
            if self._check_consensus(debate_history[-len(self.agents):]):
                consensus = self._check_consensus(debate_history[-len(self.agents):])
                break

        return DebateResult(verdict=consensus or "NO_CONSENSUS", ...)
```

### Streaming for Live UI
```python
# For showing "thinking" in Streamlit
with st.status("Sentiment Agent analyzing...", expanded=True) as status:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        stream=True
        messages=[...]
    )

    for text in response.stream():
        if text.type == "content_block_delta":
            st.write(text.delta.text)
```

### Tool Wrapper Interface
- Each tool in `tools/` exposes a single async or sync function with typed inputs and outputs
- Tool functions raise specific exceptions (e.g., `TavilyError`, `CrunchbaseError`) — never return raw error dicts
- All tool functions include a docstring describing inputs, outputs, and which API they call

### Orchestrator Interface
- `Orchestrator.run(company: str, risk_tolerance: str) -> DebateResult`
- Runs a single unified two-phase pipeline: Phase 1 (each agent runs once: Search → Sentiment → Valuation), then Phase 2 (round-robin debate until consensus)
- `DebateResult` contains `verdict` (`GO` | `NOGO` | `NO_CONSENSUS`), `rounds`, `agent_messages`, and `report`

### Anthropic API Usage
- Use `client.messages.create()` with `model="claude-sonnet-4-6"`
- Always set `max_tokens` explicitly
- Pass tool definitions as `tools=` parameter when agents need to call external tools
- Use streaming (`stream=True`) for long Sentiment Agent responses displayed in Streamlit
