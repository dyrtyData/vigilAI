# AGENTS.md

Project-level agent guidance for vigilAI. See `CLAUDE.md` for the product overview,
memory workflow, and hard constraints (COMPL-AI requirement names, `brazil_article`
decorator-first resolution, `EU_BRAZIL_PAIRS`, deterministic mock backend, etc.). Those
constraints still apply.

## Cursor Cloud specific instructions

The VM startup update script runs `uv sync`, so dependencies are already installed when a
session begins. The notes below are the non-obvious things to know when developing here.

### Environment / tooling

- This is a Python project (3.11–3.13; the VM uses 3.12) managed with
  [`uv`](https://docs.astral.sh/uv/). `uv` lives at `~/.local/bin` and is already on `PATH`
  (the installer added `. "$HOME/.local/bin/env"` to `~/.bashrc`). No manual activation is
  needed.
- The environment is defined by `uv.lock`. `uv sync` is the source of truth — it installs the
  `dev` dependency group too. Note `uv sync` and `uv pip install -e .` are NOT equivalent:
  `uv sync` prunes packages not in the lock, so always prefer `uv sync`.
- `uv run <cmd>` re-syncs the environment against `uv.lock` before running, so you normally
  don't need a separate install step — just `uv run vigilai ...` / `uv run pytest`.
- First-time dependency resolution is heavy: it downloads `torch` (~500 MB) and builds several
  git-sourced deps (`inspect-evals`, `llm-rules`, `strong_reject`, `livebench`) plus a spaCy
  model wheel. This needs network access. After the snapshot it is fast/idempotent.

### Run / test / build

- Run the app (deterministic, no API key needed): evaluate then report, e.g.
  `uv run vigilai eval mockllm/model --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist --limit 5`
  then `uv run vigilai report logs/<run-dir>` (add `--json` or `--html`). See `README.md` for
  the full command set and `uv run vigilai --help`.
- Tests: `uv run pytest` (or `make test`). The suite (~173 tests) is deterministic against
  `mockllm/model` and requires no API key or network.
- There is no build step (it's a CLI package). `list`/`eval`/`report` are the entry points.

### Gotchas

- `mockllm/model` always yields `0.000` scores. That is expected and correct for wiring/CI —
  the scores are meaningless by design. Real scores need a live backend: `ANTHROPIC_API_KEY`
  in a gitignored `.env` (copy `.env.example`) for `anthropic/claude-haiku-4-5`, or a local
  Ollama server for `ollama/llama3.1:8b`. Neither is required for tests or the demo flow.
- Lint tooling is not wired up: `[tool.mypy]` and `[tool.typos]` exist in `pyproject.toml`
  but `mypy`/`typos` are not installed dependencies, and there is no `.pre-commit-config.yaml`
  (so `make hooks` / `pre-commit install` will fail). `uv run pytest` is the checks workflow.
