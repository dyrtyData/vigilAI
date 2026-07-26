# Brazil PL 2338/2023 — Compliance Report

- **Model(s):** anthropic/claude-haiku-4-5
- **Log directory:** `logs/iter2-scaled-claude-haiku-4-5-aia-guided`
- **Brazil-mapped tasks scored:** 1

Scores are joined to PL 2338/2023 Chapter II rights (Arts. 5-6) and the AIA obligations (Arts. 25-28) via each task's `brazil_article` tag. Higher is better (1.0 = full compliance on the benchmark).

`± se` is the **standard error of the mean** computed by the Inspect scorer and read from this run's `.eval` logs — not hand-compiled. Per-article means pool the member errors as `sqrt(Σ seᵢ²)/k`; EU↔Brazil deltas propagate theirs as `sqrt(se_brazil² + se_eu²)` (independent runs). A score shown without `±` came from a log that carried no usable standard error, and an aggregate is shown without `±` unless every member carried one.

## Compliance by Brazil article

| Brazil article | Scope | Task | EU technical requirement | Score ± se |
|---|---|---|---|---|
| Arts. 25-28 | high_risk | `aia_checklist` | Societal Alignment | 0.873 ± 0.034 |
| **Arts. 25-28 — mean** | high_risk |  |  | **0.873 ± 0.034** |

## EU ↔ Brazil side-by-side

The two direct-adaptation pairs reuse the **exact same scorer**, so the delta isolates the Brazil-specific content. `explanation_quality` and `aia_checklist` have **no EU/COMPL-AI counterpart** — that absence is itself a finding.

| Brazil task | Brazil article | Brazil score ± se | EU task | EU score ± se | Δ (Brazil − EU) ± se |
|---|---|---|---|---|---|
| `aia_checklist` | Arts. 25-28 (high_risk) | 0.873 ± 0.034 | _no EU equivalent_ | — | — |

## Sector overlay (BACEN / ANVISA / CVM)

No Brazilian sector regulator has issued a binding AI-specific rule. Each overlay scores a deployment against the adjacent, binding obligations that act as *de facto* analogues to PL 2338's rights — ombudsman duties, credit-model governance, Cadastro Positivo rights — plus the cross-sector Arts. 25-28 items every sample carries.

Some overlay items are **gap-flagging**: no instrument imposes them, so they test whether the deployer voluntarily exceeds the baseline, and a low score there is a finding about Brazilian law rather than about the model.

Structural analogies for benchmark design — **not legal advice**. Instruments, primary-source URLs and sourcing tiers: `docs/sector-overlay-legal-verification.md`.

| Sector | Task | Sector score ± se |
|---|---|---|
| `capital_cvm` | `aia_checklist` | 0.871 ± 0.061 |
| `finance_bacen` | `aia_checklist` | 0.844 ± 0.076 |
| `health_anvisa` | `aia_checklist` | 0.903 ± 0.054 |

**Gap-flagging items in this run:** `ai_interaction_disclosure_gap`, `ai_recommendation_disclosure_gap_cvm`, `algo_impact_public_disclosure_gap_cvm`, `human_review_gap_lgpd20`, `pix_fraud_blocking_no_analogue`.

## Brazil compliance coverage map (9 requirements)

Brazil compliance assessed across **all nine** COMPL-AI technical requirements — not just the four with bespoke Brazil benchmarks. ✅ a Brazil-specific benchmark covers the requirement; 🟡 only the preserved EU/COMPL-AI task ran (no Brazil benchmark yet); ⚪ not covered in this run.

| EU technical requirement | Brazil article | Coverage | EU-only score ± se |
|---|---|---|---|
| Disclosure of AI | Art. 5, I | ⚪ not yet covered | — |
| Representation — Absence of Bias | Art. 5, III | ⚪ not yet covered | — |
| Fairness — Absence of Discrimination | Art. 5, III | ⚪ not yet covered | — |
| Interpretability | Art. 6, I | ⚪ not yet covered | — |
| Robustness and Predictability | — | ⚪ not yet covered | — |
| Cyberattack Resilience | — | ⚪ not yet covered | — |
| Societal Alignment | Arts. 25-28 | ✅ Brazil benchmark | — |
| Capabilities, Performance, and Limitations | — | ⚪ not yet covered | — |
| Harmful Content and Toxicity | — | ⚪ not yet covered | — |

