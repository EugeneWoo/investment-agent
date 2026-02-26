# Spec Requirements: Project Scaffold and Secrets Management

## Initial Description

Project Scaffold and Secrets Management — Set up the Python 3.11+ project with `pyproject.toml`, `uv` package management, `ruff`/`mypy` linting, `pytest` test structure, and `.streamlit/secrets.toml` local secrets wiring. Verify all API keys (Anthropic, Tavily, Crunchbase, Reddit, Twitter/X) are loadable and validated at startup.

## Requirements Discussion

### First Round Questions

**Q: Why `pyproject.toml` instead of `requirements.txt`?**
A: The project uses `uv` as the package manager, which is modern Python tooling that natively supports `pyproject.toml` (PEP 517/518/621). This enables unified configuration for dependencies, dev dependencies, linting, and type checking in a single file.

**Q: Why `uv` as the package manager?**
A: `uv` is a fast, modern Python package manager that provides deterministic installs, lockfile support, and is well-suited to production deployments including Streamlit Community Cloud.

**Q: How should secrets be managed across local dev and production?**
A: The `config.py` module will attempt to load secrets from `st.secrets` first (available when running on Streamlit Cloud or locally with `.streamlit/secrets.toml`), falling back to `os.environ` and `.env` file for local development without Streamlit. This dual-path strategy supports all environments without code changes.

**Q: Which API keys must be validated at startup?**
A: Six keys are required: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `CRUNCHBASE_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `TWITTER_BEARER_TOKEN`. Any missing key raises a clear error at import time naming the specific missing key.

**Q: Should `ruff` handle both linting and formatting?**
A: Yes. `ruff` replaces both `flake8` and `black`, configured for Python 3.11 target and line-length 88 (matching black defaults). `mypy` handles static type checking separately.

**Q: Should the Crunchbase API integration use an official SDK?**
A: No official Crunchbase Python SDK is listed. The `CRUNCHBASE_API_KEY` is validated at startup; the actual HTTP client will be implemented in a later spec.

**Q: Is a database required for this project?**
A: No. The application is entirely stateless — no database, no session persistence. All state lives within a single Streamlit session.

### Existing Code to Reference

No similar existing features identified for reference. This is a greenfield project.

### Follow-up Questions

None needed.

## Visual Assets

No visual assets provided.

## Requirements Summary

### Functional Requirements

1. Python 3.11+ project initialized with `pyproject.toml` as the single source of truth for project metadata, dependencies, and tool configuration.
2. `uv` used as the package manager; a `uv.lock` lockfile is generated on first install.
3. Production dependencies declared in `pyproject.toml`: `anthropic`, `tavily-python`, `praw`, `tweepy`, `streamlit`, `python-dotenv`.
4. Development dependencies declared in `pyproject.toml` under `[dependency-groups]` or `[project.optional-dependencies]`: `pytest`, `pytest-mock`, `ruff`, `mypy`.
5. `ruff` configured for Python 3.11 target and line-length 88, covering both lint and format rules, via `[tool.ruff]` in `pyproject.toml`.
6. `mypy` configured via `[tool.mypy]` in `pyproject.toml` with strict mode enabled.
7. Project directory structure created:
   - `app.py` — minimal Streamlit placeholder that imports `config` and calls `st.title()`
   - `agents/__init__.py` — empty package
   - `orchestrator/__init__.py` — empty package
   - `tools/__init__.py` — empty package
   - `ui/__init__.py` — empty package
   - `models.py` — placeholder dataclasses `AgentMessage` and `DebateResult`
   - `config.py` — secrets loading and validation module
   - `tests/conftest.py` — pytest configuration and shared fixtures
   - `tests/agents/` — empty test subpackage
   - `tests/orchestrator/` — empty test subpackage
   - `tests/tools/` — empty test subpackage
8. `.streamlit/secrets.toml` template created with all required keys present, values set to empty strings or placeholder strings (file excluded from git).
9. `.streamlit/config.toml` created with `[server]` layout set to `"wide"` and sensible theme defaults.
10. `.env.example` documents all six required environment variable names with descriptive placeholder values.
11. `.gitignore` excludes: `.env`, `.streamlit/secrets.toml`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.venv/`, `dist/`.
12. `config.py` implements a `load_secrets()` function that:
    - Attempts `st.secrets[key]` first, catching `FileNotFoundError` / `KeyError` gracefully
    - Falls back to `os.environ.get(key)` / `python-dotenv` `.env` file
    - Raises `RuntimeError` with a descriptive message naming any missing required key
    - Exposes a validated `Settings` dataclass or named tuple with all six keys as typed attributes
    - Is invoked at module import time so failures surface immediately on app start

### Reusability Opportunities

- `config.py` `Settings` object will be imported by every agent, tool, and orchestrator module that needs API credentials — designed as a singleton accessible via a single import.
- `models.py` dataclasses (`AgentMessage`, `DebateResult`) form the shared message-passing contract for all future agent and orchestrator implementations.
- `tests/conftest.py` will define shared pytest fixtures (e.g., mock `Settings`, mock API clients) reused across all test subpackages.

### Scope Boundaries

**In Scope:**
- `pyproject.toml` with all dependency and tool configuration
- `uv` lockfile generation
- Full directory and package skeleton
- `.streamlit/secrets.toml` template, `.streamlit/config.toml`, `.env.example`, `.gitignore`
- `config.py` secrets loading and startup validation
- `models.py` placeholder dataclasses
- `app.py` minimal Streamlit entry point
- `tests/` skeleton with `conftest.py` and subpackage directories
- `ruff` and `mypy` configuration

**Out of Scope:**
- Any actual agent logic or LLM calls
- Streamlit UI beyond a single placeholder title
- Any real API calls to Anthropic, Tavily, Crunchbase, Reddit, or Twitter/X
- Database setup or persistent storage of any kind
- Deployment configuration (Streamlit Cloud `secrets.toml` population)
- CI/CD pipeline setup
- Docker or container configuration

### Technical Considerations

- `st.secrets` raises `FileNotFoundError` when `.streamlit/secrets.toml` is absent and raises `KeyError` for missing keys; both must be caught in the fallback logic within `config.py`.
- `python-dotenv` should be called with `load_dotenv()` before `os.environ` reads to ensure `.env` values are available in local dev without Streamlit.
- The `.streamlit/secrets.toml` template must never contain real credentials and must be listed in `.gitignore` before the file is committed.
- `pyproject.toml` should pin a minimum Python version (`requires-python = ">=3.11"`) to prevent accidental use of older interpreters.
- `mypy` strict mode may require `# type: ignore` annotations for third-party libraries lacking stubs (e.g., `praw`, `tweepy`); stub packages (`types-*`) should be added as dev dependencies where available.
- `ruff` format replaces `black`; both `ruff check` and `ruff format` should be runnable via `uv run ruff check .` and `uv run ruff format .` respectively.
- `pytest` should be runnable via `uv run pytest` with test discovery configured for the `tests/` directory.
- All `__init__.py` files in `agents/`, `orchestrator/`, `tools/`, `ui/` should be empty to avoid circular import issues as the project grows.
