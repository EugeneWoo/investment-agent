# Plan: Adversarial Debate (AutoGen-style) for Investment Agent

## Context

The system currently has a fake "debate" — Phase 2 is a single Judge LLM call reading all 3 reports at once and issuing a one-shot GO/NOGO. `DebateResult.rounds` is hardcoded to 0. There is no actual agent-to-agent argumentation.

The goal is to replace Phase 2 with a true **round-robin adversarial debate**: each agent reads what the others said, challenges the weakest opposing argument, updates its GO/NOGO position, and the loop continues until all three agree (consensus) or `max_rounds` is exceeded (majority-vote fallback). This matches AutoGen's group chat pattern but uses pure Anthropic SDK — no AutoGen, no LangChain.

Key discovery: `app.py` bypasses `orchestrator.run()` entirely — it manually calls each agent and the private `_judge_reports()` helper. The refactor must account for this.

### How Agents "Talk" to Each Other

Agents do not communicate directly. Each debate turn is an independent LLM call. The orchestrator acts as the message bus:

1. Collects each agent's output as a `DebatePosition`
2. Appends it to `debate_history: list[dict]`
3. Serializes the full history into the next agent's user message prompt

Each agent's LLM call looks like:

```
system_prompt: "You are Search Agent, challenge the weakest opposing argument..."
user_message:  "Company: Acme
                Your Phase 1 analysis: {...}

                PRIOR DEBATE MESSAGES:
                Round 1 — Sentiment Agent: NOGO (70% confidence)
                  They said market sentiment is too negative...
                Round 1 — Valuation Agent: GO (60% confidence)
                  They said comparables justify the valuation..."
```

The adversarial behavior comes from the **system prompt framing**: each agent is instructed to identify and challenge the weakest opposing argument specifically, rather than just re-stating its own position.

---

## Implementation Plan

### Step 1 — `models.py`

Add two new dataclasses; add one optional field to `DebateResult`:

```python
@dataclass
class DebatePosition:
    agent_name: str
    position: str          # "GO" | "NOGO"
    confidence: float      # 0.0–1.0
    rationale: str
    challenges: list[str]  # counterpoints to other agents' arguments
    round_number: int

@dataclass
class DebateRound:
    round_number: int
    positions: list[DebatePosition]
    consensus_reached: bool
    consensus_position: str | None = None
```

Add to `DebateResult`:
```python
debate_rounds: list[DebateRound] | None = None
```

### Step 2 — Each Agent (`search_agent.py`, `sentiment_agent.py`, `valuation_agent.py`)

Purely additive — `run()` is untouched. Add to each agent class:

1. **Class constant**: `agent_name: str = "Search Agent"` (or Sentiment/Valuation)
2. **Two debate system prompt constants** (risk-neutral + risk-averse variants), scoped to the agent's domain:
   - Domain framing: Search → founders/market-gap; Sentiment → press/community; Valuation → market-size/comparables
   - Adversarial instruction: challenge weakest opposing argument; allow position change only if genuinely persuaded
   - Output format: JSON `{position, confidence, rationale, challenges}`
3. **`_debate_system_prompt(rt) -> str`** helper
4. **`_format_debate_history(debate_history: list[dict]) -> str`** helper (serializes history to readable text)
5. **`debate_turn(company, phase1_analysis, debate_history, round_number, risk_tolerance) -> DebatePosition`**
   - Builds user message from template (company, risk_tolerance, round_number, phase1_analysis[:2000], formatted history)
   - Calls `self._llm.messages_create()`
   - Strips markdown fences, parses JSON
   - Returns `DebatePosition`; on any parse error returns fallback `DebatePosition(position="NOGO", confidence=0.0, ...)`

### Step 3 — `orchestrator/orchestrator.py`

1. Add `max_rounds: int = 3` to `__init__`; store as `self.max_rounds`
2. Add `_run_debate(company, risk_tolerance, phase1_map, max_rounds) -> tuple[list[DebateRound], str, bool]`:
   - Round-robin order: Search → Sentiment → Valuation → repeat
   - Each turn calls `agent.debate_turn(...)` and appends to `debate_history: list[dict]`
   - After each full round, call `_check_consensus()` → if True, return early
   - After `max_rounds` exceeded, call `_majority_vote()` on final round; `consensus_reached=False`
3. Add `_check_consensus(positions: list[DebatePosition]) -> tuple[bool, str | None]`
4. Add `_majority_vote(debate_rounds: list[DebateRound]) -> str` (uses final round; defaults to NOGO on tie)
5. Update `run()` Phase 2 to call `_run_debate()` instead of `_judge_reports()`; populate `DebateResult.debate_rounds` and real `rounds` count
6. Keep `_judge_reports()` in place (dead code, but `app.py` currently calls it directly — removal is a separate cleanup)

### Step 4 — `app.py`

1. **Sidebar**: Add `max_rounds = st.slider("Max debate rounds", 1, 5, 3)` below existing controls
2. **Run block**: Replace the `_judge_reports()` call with:
   - Instantiate `Orchestrator(risk_tolerance, max_rounds)`
   - Build `phase1_map = {agent_name: msg.content}` from already-run Phase 1 results
   - Call `orchestrator._run_debate(company, risk_tolerance, phase1_map, max_rounds)`
   - Show per-round progress in `st.status()`: `"Round N: Search: GO, Sentiment: NOGO, Valuation: GO (no consensus)"`
   - Build `DebateResult` with real `rounds`, `consensus_reached`, `debate_rounds`
3. **Results section**: Insert "Debate Rounds" between verdict banner and Phase 1 analysis:
   - `st.expander(f"Round {N} — {consensus_label}", expanded=(N==1))`
   - Inside: each agent's position in colored text, rationale, bulleted challenges
4. **`_generate_report()`**: Add Phase 2 debate section to markdown export

### Step 5 — Tests

New test files (follow existing `unittest.mock.patch` pattern from `tests/`):

- `tests/agents/test_debate_turn.py`: test `debate_turn()` for each agent — happy path GO/NOGO, parse-error fallback, risk-averse prompt selection
- `tests/orchestrator/test_debate_loop.py`: test `_run_debate()` — round-1 consensus, round-3 consensus, max-rounds majority-vote fallback, `_check_consensus()`, `_majority_vote()`
- `tests/test_models.py` (or append to existing): `DebatePosition` and `DebateRound` instantiation, `DebateResult.debate_rounds` default is `None`

---

## Critical Files

| File | Change type |
|------|-------------|
| `models.py` | Add `DebatePosition`, `DebateRound`; extend `DebateResult` |
| `agents/search_agent.py` | Add `agent_name`, debate prompts, `debate_turn()` |
| `agents/sentiment_agent.py` | Same as search_agent.py |
| `agents/valuation_agent.py` | Same as search_agent.py |
| `orchestrator/orchestrator.py` | Replace Phase 2; add `_run_debate`, `_check_consensus`, `_majority_vote` |
| `app.py` | Add slider; replace judge call; add Debate Rounds UI section; update report |
| `tests/agents/test_debate_turn.py` | New |
| `tests/orchestrator/test_debate_loop.py` | New |

---

## Verification

1. `streamlit run app.py` → enter a company → verify Debate Rounds section appears with expandable rounds showing per-agent GO/NOGO + rationale + challenges
2. Set `max_rounds=1` → verify exactly 1 round runs even without consensus
3. `pytest tests/` passes — especially debate loop consensus paths and parse-error fallback
4. `ruff check . && mypy .` clean
5. Download report → verify debate section present in markdown
