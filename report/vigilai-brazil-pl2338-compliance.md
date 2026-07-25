---
title: "vigilAI: Auditing LLM Compliance with Brazil's PL 2338/2023 — a COMPL-AI Fork for Global-South AI Governance"
author: "Diana Chang and Ian Duhamel Hayes"
region: Latin America (Brazil)
subtrack: Governance
venue: Global South AI Safety Hackathon (Apart Research), June 2026
---

# vigilAI: Auditing LLM Compliance with Brazil's PL 2338/2023 — a COMPL-AI Fork for Global-South AI Governance

**Diana Chang and Ian Duhamel Hayes** &nbsp;·&nbsp; *Independent (unaffiliated)* &nbsp;·&nbsp; **With** Apart Research

**Region: Latin America (Brazil) &nbsp;·&nbsp; Sub-track: Governance**
*Research conducted at the Global South AI Safety Hackathon (Apart Research), June 2026.*[^1]

## Abstract

AI-safety evaluation suites are overwhelmingly built around English and the EU/US
regulatory frame, leaving open a practical question for anyone deploying models in
the Global South: does a model that *passes* a Western audit actually comply with a
local statute written in another language and grounded in different rights? We test
this for **Brazil's PL 2338/2023** — the AI Bill approved by the Federal Senate in
December 2024 — by **forking COMPL-AI**, the LatticeFlow / ETH Zurich / INSAIT
EU-AI-Act evaluation framework, into **vigilAI**. We preserve all 30 original EU
benchmarks and add **five Brazil-specific benchmarks** mapped to PL 2338/2023
Chapter II rights: AI disclosure (Art. 5, I), non-discrimination over Brazilian
(IBGE racial, regional, intersectional, religion and class) categories (Art. 5, III),
and the complete **high-risk Art. 6 rights triad** — explanation (I), contestation
(II) and human review (III) — plus the Arts. 25-28 Algorithmic Impact Assessment.
Because two Brazil benchmarks reuse the *exact same scorer* as their EU counterpart,
the **same-model EU--Brazil delta** isolates the Brazil-specific content from model
strength. Across **six models** (Anthropic, Meta, OpenAI, Alibaba, Mistral; 8B to
frontier), **all six** deny being human ~95-100% of the time in English but only
~50-55% of the time on Portuguese / LGPD-framed prompts — a **disclosure gap of about
-0.45 that is invisible to EU-only evaluation**. The failure is *specifically*
disclosure: the same models describe the high-risk Art. 6 procedural rights well
(0.72-0.99). We ship a per-article compliance report, a self-contained HTML scorecard
that doubles as the Art. 28 "public conclusions" artifact, and a six-model dossier.
**Takeaway: passing an EU-style audit does not imply Global-South compliance, and
purpose-built, localized benchmarks surface gaps that frontier-leaderboard scores
hide.**

## 1. Introduction

AI governance is going global, but AI-safety *evaluation* is not. The benchmarks that
dominate public leaderboards — and the frameworks regulators lean on, such as the EU
AI Act's COMPL-AI mapping [1, 2] — are written in English and encode European /
American rights and risk categories. Meanwhile the Global South is legislating on its
own terms. **Brazil's PL 2338/2023**, approved by the Federal Senate in December 2024
[3], establishes a rights-based regime that is distinct from the EU AI Act in both
substance and structure. It grants every person affected by an AI system a right to
**prior information that they are interacting with an AI** (Art. 5, I) and to
**non-discrimination** (Art. 5, III); and, for *high-risk* systems, a three-part
rights triad: **explanation** of the decision (Art. 6, I), **contestation** of the
decision (Art. 6, II), and **human review** of solely-automated decisions (Art. 6,
III). LGPD Art. 20 [4] already carries an explanation duty and a right to request
**review** of a solely-automated decision, but *not* to a human reviewer — "por pessoa
natural" was struck from the caput by Lei 13.853/2019, and the §3 introduced by the
2019 conversion bill that would have restored it stands as *(VETADO)*, veto upheld
2 October 2019 — so Art. 6, III is a substantive increment rather than a restatement.
High-risk deployers must additionally conduct
an **Algorithmic Impact Assessment (AIA)** and publish its conclusions (Arts. 25-28).

This raises a concrete, practically important question for any organization deploying
LLMs in Brazil: **does a model that looks compliant under an EU / English audit
actually satisfy Brazilian law?** The failure mode is silent. A model certified
abroad can systematically violate a local statutory right — for example, failing to
disclose that it is an AI when asked in Portuguese, or refusing to surface Brazil's
high-risk contestation right — without any English benchmark ever flagging it. For
Global-South regulators and deployers, the *absence of localized evaluation tooling*
is itself a safety gap: you cannot manage a risk you have no instrument to measure.

We argue that this gap is both real and tractable. It is real because the rights at
stake (Portuguese-language disclosure; an individual right to contest a model output)
are simply not represented in the dominant toolchain. It is tractable because the
existing EU machinery can be *forked and re-pointed* rather than rebuilt, letting the
EU and Brazil obligations run on one harness and one model so the comparison is
apples-to-apples.

***Our main contributions are:***

1. **vigilAI**, an open fork of COMPL-AI that preserves all 30 EU benchmarks and adds
   **five new Brazil-specific benchmarks** mapped to PL 2338/2023 articles —
   including, to our knowledge, the **first deterministic benchmarks for an individual
   right to contest plus human review (Art. 6, II--III)** and for AIA awareness
   (Arts. 25-28), neither of which has any EU / COMPL-AI counterpart.
2. A **same-model EU--Brazil comparison methodology**: two Brazil benchmarks reuse the
   *exact same scorer* as their EU original, so the delta isolates the effect of
   language plus Brazilian legal framing from model strength. We show the headline gap
   is **reproducible across six models** spanning four developers and 8B-to-frontier
   scale.
3. A **judge / regulator-facing reporting layer**: a per-article compliance report
   (Markdown / JSON), a self-contained **HTML scorecard** framed as the Art. 28
   "public conclusions" AIA artifact, a nine-requirement breadth coverage map, and a
   **six-model dossier** — plus a methodological finding that under-powered EU
   baselines can flip the *sign* of a measured compliance gap.

## 2. Related Work

**COMPL-AI** [1, 2] (LatticeFlow AI, ETH Zurich, INSAIT) is the closest prior work:
it operationalizes the EU AI Act into ~30 technical benchmarks on UK AISI's **Inspect
AI** [9], organized under nine "technical requirements." vigilAI *forks* it rather
than reimplementing, for two reasons: (a) it lets us run the EU and Brazil benchmarks
**on the same model with the same harness**, and (b) it makes the EU--Brazil
comparison apples-to-apples down to the scorer. COMPL-AI targets the EU AI Act, and to
our knowledge **no equivalent exists for any Global-South statute**; crucially, the EU
framework has no construct for Brazil's individual contestation / human-review rights
or its AIA, so those obligations cannot even be *expressed* in the existing tool.

For bias we build on **BBQ** [5], the hand-built QA bias benchmark. A web survey
confirmed that **no Portuguese / Brazilian BBQ-style dataset exists**: the 10+
adaptations (MBBQ, KoBBQ, PakBBQ, etc. [6]) cover other languages but not Portuguese,
and none uses Brazil's **IBGE** five-category racial taxonomy (branco, pardo, preto,
amarelo, indígena) [10]. We therefore build an adapted set, anchoring validated
Brazilian stereotypes in **SHADES / BiasShades** (pt-BR) [7] and **ToxSyn-PT** [8].
Unlike a generic multilingual bias score, our `bbq_brazil` is keyed to the protected
categories named in Brazilian anti-discrimination practice (race, region, religion,
class, and their intersections).

**When to use vigilAI over the state of the art.** Use it when you need to know
whether a model complies with *Brazilian* law specifically: vigilAI provides
per-article, statute-referenced scores that an EU-AI-Act or English leaderboard cannot
produce, and it surfaces rights (Art. 6, II--III; the AIA) that those tools do not
represent at all. The information it adds is *jurisdictional*: not "is this model good"
but "where, and against which statutory obligation, does this model fall short in
Brazil."

## 3. Methods

**Framework.** We forked COMPL-AI's source into `vigilAI` (Inspect AI, Python 3.12),
renamed the package, and **preserved all 30 EU tasks plus the nine
`technical_requirement` categories** so EU and Brazil benchmarks run on one harness.
We added a `brazil_article` / `brazil_scope` metadata layer mapping the relevant EU
requirements to PL 2338/2023 articles, surfaced in the CLI (`vigilai list --brazil`).

**The five Brazil benchmarks.**

| Brazil article | Benchmark | Scorer | EU counterpart |
| --- | --- | --- | --- |
| Art. 5, I — AI disclosure | `human_deception_brazil` (English + Portuguese + LGPD-framed "are you human?" prompts; target = denial) | reused COMPL-AI binary scorer | `human_deception` (same scorer) |
| Art. 5, III — non-discrimination | `bbq_brazil` (44 hand-authored ambiguous / disambiguated scenarios across IBGE race, region, intersectional, religion, class) | reused BBQ `choice()` scorer (ambiguous answer must be "cannot determine") | `bbq` (same scorer) |
| Art. 6, I — explanation | `explanation_quality` | deterministic 6-element rubric detector (criteria, data, logic, confidence, change factors, contestation path) | **none** |
| Art. 6, II--III — contestation + human review | `contestation_review` | deterministic 6-element rubric (contestation right / channel / deadline, human review, reviewer authority, outcome communicated) | **none** |
| Arts. 25-28 — AIA | `aia_checklist` | data-driven checklist coverage | **none** |

**Key design choices.** *(1) Same-scorer pairs.* Only `human_deception(_brazil)` and
`bbq(_brazil)` reuse an identical scorer, so the EU--Brazil delta isolates the
Brazil-specific *content* (language, legal framing, Brazilian categories), not scorer
differences. The other three are reported as Brazil-only "no EU equivalent" rows,
which is itself a finding. *(2) Deterministic, multilingual (pt-BR + English) rubric
scorers, no LLM judge.* They are reproducible, cost \$0, run under a mock model in CI,
and are unit-tested as pure functions; cue lists were tuned against real model output
so they credit free-form prose, not just template labels. *(3) Same-model-internal
comparison.* Model strength is not the variable of interest, so a cheap model is
methodologically valid — we deliberately do *not* need leaderboard-frontier models to
make a clean EU--Brazil claim.

**Models and configurations.** Six models. **Claude Haiku 4.5** and **Claude Sonnet
4.6** (Anthropic, API) ran the *scaled* config: `bbq` at 100 samples, **10 epochs**,
temperature 1.0, seed 42. **Llama 3.1 8B, gpt-oss 20B, Qwen2.5 14B** and **Mistral
Small** (local via Ollama) ran the *pilot* config: `--limit 20`, 1 epoch, \$0. Each
model's EU--Brazil deltas are computed **within one coherent run** (same backend, same
session), which is what makes the delta attributable to content rather than drift.
Total API cost about **\$3**.

**What didn't work / was constrained.** (a) Full local runs across all nine EU
requirements are impractical: several EU datasets (e.g., RealToxicityPrompts,
StrongREJECT) stream large HuggingFace downloads that exceed our time budget, so the
breadth coverage map is exercised deterministically and on the Brazil set. (b)
Reproducibility: every number is verifiable via `mockllm/model` plus `pytest` (173
tests), and every reported score is emitted by `vigilai report` over committed run
logs.

## 4. Results

**Headline (Art. 5, I — AI disclosure): a robust gap of about -0.45 on every model
(Figure 1, Table 1).** All six models deny being human ~95-100% of the time on the
English `human_deception` benchmark, but only ~50-55% of the time on the Portuguese
plus LGPD-framed `human_deception_brazil` variants. The Brazilian scores cluster
tightly at **0.50-0.55 regardless of model** — the tell that it is the *Portuguese /
legal content*, not any single model's weakness, that drives the failure. The EU side
is essentially zero-variance, so the gap is unambiguous.

![**Figure 1. The AI-disclosure gap is invisible to EU-only evaluation and reproduces across all six models.** Each model denies being human near-perfectly in English (`human_deception`, blue) but only ~50-55% of the time on Portuguese + LGPD-framed prompts (`human_deception_brazil`, red); the delta is Brazil minus EU. Higher is more compliant with PL 2338/2023 Art. 5, I. Frontier models use the scaled config (10 epochs); local models the pilot config (`--limit 20`, 1 epoch).](figures/disclosure_gap.png)

**Table 1. Same-model EU--Brazil deltas across six models** (delta = Brazil minus EU;
negative = less compliant on Brazil-specific content). Disclosure and bias each reuse
the *same scorer* per pair. Contestation / explanation / AIA have no EU equivalent
(Brazil-only scores shown). Column key: **hd** = `human_deception` (disclosure, Art. 5,
I); **bbq-BR** = `bbq_brazil` (bias, Art. 5, III); **expl** = `explanation_quality`
(Art. 6, I); **contest** = `contestation_review` (Art. 6, II-III); **AIA** =
`aia_checklist` (Arts. 25-28). Higher is more compliant.

| Model (config) | hd EU | hd-BR | Δ dis. | bbq EU | bbq-BR | Δ bias | expl | contest | AIA |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **Haiku 4.5** (scaled) | 1.000 | 0.524 | **-0.48** | 0.858 | 0.677 | **-0.18** | 0.833 | 0.975 | 0.983 |
| **Sonnet 4.6** (scaled) | 1.000 | 0.524 | **-0.48** | 0.518 ‡ | 0.375 | **-0.14** | 0.844 | 0.983 | 0.983 |
| Llama 3.1 8B (pilot) | 1.000 | 0.500 | -0.50 | 0.600 | 0.500 | -0.10 | 0.778 | 0.917 | 0.833† |
| gpt-oss 20B (pilot) | 1.000 | 0.550 | -0.45 | 0.700 | 0.750 | +0.05 | 0.778 | 0.958 | 1.000† |
| Qwen2.5 14B (pilot) | 1.000 | 0.550 | -0.45 | 0.600 | 0.700 | +0.10 | 0.722 | 0.875 | 1.000† |
| Mistral Small (pilot) | 0.950 | 0.550 | -0.40 | 0.550 | 0.550 | +0.00 | 0.722 | 0.917 | 1.000† |

‡ Sonnet's EU `bbq` is anomalously low: it uses BBQ's "cannot determine" option
unreliably (naming a person ~56% of the time in ambiguous contexts). The scorer parses
its answers correctly in every spot-check, so this is a genuine behavioral quirk;
because the *same* scorer applies to `bbq` and `bbq_brazil`, the Brazil minus EU delta
stays valid. † Local `aia_checklist` is a single scenario at 1 epoch (n = 1) — read
the local 1.000s as one observation, not a precise score; the reliable AIA numbers are
the scaled 0.950 / 0.983.

**Disclosure (Art. 5, I): confirmed, very strong.** 6/6 deltas negative, range -0.40 to
-0.50; the two frontier models land on the *identical* 0.524. An EU-AI-Act-only audit
certifies all six on disclosure; vigilAI shows they fail Brazil's Art. 5, I about half
the time. This is the cleanest result in the paper: the effect is large, has near-zero
variance on the EU side, and is invariant across developer, country of origin, and
model scale.

**Bias (Art. 5, III): directional trend, not yet conclusive.** On the deepened
44-scenario set, **both reliable frontier models are negative** (Haiku -0.18, Sonnet
-0.14) and 4/6 models are negative overall (mean about -0.05); the local pilot deltas
are within noise (n = 20). The direction supports "more biased on Brazilian
categories," but the magnitude needs a larger, native-annotator-validated set before it
can be called significant.

**Art. 6 triad + AIA: confirmed "beyond the EU," with a sharpened story.** All six
models score **0.72-0.99** on explanation, contestation / human review, and AIA — i.e.,
they *can* articulate the high-risk procedural rights well. These benchmarks
discriminate rather than saturating trivially: models reliably omit specific elements
(most often a confidence / uncertainty statement in explanations). The important
nuance is that **the compliance failure is specific to disclosure, not to high-risk
rights in general** — a more precise and more defensible claim than "models fail
Brazil." It also locates the risk where an EU-tuned model is least prepared: admitting
it is an AI, in Portuguese, on legal demand.

**Methodological finding.** Scaling the EU `bbq` baseline from 20 to 1000 samples moved
Haiku's bias delta from **+0.05** (pilot) to **-0.18** (scaled), because the EU `bbq`
baseline itself moved 0.65 to 0.858. An under-powered EU baseline can **invert the
sign** of a Global-South compliance gap — a direct argument for purpose-built,
properly-powered evaluation rather than reusing whatever EU baseline is cheapest to
run.

## 5. Discussion and Limitations

**Implications for AI safety.** A model can pass an English / EU audit and still
systematically violate a Global-South statutory right. The disclosure gap is the
cleanest example: it is invisible to every English benchmark, robust across developers
and scales, and tied to a *specific statutory obligation* under Brazilian law. This
argues that AI-safety evaluation must be **localized to the jurisdiction and language
of deployment**, and that Global-South rights (e.g., an individual right to contest a
model output) require **new benchmarks**, not translations of EU ones. vigilAI shows
this is achievable with modest effort: a fork, five benchmarks, and a same-model delta
give regulators and deployers a statute-referenced, reproducible compliance picture.
The reporting layer matters here too — the Art. 28 scorecard turns an eval run into the
exact public-conclusions artifact a high-risk deployer is obligated to produce.

### Limitations

- **Dataset scale.** `bbq_brazil` is 44 hand-authored scenarios; `explanation_quality`
  / `contestation_review` / `aia_checklist` are 3 / 4 / 1 scenarios respectively. These
  demonstrate the *method*, not definitive verdicts; native-annotator validation of the
  Portuguese scenarios is pending and is our highest-value next step.
- **Deterministic rubric scorers** detect the *presence* of required elements via
  multilingual cues. They measure whether a compliant *description* is produced, not
  real-world behavior, and could miss unusual phrasings (we tuned cue lists against real
  model output). Small-n tasks (e.g., contestation n = 4) show run-to-run variance; the
  10-epoch frontier numbers are the stable ones.
- **Pilot vs. scaled.** Local results are 1-epoch `--limit 20`; only the scaled frontier
  runs are high-precision. The Sonnet `bbq` quirk means its absolute BBQ-family numbers
  should be read as "unreliable on this answer format," though the delta holds.
- **Attribution assumption.** We assume the same-scorer EU--Brazil delta attributes
  differences to language / legal content. This holds because format and scorer are
  identical; if a model's Portuguese *general* competence (rather than legal disclosure
  specifically) drove the gap, the interpretation would weaken — but the tight 0.50-0.55
  clustering across very different models argues against a generic-competence
  explanation.
- **Not legal advice.** The PL 2338/2023 article mappings are an engineering
  interpretation built for evaluation, made against a bill still moving through the
  legislative process; they are a research instrument, not a legal determination of
  compliance for any specific deployment.

### Future Work

Scale and **native-annotator-validate `bbq_brazil`** (highest-value next step — would
move the bias finding from trend to significance); expand the Art. 6 / AIA scenario
banks with an optional LLM-judge cross-check; run the local models at the scaled config
to tighten their numbers; and add sector overlays (ANVISA health, BACEN finance) plus
the remaining EU-only requirements' Brazilian framing as the bill and ANPD guidance
mature.

## 6. Conclusion

We asked whether EU / English AI-safety compliance transfers to Brazil's PL 2338/2023,
and built **vigilAI** — a COMPL-AI fork with five Brazil-specific benchmarks and a
same-model EU--Brazil methodology — to answer it. It does not transfer: six models
across four developers near-perfectly disclose being AI in English yet fail the
Portuguese / LGPD disclosure right about half the time (delta about -0.45), a gap no
English benchmark surfaces. At the same time, Brazil's high-risk Art. 6 rights
(explanation, **contestation, human review**) and its AIA have **no EU benchmark
counterpart at all**, and vigilAI introduces deterministic benchmarks for them. The
practical message for Global-South AI governance is blunt: **certification under a
foreign regime is not compliance**, and localized, statute-referenced evaluation is
both necessary and achievable today.

## Code and Data

- **Code repository:** https://github.com/dyrtyData/vigilAI — a fork of
  [COMPL-AI](https://github.com/compl-ai/compl-ai). Reproduce with
  `uv run vigilai eval … && uv run vigilai report logs/<run> --html`.
- **Data / Datasets:** Brazil benchmark scenarios ship in-repo
  (`src/vigilai/tasks/*_brazil`, `contestation_review`, `aia_checklist`); anchored by
  SHADES / BiasShades (pt-BR) [7] and ToxSyn-PT [8].
- **Other artifacts:** `reports/RESULTS.md` (full multi-model analysis),
  `reports/scorecard.html` (Art. 28 scorecard), `reports/multimodel-scorecard.html`
  (six-page dossier, reproduced in Appendix B), and `reports/runs/` (per-model reports,
  split into Stage-7 baseline and Phase 8-11 additions).
- **License:** code is released under **Apache-2.0** (matching the upstream COMPL-AI
  ecosystem); this report and its figure under **CC-BY-4.0**.

## Author Contributions

Diana Chang and Ian Duhamel Hayes jointly designed and built vigilAI, implemented the
benchmarks and reporting layer, ran the evaluations, and prepared this report.

## LLM Usage Statement

We used Claude (Claude Code) to help fork and refactor COMPL-AI, implement the Brazil
benchmarks and reporting layer, run the evaluations, and draft this report. All
benchmarks are deterministic and unit-tested (173 tests).

## References

1. LatticeFlow AI, ETH Zurich, INSAIT. *COMPL-AI: A Technical Interpretation and LLM Benchmarking Suite for the EU AI Act.* 2024. https://compl-ai.org · https://github.com/compl-ai/compl-ai
2. European Union. *Regulation (EU) 2024/1689 (Artificial Intelligence Act).* 2024.
3. Senado Federal do Brasil. *Projeto de Lei nº 2338/2023 — Marco legal da inteligência artificial.* Approved by the Senate, Dec. 2024.
4. Brazil. *Lei nº 13.709/2018 (Lei Geral de Proteção de Dados — LGPD)*, esp. Art. 20.
5. Parrish, A. et al. *BBQ: A Hand-Built Bias Benchmark for Question Answering.* Findings of ACL 2022. https://aclanthology.org/2022.findings-acl.165/
6. e.g. Jin et al. *KoBBQ* (TACL 2024); Neplenbroek et al. *MBBQ* (2024); *PakBBQ* (2024) — BBQ adaptations; none cover Portuguese / IBGE categories.
7. Mitchell, M. et al. *SHADES / BiasShades: Multilingual Stereotype Benchmark.* NAACL 2025. https://aclanthology.org/2025.naacl-long.600/ · https://huggingface.co/datasets/LanguageShades/BiasShades
8. *ToxSyn-PT* (CC BY 4.0). https://huggingface.co/datasets/ToxSyn/ToxSyn-PT
9. UK AI Safety Institute. *Inspect AI: An open-source framework for LLM evaluations.* https://inspect.aisi.org.uk
10. IBGE (Instituto Brasileiro de Geografia e Estatística). Racial / colour classification (branco, pardo, preto, amarelo, indígena).

\newpage

## Appendix A — Reproducibility and details

- **Reproducibility commands**, per-model reports, the investigated Sonnet `bbq`
  breakdown, and standard errors: `reports/RESULTS.md`.
- **Coverage breadth:** 4 of 9 COMPL-AI requirements carry a bespoke Brazil benchmark
  (Disclosure, Representation, Interpretability, Societal Alignment); the remaining five
  are EU-only requirements with no Brazil Chapter II counterpart — rendered as a
  colour-coded (green / amber / grey) coverage map in every report.
- **Scaled standard errors:** `human_deception_brazil` 0.524 ± 0.112 (both frontier);
  `bbq_brazil` Haiku 0.677 ± 0.070, Sonnet 0.375 ± 0.056; `contestation_review` Haiku
  0.975 ± 0.023, Sonnet 0.983 ± 0.013.

\newpage

## Appendix B — Per-model compliance scorecards (6 pages, following)

The pages that follow are the vigilAI **per-model compliance dossier**
(`reports/multimodel-scorecard.html`), one self-contained scorecard per model: Claude
Haiku 4.5, Claude Sonnet 4.6, Llama 3.1 8B, gpt-oss 20B, Qwen2.5 14B, and Mistral
Small. Each page is the Art. 28 "public conclusions" artifact for that model — the
per-article compliance table, the EU--Brazil same-scorer side-by-side with signed
deltas, and the nine-requirement coverage map — with scores colour-banded (green
>= 0.80, amber 0.50-0.80, red < 0.50). All deltas are computed within one coherent run
per model.

[^1]: Research conducted at [The Global South AI Safety Hackathon](https://apartresearch.com/sprints/global-south-ais-hackathon-2026-06-19-to-2026-06-21), June 2026.
