"""Investment Agent — Streamlit dashboard for Seed-to-Series B AI startup analysis."""

from __future__ import annotations

import json
import logging

import streamlit as st

import config  # noqa: F401 — validates API keys at startup
from models import DebateResult

logging.basicConfig(level=logging.INFO)


def _escape_dollars(text: str) -> str:
    """Escape $ signs so Streamlit doesn't render them as LaTeX math."""
    return text.replace("$", r"\$")


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
                f"{c['name']} ({c.get('outcome', '?')})" for c in v["comparables"][:3]
            ))

    summary_key = next((k for k in data if k.endswith("_summary")), None)
    if summary_key:
        st.info(_escape_dollars(data[summary_key]))


def _generate_report(result: DebateResult, config_used: dict) -> str:  # type: ignore[type-arg]
    """Generate a markdown report from the analysis result."""
    company = config_used.get("company", "Unknown")
    risk_tolerance = config_used.get("risk_tolerance", "unknown")
    lines = [
        f"# Investment Analysis: {company}",
        f"**Risk Tolerance**: {risk_tolerance}  ",
        f"**Verdict**: {result.verdict}  ",
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

    judge_msgs = [m for m in result.messages if m.role == "judge"]
    if judge_msgs:
        lines += ["---", "", "## Judge Verdict", ""]
        for msg in judge_msgs:
            lines.append(msg.content)
            lines.append("")

    return "\n".join(lines)


# --- Page setup ---

st.set_page_config(page_title="Investment Agent", layout="wide")
st.title("Investment Agent")
st.caption("Multi-agent analysis for Seed-to-Series B AI startups")

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
    input_mode = st.radio(
        "Input type",
        options=["company", "topic"],
        format_func=lambda x: "Specific company" if x == "company" else "Topic / space",
        help="Specific company: analyze one startup. Topic / space: analyze a theme and get 3 company recommendations on GO.",
    )
    st.divider()
    st.caption("3 independent agents → Judge issues GO/NOGO")

# --- Input ---
_placeholder = "e.g. Anthropic, Harvey AI" if input_mode == "company" else "e.g. AI medical imaging, legal AI startups"
company = st.text_input(
    "Company name" if input_mode == "company" else "Topic or space",
    placeholder=_placeholder,
)

run_btn = st.button("Analyze", type="primary", disabled=not company)

# --- Run analysis ---
if run_btn and company:
    from agents.search_agent import SearchAgent
    from agents.sentiment_agent import SentimentAgent
    from agents.valuation_agent import ValuationAgent
    from orchestrator.orchestrator import Orchestrator

    st.session_state.pop("debate_result", None)
    st.session_state.pop("agent_messages", None)

    with st.status("Running analysis...", expanded=True) as status:
        try:
            orchestrator = Orchestrator(risk_tolerance=risk_tolerance)

            search_agent = SearchAgent(risk_tolerance)
            sentiment_agent = SentimentAgent(risk_tolerance)
            valuation_agent = ValuationAgent(risk_tolerance)

            st.write("🔍 Search Agent: analyzing founders and market gap...")
            search_msg = search_agent.run(company, risk_tolerance)
            st.write("✓ Search Agent complete")

            st.write("📰 Sentiment Agent: analyzing press and community...")
            sentiment_msg = sentiment_agent.run(company, risk_tolerance)
            st.write("✓ Sentiment Agent complete")

            st.write("📊 Valuation Agent: analyzing market size and comparables...")
            valuation_msg = valuation_agent.run(company, risk_tolerance)
            st.write("✓ Valuation Agent complete")

            st.write("⚖️ Judge: reviewing all three reports...")
            phase1_messages = [search_msg, sentiment_msg, valuation_msg]
            full_analysis = orchestrator._format_phase1_summary(phase1_messages)
            judge_msg, verdict = orchestrator._judge_reports(company, full_analysis, risk_tolerance)
            st.write("✓ Judge decision complete")

            recommendations = None
            if verdict == "GO" and input_mode == "topic":
                st.write("💡 Generating company recommendations...")
                recommendations = orchestrator._recommend_companies(company, full_analysis)
                st.write("✓ Recommendations ready")

            result = DebateResult(
                verdict=verdict,
                rounds=0,
                messages=phase1_messages + [judge_msg],
                consensus_reached=True,
                recommendations=recommendations,
            )

            st.session_state["debate_result"] = result
            st.session_state["agent_messages"] = phase1_messages
            st.session_state["run_config"] = {"company": company, "risk_tolerance": risk_tolerance}
            status.update(label="Analysis complete!", state="complete")

        except Exception as e:
            status.update(label=f"Error: {e}", state="error")
            st.error(f"Analysis failed: {e}")
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

    # Judge rationale
    judge_msgs = [m for m in result.messages if m.role == "judge"]
    if judge_msgs:
        lines = judge_msgs[0].content.strip().split("\n", 1)
        if len(lines) > 1:
            st.markdown(_escape_dollars(lines[1].strip()))

    if verdict == "GO" and result.recommendations:
        st.divider()
        st.subheader("Companies to Investigate")
        for rec in result.recommendations:
            st.markdown(f"- {rec}")

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
        file_name=f"investment_analysis_{config_used.get('company', 'unknown').replace(' ', '_')}.md",
        mime="text/markdown",
    )
