## Streamlit Styling

- **Minimal custom CSS:** Use Streamlit's native components and layout primitives before reaching for `st.markdown()` with custom HTML/CSS
- **Custom CSS:** If needed, inject via `st.markdown("<style>...</style>", unsafe_allow_html=True)` in a dedicated `ui/styles.py` function called once at app startup
- **Theme:** Use Streamlit's built-in theming via `.streamlit/config.toml`; define primary color, background, and font there
- **Colors for verdict:** GO = green (`#00C851`), NOGO = red (`#FF4444`), NO_CONSENSUS = orange (`#FF8800`) — consistent across all UI elements
