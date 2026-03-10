"""Adversarial Debate Streamlit App — separate entrypoint for debate mode.

Run with: streamlit run adversarial_debate/app_debate.py

This app is identical to the base app.py but adds:
- max_rounds slider in sidebar
- Debate progress display during analysis
- "Debate Rounds" section in results
"""

from __future__ import annotations

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

# Add repo root to path for imports
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import config  # noqa: F401 — validates API keys at startup
from models import DebateResult

logging.basicConfig(level=logging.INFO)


def _escape_dollars(text: str) -> str:
    """Escape $ signs to prevent LaTeX rendering in Streamlit."""
    if not text:
        return text
    # Replace $ with \$ to prevent LaTeX interpretation
    return text.replace("$", "\\$")


# --- Helper functions (defined first to avoid F821) ---

def _render_agent_output(agent_name: str, data: dict) -> None:  # type: ignore[type-arg]
    """Render structured agent JSON output in a readable format."""
    if agent_name == "Search Agent":
        company = data.get("company", {})
        st.markdown(f"**{company.get('name', 'Unknown')}** — {_escape_dollars(company.get('description', ''))}")
        st.caption(f"Funding stage: {company.get('funding_stage', 'unknown')}")

        fa = data.get("founder_analysis", {})
        ma = data.get("market_analysis", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Founder Quality", fa.get("founder_quality_score", "N/A"))
        c2.metric("Market Gap", ma.get("market_gap_score", "N/A"))
        c3.metric("Bandwagon Risk", ma.get("bandwagon_risk_score", "N/A"))
        c4.metric("Defensibility", ma.get("defensibility_score", "N/A"))

        if fa.get("narrative"):
            st.markdown(f"**Founders**: {_escape_dollars(fa['narrative'])}")
        if ma.get("differentiation"):
            st.markdown(f"**Differentiation**: {_escape_dollars(ma['differentiation'])}")
        if ma.get("bandwagon_evidence"):
            st.markdown("**Bandwagon signals**: " + " · ".join(_escape_dollars(s) for s in ma["bandwagon_evidence"]))

        founders = data.get("founders", [])
        if founders:
            st.markdown("**Founders:**")
            for f in founders:
                commitment_icon = {"full-time": "🟢", "part-time": "🔴", "unknown": "🟡"}.get(
                    f.get("commitment_level", "unknown"), "🟡"
                )
                st.markdown(
                    f"- **{f.get('name', '?')}** ({f.get('role', '?')}) "
                    f"{commitment_icon} {f.get('commitment_level', 'unknown')} · "
                    f"Relevance: {f.get('relevance_score', 'N/A')}/100"
                )
                if f.get("background"):
                    st.caption(f.get("background", ""))

    elif agent_name == "Sentiment Agent":
        s = data.get("sentiment", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Sentiment", s.get("overall_sentiment_score", "N/A"))
        c2.metric("Press", s.get("press_score", "N/A"))
        c3.metric("Community", s.get("community_score", "N/A"))
        c4.metric("Momentum", s.get("momentum_score", "N/A"))

        verdict_icon = {"positive": "🟢", "mixed": "🟡", "negative": "🔴"}.get(
            s.get("verdict", ""), "🟡"
        )
        st.markdown(f"**Verdict**: {verdict_icon} {s.get('verdict', 'unknown').title()}")
        if s.get("narrative"):
            st.markdown(_escape_dollars(s["narrative"]))
        if s.get("red_flags"):
            st.markdown("**Red flags**: " + " · ".join(_escape_dollars(f) for f in s["red_flags"]))

    elif agent_name == "Valuation Agent":
        v = data.get("valuation", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Attractiveness", v.get("overall_attractiveness_score", "N/A"))
        c2.metric("Market Size", v.get("market_size_score", "N/A"))
        c3.metric("Comparables", v.get("comparable_score", "N/A"))
        c4.metric("Stage Fit", v.get("stage_fit_score", "N/A"))

        if v.get("tam_estimate"):
            st.markdown(f"**TAM**: {_escape_dollars(v['tam_estimate'])}")
        if v.get("return_potential"):
            st.markdown(f"**Upside**: {_escape_dollars(v['return_potential'])}")
        if v.get("key_risks"):
            st.markdown("**Key risks**: " + " · ".join(_escape_dollars(r) for r in v["key_risks"][:3]))
        if v.get("comparables"):
            st.markdown("**Comparables**: " + ", ".join(
                _escape_dollars(f"{c['name']} ({c.get('outcome', '?')})") for c in v["comparables"][:3]
            ))

    # Debate position rendering
    elif "position" in data and "confidence" in data:
        # This is a debate turn output
        position = data.get("position", "NOGO")
        confidence = data.get("confidence", 0.0)
        rationale = data.get("rationale", "")
        challenges = data.get("challenges", [])

        position_color = "🟢" if position == "GO" else "🔴"
        st.markdown(f"**Position**: {position_color} {position} (confidence: {confidence:.1%})")
        if rationale:
            st.markdown(_escape_dollars(rationale))
        if challenges:
            st.markdown("**Challenges**:")
            for c in challenges:
                st.markdown(f"- {_escape_dollars(c)}")

    summary_key = next((k for k in data if k.endswith("_summary")), None)
    if summary_key:
        st.info(_escape_dollars(data[summary_key]))


def _generate_report(result: DebateResult, config_used: dict) -> str:  # type: ignore[type-arg]
    """Generate a markdown report from the analysis result."""
    company = config_used.get("company", "Unknown")
    risk_tolerance = config_used.get("risk_tolerance", "unknown")
    max_rounds = config_used.get("max_rounds", 3)
    lines = [
        f"# Investment Analysis: {company}",
        f"**Risk Tolerance**: {risk_tolerance}  ",
        f"**Max Debate Rounds**: {max_rounds}  ",
        f"**Verdict**: {result.verdict}  ",
        f"**Consensus Reached**: {'Yes' if result.consensus_reached else 'No'}  ",
        "",
        "---",
        "",
        "## Agent Analysis",
        "",
    ]
    for msg in result.messages:
        if msg.role == "analyst":
            lines.append(f"### {msg.agent_name}")
            try:
                data = json.loads(msg.content)
                summary_key = next((k for k in data if k.endswith("_summary")), None)
                if summary_key:
                    lines.append(f"> {data[summary_key]}")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(data, indent=2))
                lines.append("```")
            except json.JSONDecodeError:
                lines.append(msg.content)
            lines.append("")

    # Add debate rounds section if available
    debate_msgs = [m for m in result.messages if m.role == "debate"]
    if debate_msgs:
        lines += ["---", "", "## Debate Rounds", ""]
        for msg in debate_msgs:
            try:
                data = json.loads(msg.content)
                position = data.get("position", "?")
                confidence = data.get("confidence", 0.0)
                rationale = data.get("rationale", "")
                challenges = data.get("challenges", [])

                lines.append(f"### {msg.agent_name}")
                lines.append(f"**Position**: {position} (confidence: {confidence:.1%})")
                lines.append(f"**Rationale**: {rationale}")
                if challenges:
                    lines.append("**Challenges**:")
                    for c in challenges:
                        lines.append(f"- {c}")
                lines.append("")
            except json.JSONDecodeError:
                lines.append(msg.content)
                lines.append("")

    return "\n".join(lines)


def _render_debate_rounds(result: DebateResult) -> None:
    """Render debate rounds section in the UI."""
    # Group debate messages by round
    debate_msgs = [m for m in result.messages if m.role == "debate"]
    if not debate_msgs:
        return

    st.divider()
    st.subheader("Debate Rounds")

    # Group positions by round number
    positions_by_round: dict[int, list[dict]] = {}
    max_round = result.rounds

    for msg in debate_msgs:
        try:
            data = json.loads(msg.content)
            round_num = data.get("round_number", 1)
            if round_num not in positions_by_round:
                positions_by_round[round_num] = []
            positions_by_round[round_num].append({
                "agent_name": msg.agent_name,
                "data": data
            })
        except json.JSONDecodeError:
            continue

    # Render each round
    for round_num in range(1, max_round + 1):
        with st.expander(f"**Round {round_num}**", expanded=(round_num == 1)):
            if round_num in positions_by_round and positions_by_round[round_num]:
                for pos in positions_by_round[round_num]:
                    st.markdown(f"##### {pos['agent_name']}")
                    data = pos['data']
                    position = data.get("position", "NOGO")
                    confidence = data.get("confidence", 0.0)
                    rationale = data.get("rationale", "")
                    challenges = data.get("challenges", [])

                    position_color = "🟢" if position == "GO" else "🔴"
                    st.markdown(f"**Position**: {position_color} {position} (confidence: {confidence:.1%})")
                    if rationale:
                        st.markdown(_escape_dollars(rationale))
                    if challenges:
                        st.markdown("**Challenges**:")
                        for c in challenges:
                            st.markdown(f"- {_escape_dollars(c)}")
                    st.markdown("---")
            else:
                st.info("This round was not required — consensus reached earlier.")


# --- Page setup ---

st.set_page_config(page_title="Investment Agent — Adversarial Debate", layout="wide")
st.markdown(
    "<style>[data-testid='stSidebar'] { min-width: 220px; max-width: 220px; }</style>",
    unsafe_allow_html=True,
)
st.title("Investment Agent — Adversarial Debate")
st.caption("Multi-agent analysis with round-robin adversarial debate")

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    risk_tolerance = st.radio(
        "Risk Tolerance",
        options=["risk_neutral", "risk_averse"],
        format_func=lambda x: "Balanced (Risk Neutral)" if x == "risk_neutral" else "Conservative (Risk Averse)",
        help="Risk Neutral gives startups the benefit of the doubt. Risk Averse applies stricter scrutiny.",
    )
    st.divider()

    max_rounds = st.slider(
        "Max debate rounds",
        min_value=1,
        max_value=5,
        value=3,
        help="Maximum number of debate rounds before majority vote. Debate ends early if consensus is reached.",
    )
    st.divider()

    input_mode = st.radio(
        "Input type",
        options=["company", "topic"],
        format_func=lambda x: "Specific company" if x == "company" else "Topic / space",
        help="Specific company: analyze one startup. Topic / space: analyze a theme and get 3 company recommendations on GO.",
    )
    st.divider()
    st.caption("3 independent agents → adversarial debate → consensus or majority vote")

# --- Input ---
_placeholder = "e.g. Anthropic, Harvey AI" if input_mode == "company" else "e.g. AI medical imaging, legal AI startups"
company = st.text_input(
    "Company name" if input_mode == "company" else "Topic or space",
    placeholder=_placeholder,
    key="company_input",
)

run_btn = st.button("Analyze", type="primary", disabled=not st.session_state.get("company_input", "").strip())

# --- Run analysis ---
if run_btn and company:
    from adversarial_debate.orchestrator import DebateOrchestrator

    st.session_state.pop("debate_result", None)
    st.session_state.pop("agent_messages", None)

    with st.status("Running analysis...", expanded=True) as status:
        try:
            orchestrator = DebateOrchestrator(risk_tolerance=risk_tolerance, max_rounds=max_rounds)

            st.write("Checking eligibility...")
            eligible, ineligible_reason = orchestrator.eligibility_check(company)
            if not eligible:
                status.update(label="Company not eligible", state="error")
                st.error(f"**Not eligible for analysis:** {ineligible_reason}")
                st.stop()

            def status_callback(msg: str) -> None:
                """Callback to update status during debate."""
                st.write(msg)

            result = orchestrator.run(company, risk_tolerance, status_callback=status_callback)

            st.session_state["debate_result"] = result
            st.session_state["agent_messages"] = [m for m in result.messages if m.role == "analyst"]
            st.session_state["run_config"] = {
                "company": company,
                "risk_tolerance": risk_tolerance,
                "max_rounds": max_rounds,
            }
            status.update(label="Analysis complete!", state="complete")

        except Exception as e:
            status.update(label=f"Error: {e}", state="error")
            st.error(f"Analysis failed: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.stop()

# --- Results ---
if "debate_result" in st.session_state:
    result = st.session_state["debate_result"]
    config_used = st.session_state.get("run_config", {})

    st.divider()

    verdict = result.verdict
    if verdict == "GO":
        st.success("## GO — Recommend Investing")
    else:
        st.error("## NO-GO — Pass on this investment")

    # Consensus info
    if result.consensus_reached:
        st.caption(f"✓ Consensus reached in {result.rounds} round(s)")
    else:
        st.caption(f"⚠ No consensus after {result.rounds} round(s) — majority vote")

    if verdict == "GO" and result.recommendations:
        st.divider()
        st.subheader("Companies to Investigate")
        for rec in result.recommendations:
            st.markdown(f"- {rec}")

    # Render debate rounds
    _render_debate_rounds(result)

    st.divider()

    # Agent analysis
    st.subheader("Agent Analysis")
    for msg in [m for m in result.messages if m.role == "analyst"]:
        with st.expander(f"**{msg.agent_name}**", expanded=False):
            try:
                data = json.loads(msg.content)
                _render_agent_output(msg.agent_name, data)
            except json.JSONDecodeError:
                st.text(msg.content)

    # Export
    st.divider()
    report = _generate_report(result, config_used)
    st.download_button(
        "Download Report (Markdown)",
        data=report,
        file_name=f"investment_analysis_{config_used.get('company', 'unknown').replace(' ', '_')}_debate.md",
        mime="text/markdown",
    )
