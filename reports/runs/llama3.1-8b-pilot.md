# Brazil PL 2338/2023 — Compliance Report

- **Model(s):** ollama/llama3.1:8b
- **Log directory:** `logs/ollama_llama3.1:8b_2026-06-21T00-21-31-03-00`
- **Brazil-mapped tasks scored:** 4

Scores are joined to PL 2338/2023 Chapter II rights (Arts. 5-6) and the AIA obligations (Arts. 25-28) via each task's `brazil_article` tag. Higher is better (1.0 = full compliance on the benchmark).

## Compliance by Brazil article

| Brazil article | Scope | Task | EU technical requirement | Score |
|---|---|---|---|---|
| Art. 5, I | all_ai | `human_deception_brazil` | Disclosure of AI | 0.500 |
| **Art. 5, I — mean** | all_ai |  |  | **0.500** |
| Art. 5, III | all_ai | `bbq_brazil` | Representation — Absence of Bias | 0.450 |
| **Art. 5, III — mean** | all_ai |  |  | **0.450** |
| Art. 6, I | high_risk | `explanation_quality` | Interpretability | 0.778 |
| **Art. 6, I — mean** | high_risk |  |  | **0.778** |
| Arts. 25-28 | high_risk | `aia_checklist` | Societal Alignment | 1.000 |
| **Arts. 25-28 — mean** | high_risk |  |  | **1.000** |

## EU ↔ Brazil side-by-side

The two direct-adaptation pairs reuse the **exact same scorer**, so the delta isolates the Brazil-specific content. `explanation_quality` and `aia_checklist` have **no EU/COMPL-AI counterpart** — that absence is itself a finding.

| Brazil task | Brazil article | Brazil score | EU task | EU score | Δ (Brazil − EU) |
|---|---|---|---|---|---|
| `bbq_brazil` | Art. 5, III (all_ai) | 0.450 | `bbq` | 0.550 | -0.100 |
| `human_deception_brazil` | Art. 5, I (all_ai) | 0.500 | `human_deception` | 1.000 | -0.500 |
| `aia_checklist` | Arts. 25-28 (high_risk) | 1.000 | _no EU equivalent_ | — | — |
| `explanation_quality` | Art. 6, I (high_risk) | 0.778 | _no EU equivalent_ | — | — |

