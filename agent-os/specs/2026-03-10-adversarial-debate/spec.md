# Specification: Adversarial Debate (Phase 2)

## Goal
Replace the current single-call Judge with a true round-robin adversarial debate where each agent reads prior positions, challenges the weakest opposing argument, and updates its GO/NOGO stance until consensus is reached or `max_rounds` is exceeded.

## User Stories
- As an investor, I want to see agents challenge each other's positions across multiple rounds so that the final verdict reflects adversarial scrutiny rather than a single Judge call.
- As an investor, I want to control the maximum number of debate rounds so that I can trade off analysis depth against time.

## Specific Requirements

**New model dataclasses in `models.py`**
- Add `DebatePosition` dataclass with fields: `agent_name: str`, `position: str` (GO|NOGO), `confidence: float` (0.0–1.0), `rationale: str`, `challenges: list[str]`, `round_number: int`
- Add `DebateRound` dataclass with fields: `round_number: int`, `positions: list[DebatePosition]`, `consensus_reached: bool`, `consensus_position: str | None = None`
- Add `debate_rounds: list[DebateRound] | None = None` field to the existing `DebateResult` dataclass — all other fields on `DebateResult` remain unchanged

**`agent_name` class constant on each agent**
- Add `agent_name: str` as a class-level constant to `SearchAgent`, `SentimentAgent`, and `ValuationAgent` (e.g. `"Search Agent"`, `"Sentiment Agent"`, `"Valuation Agent"`)
- This constant is used by the orchestrator to populate `DebatePosition.agent_name` without coupling to string literals scattered across the orchestrator

**Debate system prompts per agent**
- Add two module-level constants per agent file: `DEBATE_SYSTEM_PROMPT_RISK_NEUTRAL` and `DEBATE_SYSTEM_PROMPT_RISK_AVERSE`
- Each prompt is scoped to that agent's analysis domain (founder/market for Search, sentiment for Sentiment, valuation/return for Valuation)
- Prompts must instruct the LLM to: review prior round positions, identify the weakest opposing argument, challenge it specifically, then output `{position, confidence, rationale, challenges}` as valid JSON
- Add a `_debate_system_prompt(risk_tolerance: str) -> str` helper method that selects the correct constant

**`_format_debate_history()` helper per agent**
- Add `_format_debate_history(debate_history: list[dict]) -> str` as an instance method on each agent
- Formats the accumulated round history into a readable string for inclusion in the debate turn user message
- Output should include round number, agent name, position, confidence, rationale, and challenges for each prior turn

**`debate_turn()` method per agent**
- Add `debate_turn(company: str, phase1_analysis: str, debate_history: list[dict], round_number: int, risk_tolerance: str) -> DebatePosition` to each agent class
- Single-shot `AnthropicClient.messages_create()` call — no tool use, no Tavily calls during debate
- User message must include: company, risk_tolerance, round_number, `phase1_analysis[:2000]`, and formatted debate history
- Parse the LLM JSON response into a `DebatePosition`; on any parse error return a safe fallback `DebatePosition(position="NOGO", confidence=0.0, rationale="Parse error", challenges=[], round_number=round_number)`
- Reuse the existing `_extract_json()` utility already present in `search_agent.py`; replicate the same pattern in the other two agent files

**`_run_debate()` method on `Orchestrator`**
- Add `_run_debate(company: str, risk_tolerance: str, phase1_map: dict[str, AgentMessage], max_rounds: int) -> tuple[list[DebateRound], str, bool]` to `Orchestrator`
- Round-robin order: Search Agent → Sentiment Agent → Valuation Agent, repeated each round
- Maintain `debate_history: list[dict]` that grows each turn; each dict captures agent name, position, confidence, rationale, challenges, and round number
- After each full round (all three agents have spoken), call `_check_consensus()` — exit early if consensus reached
- On `max_rounds` exceeded without consensus, call `_majority_vote()` to determine the final verdict; default NOGO on a tie
- Return `(debate_rounds, final_verdict, consensus_reached)`

**`_check_consensus()` and `_majority_vote()` on `Orchestrator`**
- Add `_check_consensus(positions: list[DebatePosition]) -> tuple[bool, str | None]`: returns `(True, "GO"|"NOGO")` when all positions agree, else `(False, None)`
- Add `_majority_vote(debate_rounds: list[DebateRound]) -> str`: tallies all positions across all rounds, returns the majority; defaults to `"NOGO"` on a tie

**`max_rounds` parameter and `run()` Phase 2 wiring in `Orchestrator`**
- Add `max_rounds: int = 3` to `Orchestrator.__init__`
- Update `run()` to call `_run_debate()` after Phase 1 completes, passing the three `AgentMessage` objects as `phase1_map`
- Populate `DebateResult.debate_rounds` with the returned `list[DebateRound]` and set `rounds` to the actual number of debate rounds executed
- Keep `_judge_reports()` unchanged — `app.py` currently calls it directly and it must remain accessible

**Sidebar slider and `_run_debate()` wiring in `app.py`**
- Add `max_rounds = st.slider("Max debate rounds", 1, 5, 3)` to the sidebar, below the existing divider
- After Phase 1 agents complete, replace the `_judge_reports()` call block with a call to `orchestrator._run_debate(company, risk_tolerance, phase1_map, max_rounds)`
- Construct `phase1_map` as `{msg.agent_name: msg for msg in phase1_messages}` before calling `_run_debate()`
- Update `st.session_state["run_config"]` to include `max_rounds`

**Debate progress display in `st.status()`**
- During `_run_debate()`, emit per-round progress text into the existing `st.status()` block: `"Round N: Search: GO (0.8), Sentiment: NOGO (0.6), Valuation: GO (0.7) — no consensus"` or `"Round N: consensus reached — GO"`
- Pass a `status_callback: Callable[[str], None] | None = None` parameter to `_run_debate()` so the orchestrator can remain UI-agnostic; `app.py` passes `st.write`

**"Debate Rounds" section in results UI**
- Insert a "Debate Rounds" subsection between the verdict banner and the "Agent Analysis" expanders
- Render one `st.expander(f"Round {n} — {'Consensus' if r.consensus_reached else 'No Consensus'}", expanded=(n == 1))` per `DebateRound` in `result.debate_rounds`
- Inside each expander, show each agent's position in colored text (GO = green, NOGO = red), confidence as a percentage, rationale paragraph, and challenges as a bulleted list
- Skip this section entirely when `result.debate_rounds` is `None` or empty (backward compatible with existing results in session state)

**`_generate_report()` markdown export update**
- Extend the existing `_generate_report()` function to append a "## Debate Rounds" section when `result.debate_rounds` is not `None`
- For each round, output a markdown table or heading with agent name, position, confidence, rationale, and challenges

**Tests**
- `tests/agents/test_debate_turn.py`: happy-path GO and NOGO parsing, parse-error fallback returning `NOGO/0.0`, risk-averse prompt selection via `_debate_system_prompt()`; mock `AnthropicClient.messages_create`
- `tests/orchestrator/test_debate_loop.py`: round-1 consensus exits early, round-3 consensus, max-rounds exceeded triggers majority-vote fallback, `_check_consensus()` with all-GO / mixed / all-NOGO inputs, `_majority_vote()` with tie defaulting to NOGO
- Append to `tests/test_models.py`: `DebatePosition` and `DebateRound` instantiation with all required fields, `DebateResult.debate_rounds` defaults to `None`

## Existing Code to Leverage

**`models.py` — `AgentMessage`, `DebateResult` dataclasses**
- `AgentMessage` is already used across all agents and the orchestrator; the new `DebatePosition` should follow the same `@dataclass` pattern with `from __future__ import annotations`
- `DebateResult` receives only an additive `debate_rounds` field; all current consumers (`app.py`, tests) remain valid because the field defaults to `None`

**`orchestrator.py` — `_format_phase1_summary()` and `_judge_reports()`**
- `_format_phase1_summary()` already converts `list[AgentMessage]` to a readable string; pass its output (truncated to 2000 chars) as `phase1_analysis` to each `debate_turn()` call
- `_judge_reports()` must not be removed; `app.py` calls it directly and it serves as a fallback path

**`search_agent.py` — `_extract_json()` utility and dual system prompt pattern**
- The module-level `_extract_json()` function and the `SYSTEM_PROMPT_RISK_NEUTRAL` / `SYSTEM_PROMPT_RISK_AVERSE` dual-constant pattern are already established; replicate this exact structure for the new `DEBATE_SYSTEM_PROMPT_*` constants in all three agent files
- The `run()` method's pattern of selecting a prompt via `rt == "risk_averse"` should be mirrored in `_debate_system_prompt()`

**`app.py` — `st.status()` block and session state keys**
- The existing `with st.status("Running analysis...", expanded=True) as status:` block is where debate progress writes should go; use `st.write()` calls consistent with the existing agent progress messages
- Session state keys `"debate_result"`, `"agent_messages"`, and `"run_config"` are already established; extend `"run_config"` with `max_rounds` rather than adding new keys

**`app.py` — `_render_agent_output()` and `_generate_report()`**
- The color/icon pattern in `_render_agent_output()` (e.g. `{"positive": "🟢", "mixed": "🟡", "negative": "🔴"}`) should be mirrored for GO/NOGO coloring in the debate rounds UI
- `_generate_report()` currently iterates `result.messages`; the debate section should be appended after the existing Judge Verdict section using the same markdown heading style

## Out of Scope
- Modifying or wrapping the existing `run()` method on any agent class
- Removing or altering `_judge_reports()` in the orchestrator
- Changing the Phase 1 parallel agent execution logic in `app.py`
- Agent-to-agent direct communication (orchestrator remains the sole message bus)
- Tool use (Tavily, Crunchbase, Reddit, Twitter) during debate turns
- Streaming or real-time token output during debate turns
- Persisting debate results to a database or external storage
- Authentication, user accounts, or multi-user session management
- Changes to `tools/`, `config.py`, or any file not listed in the requirements
