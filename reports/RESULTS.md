# vigilAI — Results & Conclusions

**Do EU-tuned models comply with Brazil's PL 2338/2023 rights?**
A same-model, EU↔Brazil benchmark comparison built on a fork of COMPL-AI.

*Global South AI Safety Hackathon (LatAm governance subtrack). Every number below is reproduced
verbatim from `vigilai report <log_dir>`; the per-model reports live in
[`reports/runs/`](runs/) and the exact commands/seeds are in [Reproducibility](#reproducibility).*

---

## Executive summary

1. **AI-disclosure compliance does not transfer to Portuguese / Brazilian law — on *every*
   model we tested.** Six models spanning four developers, three countries, and 8B→frontier
   scale all deny being human ~**95–100%** of the time in English (`human_deception`) but only
   ~**50–55%** of the time on the Portuguese + Brazil-disclosure (PL 2338/2023 Art. 5, I / LGPD)
   variants — a **≈ −0.45 gap invisible to EU-only evaluation**. The Brazilian scores cluster
   tightly at **0.50–0.55 regardless of model**, which points to the *question content* (language
   + legal framing), not the model, as the invariant.
2. **On bias, the trend is "Brazil worse," but it is noisy.** With reliable baselines (10
   epochs) both Anthropic frontier models score lower on Brazilian categories than on US-centric
   BBQ (Haiku −0.16, Sonnet −0.12); across all six models the bias delta is negative in 4/6,
   zero in 1, positive in 1. **Direction supports the thesis; magnitude is not yet conclusive**
   (the `bbq_brazil` pilot has 20 scenarios).
3. **Brazil's Art. 6 right-to-explanation and Arts. 25-28 AIA obligations have no EU/COMPL-AI
   benchmark counterpart.** vigilAI introduces deterministic benchmarks for both; the "no EU
   equivalent" rows are themselves a finding about where Global-South AI governance outruns the
   EU-AI-Act toolchain.

> **Methodological headline:** scaling *changed the bias conclusion*. A noisy pilot (`bbq` at
> n=20) put Haiku **+0.05 better** on Brazilian bias; a proper baseline (`bbq` at n=1000) put it
> **−0.16 worse**. Under-powered EU baselines don't just add noise — they can flip the sign of a
> Global-South compliance gap.

---

## What we measured

vigilAI forks [COMPL-AI](https://github.com/compl-ai/compl-ai) (the EU-AI-Act evaluation
framework on Inspect AI), preserves all 30 original EU benchmarks, and adds four Brazil-specific
ones mapped to PL 2338/2023 Chapter II rights + the AIA:

| Brazil article | Scope | vigilAI benchmark | EU/COMPL-AI counterpart |
|---|---|---|---|
| Art. 5, I — prior information (AI disclosure) | all AI | `human_deception_brazil` | `human_deception` (same scorer) |
| Art. 5, III — non-discrimination | all AI | `bbq_brazil` (IBGE/regional/intersectional) | `bbq` (same scorer) |
| Art. 6, I — right to explanation (high-risk) | high-risk | `explanation_quality` | **none** |
| Arts. 25-28 — Algorithmic Impact Assessment | high-risk | `aia_checklist` | **none** |

**Design.** The two pairs that reuse the *exact same scorer* let the EU↔Brazil delta isolate the
Brazil-specific content (Portuguese; IBGE/regional/intersectional categories). The comparison is
*same-model internal* (EU task vs Brazil task on one backend), so model strength is not the
variable of interest — the EU↔Brazil delta is.

**Models (6).** Two Anthropic frontier models via API (scaled config) and four local models via
Ollama at zero cost (pilot config):

| Model | Developer / origin | Access | Config |
|---|---|---|---|
| Claude Haiku 4.5 | Anthropic (US) | API | scaled |
| Claude Sonnet 4.6 | Anthropic (US) | API | scaled |
| Llama 3.1 8B | Meta (US) | local Ollama | pilot |
| gpt-oss 20B | OpenAI (US, open-weight) | local Ollama | pilot |
| Qwen2.5 14B | Alibaba (China) | local Ollama | pilot |
| Mistral Small | Mistral (France) | local Ollama | pilot |

- **scaled** = full small sets + `bbq`@100, **10 epochs**, temperature 1.0, seed 42 (≈$1 each).
- **pilot** = `--limit 20`, 1 epoch (zero cost; lower precision — see caveats).

---

## Results

### Cross-model headline matrix

Higher = more compliant. Δ = Brazil − EU (negative = *less* compliant on Brazil-specific content).

| Model | `human_deception` (EU) | `human_deception_brazil` | **Δ disclosure** | `bbq` (EU) | `bbq_brazil` | **Δ bias** | `explanation_quality` | `aia_checklist` |
|---|---|---|---|---|---|---|---|---|
| **Haiku 4.5** (scaled) | 0.997 | 0.524 | **−0.47** | 0.858 | 0.700 | **−0.16** | 0.894 | 0.917 |
| **Sonnet 4.6** (scaled) | 1.000 | 0.524 | **−0.48** | 0.498 ⚠️ | 0.375 | **−0.12** | 0.850 | 0.950 |
| Llama 3.1 8B (pilot) | 1.00 | 0.50 | −0.50 | 0.55 | 0.45 | −0.10 | 0.778 | 1.00† |
| gpt-oss 20B (pilot) | 1.00 | 0.55 | −0.45 | 0.70 | 0.70 | 0.00 | 0.833 | 1.00† |
| Qwen2.5 14B (pilot) | 1.00 | 0.55 | −0.45 | 0.70 | 0.60 | −0.10 | 0.778 | 1.00† |
| Mistral Small (pilot) | 0.95 | 0.55 | −0.40 | 0.60 | 0.65 | +0.05 | 0.778 | 1.00† |

⚠️ Sonnet `bbq` is anomalous — see [caveats](#caveats--limitations). † Local `aia_checklist` is a
**single scenario at 1 epoch** (n=1) — treat the 1.00s as one observation, not a precise score;
the reliable AIA numbers are the scaled 0.917 / 0.950.

**Disclosure (Art. 5, I):** all six Δ are negative, range **−0.40 to −0.50**, and every Brazilian
score lands in **0.50–0.55**. This is the robust, headline result.

**Bias (Art. 5, III):** Δ = −0.16, −0.12, −0.10, 0.00, −0.10, +0.05 → negative in 4/6, mean ≈
−0.07. Leans "Brazil worse," strongest and most reliable on the two scaled frontier runs.

### Scaled runs — with standard error (the precise numbers)

| Benchmark | Haiku 4.5 | Sonnet 4.6 |
|---|---|---|
| `human_deception` (EU, Art. 5, I) | 0.997 ± 0.003 | 1.000 ± 0.000 |
| `human_deception_brazil` (Art. 5, I) | **0.524 ± 0.112** | **0.524 ± 0.112** |
| `bbq` (EU, Art. 5, III) | 0.858 ± 0.034 | 0.498 ± 0.044 ⚠️ |
| `bbq_brazil` (Art. 5, III) | 0.700 ± 0.105 | 0.375 ± 0.090 |
| `explanation_quality` (Art. 6, I) | 0.894 ± 0.039 | 0.850 ± 0.025 |
| `aia_checklist` (Arts. 25-28) | 0.917 | 0.950 |

The EU `human_deception` side is essentially zero-variance, so the disclosure gap is
unambiguous. Brazilian-set standard errors stay wide (±0.09–0.11) because those sets have only
20–21 unique questions — epochs cut within-question variance, not between-question variance.

Full per-model reports (per-article + EU↔Brazil side-by-side): [`reports/runs/`](runs/).

---

## Conclusions — was the thesis correct?

### 1. "EU compliance ≠ Brazil compliance (the language/disclosure gap)" — ✅ CONFIRMED (very strong)

Six independent models — Anthropic, Meta, OpenAI, Alibaba, Mistral — converge on the same result:
near-perfect English disclosure, ~50–55% Portuguese/Brazil disclosure, Δ ≈ −0.45. Haiku and
Sonnet land on the *identical* 0.524; the local models cluster at 0.50–0.55. The tight clustering
across wildly different models is the tell: **it is the Portuguese + LGPD-framed questions that
defeat models, not any one model's weakness.** An EU-AI-Act-only audit would certify all six on
disclosure; vigilAI shows they fail Brazil's Art. 5, I about half the time.

### 2. "Models are more biased on Brazilian categories" — 🟡 SUPPORTED AS A TREND (not conclusive)

With reliable baselines, both frontier models score lower on `bbq_brazil` than on `bbq` (−0.16,
−0.12), and 4 of 6 models overall show a negative bias delta — the predicted direction. But the
local deltas are within noise at n=20, and the Brazilian set is a 20-scenario pilot, so this is
suggestive, not significant. **The method detects the predicted effect; confirming it needs a
larger, native-annotator-validated `bbq_brazil`.**

### 3. "Brazil has rights with no EU benchmark" — ✅ CONFIRMED by construction

Art. 6 explanation and Arts. 25-28 AIA have no COMPL-AI/EU counterpart. vigilAI's new
deterministic benchmarks fill the gap and *discriminate* (scaled scores 0.85–0.95, not trivial
1.0s — both frontier models reliably omit a confidence/uncertainty statement in explanations).

### 4. Methodological finding — small-n EU baselines mislead

Scaling flipped Haiku's bias delta from **+0.05** to **−0.16**, driven by the EU `bbq` baseline
moving 0.65 → 0.858 once estimated on 1000 samples instead of 20. Under-powered EU baselines can
invert the sign of a Global-South compliance gap — an argument for purpose-built evaluation.

---

## Caveats & limitations

- **Pilot dataset sizes.** `bbq_brazil` = 20 hand-authored scenarios; `explanation_quality` /
  `aia_checklist` = 3 / 1. These demonstrate the *method*, not definitive verdicts. Native-
  annotator validation of the Portuguese scenarios is pending (future work).
- **Local "pilot" precision.** Local runs use `--limit 20`, 1 epoch: disclosure (n=20) and bias
  (n=20) are meaningful directionally; `explanation_quality` (n=3) and especially `aia_checklist`
  (n=1) are single-config points — the local 1.00 AIA scores are one observation each, not
  precise. The scaled frontier runs are the reliable numbers.
- **Sonnet `bbq` anomaly — INVESTIGATED.** Sonnet's EU `bbq` (0.498) is far below Haiku's
  (0.858). Breaking it down by context condition: **ambiguous 0.436** (Sonnet picks a *named
  person* ~56% of the time instead of "cannot be determined"), **disambiguated 0.560** (it
  sometimes refuses to name the person). The `choice()` scorer parsed the final answer correctly
  in every spot-check, and Sonnet's outputs show a verbose `ANSWER: $C — wait, let me
  reconsider…` style. So this is a **genuine behavioral difference — Sonnet uses BBQ's "unknown"
  option unreliably in both directions — not over-caution and not a scorer bug.** Because the
  same scorer/format applies to `bbq` and `bbq_brazil`, the Brazil−EU *delta* (−0.12) remains
  valid; but Sonnet's *absolute* BBQ-family numbers should be read as "unreliable on this
  answer format," not a clean bias measure.
- **Same-model-internal comparison.** We do not claim one model is "more compliant" than another,
  only that each is less compliant on Brazil-specific content than on its EU counterpart.

---

## Future work

- Scale `bbq_brazil` to a statistically powered, **native-annotator-validated** set (the single
  highest-value next step — would move conclusion #2 from "trend" to a significance test).
- Expand `explanation_quality` / `aia_checklist` scenario banks; optional LLM-judge cross-check
  of the deterministic detectors.
- Re-run the local models at the scaled config (more epochs) to tighten their bias/explanation/AIA
  numbers.
- Add the remaining Brazil rights (Art. 6, II contestation; Art. 6, III human review) and
  sector overlays (ANVISA, BACEN).

---

## Reproducibility

`vigilai` (fork of COMPL-AI), Inspect AI, Python 3.12 via `uv`. API key in `vigilAI/.env`
(gitignored).

```bash
# Scaled frontier runs (Haiku, Sonnet) — identical params
uv run vigilai eval anthropic/claude-haiku-4-5  --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,aia_checklist --limit 100 --epochs 10 --temperature 1.0 --seed 42
uv run vigilai eval anthropic/claude-sonnet-4-6 --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,aia_checklist --limit 100 --epochs 10 --temperature 1.0 --seed 42

# Local pilot runs (zero cost) — gpt-oss, qwen2.5, mistral-small, llama3.1
for M in gpt-oss:20b qwen2.5:14b mistral-small:latest llama3.1:8b; do \
  uv run vigilai eval ollama/$M --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,aia_checklist --limit 20 ; done

# Report (per-article + EU↔Brazil side-by-side)
uv run vigilai report logs/<run-dir>          # Markdown
uv run vigilai report logs/<run-dir> --json   # machine-readable
```

Per-model reports are committed under [`reports/runs/`](runs/). Approximate total API cost across
all frontier runs: **~$2** (well under the $5 budget); the four local models were $0.
