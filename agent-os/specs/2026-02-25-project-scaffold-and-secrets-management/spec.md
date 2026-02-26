# Specification: Project Scaffold and Secrets Management

## Goal

Initialize the `investment-agent` Python project with a complete directory skeleton, unified `pyproject.toml` configuration, `uv` package management, `ruff`/`mypy` tooling, and a `config.py` module that validates all six required API keys at startup across local and production environments.

## User Stories

- As a developer, I want to run `uv sync` and have all dependencies installed from a lockfile so that the environment is reproducible across machines.
- As a developer, I want `config.py` to raise a clear error naming any missing API key at import time so that misconfigured environments fail fast before any agent runs.
- As a developer, I want `pytest`, `ruff check`, `ruff format`, and `mypy` all runnable via `uv run` so that the full quality pipeline works from a single tool.

## Specific Requirements

**pyproject.toml Configuration**
- Sets `requires-python = ">=3.11"` to prevent use on older interpreters.
- Declares production dependencies: `anthropic`, `tavily-python`, `praw`, `tweepy`, `streamlit`, `python-dotenv`.
- Declares development dependencies (`pytest`, `pytest-mock`, `ruff`, `mypy`) under `[dependency-groups]` or `[project.optional-dependencies]`.
- Configures `[tool.ruff]` with `target-version = "py311"` and `line-length = 88`, enabling both lint and format rules.
- Configures `[tool.mypy]` with strict mode enabled.
- Configures `[tool.pytest.ini_options]` with `testpaths = ["tests"]` for test discovery.

**uv Package Management**
- `uv` is the required package manager; `uv sync` installs all dependencies from `pyproject.toml`.
- A `uv.lock` lockfile is generated on first install and committed to the repository.
- Running `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, and `uv run mypy .` must all work after `uv sync`.

**Directory and Package Skeleton**
- `app.py` — minimal Streamlit entry point that imports `config` and calls `st.title()` with the app name.
- `agents/__init__.py` — empty package file.
- `orchestrator/__init__.py` — empty package file.
- `tools/__init__.py` — empty package file.
- `ui/__init__.py` — empty package file.
- `models.py` — placeholder `AgentMessage` and `AnalysisResult` dataclasses with typed fields matching the architecture in `CLAUDE.md`. (`AnalysisResult` covers Phase 1 sequential output; `DebateResult` is an optional extension for Phase 2 debate.)
- `config.py` — secrets loading and validation module (see Config Module requirement).
- `tests/conftest.py` — pytest configuration with shared fixtures (e.g., mock `Settings`, mock API clients).
- `tests/agents/`, `tests/orchestrator/`, `tests/tools/` — empty test subpackages (each with `__init__.py`).

**Config Module (`config.py`)**
- Implements a `load_secrets()` function that loads all six required keys: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `CRUNCHBASE_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `TWITTER_BEARER_TOKEN`.
- Attempts `st.secrets[key]` first, catching both `FileNotFoundError` and `KeyError` gracefully before falling back.
- Falls back to `os.environ.get(key)` after calling `load_dotenv()` from `python-dotenv` to populate `.env` values.
- Raises `RuntimeError` with a descriptive message naming the specific missing key if any required key is absent after all fallbacks.
- Exposes a validated `Settings` dataclass or named tuple with all six keys as typed `str` attributes.
- `load_secrets()` is invoked at module import time so failures surface immediately on app startup.
- `Settings` instance is accessible as a module-level singleton (e.g., `from config import settings`).

**Streamlit Configuration Files**
- `.streamlit/secrets.toml` template created with all six required key names present, values set to empty strings or clearly labelled placeholder strings (e.g., `"YOUR_KEY_HERE"`). This file must be listed in `.gitignore` before it is committed.
- `.streamlit/config.toml` created with `[server]` section setting `layout = "wide"` and sensible theme defaults.

**Environment and Git Configuration**
- `.env.example` documents all six required environment variable names with descriptive placeholder values (never real credentials).
- `.gitignore` excludes: `.env`, `.streamlit/secrets.toml`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.venv/`, `dist/`.

**models.py Placeholder Dataclasses**
- `AgentMessage` dataclass includes typed fields sufficient for inter-agent message passing (e.g., `agent_name`, `content`, `role`).
- `AnalysisResult` dataclass includes typed fields for the Phase 1 pipeline output (e.g., `verdict`, `messages`, `agent_summaries`). This is the primary result type.
- `DebateResult` dataclass includes typed fields for the Phase 2 debate outcome (e.g., `verdict`, `rounds`, `messages`, `consensus_reached`) — deferred, lower priority.
- All dataclasses use standard library `dataclasses` module only — no third-party dependencies.

**Secrets Fallback Strategy**
- `st.secrets` is tried first; `FileNotFoundError` (no `secrets.toml`) and `KeyError` (key missing) are both caught separately.
- `load_dotenv()` is called before any `os.environ` reads to ensure `.env` file values are available in local dev without Streamlit running.
- The fallback chain is: `st.secrets` → `os.environ` (populated by `load_dotenv`) → `RuntimeError`.

**mypy and ruff Compatibility**
- Dev dependencies include stub packages (`types-*`) where available for third-party libraries used in type-checked modules.
- Third-party libraries lacking stubs (e.g., `praw`, `tweepy`) are handled with `# type: ignore` annotations or `ignore_missing_imports = true` scoped appropriately in `[tool.mypy]`.

## Visual Design

No visual mockups provided.

## Existing Code to Leverage

Greenfield project — no existing code to leverage.

## Out of Scope

- Any agent logic or LLM calls to the Anthropic API.
- Streamlit UI beyond a single placeholder `st.title()` call in `app.py`.
- Real API calls to Tavily, Crunchbase, Reddit, or Twitter/X.
- Full implementation of tool wrappers (`tools/tavily.py`, `tools/crunchbase.py`, etc.).
- Full implementation of `agents/`, `orchestrator/`, or `ui/` modules beyond empty `__init__.py` files.
- Database setup or any form of persistent storage.
- Deployment configuration (populating Streamlit Cloud secrets manager).
- CI/CD pipeline setup (GitHub Actions or equivalent).
- Docker or container configuration.
- `REDDIT_USER_AGENT` secret (deferred to the Reddit tool spec).
