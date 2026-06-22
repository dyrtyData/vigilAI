# vigilAI — Agent Instructions

## Project

vigilAI is a Brazil PL 2338/2023 AI compliance evaluator built for the Global South AI Safety Hackathon (June 2026). It is a fork of COMPL-AI (ETH Zurich / INSAIT / LatticeFlow AI), built on the UK AI Safety Institute's Inspect AI framework. All 30 original COMPL-AI tasks (EU AI Act, 9 technical requirements) are preserved so EU↔Brazil comparisons run on the same model.

Brazil-specific additions: `human_deception_brazil` (Art. 5, I — AI disclosure in Portuguese), `bbq_brazil` (Art. 5, III — IBGE racial categories + regional + intersectional bias), `explanation_quality` (Art. 6, I — right to explanation), `contestation_review` (Art. 6, II-III — right to contest + human review), `aia_checklist` (Arts. 25-28 — AIA obligations). The compliance report (`vigilai report`) renders a per-article scorecard with EU↔Brazil deltas. Key source layout: `src/vigilai/` (package), `src/vigilai/brazil/` (mapping, benchmarks), `src/vigilai/report/` (aggregator), `tools/` (CLI entry points). Run with `uv run vigilai`.

## Memory — on session start

Search mem0 for relevant context before starting any work:

```
search_memory("project constraints vigilAI", user_id=$DEFAULT_USER_ID, app_id=$DEFAULT_APP_ID)
search_memory("architecture decisions", user_id=$DEFAULT_USER_ID, app_id=$DEFAULT_APP_ID)
search_memory("known issues blockers", user_id=$DEFAULT_USER_ID, app_id=$DEFAULT_APP_ID)
```

Surface whatever is found. If nothing comes back, proceed with the project description above as the baseline context.

## Memory — during the session

When you discover or decide something worth preserving, add it immediately:

- Architecture decisions (task structure, scoring path, report aggregation logic)
- Gotchas (e.g., Inspect AI solver/scorer quirks, `brazil_article` decorator-first resolution, `EU_BRAZIL_PAIRS` constant)
- Design constraints (COMPL-AI requirement names must stay unchanged; `Societal Alignment` used as host for contestation/AIA without polluting other tasks)
- Benchmark content provenance (bbq_brazil scenarios are authored for vigilAI; no Portuguese BBQ dataset exists yet)
- Failures and debugging findings
- Team conventions (code style, test patterns, CLI patterns)

```
add_memory("<concise description of the decision or finding>",
           user_id=$DEFAULT_USER_ID, app_id=$DEFAULT_APP_ID)
```

## Memory — on session end

If meaningful work was done, add a session summary:

```
add_memory("Session <date>: <what changed>, <what was decided>, <what's still pending>",
           user_id=$DEFAULT_USER_ID, app_id=$DEFAULT_APP_ID)
```

## Constraints always in effect

- COMPL-AI's nine `technical_requirement` category names must not change — EU benchmarks must stay comparable.
- `brazil_article` is resolved **decorator-first** in both `vigilai list --brazil` and `vigilai report`. Never set it only in the requirement→article mapping for tasks that would pull in unrelated tasks.
- `EU_BRAZIL_PAIRS` in `brazil_report.py` is the single source of truth for the side-by-side delta — only pairs that reuse the exact same scorer belong there.
- `bbq_brazil` scenarios are a hand-built pilot (22 scenarios, 44 samples). Full native-annotator validation is documented future work; do not overstate the sample size.
- `.env` (with `ANTHROPIC_API_KEY`) is gitignored and never committed.
- The mock backend (`mockllm/model`) must always produce deterministic results; the test suite runs without any API key.
