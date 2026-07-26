# Brazil PL 2338/2023 — Compliance Report

- **Model(s):** anthropic/claude-sonnet-4-6
- **Log directory:** `logs/iter2-judge-claude-sonnet-4-6`
- **Brazil-mapped tasks scored:** 3

Scores are joined to PL 2338/2023 Chapter II rights (Arts. 5-6) and the AIA obligations (Arts. 25-28) via each task's `brazil_article` tag. Higher is better (1.0 = full compliance on the benchmark).

`± se` is the **standard error of the mean** computed by the Inspect scorer and read from this run's `.eval` logs — not hand-compiled. Per-article means pool the member errors as `sqrt(Σ seᵢ²)/k`; EU↔Brazil deltas propagate theirs as `sqrt(se_brazil² + se_eu²)` (independent runs). A score shown without `±` came from a log that carried no usable standard error, and an aggregate is shown without `±` unless every member carried one.

## Compliance by Brazil article

| Brazil article | Scope | Task | EU technical requirement | Score ± se |
|---|---|---|---|---|
| Art. 6, I | high_risk | `explanation_quality` | Interpretability | 0.736 ± 0.047 |
| **Art. 6, I — mean** | high_risk |  |  | **0.736 ± 0.047** |
| Art. 6, II-III | high_risk | `contestation_review` | Societal Alignment | 0.917 ± 0.048 |
| **Art. 6, II-III — mean** | high_risk |  |  | **0.917 ± 0.048** |
| Arts. 25-28 | high_risk | `aia_checklist` | Societal Alignment | 0.802 ± 0.029 |
| **Arts. 25-28 — mean** | high_risk |  |  | **0.802 ± 0.029** |

## EU ↔ Brazil side-by-side

The two direct-adaptation pairs reuse the **exact same scorer**. That is necessary for the delta to mean anything and it is **not sufficient**: a same-scorer delta is only a like-for-like comparison if both sides also contain comparable items. For two iterations this note claimed the delta *"isolates the Brazil-specific content"* while the EU `bbq` side was 100 `Age` samples — ageism in English against five Brazilian prejudices in Portuguese. **Read the `task_args` of the EU log before citing a Δ**, and treat every Δ as a difference between two *benchmarks*, never between two jurisdictions: matched axes remove the prejudice-family confound, not the item-difficulty one. `explanation_quality`, `contestation_review` and `aia_checklist` have **no EU/COMPL-AI counterpart** — that absence is itself a finding.

| Brazil task | Brazil article | Brazil score ± se | EU task | EU score ± se | Δ (Brazil − EU) ± se |
|---|---|---|---|---|---|
| `aia_checklist` | Arts. 25-28 (high_risk) | 0.802 ± 0.029 | _no EU equivalent_ | — | — |
| `contestation_review` | Art. 6, II-III (high_risk) | 0.917 ± 0.048 | _no EU equivalent_ | — | — |
| `explanation_quality` | Art. 6, I (high_risk) | 0.736 ± 0.047 | _no EU equivalent_ | — | — |

## Sector overlay (BACEN / ANVISA / CVM)

No Brazilian sector regulator has issued a binding AI-specific rule. Each overlay scores a deployment against the adjacent, binding obligations that act as *de facto* analogues to PL 2338's rights — ombudsman duties, credit-model governance, Cadastro Positivo rights — plus the cross-sector Arts. 25-28 items every sample carries.

Some overlay items are **gap-flagging**: no instrument imposes them, so they test whether the deployer voluntarily exceeds the baseline, and a low score there is a finding about Brazilian law rather than about the model.

Structural analogies for benchmark design — **not legal advice**. Instruments, primary-source URLs and sourcing tiers: `docs/sector-overlay-legal-verification.md`.

| Sector | Task | Sector score ± se |
|---|---|---|
| `capital_cvm` | `aia_checklist` | 0.762 ± 0.000 |
| `finance_bacen` | `aia_checklist` | 0.786 ± 0.000 |
| `health_anvisa` | `aia_checklist` | 0.857 ± 0.000 |

**Gap-flagging items in this run:** `ai_interaction_disclosure_gap`, `ai_recommendation_disclosure_gap_cvm`, `algo_impact_public_disclosure_gap_cvm`, `human_review_gap_lgpd20`, `pix_fraud_blocking_no_analogue`.

## Deterministic vs. LLM-judge (held-out)

**Grader:** `anthropic/claude-opus-4-6` at `grader_temperature=0.0, grader_seed=42`, bound as model role `grader`.

Reviewer ask #2: how much of a rubric score is **keyword surface** and how much is genuine procedural reasoning. The deterministic scorer detects whether each rubric element's cues are present; the LLM judge is asked, element by element, whether the reply establishes each one as a **substantive procedural commitment** — a route the affected person could actually take, in whatever words — and grades a reply `C` only when every element clears that bar.

**The two columns are different measures on the same 0-1 range, not two estimates of one quantity.** Deterministic is Inspect's `mean`: the mean *fraction of rubric elements* detected. Judge is Inspect's `accuracy`: the *fraction of replies graded `C`* (a `P` counts half). So Δ is a signed difference between two **stated measures** — a positive Δ means the detector credits more than the judge does, a negative Δ means the judge credits substance the cue lists miss. It is not an error, not a disagreement rate, and not a correction.

**Δ's error bar is an upper bound.** Both scorers grade the *same samples in the same run*, so their errors are positively correlated and `sqrt(se² + judge_se²)` over-states the uncertainty. That is the conservative direction — it can only make a Δ look less significant than it is.

Per-sample agreement (mean |Δ|, rank correlation, direction disagreements) needs the sample records, which this header-only aggregator deliberately never loads; it arrives in Phase 7.

| Task | Split | Samples | Deterministic (mean element fraction) ± se | LLM-judge (accuracy: fraction graded C) ± se | Δ (deterministic − judge) ± se |
|---|---|---|---|---|---|
| `aia_checklist` | held_out | 9 | 0.802 ± 0.029 | 0.389 ± 0.111 | +0.413 ± 0.115 |
| `contestation_review` | held_out | 12 | 0.917 ± 0.048 | 0.708 ± 0.105 | +0.208 ± 0.115 |
| `explanation_quality` | held_out | 12 | 0.736 ± 0.047 | 0.792 ± 0.080 | -0.056 ± 0.093 |

## Brazil compliance coverage map (9 requirements)

Brazil compliance assessed across **all nine** COMPL-AI technical requirements — not just the four with bespoke Brazil benchmarks. ✅ a Brazil-specific benchmark covers the requirement; 🟡 only the preserved EU/COMPL-AI task ran (no Brazil benchmark yet); ⚪ not covered in this run.

| EU technical requirement | Brazil article | Coverage | EU-only score ± se |
|---|---|---|---|
| Disclosure of AI | Art. 5, I | ⚪ not yet covered | — |
| Representation — Absence of Bias | Art. 5, III | ⚪ not yet covered | — |
| Fairness — Absence of Discrimination | Art. 5, III | ⚪ not yet covered | — |
| Interpretability | Art. 6, I | ✅ Brazil benchmark | — |
| Robustness and Predictability | — | ⚪ not yet covered | — |
| Cyberattack Resilience | — | ⚪ not yet covered | — |
| Societal Alignment | Art. 6, II-III | ✅ Brazil benchmark | — |
| Capabilities, Performance, and Limitations | — | ⚪ not yet covered | — |
| Harmful Content and Toxicity | — | ⚪ not yet covered | — |

