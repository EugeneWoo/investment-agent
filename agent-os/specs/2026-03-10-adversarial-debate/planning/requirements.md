# Requirements: Adversarial Debate (Phase 2)

## Overview

Replace the current fake "debate" (single Judge LLM call) with a true round-robin adversarial debate where each agent reads what the others said, challenges the weakest opposing argument, updates its GO/NOGO position, and the loop continues until consensus or `max_rounds` is exceeded.

## Source

Full implementation plan: `adversarial-debate-plan.md` (repo root)

## Functional Requirements

### Models (`models.py`)
- Add `DebatePosition` dataclass: `agent_name`, `position` (GO|NOGO), `confidence` (0.0–1.0), `rationale`, `challenges: list[str]`, `round_number`
- Add `DebateRound` dataclass: `round_number`, `positions: list[DebatePosition]`, `consensus_reached`, `consensus_position: str | None = None`
- Add `debate_rounds: list[DebateRound] | None = None` field to existing `DebateResult`

### Agents (`search_agent.py`, `sentiment_agent.py`, `valuation_agent.py`)
- Add `agent_name` class constant (e.g. `"Search Agent"`)
- Add two debate system prompt constants (risk-neutral + risk-averse variants), scoped to each agent's domain
- Add `_debate_system_prompt(rt) -> str` helper
- Add `_format_debate_history(debate_history: list[dict]) -> str` helper
- Add `debate_turn(company, phase1_analysis, debate_history, round_number, risk_tolerance) -> DebatePosition`
  - Single-shot LLM call (no tool use during debate)
  - Parse JSON `{position, confidence, rationale, challenges}`
  - Fallback `DebatePosition(position="NOGO", confidence=0.0, ...)` on parse error

### Orchestrator (`orchestrator/orchestrator.py`)
- Add `max_rounds: int = 3` to `__init__`
- Add `_run_debate(company, risk_tolerance, phase1_map, max_rounds) -> tuple[list[DebateRound], str, bool]`
  - Round-robin: Search → Sentiment → Valuation → repeat
  - Append each turn to `debate_history: list[dict]`
  - Check consensus after each full round
  - Majority-vote fallback on `max_rounds` exceeded (default NOGO on tie)
- Add `_check_consensus(positions) -> tuple[bool, str | None]`
- Add `_majority_vote(debate_rounds) -> str`
- Update `run()` Phase 2 to use `_run_debate()`; populate `DebateResult.debate_rounds` and real `rounds` count
- Keep `_judge_reports()` (dead code, `app.py` currently calls it directly)

### UI (`app.py`)
- Add `max_rounds = st.slider("Max debate rounds", 1, 5, 3)` to sidebar
- Replace `_judge_reports()` call with `orchestrator._run_debate()`
- Show per-round progress in `st.status()`: "Round N: Search: GO, Sentiment: NOGO, Valuation: GO (no consensus)"
- Add "Debate Rounds" section between verdict banner and Phase 1 analysis
  - `st.expander(f"Round {N} — {consensus_label}", expanded=(N==1))`
  - Per-agent position in colored text, rationale, bulleted challenges
- Update `_generate_report()` markdown export to include debate section

### Tests
- `tests/agents/test_debate_turn.py`: happy path GO/NOGO, parse-error fallback, risk-averse prompt selection
- `tests/orchestrator/test_debate_loop.py`: round-1 consensus, round-3 consensus, max-rounds majority-vote fallback, `_check_consensus()`, `_majority_vote()`
- `tests/test_models.py` (append): `DebatePosition`, `DebateRound` instantiation; `DebateResult.debate_rounds` defaults to `None`

## Non-Functional Requirements

- No tool use during debate turns (single-shot LLM calls only — avoids 8s+ latency per turn)
- Phase 1 `run()` methods remain untouched
- `ruff check . && mypy .` clean
- All existing tests continue to pass

## Key Design Constraints

- Pure `anthropic` SDK — no AutoGen, no LangChain
- Agents do not communicate directly; orchestrator is the message bus
- Adversarial behavior comes from system prompt framing (challenge weakest opposing argument)
- `debate_turn()` user message includes: company, risk_tolerance, round_number, phase1_analysis[:2000], formatted history
