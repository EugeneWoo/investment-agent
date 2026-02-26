## Data Persistence

This project has no database or migrations. All state is ephemeral within a Streamlit session.

### Session State
- Use `st.session_state` to persist debate results within a browser session
- Key naming: `st.session_state["debate_result"]`, `st.session_state["agent_messages"]`, `st.session_state["run_config"]`
- Clear session state when user starts a new debate run

### Report Export
- Debate reports are exported as markdown strings; provide a Streamlit download button for `.md` export
- No server-side storage; reports exist only in the user's browser session
