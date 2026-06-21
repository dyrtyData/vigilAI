# Phase 8–11 batch — new / changed benchmarks across all models

This batch covers the two benchmarks that are **new or changed since the Stage-7 baseline**
(`reports/runs/stage7-phases1-7/`):

1. **`contestation_review` (Art. 6, II + III)** — brand-new benchmark completing the high-risk
   Art. 6 rights triad (explanation / contestation / human review). No EU/COMPL-AI counterpart.
2. **`bbq_brazil` (Art. 5, III) — deepened** from 10 scenarios / 20 samples to **22 scenarios /
   44 samples** (added Religion + Class axes plus more Race_IBGE / Region / Intersectional
   scenarios).

The other four Brazil benchmarks (`human_deception_brazil`, `explanation_quality`,
`aia_checklist`) and the EU pairs (`human_deception`, `bbq`) are **unchanged** since Stage 7, so
their numbers carry over from `reports/runs/stage7-phases1-7/` (re-running them reproduces the
same scores modulo sampling noise). The lone exception is **Haiku 4.5**, which was re-run
completely on the deepened set for a single coherent headline artifact — see
[`haiku-4-5-complete.md`](haiku-4-5-complete.md) and `reports/scorecard.html`.

**Run configs (identical to Stage 7):** scaled = `--limit 100 --epochs 10 --temperature 1.0
--seed 42` (Haiku, Sonnet; ≈$0.20 each for these two small tasks); pilot = local Ollama, full
sets, 1 epoch ($0).

## `contestation_review` — Art. 6, II + III (right to contest + human review)

The deterministic 6-element rubric scorer (mean fraction of elements present). Higher = a more
complete description of the contestation + human-review process.

| Model | Config | `contestation_review` mean | stderr |
|---|---|---|---|
| Claude Haiku 4.5 | scaled (4×10) | **0.975** | ±0.023 |
| Claude Sonnet 4.6 | scaled (4×10) | **0.988** | ±0.013 |
| gpt-oss 20B | pilot (4×1) | 1.000 | ±0.000 |
| Mistral Small | pilot (4×1) | 0.958 | ±0.042 |
| Qwen2.5 14B | pilot (4×1) | 0.875 | ±0.080 |
| Llama 3.1 8B | pilot (4×1) | 0.708 | ±0.105 |

*(Haiku scored 0.967 ± 0.023 in the standalone two-task run and 0.975 in the coherent full run —
run-to-run variance on n=4; the coherent full-run value is used for the headline.)*

**Finding.** Unlike AI disclosure (Art. 5, I), models are **good** at articulating the
contestation + human-review process when prompted with the rubric/few-shot: frontier models score
0.97–0.99, and even the 8B local model clears 0.70. The Art. 6, II–III right is "describable," and
the models largely produce a compliant description — completing the triad with real numbers
(explanation 0.83 / contestation 0.97 / + the disclosure gap stays the headline failure).

## `bbq_brazil` — Art. 5, III, **deepened set (44 samples)**

Brazil-adapted BBQ with IBGE / regional / intersectional + (new) Religion / Class categories.
Higher = less biased (correctly answers "Não é possível determinar" in ambiguous contexts).
Δ bias = `bbq_brazil` − the model's EU `bbq` baseline (the EU `bbq` task is unchanged from
Stage 7, so its baseline carries over).

| Model | Config | `bbq_brazil` v2 (44) | stderr | EU `bbq` baseline | Δ bias (Brazil − EU) |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | scaled | **0.677** | ±0.070 | 0.858 (n=1000) | **−0.181** |
| Claude Sonnet 4.6 | scaled | **0.402** | ±0.056 | 0.498 ⚠️ (n=1000) | **−0.096** |
| gpt-oss 20B | pilot | 0.727 | ±0.068 | 0.70 (n=20) | +0.027 |
| Mistral Small | pilot | 0.659 | ±0.072 | 0.60 (n=20) | +0.059 |
| Qwen2.5 14B | pilot | 0.659 | ±0.072 | 0.70 (n=20) | −0.041 |
| Llama 3.1 8B | pilot | 0.477 | ±0.076 | 0.55 (n=20) | −0.073 |

⚠️ Sonnet's EU `bbq` baseline (0.498) is anomalous — see the Stage-7 analysis in
`reports/RESULTS.md` (caveats); the Brazil−EU *delta* stays valid because the same scorer applies
to both.

**Finding.** The deepened 44-sample set keeps the Stage-7 conclusion: bias delta is negative in
**4 / 6** models (mean ≈ −0.05), and **both reliable scaled frontier models are negative** (Haiku
−0.18, Sonnet −0.10). Direction supports "models are more biased on Brazilian categories";
magnitude on the local pilots remains within noise. The deeper set marginally tightened the
frontier estimates vs. the 20-sample pilot (Haiku Δ −0.16 → −0.18; Sonnet −0.12 → −0.10).
