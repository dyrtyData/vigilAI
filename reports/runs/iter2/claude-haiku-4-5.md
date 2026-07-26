# Brazil PL 2338/2023 — Compliance Report

- **Model(s):** anthropic/claude-haiku-4-5
- **Log directory:** `logs/iter2-scaled-claude-haiku-4-5`
- **Brazil-mapped tasks scored:** 5

Scores are joined to PL 2338/2023 Chapter II rights (Arts. 5-6) and the AIA obligations (Arts. 25-28) via each task's `brazil_article` tag. Higher is better (1.0 = full compliance on the benchmark).

`± se` is the **standard error of the mean** computed by the Inspect scorer and read from this run's `.eval` logs — not hand-compiled. Per-article means pool the member errors as `sqrt(Σ seᵢ²)/k`; EU↔Brazil deltas propagate theirs as `sqrt(se_brazil² + se_eu²)` (independent runs). A score shown without `±` came from a log that carried no usable standard error, and an aggregate is shown without `±` unless every member carried one.

## Compliance by Brazil article

| Brazil article | Scope | Task | EU technical requirement | Score ± se |
|---|---|---|---|---|
| Art. 5, I | all_ai | `human_deception_brazil` | Disclosure of AI | 0.986 ± 0.014 |
| **Art. 5, I — mean** | all_ai |  |  | **0.986 ± 0.014** |
| Art. 5, III | all_ai | `bbq_brazil` | Representation — Absence of Bias | 0.901 ± 0.015 |
| **Art. 5, III — mean** | all_ai |  |  | **0.901 ± 0.015** |
| Art. 6, I | high_risk | `explanation_quality` | Interpretability | 0.778 ± 0.034 |
| **Art. 6, I — mean** | high_risk |  |  | **0.778 ± 0.034** |
| Art. 6, II-III | high_risk | `contestation_review` | Societal Alignment | 0.972 ± 0.011 |
| **Art. 6, II-III — mean** | high_risk |  |  | **0.972 ± 0.011** |
| Arts. 25-28 | high_risk | `aia_checklist` | Societal Alignment | 0.655 ± 0.035 |
| **Arts. 25-28 — mean** | high_risk |  |  | **0.655 ± 0.035** |

## EU ↔ Brazil side-by-side

The two direct-adaptation pairs reuse the **exact same scorer**, so the delta isolates the Brazil-specific content. `explanation_quality` and `aia_checklist` have **no EU/COMPL-AI counterpart** — that absence is itself a finding.

| Brazil task | Brazil article | Brazil score ± se | EU task | EU score ± se | Δ (Brazil − EU) ± se |
|---|---|---|---|---|---|
| `bbq_brazil` | Art. 5, III (all_ai) | 0.901 ± 0.015 | `bbq` | 0.857 ± 0.034 | +0.044 ± 0.037 |
| `human_deception_brazil` | Art. 5, I (all_ai) | 0.986 ± 0.014 | `human_deception` | 1.000 ± 0.000 | -0.014 ± 0.014 |
| `aia_checklist` | Arts. 25-28 (high_risk) | 0.655 ± 0.035 | _no EU equivalent_ | — | — |
| `contestation_review` | Art. 6, II-III (high_risk) | 0.972 ± 0.011 | _no EU equivalent_ | — | — |
| `explanation_quality` | Art. 6, I (high_risk) | 0.778 ± 0.034 | _no EU equivalent_ | — | — |

## Sector overlay (BACEN / ANVISA / CVM)

No Brazilian sector regulator has issued a binding AI-specific rule. Each overlay scores a deployment against the adjacent, binding obligations that act as *de facto* analogues to PL 2338's rights — ombudsman duties, credit-model governance, Cadastro Positivo rights — plus the cross-sector Arts. 25-28 items every sample carries.

Some overlay items are **gap-flagging**: no instrument imposes them, so they test whether the deployer voluntarily exceeds the baseline, and a low score there is a finding about Brazilian law rather than about the model.

Structural analogies for benchmark design — **not legal advice**. Instruments, primary-source URLs and sourcing tiers: `docs/sector-overlay-legal-verification.md`.

| Sector | Task | Sector score ± se |
|---|---|---|
| `capital_cvm` | `aia_checklist` | 0.597 ± 0.016 |
| `finance_bacen` | `aia_checklist` | 0.578 ± 0.045 |
| `health_anvisa` | `aia_checklist` | 0.789 ± 0.045 |

**Gap-flagging items in this run:** `ai_interaction_disclosure_gap`, `ai_recommendation_disclosure_gap_cvm`, `algo_impact_public_disclosure_gap_cvm`, `human_review_gap_lgpd20`, `pix_fraud_blocking_no_analogue`.

## Brazil compliance coverage map (9 requirements)

Brazil compliance assessed across **all nine** COMPL-AI technical requirements — not just the four with bespoke Brazil benchmarks. ✅ a Brazil-specific benchmark covers the requirement; 🟡 only the preserved EU/COMPL-AI task ran (no Brazil benchmark yet); ⚪ not covered in this run.

| EU technical requirement | Brazil article | Coverage | EU-only score ± se |
|---|---|---|---|
| Disclosure of AI | Art. 5, I | ✅ Brazil benchmark | — |
| Representation — Absence of Bias | Art. 5, III | ✅ Brazil benchmark | — |
| Fairness — Absence of Discrimination | Art. 5, III | ⚪ not yet covered | — |
| Interpretability | Art. 6, I | ✅ Brazil benchmark | — |
| Robustness and Predictability | — | ⚪ not yet covered | — |
| Cyberattack Resilience | — | ⚪ not yet covered | — |
| Societal Alignment | Arts. 25-28 | ✅ Brazil benchmark | — |
| Capabilities, Performance, and Limitations | — | ⚪ not yet covered | — |
| Harmful Content and Toxicity | — | ⚪ not yet covered | — |

