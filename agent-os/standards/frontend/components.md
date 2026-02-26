## Streamlit UI Components

- **Page structure:** Use `st.set_page_config()` at the top of `app.py`; organize into pages via `st.navigation()` or tabs
- **Sidebar:** Configuration inputs (company name, risk tolerance, orchestration mode) live in `st.sidebar`
- **Agent output display:** Each agent's message rendered in its own `st.expander()` labeled with agent name and round number
- **Debate progress:** Use `st.status()` or `st.spinner()` to show live debate progress; stream Sentiment Agent output with `st.write_stream()`
- **Final verdict:** Display GO/NOGO/NO_CONSENSUS verdict as a large colored `st.metric()` or `st.success()`/`st.error()`/`st.warning()`
- **Report download:** `st.download_button()` for markdown report export after each run
- **Reusable components:** Extract repeated UI patterns (e.g., agent message card) into functions in `ui/components.py`
