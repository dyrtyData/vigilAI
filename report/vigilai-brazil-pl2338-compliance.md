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
A primary-source reading of the legislative record shows why the Art. 6 rights are
worth measuring at all: Brazilian law twice grants a right to *review* of a
solely-automated decision — LGPD Art. 20 and Cadastro Positivo Art. 5, VI — and twice
declines to say who performs it, so **Art. 6, III is a substantive increment rather
than a restatement**. We also state plainly what this work has *not* done: the
Brazilian categories were chosen, written and reviewed without Brazilian
participation, and we publish the participation protocol that would change that
rather than claiming it already has. **Takeaway: passing an EU-style audit does not
imply Global-South compliance, and purpose-built, localized benchmarks surface gaps
that frontier-leaderboard scores hide.**

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
2 October 2019 [11, 12] — so Art. 6, III is a substantive increment rather than a
restatement. Section 6 shows this is a *pattern* rather than a single statute's
accident: Lei 12.414/2011 Art. 5, VI [13] grants the same review right, with the same
silence about who performs it, in consumer credit. High-risk deployers must
additionally conduct an **Algorithmic Impact Assessment (AIA)** and publish its
conclusions (Arts. 25-28).

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
4. A **positionality and participation stance that is executable rather than
   declarative** (§5): the Brazilian scholarship on *racismo algorítmico* [14, 15] and
   the binding instruments Brazil has ratified as the normative frame; the
   helicopter-research test [16] applied to this project by name; and a written,
   costed participation protocol composed from three published BBQ-family annotation
   protocols. We report what has **not** happened as carefully as what has.

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
| Art. 5, III — non-discrimination | `bbq_brazil` (100 scenarios / 400 samples across IBGE race, region, intersectional, religion, class: 2 context conditions × 2 question polarities, 20 scenarios per axis; 22 from the iteration-1 pilot, 78 from a committed deterministic generator) | reused BBQ `choice()` scorer (ambiguous answer must be "cannot determine") | `bbq` (same scorer) |
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

**Bias (Art. 5, III): directional trend, not yet conclusive.** On iteration 1's
44-sample set, **both reliable frontier models are negative** (Haiku -0.18, Sonnet
-0.14) and 4/6 models are negative overall (mean about -0.05); the local pilot deltas
are within noise (n = 20). The direction supports "more biased on Brazilian
categories," but the magnitude needs a larger, native-annotator-validated set before it
can be called significant — and the second of those two conditions is the one §5 says
has not been met.

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

## 5. Positionality, participation, and human rights

A benchmark that measures Brazilian prejudice, whose categories were chosen by two
people who are not Brazilian, whose items were drafted by a language model, and whose
only review has been by other language models, is in a poor position to cite decolonial
theory. Citing the theory without a participation stance is the failure mode the theory
names. This section states the frame we work in, the instruments that make it binding
rather than aspirational, and then applies both to this project by name.

### 5.1 *Racismo algorítmico*, not "AI bias"

The central citation is Brazilian and in Portuguese: Tarcízio Silva's **_Racismo
Algorítmico_** [14], for whom *"o racismo algorítmico é uma espécie de atualização do
racismo estrutural"* — algorithmic racism as an *update* to structural racism rather
than a defect of a model. That reframing changes the object of measurement. A "bias
score" invites the reading that a model has a fixable flaw; *racismo algorítmico*
insists that the flaw is continuous with a structure the system is embedded in, which
is why PL 2338 places non-discrimination among *rights of affected persons* (Art. 5,
III) rather than among model-quality requirements. The 2024 IRIS-BH / Tarcízio Silva /
Ação Educativa report on AI and racial discrimination in Brazil [15] — produced with
Brazilian expert input feeding a UN thematic report — is the companion source, and the
reason `bbq_brazil`'s axes are Brazilian rather than translated: IBGE's five-category
*cor ou raça* taxonomy [10]; regional prejudice, documented as "internal orientalism";
class markers from ABEP's *Critério Brasil*; and ***racismo religioso***, a term
Brazilian scholarship originated, covering communities that are roughly 1% of the
population and 50–65% of recorded religious-intolerance victims. No US-derived
taxonomy produces that last axis at all.

### 5.2 Categories are not neutral data fields

Ricaurte [17] argues that treating locally-produced categories as neutral data fields
reproduces an epistemic hierarchy — the categories become inputs to somebody else's
model rather than descriptions their holders control. Couldry and Mejias [18] extend
this to the dataset itself: a corpus of stereotype scenarios about real communities is a
site of extraction, not only of measurement. Mohamed, Png and Isaac [19] pose the
question that a bias benchmark cannot avoid — *whose knowledge counts as ground truth*
— though we cite them with a tension acknowledged, since their "reverse tutelage"
proposal has itself been criticized for risking a framing in which the Global North
grants permission to participate. Adams [20] asks whether AI can be decolonized at all
without changing who builds it, which is a harder question than the one we answer here.
Birhane's relational account [21] is the reason `bbq_brazil` has a compound
*intersectional* axis rather than stackable independent ones: *mulher negra nordestina*
is not the sum of three filters. And *Data Feminism* [22] and *Design Justice* [23]
supply the two propositions this section is measured against — centre the lived
experience of the categories rather than literature-derived descriptions of them, and
remember that "power shapes participation in all design processes", so a participatory
step is not automatically an equitable one. On the first proposition, this project
currently fails: our stereotypes are literature-derived.

### 5.3 The instruments are binding, not aspirational

Domestically, CF/88 Art. 5 makes equality a fundamental right and racism an
imprescriptible, non-bailable crime; Lei 7.716/1989, Lei 12.288/2010 (Estatuto da
Igualdade Racial) and Lei 14.532/2023 give it statutory shape; and **LGPD Art. 5º, II**
names racial or ethnic origin and religious conviction as *sensitive personal data* —
which is directly relevant, because two of `bbq_brazil`'s five axes are LGPD-sensitive
categories and the participation protocol in §5.6 would collect exactly that data from
its annotators.

Internationally, Brazil has ratified the **American Convention on Human Rights**
(Decreto 678/1992; IACtHR compulsory jurisdiction accepted 1998), Arts. 1 and 24; and
**ICERD** (ratified 27 March 1968, Decreto 65.810/1969), whose Art. 1 definition is
**effects-based** and so reaches facially neutral systems with discriminatory outcomes
[24]. The feminist anchor is the **Convention of Belém do Pará**, adopted in 1994 *in
Belém, Brazil* and ratified in November 1995: it obliges states to modify the
*"socio-cultural patterns"* that perpetuate stereotyped roles. That is a binding treaty,
adopted on Brazilian soil, that makes **stereotype itself** the object of a state
obligation — which is precisely the object a stereotype benchmark measures, and a
stronger foundation for the feminist framing than any citation we could import.

**One caution we impose on ourselves.** Brazil has been an ICERD party since 1968 and
the CERD Committee's 2022 Concluding Observations address racial discrimination in
Brazil. **We attribute no finding about AI or algorithms to the Committee and cite no
paragraph of it.** The step from ICERD Art. 1's effects-based definition to algorithmic
systems, and specifically to facial recognition, is **our own argument**, and it should
be read and contested as ours. On the soft-law side, the UNESCO Recommendation on the
Ethics of AI [25] (adopted 2021; pt-BR translation by UNESCO Brasília, 2022) and the
UNGPs with OHCHR's B-Tech work [26] are the natural frame for an AIA, since
human-rights due diligence is what Arts. 25-28 amount to in substance.

### 5.4 *Not My AI*, adapted rather than cited

Coding Rights' feminist-decolonial framework for public-sector algorithmic systems [27]
is designed to be used, so we used it, turning its orientation into questions we put to
vigilAI and answered:

| Question | Answer for vigilAI |
| --- | --- |
| Who is the system *for*, and who is it done *to*? | It is for regulators and deployers. The affected person is *represented* by the benchmark, not *present* in it. Partial mitigation: the Art. 28 scorecard is built to be a public-facing artifact rather than an internal report. |
| Whose categories? | Ours — see §5.5. |
| Does it make an existing power asymmetry legible, or add one? | Both. A compliance score is a thing a deployer can use to certify itself. The counterweight is the **gap-flagging items**, which measure whether a deployer exceeds duties that no Brazilian instrument imposes; a low score there is a finding about the regulatory regime, not about the model. |
| Who can contest the instrument itself? | Today, nobody. There is no channel through which a Brazilian who thinks an item is wrong can have it removed. §4.3 of the participation protocol is the design of that channel, including a removal power the researchers cannot overrule. |
| What happens to data about people? | The scenarios are synthetic and describe no real individual. The annotator data the protocol *would* collect is LGPD-sensitive and is minimized, separated and deleted on a stated schedule. |
| Who benefits from publishing? | We do. That is the honest answer to Birhane et al.'s question [28], and it is the one the protocol's co-authorship and benefit-sharing terms exist to change. |

### 5.5 Participation-washing, and the helicopter-research test applied to vigilAI

Sloane, Moss, Awomolo and Forlano name **participation-washing** [29]: participatory
language, or a thin participatory gesture, used to launder a system whose design
decisions were made elsewhere. Birhane, Isaac, Prabhakaran and Díaz [28] ask who the
primary beneficiaries of participatory activity actually are. The helicopter-research
literature [16] converts both into a test with four checkable questions. We answer them
about this project, in the paper rather than in a supplement, because an answer kept in
a supplement is the gesture the critique is about.

**Who conceived the categories?** The two authors, neither Brazilian, neither resident
in Brazil. The five axes were selected from Brazilian secondary sources, but *which*
axes exist — and what counts as an axis at all — was our decision.

**Who wrote the items?** A large language model (Claude, via Claude Code), under our
direction, from term banks the same model assembled from those secondary sources. The
22 pilot scenarios were drafted item by item; the other 78 are deterministic expansions
of 30 templates over 34 contrast pairs. The generation *pipeline* contains no model call
and reproduces byte-for-byte — but that is a reproducibility property, not a provenance
one, and it would be misleading to let it stand as an answer to this question. **No
Brazilian wrote a scenario.**

**Who validated them?** Nobody who lives the categories. Every review to date has been
by **LLM judges** — five rounds over the 100 `bbq_brazil` scenarios and one over the 24
rubric scenarios, both committed to the repository, and each document opening by stating
that it is a pre-screen and not validation. Those rounds caught real defects — seven
items that measured backwards, one keyed to its own biased answer, a template pointed at
an axis no Brazilian prejudice occupies — which is evidence that the items *needed*
review, not that they have had it.

**Who is a co-author?** Two authors. No Brazilian co-author, no Brazilian institutional
partner, no Brazilian ethics review.

**What this does and does not undermine**, stated because a positionality section that
made every finding equally suspect would be as uninformative as one that made none. It
bears directly on `bbq_brazil` (Art. 5, III), whose construct validity rests entirely on
whether these stereotypes are attested in Brazil and pointed in the right direction — a
judgment we have not obtained, and the reason the bias result is reported as a
direction and not a magnitude. It bears partly on the three pt-BR rubric benchmarks,
whose scenarios are similarly authored but whose scoring targets a procedural checklist
drawn from statute rather than from a social judgment. It bears least on the paper's
headline, `human_deception_brazil` (Art. 5, I): its target is "the model denies being
human", scored by the same scorer as the English original, with no stereotype judgment
anywhere in it.

### 5.6 The protocol, and the claim we are not making

`docs/participation-protocol.md` sets out the validation that would close §5.5, composed
from three published BBQ-family protocols and citing each for the component it actually
contributes: **KoBBQ's quantitative core** [30] (a defined N per item, demographic
balancing, a **>2/3 validity threshold**, a reading-comprehension check, and *reporting
how many candidate items were eliminated*); **SeeGULL's qualification rule** [31] —
in-region residency, generalized to lived membership, so that a *nordestino* stereotype
is validated by nordestinos and a *candomblecista* one by candomblecistas; and
**PakBBQ's transparency and duty of care** [32] — named annotators, a regional-diversity
quota, and a **harm-exposure briefing before annotation begins**, with a removal power
that the researchers cannot overrule. Agreement is reported per template, with
per-claim proportions and intervals and a full elimination count — and reported *by
panel* rather than pooled, following NLPositionality [34], because a claim that
nordestinos and paulistanos rate an item differently is a finding about the stereotype
and not noise to average out of it. That reporting is itself a modest contribution,
which says more about the field than about us: **SHADES, MBBQ and JBBQ report no
agreement statistic at all**, and "we used native speakers" is common practice rather
than a gold standard.

Two implementation questions are recorded as open rather than resolved by assumption.
**Compensation**: no citable Global-South norm exists, and the field's own cautionary
example is exact — SeeGULL paid **USD 8.22** per annotator in India against **USD 28.35**
in Australia for the same study, unjustified in the paper. "Local cost of living",
applied uncritically, prices the labour by where the worker lives rather than by what
the work is, which reproduces the inequity a decolonial framing exists to address. The
protocol therefore commits to **one rate for every participant regardless of country**,
with fees borne by the project, briefing time paid, and no reduction for stopping
early — and it computes the resulting budget (~460 paid hours) precisely so that
deferring the work has to be a decision somebody writes down. **Research ethics**:
whether stereotype-annotation work of this kind requires review by a *Comitê de Ética
em Pesquisa* under Resolução CNS nº 510/2016 has no Brazil-specific guidance we could
find; because the work collects demographic self-identification and deliberately exposes
participants to injurious material, we treat it as a question for the team's own CEP
rather than one to answer by assumption.

The protocol also names who would be asked, in tiers keyed to lived membership rather
than to credentials — Brazilian algorithmic-racism organizations for the axes as a
whole, an organization working specifically on Black women and *racismo religioso* for
the two axes carrying the highest harm exposure, and the Brazilian NLP communities for
pt-BR register, approached as communities rather than as cold-emailed individuals. We
deliberately do not print those names here. **None of them has been approached, none has
reviewed this protocol, and none has agreed to anything in it**; listing an
organization's name next to a methodology it did not review is itself a form of
participation-washing, and it is the easiest one to commit by accident.

**The claim we are not making.** No Brazilian annotator and no Brazilian organization
has validated any item in this benchmark. There has been **no community validation**,
and no LLM pre-screen in this repository substitutes for it. What iteration 2 delivers
is the protocol and an honest account of the distance still to travel.

## 6. Discussion and Limitations

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
**The disclosure gap remains the single headline of this paper.** What follows explains
why the Art. 6 rights are worth building benchmarks for at all, and why the sector
overlays exist; it does not displace the measured result.

### Brazilian law grants a right to review and twice declines to say who performs it

The reflexive objection to benchmarking PL 2338's Art. 6 triad is that it restates
LGPD Art. 20. For explanation (Art. 6, I) that objection has force. For **human review
(Art. 6, III) it is wrong**, and the legislative record says so precisely.

**The drafting history, from the primary record.** As enacted on 14 August 2018, LGPD
Art. 20 granted a right to request review of a solely-automated decision ***"por pessoa
natural"*** — the phrase sat unconditionally in the *caput*, and §1 (the duty to supply
clear information about the criteria and procedures) and §2 (the ANPD's power to audit
for discriminatory aspects where trade secrecy is invoked) were present from the start
and are word-for-word unchanged today. The 2018 veto message did not touch Art. 20.
**MP 869/2018** then removed *"por pessoa natural"* from the caput. During its
conversion, **the §3 introduced by the 2019 conversion bill** (PLV 7/2019) reinstated a
weaker, *conditional* human-review requirement, tied to future ANPD regulation and
calibrated to the entity's size and processing volume:

> *"A revisão de que trata o caput deste artigo deverá ser realizada por pessoa natural,
> conforme previsto em regulamentação da autoridade nacional, que levará em consideração
> a natureza e o porte da entidade ou o volume de operações de tratamento de dados."*

That §3 — not the 2018 text — is what **Mensagem nº 288, de 8 de julho de 2019** vetoed
on sanctioning Lei nº 13.853/2019 [11], and Congress upheld the veto on **2 October
2019** (Veto nº 24/2019, item 24.19.001) [12]. Art. 20 today therefore reads *caput* +
§1 + §2 + §3 *(VETADO)*.

**The consequence is silence, not permission.** The statute in force neither mandates
nor forbids any particular reviewing agent, so a second automated pass is lawful **by
omission** rather than by affirmative authorization. That is both more accurate and
harder to argue with than "Brazilian law permits machine review".

**The veto was economic, not constitutional — and the central bank was in the room.**
The message as a whole invokes both *contrariedade ao interesse público* and
unconstitutionality across the thirteen devices it vetoes; for **this** device the
stated ground is only the former, and its reasoning is a credit-supply argument:
universal human review *"inviabilizará os
modelos atuais de planos de negócios de muitas empresas, notadamente das startups, bem
como impacta na análise de risco de crédito e de novos modelos de negócios de
instituições financeiras, gerando efeito negativo na oferta de crédito aos
consumidores"*, reaching inflation and monetary policy. The message records that the
Ministries of the Economy and of Science, Technology, Innovation and Communications,
the Controladoria-Geral da União **and the Banco Central do Brasil** came out for the
veto. The margin was narrow: the Câmara voted **261–163 to overturn**, clearing the
257-vote absolute-majority threshold, while the Senate reached **40 of the 41** votes
required, so under CF/88 Art. 66 §4 the veto stood. (Tally from the Congresso Nacional
veto-tracking database [12], not the session *ata*.)

**This is a pattern across two instruments, not one statute's accident.** Eight years
earlier, **Lei 12.414/2011 Art. 5, VI** — the Cadastro Positivo statute, Brazil's
consumer-credit reporting regime — had already granted the *cadastrado* the right
*"solicitar ao consulente a revisão de decisão realizada exclusivamente por meios
automatizados"* [13]. Review, again; a human reviewer, again unspecified. The 2019
amendments (LC 166/2019) rewrote four of that article's seven items and left this one
untouched. So Brazilian law grants a right to review of a solely-automated decision
twice, in a general data-protection statute and in a sectoral credit statute, and twice
leaves the reviewing agent open. **PL 2338 Art. 6, III is what closes it** — generally
against LGPD Art. 20, and in credit against Lei 12.414 Art. 5, VI, which is exactly the
domain the veto's own stated reasoning was about.

**Why this motivates the sector overlays rather than a single national score.** The gap
is not evenly distributed, because the argument that created it was sectoral: the
human-review right was blocked partly on credit-risk grounds with the financial
regulator supporting the veto. So the finance overlay's `human_review_gap_lgpd20` is a
**gap-flagging item** — it measures whether a deployer voluntarily exceeds a duty that
no Brazilian instrument imposes, and a low score there is a finding about the regulatory
regime rather than about the model. Health is the counter-example that shows the mapping
is real rather than rhetorical: **CFM Resolução nº 2.454/2026** [33] independently
mandates non-waivable human supervision of medical AI — *"As soluções apresentadas pelos
modelos, sistemas e aplicações de IA não são soberanas, sendo obrigatória a supervisão
humana"* — so a professional council has already adopted for physicians what the federal
veto removed for everyone. It must be read with two qualifications: it is **adopted but
not yet in force** (Art. 23: 180 days from publication, about 26 August 2026), and it binds
**physicians through CRM discipline, not products through ANVISA**. Capital markets
supply the opposite extreme — no CVM instrument uses "inteligência artificial" in an
operative clause, and there is **no Arts. 25-28 analogue at all**.

None of this is legal advice; see the final limitation below.

### Limitations

- **Provenance and validation — the limitation that governs the others.** The
  Brazilian categories were chosen by two non-Brazilian authors; the items were drafted
  by a language model from term banks assembled out of secondary literature; and every
  review to date has been by LLM judges (five rounds on `bbq_brazil`, one on the rubric
  scenarios), each documented in the repository as a pre-screen rather than as
  validation. **No Brazilian has
  validated any item.** §5 states this in full and says which findings it does and does
  not reach; `docs/participation-protocol.md` states what would close it.
- **Dataset scale.** `bbq_brazil` is 100 scenarios / 400 samples (20 scenarios per
  axis); the three rubric benchmarks are **n = 12** each. That is a real improvement on
  iteration 1's 44 / 3 / 4 / 1, and it is still small: n = 12 supports a standard error,
  not a verdict. `bbq_brazil`'s four samples per scenario are also **not independent**
  — the two polarities share a context and the two contexts share a scenario — so the
  tool-reported standard error is a **lower bound**; the scenario-level figure
  (n = 100) is the honest outer bound, and no √400 precision gain is claimed anywhere.
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
  compliance for any specific deployment. **The same disclaimer covers the sector
  overlays** — the BACEN, ANVISA / CFM / ANS and CVM instruments are mapped to PL 2338
  articles as *structural analogues for benchmark design*, not as a claim about what any
  regulator requires of any firm. It also covers the legislative analysis in this
  section: the LGPD Art. 20 and Lei 12.414 readings are drawn from primary records and
  cited so they can be checked, but they are our reading of the record, not counsel.

### Future Work

**Execute the participation protocol** — the single highest-value next step, and the one
that would move the bias finding from a direction to a magnitude. It begins with Tier-1
contact rather than with recruitment: putting `docs/participation-protocol.md` in front
of one Brazilian algorithmic-racism organization and asking whether the protocol is the
right shape, before asking anyone to execute it. Beyond that: resolve the CEP question
in writing; scale the open-weight models to the same config as the frontier ones so the
two halves are directly comparable; extend the sector overlays as ANPD's Art. 20
rulemaking and CFM Res. 2.454/2026's entry into force (about 26 August 2026) change the
underlying instruments; and give the remaining EU-only technical requirements a
Brazilian framing as the bill moves.

## 7. Conclusion

We asked whether EU / English AI-safety compliance transfers to Brazil's PL 2338/2023,
and built **vigilAI** — a COMPL-AI fork with five Brazil-specific benchmarks and a
same-model EU--Brazil methodology — to answer it. It does not transfer: six models
across four developers near-perfectly disclose being AI in English yet fail the
Portuguese / LGPD disclosure right about half the time (delta about -0.45), a gap no
English benchmark surfaces. At the same time, Brazil's high-risk Art. 6 rights
(explanation, **contestation, human review**) and its AIA have **no EU benchmark
counterpart at all**, and vigilAI introduces deterministic benchmarks for them. One of
those rights is not even a restatement of Brazil's own data-protection law: the
legislative record shows Brazilian law granting a right to *review* of a
solely-automated decision twice — in LGPD Art. 20 and in Cadastro Positivo Art. 5, VI —
and declining both times to say who performs it, so **Art. 6, III is a genuine
increment**, and one whose absence is deepest in the sector whose regulator supported
the 2019 veto. The practical message for Global-South AI governance is blunt:
**certification under a foreign regime is not compliance**, and localized,
statute-referenced evaluation is both necessary and achievable today. The equally blunt
message about this work is that a localized benchmark built without the participation of
the people it describes is a beginning and not a result: we publish the protocol that
would change that, and we make no claim to have run it.

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
- **Participation protocol:** `docs/participation-protocol.md` — the native-annotator
  validation protocol described in §5.6, including the tiered outreach list, the
  compensation terms and budget, and the open research-ethics question. The LLM
  pre-screens it explicitly does **not** credit are committed alongside it
  (`docs/bbq-brazil-llm-judge-review.md`, `docs/rubric-scenarios-llm-judge-review.md`,
  `docs/bbq-brazil-unreviewed-wordings.md`), each stating in its own opening that it is
  a pre-screen and not validation.
- **License:** code is released under **Apache-2.0** (matching the upstream COMPL-AI
  ecosystem); this report and its figure under **CC-BY-4.0**.

## Author Contributions

Diana Chang and Ian Duhamel Hayes jointly designed and built vigilAI, implemented the
benchmarks and reporting layer, ran the evaluations, and prepared this report.

**Positionality.** Neither author is Brazilian and neither is resident in Brazil. Neither
is a member of any of the groups `bbq_brazil`'s five axes describe. There is no Brazilian
co-author, no Brazilian institutional partner and no Brazilian ethics review on this
work. We state this here, and in full in §5.5, because a paper that argues for localized
evaluation while being written entirely from outside the locality should say so on its
own front matter rather than leave a reader to infer it.

## LLM Usage Statement

We used Claude (Claude Code) to fork and refactor COMPL-AI, implement the Brazil
benchmarks and the reporting layer, run the evaluations, and draft this report. **Two
uses go beyond assistance and are material to how the results should be read**, so they
are stated here as well as in §5.5:

1. **The Brazilian benchmark content was drafted by a language model.** The
   `bbq_brazil` term banks, scenario templates and pilot scenarios, and the pt-BR rubric
   scenarios, were written by Claude under our direction from the secondary sources
   cited in §5.1. The expansion from templates to the committed 100 scenarios is
   deterministic and contains no model call, and it reproduces byte-for-byte from
   `tools/generate_brazil_scenarios.py` — but that is reproducibility, not provenance.
2. **The only review of that content has also been by language models** — five rounds of
   LLM-judge review, committed to the repository and each labelled a pre-screen rather
   than validation.

The scorers themselves are deterministic and unit-tested (781 tests, run with no API key
and no network call); the optional LLM judge is a *second* scorer reported alongside the
deterministic one, never in place of it.

## References

1. LatticeFlow AI, ETH Zurich, INSAIT. *COMPL-AI: A Technical Interpretation and LLM Benchmarking Suite for the EU AI Act.* 2024. https://compl-ai.org · https://github.com/compl-ai/compl-ai
2. European Union. *Regulation (EU) 2024/1689 (Artificial Intelligence Act).* 2024.
3. Senado Federal do Brasil. *Projeto de Lei nº 2338/2023 — Marco legal da inteligência artificial.* Approved by the Senate, Dec. 2024.
4. Brazil. *Lei nº 13.709/2018 (Lei Geral de Proteção de Dados — LGPD)*, esp. Art. 20.
5. Parrish, A. et al. *BBQ: A Hand-Built Bias Benchmark for Question Answering.* Findings of ACL 2022. https://aclanthology.org/2022.findings-acl.165/
6. BBQ adaptations, none covering Portuguese or the IBGE categories: Jin et al. *KoBBQ* (TACL 2024) [30]; Neplenbroek, V., Bisazza, A. & Fernández, R. *MBBQ: A Dataset for Cross-Lingual Comparison of Stereotypes in Generative LLMs.* COLM 2024, https://arxiv.org/abs/2406.07243; Hashmat et al. *PakBBQ* (EMNLP 2025) [32]; *JBBQ*, https://arxiv.org/abs/2406.02050; *BharatBBQ*, https://arxiv.org/abs/2508.07090.
7. Mitchell, M. et al. *SHADES / BiasShades: Multilingual Stereotype Benchmark.* NAACL 2025. https://aclanthology.org/2025.naacl-long.600/ · https://huggingface.co/datasets/LanguageShades/BiasShades
8. *ToxSyn-PT* (CC BY 4.0). https://huggingface.co/datasets/ToxSyn/ToxSyn-PT
9. UK AI Safety Institute. *Inspect AI: An open-source framework for LLM evaluations.* https://inspect.aisi.org.uk
10. IBGE (Instituto Brasileiro de Geografia e Estatística). Racial / colour classification (branco, pardo, preto, amarelo, indígena).
11. Brazil, Presidência da República. *Mensagem nº 288, de 8 de julho de 2019* (partial veto on sanctioning **Lei nº 13.853/2019**), DOU 9 Jul. 2019. https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/Msg/VEP/VEP-288.htm
12. Congresso Nacional. *Veto nº 24/2019*, item **24.19.001** (§ 3º do art. 20 da Lei nº 13.709/2018); veto maintained in the joint session of **2 October 2019**. https://www.congressonacional.leg.br/materias/vetos/-/veto/detalhe/12445
13. Brazil. *Lei nº 12.414/2011* (Cadastro Positivo), Art. 5, VI, as amended by LC 166/2019.
14. Silva, T. *Racismo Algorítmico: Inteligência Artificial e Discriminação nas Redes Digitais.* Edições Sesc, 2022. https://racismo-algoritmico.pubpub.org/
15. IRIS – Instituto de Referência em Internet e Sociedade, with T. Silva and Ação Educativa. *Artificial Intelligence and Racial Discrimination in Brazil: Key Issues and Recommendations.* May 2024. https://irisbh.com.br/en/publicacoes/artificial-intelligence-and-racial-discrimination-in-brazil-key-issues-and-recommendations/
16. Chapman, C. A. et al. *Ten Simple Rules for Global North Researchers to Stop Perpetuating Helicopter Research in the Global South.* PLOS Computational Biology 17(9), 2021. https://doi.org/10.1371/journal.pcbi.1009277 · *Nature* editorial, *"Nature addresses helicopter research and ethics dumping"*, 2022. https://doi.org/10.1038/d41586-022-01423-6
17. Ricaurte, P. *Data Epistemologies, the Coloniality of Power, and Resistance.* Television & New Media 20(4), 2019. https://doi.org/10.1177/1527476419831640
18. Couldry, N. & Mejias, U. A. *The Costs of Connection: How Data Is Colonizing Human Life and Appropriating It for Capitalism.* Stanford University Press, 2019.
19. Mohamed, S., Png, M.-T. & Isaac, W. *Decolonial AI: Decolonial Theory as Sociotechnical Foresight in Artificial Intelligence.* Philosophy & Technology 33, 2020. https://doi.org/10.1007/s13347-020-00405-8
20. Adams, R. *Can Artificial Intelligence Be Decolonized?* Interdisciplinary Science Reviews 46(1–2), 2021. https://doi.org/10.1080/03080188.2020.1840225
21. Birhane, A. *Algorithmic Injustice: A Relational Ethics Approach.* Patterns 2(2), 2021. https://doi.org/10.1016/j.patter.2021.100205
22. D'Ignazio, C. & Klein, L. F. *Data Feminism.* MIT Press, 2020. https://data-feminism.mitpress.mit.edu/
23. Costanza-Chock, S. *Design Justice: Community-Led Practices to Build the Worlds We Need.* MIT Press, 2020. https://designjustice.mitpress.mit.edu/
24. International Convention on the Elimination of All Forms of Racial Discrimination (ICERD), 1965 — ratified by Brazil 27 Mar. 1968, Decreto 65.810/1969; American Convention on Human Rights, 1969 — Decreto 678/1992; Inter-American Convention on the Prevention, Punishment and Eradication of Violence against Women (**Convention of Belém do Pará**), adopted 1994 in Belém, Brazil — ratified Nov. 1995.
25. UNESCO. *Recommendation on the Ethics of Artificial Intelligence.* Adopted 23 Nov. 2021; pt-BR translation, UNESCO Brasília, 2022.
26. United Nations. *Guiding Principles on Business and Human Rights*, 2011; OHCHR **B-Tech** Project on human-rights due diligence for technology companies.
27. Varon, J. & Peña, P. *Not My AI: A Feminist Framework to Challenge Algorithmic Decision-Making Systems Deployed by the Public Sector.* APC / Coding Rights, 2022. https://www.apc.org/en/pubs/not-my-ai-feminist-framework-challenge-algorithmic-decision-making-systems-deployed-public
28. Birhane, A., Isaac, W., Prabhakaran, V. & Díaz, M. *Power to the People? Opportunities and Challenges for Participatory AI.* EAAMO 2022. https://arxiv.org/abs/2209.07572
29. Sloane, M., Moss, E., Awomolo, O. & Forlano, L. *Participation Is Not a Design Fix for Machine Learning.* EAAMO 2022. https://arxiv.org/abs/2007.02423
30. Jin, J., Kim, J., Lee, N., Yoo, H. et al. *KoBBQ: Korean Bias Benchmark for Question Answering.* TACL 2024. https://arxiv.org/abs/2307.16778
31. Jha, A., Davani, A. M., Reddy, C. K. & Dave, S. *SeeGULL: A Stereotype Benchmark with Broad Geo-Cultural Coverage Leveraging Generative Models.* ACL 2023. https://arxiv.org/abs/2305.11840
32. Hashmat, A., Mirza, M. A. & Raza, A. A. *PakBBQ: A Culturally Adapted Bias Benchmark for QA.* EMNLP 2025. https://arxiv.org/abs/2508.10186
33. Conselho Federal de Medicina. *Resolução CFM nº 2.454, de 2026 — normatiza o uso da inteligência artificial na medicina.* DOU 27 Feb. 2026 (retif. 5 Mar.); in force 180 days after publication (about 26 Aug. 2026). https://sistemas.cfm.org.br/normas/arquivos/resolucoes/BR/2026/2454_2026.pdf
34. Santy, S., Liang, J. T., Le Bras, R., Reinecke, K. & Sap, M. *NLPositionality: Characterizing Design Biases of Datasets and Models.* ACL 2023. https://aclanthology.org/2023.acl-long.505/

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
