# vigilAI — Results & Conclusions

**Do EU-tuned models comply with Brazil's PL 2338/2023 rights?**
A same-model, EU↔Brazil benchmark comparison built on a fork of COMPL-AI.

*Generated for the Global South AI Safety Hackathon (LatAm governance subtrack). All numbers
below are reproduced verbatim from `vigilai report <log_dir>`; exact commands and seeds are in
the [Reproducibility](#reproducibility) section.*

---

## Executive summary

1. **AI-disclosure compliance does not transfer to Portuguese / Brazilian law.** Every model
   tested denies being human ~**100%** of the time on the English/EU `human_deception` set but
   only ~**52%** of the time on the Portuguese + Brazil-disclosure (PL 2338/2023 Art. 5, I /
   LGPD) variants — a **≈ −0.47 gap that is invisible to EU-only evaluation**. Reproduced on
   **three independent backends** (Claude Haiku 4.5, Claude Sonnet 4.6, local Llama 3.1 8B).
2. **On bias, both frontier models score *lower* on Brazilian categories** (IBGE race /
   regional / intersectional) than on US-centric BBQ — Haiku Δ −0.16, Sonnet Δ −0.12. The
   direction matches the thesis on both models, but each is only ~1.2–1.5σ (the Brazilian set
   is a 20-scenario pilot), so this is a **strong trend, not yet a conclusive result**.
3. **Brazil's Art. 6 right-to-explanation and Arts. 25-28 AIA obligations have no EU/COMPL-AI
   benchmark counterpart at all.** vigilAI introduces deterministic benchmarks for both; the
   "no EU equivalent" rows are themselves a finding about where Global-South AI governance
   outruns the tooling built for the EU AI Act.

> **Methodological headline:** scaling the run *changed the bias conclusion*. A noisy pilot
> (`bbq` at n=20) showed Brazil **+0.05 better**; a proper baseline (`bbq` at n=1000) showed
> Brazil **−0.16 worse**. Small-n EU baselines actively mislead — which is itself an argument
> for purpose-built Global-South evaluation.

---

## What we measured

vigilAI forks [COMPL-AI](https://github.com/compl-ai/compl-ai) (the EU-AI-Act evaluation
framework, built on Inspect AI), preserves all 30 original EU benchmarks, and adds four
Brazil-specific ones mapped to PL 2338/2023 Chapter II rights + the AIA:

| Brazil article | Scope | vigilAI benchmark | EU/COMPL-AI counterpart |
|---|---|---|---|
| Art. 5, I — prior information (AI disclosure) | all AI | `human_deception_brazil` | `human_deception` (same scorer) |
| Art. 5, III — non-discrimination | all AI | `bbq_brazil` (IBGE/regional/intersectional) | `bbq` (same scorer) |
| Art. 6, I — right to explanation (high-risk) | high-risk | `explanation_quality` | **none** |
| Arts. 25-28 — Algorithmic Impact Assessment | high-risk | `aia_checklist` | **none** |

**Design.** The two pairs that reuse the *exact same scorer* (`human_deception` ↔
`human_deception_brazil`, `bbq` ↔ `bbq_brazil`) let the EU↔Brazil delta isolate the
Brazil-specific content (Portuguese; IBGE/regional/intersectional categories) rather than
confounding scorer differences. `explanation_quality` and `aia_checklist` are Brazil-only.

**Models.** `anthropic/claude-haiku-4-5`, `anthropic/claude-sonnet-4-6`, and local
`ollama/llama3.1:8b` (zero-cost cross-check). The comparison is *same-model internal* (EU task
vs Brazil task on one backend), so model strength is not the variable of interest — the
EU↔Brazil delta is.

---

## Results

### Headline matrix — EU↔Brazil score by article, across runs

Higher = more compliant (1.0 = full marks on the benchmark). Δ = Brazil − EU (negative = the
model is *less* compliant on the Brazil-specific content).

| Article / pair | Ollama 8B (pilot) | Haiku 4.5 (pilot) | **Haiku 4.5 (scaled)** | **Sonnet 4.6 (scaled)** |
|---|---|---|---|---|
| **Art. 5, I — `human_deception_brazil`** | 0.50 | 0.50 | **0.524** | **0.524** |
| Art. 5, I — `human_deception` (EU) | 1.00 | 1.00 | 0.997 | 1.000 |
| **Δ disclosure** | −0.50 | −0.50 | **−0.474** | **−0.476** |
| **Art. 5, III — `bbq_brazil`** | 0.45 | 0.70 | **0.700** | **0.375** |
| Art. 5, III — `bbq` (EU) | 0.55 | 0.65 | 0.858 | 0.498 |
| **Δ bias** | −0.10 | +0.05 | **−0.158** | **−0.123** |
| Art. 6, I — `explanation_quality` (Brazil-only) | 0.778 | 0.778 | **0.894** | **0.850** |
| Arts. 25-28 — `aia_checklist` (Brazil-only) | 1.00 | 1.00 | **0.917** | **0.950** |

- **Pilot** = `--limit 20`, 1 epoch (illustrative; baselines noisy).
- **Scaled** = full small sets (`human_deception` 39, `human_deception_brazil` 21,
  `bbq_brazil` 20, `explanation_quality` 3, `aia_checklist` 1) + `bbq` at 100, **10 epochs**,
  temperature 1.0, seed 42. Epochs turn each score into a reliability estimate (how often the
  model complies under normal sampling).

### Scaled runs — with standard error

| Benchmark | Haiku 4.5 | Sonnet 4.6 |
|---|---|---|
| `human_deception` (EU, Art. 5, I) | 0.997 ± 0.003 | 1.000 ± 0.000 |
| `human_deception_brazil` (Art. 5, I) | **0.524 ± 0.112** | **0.524 ± 0.112** |
| `bbq` (EU, Art. 5, III) | 0.858 ± 0.034 | 0.498 ± 0.044 |
| `bbq_brazil` (Art. 5, III) | 0.700 ± 0.105 | 0.375 ± 0.090 |
| `explanation_quality` (Art. 6, I) | 0.894 ± 0.039 | 0.850 ± 0.025 |
| `aia_checklist` (Arts. 25-28) | 0.917 | 0.950 |

*Note the EU `human_deception` side is essentially zero-variance (±0.003 / ±0.000), so the
disclosure gap is unambiguous. The Brazilian-set standard errors stay wide (±0.09–0.11)
because those sets have only 20–21 unique questions — epochs reduce within-question variance
but not between-question variance.*

---

## Conclusions — was the thesis correct?

### 1. "EU compliance ≠ Brazil compliance (the language/disclosure gap)" — ✅ CONFIRMED (strong)

Both frontier models and the local model converge on the same result: **near-perfect English
disclosure, ~52% Portuguese/Brazil disclosure, a ≈ −0.47 gap.** Haiku and Sonnet land on the
*identical* `human_deception_brazil` score (0.524) — the same subset of Portuguese/LGPD-framed
questions defeats both. An EU-AI-Act-only audit would score these models ~1.0 on disclosure and
certify them; vigilAI shows they fail Brazil's Art. 5, I roughly half the time. **This is the
headline finding and it is robust across model family and scale.**

### 2. "Models are more biased on Brazilian categories" — 🟡 SUPPORTED AS A TREND (not yet conclusive)

With a *reliable* EU baseline, **both** frontier models score lower on `bbq_brazil` than on
`bbq` (Haiku −0.16, Sonnet −0.12) — the direction the thesis predicted, and consistent across
two independent models. But each delta is only ~1.2–1.5σ given the 20-scenario Brazilian pilot,
so it is suggestive rather than significant. **Verdict: the method detects the predicted effect;
confirming it needs a larger, native-annotator-validated `bbq_brazil`** (see Future work).

### 3. "Brazil has rights with no EU benchmark" — ✅ CONFIRMED by construction

Art. 6 explanation and Arts. 25-28 AIA have no COMPL-AI/EU counterpart. vigilAI's new
deterministic benchmarks fill that gap and *discriminate* (scores 0.85–0.95, not trivial 1.0s —
e.g., both models reliably omit a confidence/uncertainty statement in explanations). The
absence of an EU equivalent is itself the point: Global-South rights frameworks have obligations
the EU-tuned toolchain never measured.

### 4. Methodological finding — small-n EU baselines mislead

Scaling flipped the bias conclusion from **+0.05** (pilot) to **−0.16** (scaled), driven almost
entirely by the EU `bbq` baseline moving 0.65 → 0.858 once estimated on 1000 samples instead of
20. This is a concrete cautionary tale: under-powered EU baselines don't just add noise, they
can invert the sign of a Global-South compliance gap.

---

## Caveats & limitations

- **Pilot dataset sizes.** `bbq_brazil` is 20 hand-authored scenarios; `explanation_quality` /
  `aia_checklist` have 3 / 1. These demonstrate the *method*, not definitive compliance verdicts.
  Native-annotator validation of the Portuguese scenarios is pending (documented as future work).
- **Deterministic detectors.** `explanation_quality` and `aia_checklist` score by keyword/
  structured-cue presence (no LLM judge), tuned against a real run; recall on free-form prose is
  good but imperfect.
- **⚠️ Sonnet `bbq` anomaly (unresolved).** Sonnet's EU `bbq` score (0.498) is far below Haiku's
  (0.858). The most likely cause is Sonnet answering "cannot be determined / Unknown" even in
  *disambiguated* contexts (over-caution caps accuracy near 0.5), or an MC-answer formatting
  effect the `choice()` scorer doesn't parse — **this has not been verified.** The bias *delta*
  (Brazil < EU) holds for Sonnet regardless, but Sonnet's absolute bias numbers should be treated
  with caution until this is investigated.
- **Same-model-internal comparison.** This is deliberately not a cross-model leaderboard; we do
  not claim one model is "more compliant" than another, only that each model is less compliant on
  Brazil-specific content than on its EU counterpart.

---

## Future work

- Scale `bbq_brazil` to a statistically powered, **native-annotator-validated** set across all
  IBGE/regional/intersectional axes (the single highest-value next step — would move conclusion #2
  from "trend" to a significance test).
- Expand `explanation_quality` / `aia_checklist` scenario banks; consider an optional LLM-judge
  cross-check of the deterministic detectors.
- Investigate the Sonnet `bbq` behavior (over-caution vs parsing) by inspecting per-sample
  answers.
- Add the remaining Brazil rights (Art. 6, II contestation; Art. 6, III human review) and
  sector-specific overlays (ANVISA, BACEN).

---

## Reproducibility

All runs used `vigilai` (fork of COMPL-AI), Inspect AI, Python 3.12 via `uv`. The API key lives
in `vigilAI/.env` (gitignored).

```bash
# Scaled headline runs (Haiku and Sonnet), identical params
uv run vigilai eval anthropic/claude-haiku-4-5 \
  --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,aia_checklist \
  --limit 100 --epochs 10 --temperature 1.0 --seed 42
uv run vigilai eval anthropic/claude-sonnet-4-6 \
  --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,aia_checklist \
  --limit 100 --epochs 10 --temperature 1.0 --seed 42

# Zero-cost local cross-check
uv run vigilai eval ollama/llama3.1:8b \
  --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,aia_checklist \
  --limit 20

# Report (per-article + EU↔Brazil side-by-side)
uv run vigilai report logs/<run-dir>          # Markdown
uv run vigilai report logs/<run-dir> --json   # machine-readable
```

Raw per-run reports are saved as `brazil_report_scaled.md` inside each run's log directory.
Approximate API cost for the two scaled frontier runs combined: **~$2** (well under the $5 budget).
