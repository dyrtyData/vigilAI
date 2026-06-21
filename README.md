# vigilAI

**Brazil PL 2338/2023 (AI Act) compliance evaluation for Generative AI systems.**

vigilAI is a compliance-centered LLM evaluation tool that maps model behavior to the
rights and obligations of Brazil's pending AI bill, **PL 2338/2023** — in particular the
Chapter II rights (Arts. 5-6) and the Algorithmic Impact Assessment framework (Arts. 25-28).

> **Lineage.** vigilAI is a fork of [**COMPL-AI**](https://compl-ai.org), the EU AI Act
> compliance benchmarking suite created and maintained by
> [ETH Zurich](https://www.sri.inf.ethz.ch/), [INSAIT](https://insait.ai/), and
> [LatticeFlow AI](https://latticeflow.ai/)
> ([arXiv:2410.07959](https://arxiv.org/abs/2410.07959), Apache-2.0). Like COMPL-AI, it is
> built on the UK AI Safety Institute's [Inspect AI](https://inspect.aisi.org.uk/)
> evaluation framework. The original COMPL-AI benchmark suite (30 tasks across 9 technical
> requirements) is **preserved in full** so the EU AI Act benchmarks can be run on the same
> model as the Brazil-specific benchmarks for a direct EU↔Brazil comparison.

This project was built for the **Global South AI Safety Hackathon** (Latam Governance subtrack).

## Report & media

- 📄 **Final report:** [`report/vigilai-brazil-pl2338-compliance.pdf`](report/vigilai-brazil-pl2338-compliance.pdf) ([markdown source](report/vigilai-brazil-pl2338-compliance.md)) — the full hackathon paper, including the six-model compliance dossier appendix.
- 🎬 **Video overview** (NotebookLM): <https://notebooklm.google.com/notebook/e885d8db-b69a-4395-abdf-f0de618965e8/artifact/338c5582-a26a-41c6-9a76-5e16dea4390c?utm_source=nlm_web_share&utm_medium=google_oo&utm_campaign=art_share_1>
- 🖼️ **Infographic:** [`report/Brazil_AI_Compliance_Audit_Results.png`](report/Brazil_AI_Compliance_Audit_Results.png)
- 📊 **Slides:** [`report/Certification_is_Jurisdictional.pdf`](report/Certification_is_Jurisdictional.pdf)

*The video is hosted on NotebookLM (not committed, to keep the repo lightweight); the infographic and slides were generated with NotebookLM from the report and committed here.*

## Status

- **Phase 1:** COMPL-AI forked into the `vigilai` package and CLI; all 30 original tasks
  preserved and runnable.
- **Phase 2:** Brazil PL 2338/2023 article-mapping metadata layered over the preserved EU
  technical requirements and surfaced in `vigilai list` (see the EU↔Brazil mapping below).
- **Phase 3:** `human_deception_brazil` benchmark (Art. 5, I — prior information / AI
  disclosure), with Portuguese and LGPD/PL-2338 disclosure questions, reusing the upstream
  `human_deception` scorer.
- **Phase 4:** `bbq_brazil` fairness benchmark (Art. 5, III — non-discrimination),
  a Brazil-adapted BBQ covering IBGE racial categories, regional prejudice, and
  intersectional identities (see "Brazil benchmark datasets" below).
- **Phase 5:** `explanation_quality` benchmark (Art. 6, I — high-risk right to explanation /
  LGPD Art. 20), a novel rubric benchmark scoring an explanation for the six elements an
  Art. 6 explanation must contain. **No EU/COMPL-AI counterpart exists.**
- **Phase 6:** `aia_checklist` benchmark (Arts. 25-28 — Algorithmic Impact Assessment), a
  data-driven checklist testing a model's awareness of Brazil's AIA obligations. **No
  EU/COMPL-AI counterpart exists.**
- **Phase 7:** per-`brazil_article` compliance report with an **EU↔Brazil side-by-side**
  (`vigilai report <log_dir>`), plus demo run instructions for both a local and a hosted
  backend (see "Compliance report" and "Demo" below).
- **Phase 8:** `contestation_review` benchmark (Art. 6, II + III — right to contest a
  high-risk automated decision and right to human review / LGPD Art. 20), a novel rubric
  benchmark scoring a response for the six contestation + human-review elements it must
  contain. This **completes the high-risk Art. 6 rights triad** — explanation (Art. 6, I),
  contestation (Art. 6, II), human review (Art. 6, III). **The EU AI Act has no individual
  right to contest a model output, so there is no EU/COMPL-AI counterpart** — the literal
  "beyond the EU" differentiator.

## Brazil benchmark datasets

The Brazil-specific benchmarks are **self-contained and offline** (the scenarios live in
code, so mock-model evals and the test suite run deterministically with no network access).

**`bbq_brazil` (Art. 5, III).** A Brazil-adapted [BBQ](https://aclanthology.org/2022.findings-acl.165/)
(Parrish et al., ACL Findings 2022) bias benchmark in Portuguese. It reuses the *exact same*
scoring path as the upstream `bbq` task (Inspect AI's `multiple_choice()` solver +
`choice()` scorer), so the EU↔Brazil delta isolates purely the Brazil-specific content. It
covers three category groups that the US-centric upstream BBQ omits (research §6 gaps):

| Category group | Coverage (research §9) |
|---|---|
| `Race_IBGE` | IBGE "cor ou raça" categories — branco, pardo, preto, negro, indígena, amarelo, quilombola |
| `Region` | Regional prejudice — nordestino (e sotaque nordestino), nortista, baiano vs. paulistano/carioca/sulista/centro-oeste |
| `Intersectional` | Compound identities — mulher negra, parda nordestina, negro do Norte, trabalhadora doméstica negra, negro da periferia |
| `Religion` | Afro-Brazilian religious racism (§9.4) — candomblecista, umbandista, pai de santo vs. católico/evangélico |
| `Class` | Socioeconomic markers (§9.3) — mora em favela, beneficiária do Bolsa Família, escola pública vs. classe A/bairro nobre |

The pilot set now holds **22 scenarios → 44 samples** (each scenario expands into an
ambiguous + a disambiguated sample) across these five axes.

*Provenance & future-work caveat.* As of June 2026 **no Portuguese / Brazilian BBQ-style QA
bias dataset exists**, and none of the 10+ BBQ adaptations (MBBQ, KoBBQ, JBBQ, EsBBQ,
PakBBQ, BharatBBQ, …) covers Portuguese or the IBGE 5-category racial taxonomy. The
scenarios are therefore **authored for vigilAI** using the BBQ template methodology
(ambiguous + disambiguated contexts), with the demographic terms drawn from research §9.
Two existing resources **seed / anchor** the choice of realistic stereotypes but are
deliberately *not* runtime data sources:
[SHADES / BiasShades](https://huggingface.co/datasets/LanguageShades/BiasShades) (pt-BR
stereotypes; license-gated) and
[ToxSyn-PT](https://huggingface.co/datasets/ToxSyn/ToxSyn-PT) (CC BY 4.0; classification
format). Other Brazilian hate-speech corpora (HateBR, ToLD-BR, OLID-BR) are classification,
not QA, and use coarse race labels — noted as future-work resources only. **Full
native-annotator validation and a larger sample count are documented future work**; the
current set is a hand-built pilot sufficient to demonstrate the approach for the hackathon.

## EU ↔ Brazil mapping

vigilAI keeps COMPL-AI's nine EU-AI-Act `technical_requirement` categories unchanged (so
the EU benchmarks stay comparable) and tags the relevant tasks with their **Brazil PL
2338/2023** equivalent. PL 2338/2023 places its rights in **Chapter II ("Dos Direitos")**:
**Art. 5** rights apply to *all* AI systems, while **Art. 6** rights apply to *high-risk*
systems only — captured by the `brazil_scope` tag (`all_ai` vs `high_risk`). The single
source of truth for this table is [`src/vigilai/brazil/mapping.py`](src/vigilai/brazil/mapping.py).

| EU technical requirement (COMPL-AI) | Brazil PL 2338/2023 | Scope | Right / instrument | Tasks |
|---|---|---|---|---|
| Disclosure of AI | **Art. 5, I** | `all_ai` | Prior information | `human_deception`, `human_deception_brazil` |
| Representation — Absence of Bias | **Art. 5, III** | `all_ai` | Non-discrimination | `bbq`, `bbq_brazil`, `bold`, `cab` |
| Fairness — Absence of Discrimination | **Art. 5, III** | `all_ai` | Non-discrimination | `decoding_trust`, `fairllm` |
| Interpretability | **Art. 6, I** | `high_risk` | Calibration proxy for explanation (cf. LGPD Art. 20) | `bigbench_calibration`, `triviaqa_calibration` |
| Interpretability | **Art. 6, I** | `high_risk` | Right to explanation — *Brazil-only benchmark, no EU equivalent* | `explanation_quality` |
| _Societal Alignment (EU req. reused as a host)_ | **Art. 6, II-III** | `high_risk` | Right to contest + right to human review — *Brazil-only benchmark, no EU equivalent* | `contestation_review` |
| _Societal Alignment (EU req. reused as a host)_ | **Arts. 25-28** | `high_risk` | Algorithmic Impact Assessment — *Brazil-only benchmark, no EU equivalent* | `aia_checklist` |

Together, `explanation_quality` (Art. 6, I), `contestation_review` (Art. 6, II + III), and the
upstream calibration tasks cover the **complete high-risk Art. 6 rights triad**: explanation,
contestation, and human review.

The remaining EU technical requirements (Capabilities/Performance/Limitations, Robustness
and Predictability, Cyberattack Resilience, Societal Alignment, Harmful Content and
Toxicity) have **no direct Brazil Chapter II counterpart** and are listed as "no Brazil
mapping" — that absence is itself a finding.

Three Brazil obligations have **no dedicated EU COMPL-AI benchmark at all**, so vigilAI adds
new benchmarks for them (and the compliance report renders them as "no EU equivalent" rows —
itself a headline finding):

- **Art. 6, I — right to explanation** (`explanation_quality`). COMPL-AI's `Interpretability`
  requirement only measures *calibration* (TriviaQA / BIG-Bench), which is a proxy, not the
  rights-based explanation Brazil's Art. 6 / LGPD Art. 20 require. So `explanation_quality`
  is filed under Art. 6, I via its **decorator tag**, alongside the calibration tasks.
- **Art. 6, II + III — right to contest + right to human review** (`contestation_review`).
  The **EU AI Act has no individual right to contest a model output**, so there is no EU
  requirement to host this benchmark under. Like `aia_checklist`, it is tagged
  `technical_requirement="Societal Alignment"` (an EU-only requirement deliberately absent
  from the requirement→article mapping, so the other `Societal Alignment` tasks — `mask`,
  `simpleqa_verified`, `truthfulqa` — stay unmapped) and carries
  `brazil_article="Art. 6, II-III"` as a **per-task decorator tag**, resolved decorator-first
  by both `vigilai list --brazil` and `vigilai report`. This completes the high-risk Art. 6
  rights triad.
- **Arts. 25-28 — Algorithmic Impact Assessment** (`aia_checklist`). The AIA is a PL 2338/2023
  *Chapter IV governance instrument*, not a Chapter II rights-requirement, so its article is
  **not** added to the requirement→article mapping (that would wrongly pull the other
  `Societal Alignment` tasks — `mask`, `simpleqa_verified`, `truthfulqa` — under Arts. 25-28).
  Instead `aia_checklist` carries `brazil_article="Arts. 25-28"` as a **per-task decorator
  tag**, and both `vigilai list --brazil` and `vigilai report` resolve it decorator-first.

```bash
# Group tasks by EU technical requirement, annotated with the Brazil mapping (default)
uv run vigilai list

# Group tasks by Brazil PL 2338/2023 article instead
uv run vigilai list --brazil
```

## Install

vigilAI targets Python 3.11-3.13 and uses [`uv`](https://docs.astral.sh/uv/).

```bash
# from the vigilAI/ directory
uv venv
uv pip install -e .
```

## CLI

```bash
# List all tasks, grouped by technical requirement
uv run vigilai list

# Run a single benchmark against a deterministic mock model (zero cost)
uv run vigilai eval mockllm/model --tasks human_deception --limit 5

# Run against a real backend (e.g. a local Ollama model, or an API provider)
uv run vigilai eval ollama/llama3.1:8b --tasks human_deception

# View a generated log
uv run inspect view
```

Run `uv run vigilai --help` (or `uv run vigilai COMMAND --help`) for full usage.

## Compliance report

COMPL-AI ships no report aggregation — it emits raw Inspect `.eval` logs viewable in
`inspect view`. vigilAI adds a thin aggregator that reads a run directory, joins each task's
score to its Brazil `brazil_article` / `brazil_scope` (decorator-first, matching
`vigilai list --brazil`), aggregates per article and scope, and renders a Markdown (default)
or JSON report — including an **EU↔Brazil side-by-side**:

```bash
# 1. Evaluate the EU pair tasks AND the Brazil tasks on the SAME model, into one run dir
uv run vigilai eval mockllm/model \
  --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist \
  --limit 5

# 2. Render the Brazil PL 2338/2023 compliance report for that run
uv run vigilai report logs/<run-dir>                      # Markdown to stdout (default)
uv run vigilai report logs/<run-dir> --json              # machine-readable JSON
uv run vigilai report logs/<run-dir> --html > scorecard.html  # self-contained HTML scorecard
```

The `--html` view is a **self-contained, color-coded compliance scorecard** (inline CSS, no
external assets — opens offline anywhere): a per-article dashboard with band-colored scores and
EU↔Brazil deltas, framed as the **Art. 28 "public conclusions" of the Algorithmic Impact
Assessment** — the judge-facing AIA artifact. `--json` and `--html` are mutually exclusive. See
[`reports/scorecard.html`](reports/scorecard.html) (also mirrored as
[`scorecard-preview.html`](../.humanlayer/tasks/glo-5-global-south-ai-safety-hackathon-vigilai-brazil-ai-bill/scorecard-preview.html))
for the headline scorecard generated from the scaled `anthropic/claude-haiku-4-5` run — the full
Art. 6 triad visible. The **6-model dossier** [`reports/multimodel-scorecard.html`](reports/multimodel-scorecard.html)
(one model per page; rebuild with `uv run python reports/build_multimodel_scorecard.py`) collects a
scorecard page for every model in the panel.

Every report (Markdown, JSON, and HTML) also includes a **Brazil compliance coverage map** across
**all nine** COMPL-AI technical requirements — not just the four (of nine) that carry a bespoke
Brazil benchmark. Each
requirement is flagged ✅ (a Brazil-specific benchmark covers it), 🟡 (only the preserved EU/COMPL-AI
task ran), or ⚪ (not covered in the run), so the report shows Brazil-compliance *breadth* at a
glance. To exercise the full breadth, add one EU task per remaining requirement to the run, e.g.:

```bash
uv run vigilai eval mockllm/model \
  --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist,fairllm,forecast_consistency,arc_challenge \
  --limit 3
uv run vigilai report logs/<run-dir>   # 9-requirement coverage map at the bottom
```

The side-by-side compares only the **two direct-adaptation pairs that reuse the exact same
scorer** — `human_deception` ↔ `human_deception_brazil` and `bbq` ↔ `bbq_brazil` — so the
delta isolates the Brazil-specific content (Portuguese disclosure questions; IBGE / regional /
intersectional categories) rather than confounding scorer differences. `explanation_quality`,
`contestation_review`, and `aia_checklist` are reported as **Brazil-only** rows: Brazil's
Art. 6 explanation and contestation/human-review rights and the AIA obligations have no
COMPL-AI/EU benchmark counterpart, and that absence is itself a finding. The pair set is an
explicit constant (`EU_BRAZIL_PAIRS` in
[`src/vigilai/report/brazil_report.py`](src/vigilai/report/brazil_report.py)).

### Headline result (scaled, multi-model)

> Scaled runs: `anthropic/claude-haiku-4-5` and `anthropic/claude-sonnet-4-6` — full small sets
> + `bbq`@100, **10 epochs**, temperature 1.0, seed 42 — cross-checked on local
> `ollama/llama3.1:8b` ($0). **Full multi-model analysis, standard errors, conclusions, and
> caveats: [reports/RESULTS.md](reports/RESULTS.md).**

Per-article report (Claude Haiku 4.5, scaled, all **5** Brazil benchmarks on the deepened set),
verbatim from `uv run vigilai report logs/<run>` — the run behind
[`reports/scorecard.html`](reports/scorecard.html):

```markdown
# Brazil PL 2338/2023 — Compliance Report

- **Model(s):** anthropic/claude-haiku-4-5
- **Brazil-mapped tasks scored:** 5

## Compliance by Brazil article

| Brazil article | Scope | Task | EU technical requirement | Score |
|---|---|---|---|---|
| Art. 5, I | all_ai | `human_deception_brazil` | Disclosure of AI | 0.524 |
| Art. 5, III | all_ai | `bbq_brazil` (44 samples) | Representation — Absence of Bias | 0.677 |
| Art. 6, I | high_risk | `explanation_quality` | Interpretability | 0.833 |
| Art. 6, II-III | high_risk | `contestation_review` | (Societal Alignment host) | 0.975 |
| Arts. 25-28 | high_risk | `aia_checklist` | Societal Alignment | 0.983 |
```

**EU↔Brazil delta across models** (each pair reuses the exact same scorer, so Δ isolates the
Brazil-specific content; `bbq_brazil` = deepened 44-sample set):

| Pair | Haiku 4.5 | Sonnet 4.6 |
|---|---|---|
| Art. 5, I — AI disclosure (Brazil − EU) | 0.524 − 1.000 = **−0.48** | 0.524 − 1.000 = **−0.48** |
| Art. 5, III — bias, IBGE/regional (Brazil − EU) | 0.677 − 0.858 = **−0.18** | 0.402 − 0.498 = **−0.10** |

**Key finding (Art. 5, I — AI disclosure).** Both frontier models deny being human on ~**100%**
of the English/EU `human_deception` questions but only ~**52%** of the Portuguese + Brazil-specific
(PL 2338/2023 Art. 5, I / LGPD) variants — a **≈ −0.48 gap** that EU-only benchmarking never
surfaces, reproduced on **six models across four developers** (Anthropic Haiku 4.5 & Sonnet 4.6,
Meta Llama 3.1 8B, OpenAI gpt-oss 20B, Alibaba Qwen2.5 14B, Mistral Small) — every Brazilian
disclosure score lands in 0.50–0.55. On bias, **both** frontier models score *lower* on the
Brazilian IBGE / regional / intersectional set than on US-centric BBQ (Haiku −0.18, Sonnet −0.10) —
a trend in the predicted direction (4/6 models negative; the Brazilian set is a 44-scenario pilot,
so suggestive not yet conclusive). The **complete high-risk Art. 6 rights triad** is now measured:
unlike disclosure, models articulate explanation (0.83–0.85) and contestation + human review
(`contestation_review` 0.97–0.99) well — the failure is specific to *disclosure*. Brazil's Art. 6
rights and Arts. 25-28 AIA obligations have **no EU/COMPL-AI counterpart at all** — the "no EU
equivalent" rows are themselves a finding. See [reports/RESULTS.md](reports/RESULTS.md) for the full
two-batch six-model matrix, standard errors, the investigated Sonnet `bbq` behavior, and the
methodological note that a small-n EU baseline flipped the pilot's bias sign (+0.05 → −0.18).
Per-model reports: Stage-7 baseline → [reports/runs/stage7-phases1-7/](reports/runs/stage7-phases1-7/);
Phase 8–11 additions → [reports/runs/phase8-11/](reports/runs/phase8-11/).

## Demo

The EU↔Brazil comparison is **same-model internal** (EU task vs Brazil task on one backend),
so a cheap model is methodologically valid — there is no need to match the
[compl-ai.org](https://compl-ai.org) leaderboard's frontier models. Three backends are
supported, all driven by the same two commands above:

- **`mockllm/model`** — deterministic, $0, used by the test suite and for wiring (scores are
  meaningless, as shown above).
- **Local (dev, $0): Ollama.** Install [Ollama](https://ollama.com/), pull a model, and point
  vigilAI at it — no API key, no cost:

  ```bash
  ollama pull llama3.1:8b
  uv run vigilai eval ollama/llama3.1:8b \
    --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist \
    --limit 20
  uv run vigilai report logs/<run-dir>
  ```

- **Hosted (headline): Claude Haiku 4.5.** Chosen for strong instruction-following on the
  rubric / disclosure tasks at low cost (≈ $0.22 per full pass; est. ~$2–5 total). Put a
  **funded** `ANTHROPIC_API_KEY` in `vigilAI/.env` (the repo's `.gitignore` ignores `.env`, so
  the key is never committed — copy `.env.example` to start), then:

  ```bash
  # vigilAI/.env   (NOT committed)
  # ANTHROPIC_API_KEY=sk-ant-...

  uv run vigilai eval anthropic/claude-haiku-4-5 \
    --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist \
    --limit 20
  uv run vigilai report logs/<run-dir>
  ```

  The `ANTHROPIC_API_KEY` must be a funded console.anthropic.com key, billed separately from
  any Claude subscription.

## License

- **Code:** Apache-2.0 (see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE)) — inherited from
  and matching upstream COMPL-AI.
- **Report and figures** (`report/`): Creative Commons Attribution 4.0 (CC-BY-4.0).

Copyright 2026 Diana Chang and Ian Duhamel Hayes. vigilAI is a fork of COMPL-AI
(LatticeFlow AI / ETH Zurich / INSAIT); see [`NOTICE`](NOTICE) and the Citation below.

## Citation

vigilAI builds directly on COMPL-AI; please cite the original work:

```bibtex
@article{complai24,
      title={COMPL-AI Framework: A Technical Interpretation and LLM Benchmarking Suite for the EU Artificial Intelligence Act},
      author={Philipp Guldimann and Alexander Spiridonov and Robin Staab and Nikola Jovanovi\'{c} and Mark Vero and Velko Vechev and Anna Gueorguieva and Mislav Balunovi\'{c} and Nikola Konstantinov and Pavol Bielik and Petar Tsankov and Martin Vechev},
      year={2024},
      eprint={2410.07959},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2410.07959},
}
```
