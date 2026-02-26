## Coding Style

- **Naming:** `snake_case` for variables, functions, modules; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants
- **Type hints:** Required on all function signatures (parameters and return types)
- **Line length:** 88 characters (ruff default)
- **Imports:** Group as stdlib → third-party → local, separated by blank lines; use absolute imports
- **Functions:** Small and single-purpose; prefer pure functions for agent logic
- **No dead code:** Remove unused imports, variables, and commented-out blocks
- **Dataclasses / TypedDicts:** Use for structured agent messages and debate state objects rather than bare dicts
- **f-strings:** Preferred over `.format()` or `%` formatting
- **Agent system prompts:** Define as module-level constants (all caps), not inline strings
