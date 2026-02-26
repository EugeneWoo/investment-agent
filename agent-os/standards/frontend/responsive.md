## Streamlit Layout

- **Column layout:** Use `st.columns()` for side-by-side agent outputs in collaboration mode
- **Debate timeline:** Display debate rounds vertically (top to bottom) in chronological order
- **Wide mode:** Enable `layout="wide"` in `st.set_page_config()` for better use of screen space on desktop
- **Mobile:** Streamlit Community Cloud is primarily desktop-viewed; no special mobile optimization required, but avoid fixed pixel widths in custom CSS
