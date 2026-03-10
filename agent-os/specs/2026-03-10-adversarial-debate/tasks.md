# Tasks: Adversarial Debate (Phase 2) — COMPLETED ✅

**Important:** All implementation lives in `adversarial_debate/` subfolder (with underscores). Existing codebase is NOT modified.

## Overview

The debate mechanism is a **round-robin adversarial debate** where:
1. Phase 1: Three agents (Search, Sentiment, Valuation) run independently (existing behavior)
2. Phase 2: Each agent reads prior positions, challenges the weakest opposing argument, and updates their GO/NOGO stance
3. Debate continues until **consensus** (all agents agree) OR **max_rounds** exceeded
4. If no consensus after max_rounds, a **majority vote** determines the final verdict

Each agent outputs a `DebatePosition` with:
- `position`: "GO" or "NOGO"
- `confidence`: 0.0-1.0
- `rationale`: reasoning for their position
- `challenges`: list of specific arguments they're challenging

## File Structure

```
adversarial_debate/
├── __init__.py
├── models.py                    # DebatePosition, DebateRound - extends parent models.py
├── agents/
│   ├── __init__.py
│   ├── search_debate_agent.py   # Adds debate_turn() via composition
│   ├── sentiment_debate_agent.py
│   └── valuation_debate_agent.py
├── orchestrator.py              # DebateOrchestrator - runs debate loop
├── app_debate.py                # Separate Streamlit entrypoint
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_agents.py           # debate_turn() tests
    └── test_orchestrator.py     # debate loop, consensus, majority vote tests
```

---

## Completed Tasks ✅

### 1. Create debate models (adversarial_debate/models.py)
- [x] Create `DebatePosition` dataclass with fields: `agent_name`, `position`, `confidence`, `rationale`, `challenges`, `round_number`
- [x] Create `DebateRound` dataclass with fields: `round_number`, `positions`, `consensus_reached`, `consensus_position`
- [x] Export both classes for use by orchestrator and agents
- [x] Add docstrings explaining each field

### 2. Create Search Debate Agent (adversarial_debate/agents/search_debate_agent.py)
- [x] Import parent `SearchAgent` from `agents.search_agent`
- [x] Create `SearchDebateAgent` class that wraps `SearchAgent` via composition
- [x] Add `DEBATE_SYSTEM_PROMPT_RISK_NEUTRAL` constant (founder/market focused)
- [x] Add `DEBATE_SYSTEM_PROMPT_RISK_AVERSE` constant (stricter scrutiny)
- [x] Add `_debate_system_prompt(risk_tolerance)` helper method
- [x] Add `_format_debate_history(debate_history)` method to format prior rounds
- [x] Add `debate_turn(company, phase1_analysis, debate_history, round_number, risk_tolerance) -> DebatePosition` method
- [x] Implement JSON parsing with fallback to safe `DebatePosition(position="NOGO", confidence=0.0, ...)`
- [x] Include `_extract_json()` utility (copy from parent `search_agent.py`)

### 3. Create Sentiment Debate Agent (adversarial_debate/agents/sentiment_debate_agent.py)
- [x] Import parent `SentimentAgent` from `agents.sentiment_agent`
- [x] Create `SentimentDebateAgent` class that wraps `SentimentAgent` via composition
- [x] Add `DEBATE_SYSTEM_PROMPT_RISK_NEUTRAL` constant (sentiment focused)
- [x] Add `DEBATE_SYSTEM_PROMPT_RISK_AVERSE` constant
- [x] Add `_debate_system_prompt(risk_tolerance)` helper method
- [x] Add `_format_debate_history(debate_history)` method
- [x] Add `debate_turn()` method with same signature as Search
- [x] Implement JSON parsing with fallback

### 4. Create Valuation Debate Agent (adversarial_debate/agents/valuation_debate_agent.py)
- [x] Import parent `ValuationAgent` from `agents.valuation_agent`
- [x] Create `ValuationDebateAgent` class
- [x] Add `DEBATE_SYSTEM_PROMPT_RISK_NEUTRAL` constant (valuation/return focused)
- [x] Add `DEBATE_SYSTEM_PROMPT_RISK_AVERSE` constant
- [x] Add `_debate_system_prompt(risk_tolerance)` helper method
- [x] Add `_format_debate_history(debate_history)` method
- [x] Add `debate_turn()` method with same signature as others
- [x] Implement JSON parsing with fallback

### 5. Create Debate Orchestrator (adversarial_debate/orchestrator.py)
- [x] Import parent `Orchestrator` from `orchestrator.orchestrator`
- [x] Import debate agents and models
- [x] Create `DebateOrchestrator` class that wraps parent `Orchestrator`
- [x] Add `_check_consensus(positions) -> (bool, str|None)` method
- [x] Add `_majority_vote(debate_rounds) -> str` method (defaults to "NOGO" on tie)
- [x] Add `_run_debate(company, risk_tolerance, phase1_map, max_rounds, status_callback) -> (list[DebateRound], str, bool)` method
- [x] Implement round-robin: Search → Sentiment → Valuation, repeat
- [x] After each full round, check consensus and exit early if reached
- [x] Call status_callback with progress text each round
- [x] Override `run()` method to call `_run_debate()` after Phase 1

### 6. Create Streamlit UI (adversarial_debate/app_debate.py)
- [x] Copy structure from parent `app.py`
- [x] Add `max_rounds` slider in sidebar (1-5, default 3)
- [x] Use `DebateOrchestrator` instead of `Orchestrator`
- [x] Update status messages to show debate progress per round
- [x] Add "Debate Rounds" section between verdict and agent analysis
- [x] Render each round as expander with positions (GO=green, NOGO=red)
- [x] Show confidence as percentage, rationale, and challenges as bullets
- [x] Update `_generate_report()` to include debate rounds section
- [x] Skip debate section if `result.debate_rounds` is None/empty (backward compat)

### 7. Write tests (adversarial_debate/tests/)
- [x] Create `conftest.py` with fixtures for `DebatePosition`, `DebateRound`
- [x] Create `test_agents.py`:
  - [x] Test happy-path GO and NOGO parsing for each agent
  - [x] Test parse-error fallback returning NOGO/0.0
  - [x] Test `_debate_system_prompt()` selects correct constant
  - [x] Mock `AnthropicClient.messages_create`
- [x] Create `test_orchestrator.py`:
  - [x] Test round-1 consensus exits early
  - [x] Test round-3 consensus path
  - [x] Test max_rounds exceeded triggers majority vote
  - [x] Test `_check_consensus()` with all-GO / mixed / all-NOGO inputs
  - [x] Test `_majority_vote()` with tie defaulting to NOGO
  - [x] Mock debate agents for deterministic testing

### 8. Verification ✅
- [x] Run `PYTHONPATH=. pytest adversarial_debate/tests/` — all 26 tests pass
- [x] Run `streamlit run adversarial_debate/app_debate.py` — UI loads without errors
- [x] Imports work correctly with path handling
- [x] Consensus detection works (all GO / all NOGO / mixed)
- [x] Majority vote defaults to NOGO on tie

---

## Usage

**Run tests:**
```bash
PYTHONPATH=. pytest adversarial_debate/tests/ -v
```

**Run the debate app:**
```bash
streamlit run adversarial_debate/app_debate.py
```

**Run the original app (unchanged):**
```bash
streamlit run app.py
# OR just:
streamlit run  # app.py is the default
```

The two apps are completely independent and don't interfere with each other. Note: `streamlit run` without arguments uses `app.py` as the default, so you need to explicitly specify `adversarial_debate/app_debate.py` to run the debate version.

---

## Key Design Decisions

1. **Subfolder isolation**: The `adversarial_debate/` folder (with underscores for Python imports) is completely self-contained. Parent codebase remains untouched.
2. **Composition over inheritance**: Debate agents wrap parent agents via composition, not subclassing. This keeps parent classes clean.
3. **Reuse parent orchestrator internals**: `DebateOrchestrator` calls parent methods like `_format_phase1_summary()` and `_judge_reports()`.
4. **Status callback pattern**: Orchestrator accepts optional `status_callback` for UI-agnostic progress updates.
5. **Backward compatibility**: Parent `app.py` continues to work unchanged. `app_debate.py` is a separate entrypoint.

## Notes

- The parent `models.py` already has `DebateResult` with `rounds`, `messages`, `consensus_reached`. We use this directly without extending.
- Parent agents already have dual system prompts (`RISK_NEUTRAL`, `RISK_AVERSE`). Debate agents follow this pattern.
- `_extract_json()` utility from `search_agent.py` is replicated in each debate agent for self-containment.
- Python cannot import modules with hyphens in names, so the folder uses underscores (`adversarial_debate`) even though the spec refers to it as `adversarial-debate`.
