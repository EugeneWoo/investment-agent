# Tasks: Project Scaffold and Secrets Management

## Overview

Total task groups: 5
Total tasks: 22

**Group dependencies:**
- Group 1 (Project Configuration) — no dependencies; start here
- Group 2 (Directory Skeleton) — depends on Group 1 (pyproject.toml must exist before packages are created)
- Group 3 (Config Module) — depends on Group 2 (directory skeleton must exist; tests rely on conftest.py fixture)
- Group 4 (Streamlit & Environment Files) — depends on Group 1 (independent of Groups 2–3; can run in parallel with Group 3)
- Group 5 (Tests) — depends on Group 3 (tests validate config.py logic)

---

## Group 1: Project Configuration [DONE]

**Goal:** Create `pyproject.toml` as the single source of truth for project metadata, dependencies, and tool configuration. Run `uv sync` to generate the lockfile.

**Acceptance criteria:**
- `pyproject.toml` exists at the project root with `requires-python = ">=3.11"`.
- All six production dependencies are declared: `anthropic`, `tavily-python`, `praw`, `tweepy`, `streamlit`, `python-dotenv`.
- Dev dependencies are declared under `[dependency-groups]`: `pytest`, `pytest-mock`, `ruff`, `mypy`.
- `[tool.ruff]` section sets `target-version = "py311"` and `line-length = 88` with both lint and format rules enabled.
- `[tool.mypy]` section sets `strict = true` and `ignore_missing_imports = true` for third-party libraries lacking stubs.
- `[tool.pytest.ini_options]` sets `testpaths = ["tests"]`.
- `uv sync` runs without error and generates `uv.lock`.
- `uv run ruff check .`, `uv run ruff format .`, `uv run mypy .`, and `uv run pytest` all resolve without "command not found" errors.

### Tasks

**1.1** [DONE] Write `pyproject.toml` with `[project]` metadata section: `name`, `version`, `requires-python = ">=3.11"`, and `description`.

**1.2** [DONE] Add production dependencies to `[project].dependencies` in `pyproject.toml`: `anthropic`, `tavily-python`, `praw`, `tweepy`, `streamlit`, `python-dotenv`.

**1.3** [DONE] Add dev dependencies under `[dependency-groups.dev]` in `pyproject.toml`: `pytest`, `pytest-mock`, `ruff`, `mypy`. Add stub packages `types-requests` where available.

**1.4** [DONE] Add `[tool.ruff]` section to `pyproject.toml` with `target-version = "py311"`, `line-length = 88`, and `select` list enabling lint rules (e.g., `["E", "F", "I", "UP"]`) and format settings.

**1.5** [DONE] Add `[tool.mypy]` section to `pyproject.toml` with `strict = true`, `python_version = "3.11"`, and `ignore_missing_imports = true`.

**1.6** [DONE] Add `[tool.pytest.ini_options]` section to `pyproject.toml` with `testpaths = ["tests"]`.

**1.7** [DONE] Run `uv sync` to install all dependencies and generate `uv.lock`. Confirm the lockfile is created.

---

## Group 2: Directory Skeleton [DONE]

**Goal:** Create all package directories, `__init__.py` files, and placeholder source files so the project tree matches the architecture defined in the spec.

**Acceptance criteria:**
- `app.py` exists and contains a minimal Streamlit entry point that imports `config` and calls `st.title()`.
- `agents/__init__.py`, `orchestrator/__init__.py`, `tools/__init__.py`, `ui/__init__.py` all exist as empty files.
- `models.py` exists with `AgentMessage` and `DebateResult` dataclasses using only the standard library `dataclasses` module, with all typed fields from the spec.
- `config.py` exists as a placeholder (full implementation in Group 3).
- `tests/conftest.py` exists with a `mock_settings` fixture returning a `Settings`-compatible object.
- `tests/agents/__init__.py`, `tests/orchestrator/__init__.py`, `tests/tools/__init__.py` all exist as empty files.
- `uv run ruff check .` reports no errors on the skeleton files.

### Tasks

**2.1** [DONE] Create `agents/__init__.py`, `orchestrator/__init__.py`, `tools/__init__.py`, and `ui/__init__.py` as empty files.

**2.2** [DONE] Create `models.py` with `AgentMessage` dataclass (fields: `agent_name: str`, `content: str`, `role: str`) and `AnalysisResult` dataclass (fields: `verdict: str`, `messages: list[AgentMessage]`, `agent_summaries: dict[str, str]`) as the primary Phase 1 result. Also include `DebateResult` (fields: `verdict: str`, `rounds: int`, `messages: list[AgentMessage]`, `consensus_reached: bool`) as a lower-priority placeholder for Phase 2. Uses only `from dataclasses import dataclass`.

**2.3** [DONE] Create `app.py` with a minimal Streamlit entry point: imports `streamlit as st` and `config`, then calls `st.title("Investment Agent")`.

**2.4** [DONE] Create `config.py` as an empty placeholder module with a single comment indicating it will be implemented in the next task group. (Full implementation in Group 3.)

**2.5** [DONE] Create `tests/__init__.py` (empty), `tests/agents/__init__.py` (empty), `tests/orchestrator/__init__.py` (empty), and `tests/tools/__init__.py` (empty).

**2.6** [DONE] Create `tests/conftest.py` with a `mock_settings` pytest fixture that returns a `Settings`-compatible object with all six API key fields set to placeholder strings (e.g., `"test-key"`).

---

## Group 3: Config Module [DONE]

**Goal:** Implement `config.py` with the `load_secrets()` function, `Settings` dataclass, and module-level singleton. The fallback chain must be: `st.secrets` → `os.environ` (populated by `load_dotenv`) → `RuntimeError`.

**Acceptance criteria:**
- `load_secrets()` tries `st.secrets[key]` first, catching both `FileNotFoundError` and `KeyError` without raising.
- `load_secrets()` calls `load_dotenv()` and then falls back to `os.environ.get(key)`.
- `load_secrets()` raises `RuntimeError` with a message that names the specific missing key when a key is absent from all sources.
- `Settings` is a dataclass with all six keys as typed `str` attributes: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `CRUNCHBASE_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `TWITTER_BEARER_TOKEN`.
- A module-level `settings` singleton is created at import time by calling `load_secrets()`.
- `from config import settings` works and returns a `Settings` instance.
- All 6 tests in `tests/test_config.py` pass.

### Tasks

**3.1** [DONE] Write 6 focused tests in `tests/test_config.py` covering `load_secrets()` behaviour:
  - Test 1: all six keys present in `os.environ` returns a `Settings` instance with correct values.
  - Test 2: `st.secrets` returns a key value that takes priority over `os.environ`.
  - Test 3: `st.secrets` raises `FileNotFoundError` → fallback to `os.environ` succeeds without raising.
  - Test 4: `st.secrets` raises `KeyError` for a specific key → fallback to `os.environ` succeeds for that key.
  - Test 5: one key missing from all sources raises `RuntimeError` naming that specific key.
  - Test 6: `RuntimeError` message includes the exact missing key name (string assertion).

**3.2** [DONE] Implement `Settings` dataclass in `config.py` with all six fields typed as `str`.

**3.3** [DONE] Implement the `load_secrets()` function body: iterate over the six required key names, attempt `st.secrets[key]` inside a `try/except (FileNotFoundError, KeyError)`, fall back to `os.environ.get(key)` (calling `load_dotenv()` once before the loop), collect missing keys, raise `RuntimeError` naming the first missing key.

**3.4** [DONE] Add the module-level singleton `settings: Settings = load_secrets()` at the bottom of `config.py` so it executes at import time.

**3.5** [DONE] Run `uv run pytest tests/test_config.py -v` and confirm all 6 tests pass.

---

## Group 4: Streamlit and Environment Files [DONE]

**Goal:** Create all environment and configuration files needed for local development and production deployment, and ensure sensitive files are excluded from version control.

**Acceptance criteria:**
- `.streamlit/secrets.toml` exists with all six required key names set to `"YOUR_KEY_HERE"` placeholder values.
- `.streamlit/config.toml` exists with `[server]` section (`headless = true`, `port = 8501`) and `[theme]` section with sensible defaults.
- `.env.example` exists documenting all six required environment variable names with descriptive placeholder values and no real credentials.
- `.gitignore` exists and excludes: `.env`, `.streamlit/secrets.toml`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.venv/`, `dist/`.
- `.streamlit/secrets.toml` is confirmed absent from `git status` tracked files (covered by `.gitignore`).

### Tasks

**4.1** [DONE] Create `.streamlit/` directory and `.streamlit/secrets.toml` with all six key names assigned `"YOUR_KEY_HERE"` as placeholder values.

**4.2** [DONE] Create `.streamlit/config.toml` with a `[server]` section (`headless = true`, `port = 8501`) and a `[theme]` section (e.g., `base = "dark"` or light with primary colour set).

**4.3** [DONE] Create `.env.example` documenting all six required variable names with descriptive placeholder comments above each entry and no real credentials.

**4.4** [DONE] Create `.gitignore` at the project root listing: `.env`, `.streamlit/secrets.toml`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.venv/`, `dist/`.

---

## Group 5: Full Quality Pipeline Verification [DONE]

**Goal:** Confirm that all four quality tools run cleanly across the completed codebase and the full test suite passes.

**Acceptance criteria:**
- `uv run pytest` exits with code 0 (all tests pass, no collection errors).
- `uv run ruff check .` exits with code 0 (no lint violations).
- `uv run ruff format --check .` exits with code 0 (no formatting changes needed).
- `uv run mypy .` exits with code 0 or only emits known `# type: ignore`-suppressed errors for third-party stubs.

### Tasks

**5.1** [DONE] Run `uv run pytest` from the project root and confirm all tests collected and passed with exit code 0. Fix any import or fixture errors before proceeding.

**5.2** [DONE] Run `uv run ruff check .` and resolve any lint violations in `config.py`, `models.py`, `app.py`, or test files.

**5.3** [DONE] Run `uv run ruff format --check .` and apply `uv run ruff format .` if any files are not formatted correctly.

**5.4** [DONE] Run `uv run mypy .` and add `# type: ignore` annotations or adjust `pyproject.toml` mypy overrides for any third-party library errors (`praw`, `tweepy`, `streamlit`). Confirm exit code 0.
