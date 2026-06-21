# Brazil PL 2338/2023 — Compliance Report

- **Model(s):** anthropic/claude-haiku-4-5
- **Log directory:** `logs/anthropic_claude-haiku-4-5_2026-06-21T13-12-04-03-00`
- **Brazil-mapped tasks scored:** 5

Scores are joined to PL 2338/2023 Chapter II rights (Arts. 5-6) and the AIA obligations (Arts. 25-28) via each task's `brazil_article` tag. Higher is better (1.0 = full compliance on the benchmark).

## Compliance by Brazil article

| Brazil article | Scope | Task | EU technical requirement | Score |
|---|---|---|---|---|
| Art. 5, I | all_ai | `human_deception_brazil` | Disclosure of AI | 0.524 |
| **Art. 5, I — mean** | all_ai |  |  | **0.524** |
| Art. 5, III | all_ai | `bbq_brazil` | Representation — Absence of Bias | 0.677 |
| **Art. 5, III — mean** | all_ai |  |  | **0.677** |
| Art. 6, I | high_risk | `explanation_quality` | Interpretability | 0.833 |
| **Art. 6, I — mean** | high_risk |  |  | **0.833** |
| Art. 6, II-III | high_risk | `contestation_review` | Societal Alignment | 0.975 |
| **Art. 6, II-III — mean** | high_risk |  |  | **0.975** |
| Arts. 25-28 | high_risk | `aia_checklist` | Societal Alignment | 0.983 |
| **Arts. 25-28 — mean** | high_risk |  |  | **0.983** |

## EU ↔ Brazil side-by-side

The two direct-adaptation pairs reuse the **exact same scorer**, so the delta isolates the Brazil-specific content. `explanation_quality` and `aia_checklist` have **no EU/COMPL-AI counterpart** — that absence is itself a finding.

| Brazil task | Brazil article | Brazil score | EU task | EU score | Δ (Brazil − EU) |
|---|---|---|---|---|---|
| `bbq_brazil` | Art. 5, III (all_ai) | 0.677 | `bbq` | 0.858 | -0.181 |
| `human_deception_brazil` | Art. 5, I (all_ai) | 0.524 | `human_deception` | 1.000 | -0.476 |
| `aia_checklist` | Arts. 25-28 (high_risk) | 0.983 | _no EU equivalent_ | — | — |
| `contestation_review` | Art. 6, II-III (high_risk) | 0.975 | _no EU equivalent_ | — | — |
| `explanation_quality` | Art. 6, I (high_risk) | 0.833 | _no EU equivalent_ | — | — |

## Brazil compliance coverage map (9 requirements)

Brazil compliance assessed across **all nine** COMPL-AI technical requirements — not just the four with bespoke Brazil benchmarks. ✅ a Brazil-specific benchmark covers the requirement; 🟡 only the preserved EU/COMPL-AI task ran (no Brazil benchmark yet); ⚪ not covered in this run.

| EU technical requirement | Brazil article | Coverage | EU-only score |
|---|---|---|---|
| Disclosure of AI | Art. 5, I | ✅ Brazil benchmark | — |
| Representation — Absence of Bias | Art. 5, III | ✅ Brazil benchmark | — |
| Fairness — Absence of Discrimination | Art. 5, III | ⚪ not yet covered | — |
| Interpretability | Art. 6, I | ✅ Brazil benchmark | — |
| Robustness and Predictability | — | ⚪ not yet covered | — |
| Cyberattack Resilience | — | ⚪ not yet covered | — |
| Societal Alignment | Art. 6, II-III | ✅ Brazil benchmark | — |
| Capabilities, Performance, and Limitations | — | ⚪ not yet covered | — |
| Harmful Content and Toxicity | — | ⚪ not yet covered | — |

