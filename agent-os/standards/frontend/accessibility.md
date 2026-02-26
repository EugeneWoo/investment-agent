## Streamlit Accessibility

- **Labels:** All `st.text_input`, `st.selectbox`, `st.radio`, and `st.button` calls must include a descriptive `label` argument (never empty string)
- **Help text:** Use `help=` parameter on inputs to explain what each field expects
- **Error states:** Use `st.error()` for failures, `st.warning()` for partial results, `st.info()` for in-progress states — never silent failures
- **Loading states:** Always show `st.spinner()` or `st.status()` during API calls so users know the app is working
