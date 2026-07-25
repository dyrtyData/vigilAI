# vigilAI Iteration 2 — Implementation Log

**The committed run record.** Every number the iteration-2 paper cites must be traceable to an
entry below: the exact command, the model id, the run config, the `logs/<run>` directory it wrote,
and the verbatim `vigilai report` output it produced. This file is deliberately tracked in git
(`.gitignore` carries an explicit negation for it) because **both machines append to it** — Diana
commits the code and API-run records, Ian commits the open-weight-run records from his machine.

> **Why this file and not the task directory.** The HumanLayer task artifacts
> (`.humanlayer/tasks/…`) are not in the repo Ian checks out, so a record kept only there could not
> be written to from his machine. This log lives in the repo, on the shared branch.

## How to resume from here

A fresh session should be able to continue with **only** this log plus the HumanLayer task
artifacts. Read, in order:

1. `.humanlayer/tasks/glo-5-global-south-ai-safety-hackathon-vigilai-brazil-ai-bill/13-structure-outline-iteration-two-credibility.md`
   — the eleven-phase structure outline. It is the authority; its own checkboxes track *phase
   completion*, while this log is the *run record*.
2. `11-design-discussion-iteration-two.md` (the ten resolved design questions) and
   `10-research-iteration-two-systems.md` (how the code worked before iteration 2).
3. `12-research-sector-overlays-and-framing.md` — the BACEN / ANVISA-CFM / CVM regulatory
   groundwork and the human-rights / decolonial-feminist literature, needed from Phase 4 onward.
4. Then this log, bottom-up: the last completed phase entry tells you where work stopped.

## Fixed facts for every entry

| | |
|---|---|
| Repo | `github.com/dyrtyData/vigilAI` (nested `vigilAI/` — commits go here, **not** to the parent `GS_AISafetyHackathon`) |
| Branch | `iteration-2` (Ian must check out the *same* branch to run Phase 9 against the expanded datasets) |
| Base commit | `455f7e991d19fb6219f11bd95c75960376a411d7` (`main`, 2026-06-30) |
| Toolchain | Python 3.11.13, `inspect-ai` 0.3.240, run via `uv run` |
| Scaled run config | `--limit 100 --epochs 10 --temperature 1.0 --seed 42` (identical for API and open-weight models, so the two halves are directly comparable) |
| Grader (Phase 6+) | `anthropic/claude-opus-4-6`, `GenerateConfig(temperature=0, seed=42)` — Opus 5 / 4.8 / 4.7 / Fable 5 **reject** `temperature`/`seed` with a 400 |
| Machine tags | Phases 1–7 `[either]` at $0 (mock model, no API key) · Phase 8 `[Diana]` (funded `ANTHROPIC_API_KEY`) · Phase 9 `[Ian]` (local Ollama weights) |
| Secrets | `.env` holds `ANTHROPIC_API_KEY`, is gitignored, and is **never** committed. `logs/` is gitignored — only extracted transcripts and `vigilai report` output enter the repo. |

---

## Per-phase record template

Copy this block for every phase. Leave a field as `n/a` rather than deleting it — a missing field
is indistinguishable from an unrecorded one.

```markdown
## Phase N — <title>  ·  [machine]  ·  <date> (America/New_York)

**Status:** complete | partial | blocked
**Commit(s):** <sha> <subject>

### Commands run

```bash
# exactly what was executed, copy-pasteable, in order
```

### Run config

| Model id | `--limit` | `--epochs` | `--temperature` | `--seed` | Other `--task-arg`s | Log dir | Wall clock | Approx. cost |
|---|---|---|---|---|---|---|---|---|
| | | | | | | `logs/…` | | |

### Verbatim `vigilai report` output

<!-- paste the Markdown tables exactly as printed — no re-typing, no rounding -->

### Automated verification

- [ ] <each check from the outline's Validation section, with its verbatim result>

### Deviations from the structure outline

<!-- state every one, with the reason. "None" is an acceptable answer; silence is not. -->

### Notes / gotchas for the next session
```

---

## Phase 1 — Standard errors end-to-end · [either] · 2026-07-25

**Status:** complete (automated verification passed; manual HTML layout check pending)
**Commit(s):** _pending — working tree, not yet committed_

Threads the standard error the scorers **already compute** from the `.eval` log header through
`TaskScore` → every aggregate → Markdown, JSON, and the HTML scorecard. No scorer decoration
changed; `_METRIC_PREFERENCE` / `_headline_metric` (the point-estimate resolution) are untouched.
This retires the hand-compiled `±` tables in `reports/RESULTS.md` and the paper: from here on every
published number is printed with its uncertainty **by the tool**.

### Commands run

```bash
# code + tests
uv run pytest tests/test_brazil_report.py
uv run pytest                                    # full suite
uv run --with mypy mypy src/vigilai/report/brazil_report.py
uv run make default-config && git diff --exit-code config/default_config.yaml

# end-to-end on the mock model ($0, no API key)
uv run vigilai eval mockllm/model \
  --tasks explanation_quality,contestation_review,aia_checklist,bbq_brazil,human_deception_brazil \
  --limit 3
uv run vigilai report logs/mockllm_model_2026-07-25T08-48-35-04-00
uv run vigilai report logs/mockllm_model_2026-07-25T08-48-35-04-00 --json
uv run vigilai report logs/mockllm_model_2026-07-25T08-48-35-04-00 --html > /tmp/scorecard.html
```

> `mypy` is not a project dependency, so it runs via `uv run --with mypy mypy …` rather than the
> bare `uv run mypy …` the outline lists (which fails with `Failed to spawn: mypy`).

### Run config

| Model id | `--limit` | `--epochs` | `--temperature` | `--seed` | Other `--task-arg`s | Log dir | Wall clock | Approx. cost |
|---|---|---|---|---|---|---|---|---|
| `mockllm/model` | 3 | default (1) | unset | unset | none | `logs/mockllm_model_2026-07-25T08-48-35-04-00` | ~6 s | **$0** |

### Verbatim `vigilai report` output

The mock model returns the same fixed completion for every sample, so every score is `0.000` and
every standard error is a **genuine** `0.000` (zero observed variance over n≥2) — the outline says
as much: the predicted stderr drop cannot be observed on `mockllm/model`. What this run verifies is
the *plumbing*, not the statistics.

```markdown
## Compliance by Brazil article

| Brazil article | Scope | Task | EU technical requirement | Score ± se |
|---|---|---|---|---|
| Art. 5, I | all_ai | `human_deception_brazil` | Disclosure of AI | 0.000 ± 0.000 |
| **Art. 5, I — mean** | all_ai |  |  | **0.000 ± 0.000** |
| Art. 5, III | all_ai | `bbq_brazil` | Representation — Absence of Bias | 0.000 ± 0.000 |
| **Art. 5, III — mean** | all_ai |  |  | **0.000 ± 0.000** |
| Art. 6, I | high_risk | `explanation_quality` | Interpretability | 0.000 ± 0.000 |
| **Art. 6, I — mean** | high_risk |  |  | **0.000 ± 0.000** |
| Art. 6, II-III | high_risk | `contestation_review` | Societal Alignment | 0.000 ± 0.000 |
| **Art. 6, II-III — mean** | high_risk |  |  | **0.000 ± 0.000** |
| Arts. 25-28 | high_risk | `aia_checklist` | Societal Alignment | 0.000 |
| **Arts. 25-28 — mean** | high_risk |  |  | **0.000** |

## EU ↔ Brazil side-by-side

| Brazil task | Brazil article | Brazil score ± se | EU task | EU score ± se | Δ (Brazil − EU) ± se |
|---|---|---|---|---|---|
| `bbq_brazil` | Art. 5, III (all_ai) | 0.000 ± 0.000 | `bbq` | — | — |
| `human_deception_brazil` | Art. 5, I (all_ai) | 0.000 ± 0.000 | `human_deception` | — | — |
| `aia_checklist` | Arts. 25-28 (high_risk) | 0.000 | _no EU equivalent_ | — | — |
| `contestation_review` | Art. 6, II-III (high_risk) | 0.000 ± 0.000 | _no EU equivalent_ | — | — |
| `explanation_quality` | Art. 6, I (high_risk) | 0.000 ± 0.000 | _no EU equivalent_ | — | — |
```

**Note the `aia_checklist` row: `0.000` with no `± se`.** That task is still **n=1** (one collapsed
sample) until Phase 4 splits it into 12, and Inspect's `stderr()` returns a *placeholder* `0` below
two observations, so the report deliberately shows no error bar there. See Deviations.

`--json` carries the new keys throughout (34 `stderr` occurrences in this run's output):
`stderr` per task, `mean_stderr` per article group, `brazil_stderr` / `eu_stderr` / `delta_stderr`
per side-by-side row, `eu_only_stderr` per coverage row. **This is a JSON schema addition** — noted
in the README.

`--html` emits the error as a muted sibling of the score badge, so the point estimate keeps its
band coloring:

```html
<td class='score'><span class="badge bad">0.000</span> <span class="se">± 0.000</span></td>
```

**Layout / arithmetic sanity check on non-degenerate numbers.** Because every mock score is
identical, a throwaway fixture run (10 samples/task, varied forced outputs, mock model, $0) was
used to confirm the propagation arithmetic and the visual weight of the `±`. Illustrative only —
**these are fixture numbers, not findings, and must never be cited**:

```markdown
| `human_deception_brazil` | Art. 5, I (all_ai) | 0.500 ± 0.167 | `human_deception` | 0.900 ± 0.100 | -0.400 ± 0.194 |
| **Art. 5, III — mean** | all_ai |  |  | **0.735 ± 0.100** |
```

That is the capability the phase exists to deliver: a −0.400 gap against a ±0.194 error bar is a
claim a reader can *check* (|Δ| ≈ 2.1 × se) rather than one they must accept.

### Automated verification

- [x] `uv run pytest tests/test_brazil_report.py` → **66 passed** in 58.22 s, including the new
      `TestStandardErrors` (21 tests).
- [x] Mock eval + report shows `± <value>` on every scored row **except the n=1 `aia_checklist`
      row** (deliberate — see Deviations); `--json` contains the `stderr` keys; `--html` contains
      `class="se"` (13 occurrences: 12 cells + the legend).
- [x] `uv run pytest` (full suite) → **198 passed** in 24.27 s, no regressions.
- [x] `uv run make default-config` → `git diff --exit-code config/default_config.yaml` clean (the
      report is not a task, so no construction default changed).
- [x] `uv run --with mypy mypy src/vigilai/report/brazil_report.py` → `Success: no issues found in
      1 source file` (`disallow_untyped_defs` is on).

### Deviations from the structure outline

1. **A standard error is suppressed below two samples.** Inspect's `stderr()` returns a
   placeholder `0` when it has fewer than two observations
   (`if (n - 1) < 1: return 0`, `inspect_ai/scorer/_metrics/std.py`). Rendering that verbatim would
   print `aia_checklist` at n=1 as `0.983 ± 0.000` — reading as *infinitely precise on a single
   observation*, which is the exact overconfidence this phase exists to remove, and worse than
   showing nothing. `_MIN_SAMPLES_FOR_STDERR = 2` in `brazil_report.py` therefore drops it, and
   `TestStandardErrors::test_single_sample_task_reports_no_stderr` pins the behaviour. Consequence
   for the outline's validation wording ("`± <value>` on every scored row"): with `--limit 3`, four
   of five rows carry `±` and the n=1 `aia_checklist` row does not. **Phase 4 makes this moot** by
   taking `aia_checklist` to 12 samples. A genuine `0.000` from two or more identically scored
   samples is a real estimate and *is* shown.
2. **Column headers gained a `± se` label** (`Score ± se`, `Δ (Brazil − EU) ± se`,
   `EU-only score ± se`) and both the Markdown and HTML views gained one sentence defining `± se`
   and stating the two pooling formulas. The outline specified only the cell format; a published
   Art. 28 artifact has to say what its `±` means without the paper next to it.
3. **`mypy` invocation** — `uv run --with mypy mypy …` (see above); `mypy` is not in
   `[dependency-groups] dev`.

### Notes / gotchas for the next session

- **The `.gitignore` trap.** `docs/task-artifacts/*` is ignored; this log is tracked only because
  of the explicit `!docs/task-artifacts/iteration-2-implementation-log.md` negation added in this
  phase. If a future file in that directory needs committing, it needs its own negation.
- **Two deliberate statistical choices are load-bearing and documented in the module docstring.**
  Aggregate errors are `None` unless *every* scored member carries one (no partial pooling — a
  group must never show an error bar narrower than its evidence); deltas add in quadrature because
  the EU and Brazil sides are independent runs.
- **Phase 6 will break `_task_score_from_log` if it is not careful.** That function reads
  `log.results.scores[0]` — literally the first scorer. Adding the LLM judge makes that an index
  into a two-element list, so the headline score becomes order-dependent. Selection must move to
  *by scorer name* (the outline specifies `_select_score`). The `stderr` read added here rides on
  the same `metrics` dict and inherits the same fix.
- **`reports/build_multimodel_scorecard.py` inherits `±` for free** — it imports the private
  renderers (`_render_article_table` / `_render_side_by_side_table` / `_render_coverage_table`) and
  `_HTML_STYLE`. But its hardcoded `MODELS` list points at iteration-1 `logs/` dirs that are
  gitignored and no longer exist on this machine, so it **cannot be run until Phase 11** rebuilds
  it against the `logs/iter2-*` runs. Its print CSS (`@page { size: Letter }`, table font 6.3 pt)
  is where the `±` most plausibly overflows a column — that is the Phase 1 manual check.
- **A fresh workspace needs `uv sync` first**, and it is slow (several minutes: torch, inspect-ai,
  polars, gensim). Budget for it before assuming a test failure is real.
