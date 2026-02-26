## Validation

- **API inputs:** Validate required API keys are present at startup before making any requests; fail fast with clear message naming the missing key
- **User inputs (Streamlit):** Validate ticker/company name, risk tolerance selection, and orchestration mode before triggering debate run
- **Agent outputs:** Validate that LLM responses contain expected fields (GO/NOGO signal, confidence score, rationale) before passing to next round; re-prompt once if malformed
- **Comparable data:** Validate that Valuation Agent has at least 2 comparable companies before computing return/volatility estimates; surface warning if fewer
- **Debate consensus:** A valid GO/NOGO consensus requires all agents to agree; partial agreement is not consensus
