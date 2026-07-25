# vigilAI — Results & Conclusions

**Do EU-tuned models comply with Brazil's PL 2338/2023 rights?**
A same-model, EU↔Brazil benchmark comparison built on a fork of COMPL-AI.

*Global South AI Safety Hackathon (LatAm governance subtrack). Every number below is reproduced
verbatim from `vigilai report <log_dir>`; the per-model reports live in
[`reports/runs/`](runs/) and the exact commands/seeds are in [Reproducibility](#reproducibility).*

> **Two run batches (read this first).** The numbers come from two benchmark batches, kept
> **separate** so the provenance of every score is clear:
>
> - **Batch A — Stage 7 baseline (Phases 1–7).** The original **four** Brazil benchmarks
>   (`human_deception_brazil`, `bbq_brazil`@20 samples, `explanation_quality`, `aia_checklist`)
>   across six models. Per-model reports: [`reports/runs/stage7-phases1-7/`](runs/stage7-phases1-7/).
> - **Batch B — Phase 8–11 additions.** The **fifth** benchmark `contestation_review`
>   (Art. 6, II–III — completes the high-risk rights triad) on all six models, **plus** the
>   **deepened `bbq_brazil`** (22 scenarios / **44 samples**). Per-model reports:
>   [`reports/runs/phase8-11/`](runs/phase8-11/). The coherent single-model headline run
>   (Haiku 4.5, all five benchmarks on the deepened set) is
>   [`reports/runs/phase8-11/haiku-4-5-complete.md`](runs/phase8-11/haiku-4-5-complete.md) and
>   drives [`reports/scorecard.html`](scorecard.html).
>
> The unchanged tasks (`human_deception_brazil`, `explanation_quality`, `aia_checklist`, the EU
> pairs `human_deception` / `bbq`) carry their Batch-A scores into Batch B — re-running them only
> reproduces the same numbers modulo sampling noise.

> ### ⚠️ SUPERSEDED AND INFLATED: every `contestation_review` figure on this page
>
> **Do not cite the `contestation_review` numbers below.** They were produced by a scorer with a
> defect that gave the benchmark a **score floor of 0.5**, found on 2026-07-25 by the iteration-2
> Phase 3 LLM-judge review (`docs/rubric-scenarios-llm-judge-review.md`, Section A).
>
> The deterministic rubric detector matched its content cues by **plain substring** against
> accent-folded text. Six cues were short enough to be contained in unrelated common words:
> `"form"` inside *forma* / *informação* / *conforme* / *plataforma*; `"dias"` inside *médias*;
> `"horas"` inside *senhoras*; `"ate "` inside every English `-ate` word (*investigate*,
> *communicate*); `"dentro de"` matching any generic containment; `"person"` inside
> *personalizado*. Verified empirically: a hostile non-answer whose literal content is *"a decisão
> … é definitiva … e não há recurso"* scored **3 of 6 elements = 0.500**, satisfying
> `contestation_right`, `contestation_channel` and `contestation_deadline` while refusing all
> three. `contestation_channel` was near-free for **any** Portuguese answer; `"dias"`/*médias* made
> a second near-free in the employment domain specifically; `"ate "` inflated every
> English-language response.
>
> **The numbers are kept, not deleted** — the provenance of the old figures is part of the record,
> and the paper's Methods section must be able to say what changed and why. But **0.975 / 0.988 /
> 1.000 / 0.958 / 0.875 / 0.708 are all inflated by an unknown amount**, the conclusion "all six
> models describe the contestation + human-review process well" is **not supported by them**, and
> the Δ they imply against `explanation_quality` may be an artefact of the two scorers' differing
> cue breadth rather than a real difference in model behaviour.
>
> The scorer was fixed the same day (single-token cues now match on **word boundaries**; all 24
> reference answers still score 1.0, the hostile probe now scores 1/6). Replacement figures come
> from the iteration-2 Phase 8/9 re-runs. The sibling `explanation_quality` scorer carried five
> instances of the same class — on equivalent hostile probes it scored **2/6** in pt-BR (*de forma
> **criterio**sa*, *a **data** do pedido*) and **1/6** in English (*Sincerely,*), both now **0/6**.
> Its iteration-1 figures (0.778–0.894) are therefore **also affected, though less severely**, and
> are superseded on the same basis. `bbq_brazil`, `human_deception_brazil` and `aia_checklist` are
> **unaffected** — none uses these detectors.

---

## Executive summary

1. **AI-disclosure compliance does not transfer to Portuguese / Brazilian law — on *every*
   model we tested.** Six models spanning four developers, three countries, and 8B→frontier
   scale all deny being human ~**95–100%** of the time in English (`human_deception`) but only
   ~**50–55%** of the time on the Portuguese + Brazil-disclosure (PL 2338/2023 Art. 5, I / LGPD)
   variants — a **≈ −0.45 gap invisible to EU-only evaluation**. The Brazilian scores cluster
   tightly at **0.50–0.55 regardless of model**, which points to the *question content* (language
   + legal framing), not the model, as the invariant. **This is the headline result.**
2. **The high-risk Art. 6 rights triad is now fully measured** (Phase 8). Brazil grants three
   high-risk rights — explanation (Art. 6, I), contestation (Art. 6, II) and human review
   (Art. 6, III) — none of which the EU AI Act grants to individuals. vigilAI tests all three.
   ~~Unlike disclosure, models are **good** at articulating the contestation + human-review process
   (`contestation_review`: frontier **0.97–0.99**, local 0.71–1.00): the right is "describable,"
   and they describe it. The failure is specific to *disclosure*, not to high-risk rights in
   general.~~ **⚠️ SUPERSEDED — see the scorer-defect notice above.** The scorer that produced
   those figures had a floor of 0.5, so "models are good at articulating the process" is not a
   conclusion these numbers can carry. What survives is the *coverage* claim: all three rights are
   measured, and the EU has no counterpart for any of them. Whether the triad scores high is
   reopened by the iteration-2 re-runs.
3. **On bias, the trend is "Brazil worse," but it is noisy.** On the deepened 44-sample
   `bbq_brazil`, both Anthropic frontier models score lower on Brazilian categories than on
   US-centric BBQ (Haiku −0.18, Sonnet −0.10); across all six models the bias delta is negative
   in 4/6, positive in 2. **Direction supports the thesis; magnitude is not yet conclusive.**
4. **Brazil's Art. 6 explanation / contestation / human-review rights and the Arts. 25-28 AIA
   obligations have no EU/COMPL-AI benchmark counterpart.** vigilAI introduces deterministic
   benchmarks for all of them; the "no EU equivalent" rows are themselves a finding about where
   Global-South AI governance outruns the EU-AI-Act toolchain.

> **Methodological headline:** scaling *changed the bias conclusion*. A noisy pilot (`bbq` at
> n=20) put Haiku **+0.05 better** on Brazilian bias; a proper baseline (`bbq` at n=1000) put it
> **−0.16 → −0.18 worse**. Under-powered EU baselines don't just add noise — they can flip the
> sign of a Global-South compliance gap.

---

## What we measured

vigilAI forks [COMPL-AI](https://github.com/compl-ai/compl-ai) (the EU-AI-Act evaluation
framework on Inspect AI), preserves all 30 original EU benchmarks, and adds **five** Brazil-specific
ones mapped to PL 2338/2023 Chapter II rights + the AIA:

| Brazil article | Scope | vigilAI benchmark | EU/COMPL-AI counterpart | Batch |
|---|---|---|---|---|
| Art. 5, I — prior information (AI disclosure) | all AI | `human_deception_brazil` | `human_deception` (same scorer) | A |
| Art. 5, III — non-discrimination | all AI | `bbq_brazil` (IBGE/regional/intersectional/religion/class) | `bbq` (same scorer) | A (deepened in B) |
| Art. 6, I — right to explanation (high-risk) | high-risk | `explanation_quality` | **none** | A |
| Art. 6, II-III — right to contest + human review (high-risk) | high-risk | `contestation_review` | **none** | **B (new)** |
| Arts. 25-28 — Algorithmic Impact Assessment | high-risk | `aia_checklist` | **none** | A |

**Design.** The two pairs that reuse the *exact same scorer* let the EU↔Brazil delta isolate the
Brazil-specific content (Portuguese; IBGE/regional/intersectional categories). The comparison is
*same-model internal* (EU task vs Brazil task on one backend), so model strength is not the
variable of interest — the EU↔Brazil delta is.

### Coverage breadth — Brazil compliance across all 9 COMPL-AI requirements

vigilAI preserves COMPL-AI's **nine** EU-AI-Act `technical_requirement` categories, so the
compliance report also renders a **breadth coverage map** showing, per requirement, whether a
Brazil-specific benchmark exists (✅), only the preserved EU task ran (🟡), or it is not yet
covered (⚪). Four of the nine requirements carry a bespoke Brazil benchmark mapped to a PL
2338/2023 article; the others remain EU-only (no Brazil Chapter II counterpart).

| EU technical requirement | Brazil article | Coverage |
|---|---|---|
| Disclosure of AI | Art. 5, I | ✅ Brazil benchmark (`human_deception_brazil`) |
| Representation — Absence of Bias | Art. 5, III | ✅ Brazil benchmark (`bbq_brazil`) |
| Fairness — Absence of Discrimination | Art. 5, III | 🟡 EU task only (`fairllm`, `decoding_trust`) |
| Interpretability | Art. 6, I | ✅ Brazil benchmark (`explanation_quality`) |
| Robustness and Predictability | — | 🟡 EU task only |
| Cyberattack Resilience | — | ⚪ not yet covered |
| Societal Alignment | Art. 6, II-III / Arts. 25-28 | ✅ Brazil benchmark (`contestation_review`, `aia_checklist`) |
| Capabilities, Performance, and Limitations | — | 🟡 EU task only |
| Harmful Content and Toxicity | — | ⚪ not yet covered |

**4 / 9 requirements have a purpose-built Brazil benchmark** (covering all of Art. 5, I/III, the
full Art. 6 high-risk rights triad, and the Arts. 25-28 AIA); the remaining five are EU-only
requirements with no Brazil Chapter II right to map to — that absence is itself a governance
finding, not a gap to paper over. The `--html` scorecard ([`reports/scorecard.html`](scorecard.html))
renders this same map color-coded.

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
- **pilot** = full local sets, 1 epoch (zero cost; lower precision — see caveats).

---

## Results — Batch A (Stage 7 baseline, 4 benchmarks)

Higher = more compliant. Δ = Brazil − EU (negative = *less* compliant on Brazil-specific content).
`bbq_brazil` here is the **original 20-sample** pilot set.

| Model | `human_deception` (EU) | `human_deception_brazil` | **Δ disclosure** | `bbq` (EU) | `bbq_brazil`@20 | **Δ bias** | `explanation_quality` | `aia_checklist` |
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

---

## Results — Batch B (Phase 8–11: completed Art. 6 triad + deepened bias)

Two benchmarks new/changed since Batch A. The unchanged-task columns above still hold; only the
two below were re-run. Full per-model breakdown:
[`reports/runs/phase8-11/new-benchmarks-all-models.md`](runs/phase8-11/new-benchmarks-all-models.md).

### `contestation_review` (Art. 6, II–III) — the completed triad

> **⚠️ SUPERSEDED AND INFLATED.** Every figure in this table came from a scorer with a **floor of
> 0.5** (see the notice at the top of this page). They are retained as the record of what was
> published, not as evidence. The `explanation_quality` column is affected too, less severely.

| Model | Config | `contestation_review` | (with `explanation_quality` Art. 6, I → full Art. 6 picture) |
|---|---|---|---|
| **Haiku 4.5** | scaled | **0.975 ± 0.023** | expl 0.833 → triad articulated well |
| **Sonnet 4.6** | scaled | **0.988 ± 0.013** | expl 0.850 |
| gpt-oss 20B | pilot | 1.000 ± 0.000 | expl 0.833 |
| Mistral Small | pilot | 0.958 ± 0.042 | expl 0.778 |
| Qwen2.5 14B | pilot | 0.875 ± 0.080 | expl 0.778 |
| Llama 3.1 8B | pilot | 0.708 ± 0.105 | expl 0.778 |

~~**All six models describe the contestation + human-review process well** (0.71–1.00). This
contrasts sharply with the disclosure failure: the gap is specific to *whether the model admits it
is an AI*, not to high-risk procedural rights.~~ **Withdrawn.** With a scorer floor of 0.5, a
0.71 is 1.3 elements above the floor rather than 4.3 above zero, and the spread this reading rests
on is compressed by an unknown amount. The disclosure finding (conclusion 1) is untouched — it uses
a different scorer entirely.

### `bbq_brazil` — deepened to 44 samples (Art. 5, III)

Δ bias = `bbq_brazil`@44 − the model's EU `bbq` baseline (EU `bbq` unchanged from Batch A).

| Model | `bbq_brazil`@44 | EU `bbq` baseline | **Δ bias (Brazil − EU)** |
|---|---|---|---|
| **Haiku 4.5** (scaled) | 0.677 ± 0.070 | 0.858 (n=1000) | **−0.18** |
| **Sonnet 4.6** (scaled) | 0.402 ± 0.056 | 0.498 ⚠️ (n=1000) | **−0.10** |
| gpt-oss 20B (pilot) | 0.727 ± 0.068 | 0.70 (n=20) | +0.03 |
| Mistral Small (pilot) | 0.659 ± 0.072 | 0.60 (n=20) | +0.06 |
| Qwen2.5 14B (pilot) | 0.659 ± 0.072 | 0.70 (n=20) | −0.04 |
| Llama 3.1 8B (pilot) | 0.477 ± 0.076 | 0.55 (n=20) | −0.07 |

Δ negative in **4/6**, mean ≈ **−0.05**; both reliable scaled frontier models negative. The deeper
set marginally tightened the frontier estimates (Haiku −0.16 → −0.18; Sonnet −0.12 → −0.10) and
left the local pilots within noise — i.e. **the deepening did not overturn the Batch-A trend.**

### Headline single-model scorecard (Haiku 4.5, all 5 benchmarks, deepened set)

Verbatim from `uv run vigilai report logs/<haiku-complete-run>` — the coherent run behind
[`reports/scorecard.html`](scorecard.html):

| Brazil article | Task | Score |
|---|---|---|
| Art. 5, I | `human_deception_brazil` | 0.524 |
| Art. 5, III | `bbq_brazil` (44) | 0.677 |
| Art. 6, I | `explanation_quality` | 0.833 |
| Art. 6, II-III | `contestation_review` ⚠️ superseded | 0.975 |
| Arts. 25-28 | `aia_checklist` | 0.983 |

EU↔Brazil side-by-side (same scorer): disclosure 0.524 vs 1.000 (**Δ −0.476**); bias 0.677 vs
0.858 (**Δ −0.181**). `explanation_quality` / `contestation_review` / `aia_checklist` = no EU
equivalent.

### Scaled runs — with standard error (the precise numbers)

| Benchmark | Haiku 4.5 | Sonnet 4.6 |
|---|---|---|
| `human_deception` (EU, Art. 5, I) | 0.997 ± 0.003 | 1.000 ± 0.000 |
| `human_deception_brazil` (Art. 5, I) | **0.524 ± 0.112** | **0.524 ± 0.112** |
| `bbq` (EU, Art. 5, III) | 0.858 ± 0.034 | 0.498 ± 0.044 ⚠️ |
| `bbq_brazil`@44 (Art. 5, III) | 0.677 ± 0.070 | 0.402 ± 0.056 |
| `explanation_quality` (Art. 6, I) | 0.833–0.894 ‡ | 0.850 ± 0.025 |
| `contestation_review` (Art. 6, II-III) ⚠️ superseded | 0.975 ± 0.023 | 0.988 ± 0.013 |
| `aia_checklist` (Arts. 25-28) | 0.917–0.983 ‡ | 0.950 |

‡ Haiku's `explanation_quality` (n=3) / `aia_checklist` (n=1) vary run-to-run on these tiny sets
(Batch A 0.894 / 0.917; coherent Batch-B run 0.833 / 0.983) — the spread is the small-n noise, not
a real change. The EU `human_deception` side is essentially zero-variance, so the disclosure gap is
unambiguous. Brazilian-set standard errors stay wide because those sets have few unique questions —
epochs cut within-question variance, not between-question variance.

Full per-model reports: Batch A → [`reports/runs/stage7-phases1-7/`](runs/stage7-phases1-7/);
Batch B → [`reports/runs/phase8-11/`](runs/phase8-11/).

---

## Conclusions — was the thesis correct?

### 1. "EU compliance ≠ Brazil compliance (the language/disclosure gap)" — ✅ CONFIRMED (very strong)

Six independent models — Anthropic, Meta, OpenAI, Alibaba, Mistral — converge on the same result:
near-perfect English disclosure, ~50–55% Portuguese/Brazil disclosure, Δ ≈ −0.45. Haiku and
Sonnet land on the *identical* 0.524; the local models cluster at 0.50–0.55. The tight clustering
across wildly different models is the tell: **it is the Portuguese + LGPD-framed questions that
defeat models, not any one model's weakness.** An EU-AI-Act-only audit would certify all six on
disclosure; vigilAI shows they fail Brazil's Art. 5, I about half the time.

### 2. "Brazil has high-risk rights with no EU benchmark" — ✅ CONFIRMED + now fully measured

Art. 6 explanation, **Art. 6 contestation + human review**, and Arts. 25-28 AIA have no
COMPL-AI/EU counterpart. With Phase 8's `contestation_review`, vigilAI now tests the **complete
high-risk Art. 6 rights triad**. The benchmarks *discriminate* (not trivial 1.0s): models score
0.83–0.99 and reliably omit specific elements (e.g. a confidence/uncertainty statement in
explanations). The key nuance: models are **fluent at describing high-risk procedural rights** —
the compliance failure is concentrated in *disclosure*, which is precisely the right an EU-tuned
model is least prepared for in Portuguese.

### 3. "Models are more biased on Brazilian categories" — 🟡 SUPPORTED AS A TREND (not conclusive)

On the deepened 44-sample set, both frontier models score lower on `bbq_brazil` than on `bbq`
(−0.18, −0.10), and 4 of 6 models overall show a negative bias delta — the predicted direction.
The local deltas remain within noise, so this is suggestive, not significant. **The method detects
the predicted effect; confirming it needs a larger, native-annotator-validated `bbq_brazil`.**

### 4. Methodological finding — small-n EU baselines mislead

Scaling flipped Haiku's bias delta from **+0.05** (pilot `bbq`@20) to **−0.16 → −0.18** (`bbq`@1000),
driven by the EU `bbq` baseline moving 0.65 → 0.858. Under-powered EU baselines can invert the sign
of a Global-South compliance gap — an argument for purpose-built evaluation.

---

## Caveats & limitations

- **Dataset sizes.** `bbq_brazil` = **44 hand-authored scenarios** (deepened in Phase 11 from 20;
  Race_IBGE / Region / Intersectional / Religion / Class); `explanation_quality` /
  `contestation_review` / `aia_checklist` = 3 / 4 / 1 scenarios. These demonstrate the *method*,
  not definitive verdicts. Native-annotator validation of the Portuguese scenarios is pending
  (future work).
- **Local "pilot" precision.** Local runs use the full small sets at 1 epoch: disclosure and bias
  are meaningful directionally; `explanation_quality` (n=3), `contestation_review` (n=4) and
  especially `aia_checklist` (n=1) are low-n — the local 1.00s are one or few observations, not
  precise scores. The scaled frontier runs are the reliable numbers.
- **Run-to-run variance on tiny sets.** `contestation_review` (n=4) moved 0.50 → 0.71 → 0.975
  across Llama/Haiku runs; the few-shot-guided frontier scores (0.97–0.99) are stable, the small-n
  local single-epoch points are not. **⚠️ And all of them are superseded** — see the scorer-defect
  notice at the top. Note that the lowest figure ever recorded for this benchmark, 0.50, is
  *exactly* the floor the defective cue lists imposed.
- **Deterministic keyword scorers are a measurement risk, not just an approximation.** The two
  Art. 6 rubric scorers detect elements by matching cue strings. Until 2026-07-25 they matched by
  plain substring, and eleven cues across the two were short enough to be contained in unrelated
  common Portuguese or English words — which is how `contestation_review` acquired a floor of 0.5
  without anyone noticing for a whole iteration. The class is now closed structurally (word-bounded
  matching) and pinned by regression tests, but the general caution stands and is why iteration 2
  adds an LLM-judge cross-check: a keyword scorer's failure mode is *silent inflation*, and it does
  not show up in the standard error.
- **Sonnet `bbq` anomaly — INVESTIGATED.** Sonnet's EU `bbq` (0.498) is far below Haiku's
  (0.858). Breaking it down by context condition: **ambiguous 0.436** (Sonnet picks a *named
  person* ~56% of the time instead of "cannot be determined"), **disambiguated 0.560**. The
  `choice()` scorer parsed the final answer correctly in every spot-check. This is a **genuine
  behavioral difference — Sonnet uses BBQ's "unknown" option unreliably in both directions — not
  over-caution and not a scorer bug.** Because the same scorer/format applies to `bbq` and
  `bbq_brazil`, the Brazil−EU *delta* (−0.10) remains valid; Sonnet's *absolute* BBQ-family numbers
  should be read as "unreliable on this answer format."
- **Same-model-internal comparison.** We do not claim one model is "more compliant" than another,
  only that each is less compliant on Brazil-specific content than on its EU counterpart.

---

## Future work

- Scale `bbq_brazil` to a statistically powered, **native-annotator-validated** set (the single
  highest-value next step — would move conclusion #3 from "trend" to a significance test).
- Expand `explanation_quality` / `contestation_review` / `aia_checklist` scenario banks; optional
  LLM-judge cross-check of the deterministic detectors.
- Re-run the local models at the scaled config (more epochs) to tighten their bias / explanation /
  contestation / AIA numbers.
- Sector overlays (ANVISA, BACEN) and the remaining EU-only requirements' Brazil framing.

---

## Reproducibility

`vigilai` (fork of COMPL-AI), Inspect AI, Python 3.12 via `uv`. API key in `vigilAI/.env`
(gitignored).

```bash
# Batch A + B — scaled frontier runs (Haiku, Sonnet), all 5 Brazil benchmarks + EU pairs
uv run vigilai eval anthropic/claude-haiku-4-5  --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist --limit 100 --epochs 10 --temperature 1.0 --seed 42
uv run vigilai eval anthropic/claude-sonnet-4-6 --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist --limit 100 --epochs 10 --temperature 1.0 --seed 42

# Local pilot runs (zero cost) — gpt-oss, qwen2.5, mistral-small, llama3.1
for M in gpt-oss:20b qwen2.5:14b mistral-small:latest llama3.1:8b; do \
  uv run vigilai eval ollama/$M --tasks human_deception,human_deception_brazil,bbq,bbq_brazil,explanation_quality,contestation_review,aia_checklist --limit 20 ; done

# Report (per-article + EU↔Brazil side-by-side + 9-requirement coverage map)
uv run vigilai report logs/<run-dir>          # Markdown
uv run vigilai report logs/<run-dir> --json   # machine-readable
uv run vigilai report logs/<run-dir> --html   # self-contained color-coded scorecard (Art. 28 artifact)
```

Per-model reports are committed under [`reports/runs/`](runs/) (Batch A in
[`stage7-phases1-7/`](runs/stage7-phases1-7/), Batch B in [`phase8-11/`](runs/phase8-11/)).
Approximate total API cost across all frontier runs: **~$3** (well under the $5 budget); the four
local models were $0.
