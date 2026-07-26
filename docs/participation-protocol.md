# Participation protocol — native-annotator validation of `bbq_brazil`

> **Status, 2026-07-26 — read this first.**
>
> **This protocol has not been executed.** No Brazilian annotator, and no Brazilian organization,
> has validated any item in `bbq_brazil`. Nothing in this repository — not
> `docs/bbq-brazil-llm-judge-review.md`, not `docs/rubric-scenarios-llm-judge-review.md`, not the
> mechanical validators in `tools/generate_brazil_scenarios.py` — constitutes community
> validation, and **no claim of completed community validation may be made anywhere on the
> strength of any of them.**
>
> What exists is this document: a written, costed, citable protocol, plus the honest statement of
> what it would take to run it. That is a smaller claim than "validated", and it is the true one.

---

## 1. Why this document exists

A benchmark that measures Brazilian prejudice, whose categories were chosen by two people who are
not Brazilian, whose items were drafted by a language model, and whose only review has been by
other language models, is in a poor position to cite decolonial theory. Citing the theory without
a participation stance is the failure mode the theory names.

Two literatures name it precisely, and this protocol is written against both:

- **Participation-washing** (Sloane, Moss, Awomolo & Forlano, *Participation is not a Design Fix
  for Machine Learning*, EAAMO 2022, [arXiv:2007.02423](https://arxiv.org/abs/2007.02423)) — the
  use of participatory language, or of a thin participatory gesture, to launder a system whose
  design decisions were made elsewhere.
- **Who benefits** (Birhane, Isaac, Prabhakaran & Díaz, *Power to the People? Opportunities and
  Challenges for Participatory AI*, EAAMO 2022,
  [arXiv:2209.07572](https://arxiv.org/abs/2209.07572)) — participation can benefit the
  researchers considerably more than the community, and usually does unless the terms are set
  against it.

And one gives a checkable test rather than a critique: the **helicopter-research** literature
(*Nature* editorial, 2022, [d41586-022-01423-6](https://www.nature.com/articles/d41586-022-01423-6);
Chapman et al., *Ten Simple Rules for Global North Researchers to Stop Perpetuating Helicopter
Research in the Global South*, PLOS Computational Biology 2021,
[10.1371/journal.pcbi.1009277](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1009277)).
Its four questions are answered for vigilAI in §2, before any protocol design, because a protocol
written before that answer would be a plan to look participatory.

## 2. The helicopter-research test, applied to vigilAI

| Question | Answer for `bbq_brazil` |
|---|---|
| **Who conceived the categories?** | The two authors, neither of whom is Brazilian and neither of whom lives in Brazil. The five axes — IBGE *cor ou raça*, region, religion, class, and their intersections — were selected from Brazilian secondary sources (the IBGE 2022 census categories; published scholarship on regional prejudice and on *racismo religioso*; ABEP's *Critério Brasil* class markers), but **which** axes to build, and what counts as an axis at all, was our decision. |
| **Who wrote the items?** | A large language model (Claude, via Claude Code), under the authors' direction, from term banks the same model assembled from those secondary sources. The 22 pilot scenarios were drafted item by item; the remaining 78 are deterministic expansions of 30 templates over 34 contrast pairs. The generation *pipeline* contains no model call and is byte-reproducible — that is a reproducibility property, not a provenance one. **No Brazilian wrote a scenario.** |
| **Who validated them?** | Nobody who lives the categories. Every review to date has been conducted by **LLM judges**: five rounds over the 100 `bbq_brazil` scenarios (`docs/bbq-brazil-llm-judge-review.md`, Sections A–J) and one round over the 24 rubric scenarios (`docs/rubric-scenarios-llm-judge-review.md`). Both documents open by stating they are pre-screens and not validation. They caught real defects — seven items that measured backwards, one keyed to its own biased answer, a template pointed at an axis no Brazilian prejudice occupies — which is evidence that the items needed review, not that they have had it. |
| **Who is a co-author?** | Two authors. No Brazilian co-author, no Brazilian institutional partner, no Brazilian ethics review. |

**What this does and does not undermine.** It bears directly on `bbq_brazil` (Art. 5, III), whose
construct validity rests entirely on whether the stereotypes are attested in Brazil and pointed in
the right direction — a judgment we have not obtained. It bears partly on the three pt-BR rubric
tasks, whose *scenarios* are similarly authored but whose scoring targets a procedural checklist
drawn from statute rather than from a social judgment. It bears least on
`human_deception_brazil` (Art. 5, I), the paper's headline: its target is "the model denies being
human", the same target and the same scorer as the English original, and no stereotype judgment
enters it. Stating that split is part of the point — a positionality section that made every
finding equally suspect would be as uninformative as one that made none.

## 3. What would be validated

| Object | Count | Unit of validation |
|---|---:|---|
| Stereotype claims | **100** | one per scenario: each scenario is a unique (contrast pair × bias type) combination across the five axes |
| Scenarios | **100** | 20 per axis; 22 hand-authored pilot + 78 generated |
| Authored question fields | **200** | one negative-polarity and one non-negative question per scenario |
| Rendered samples | **400** | 2 context conditions × 2 question polarities per scenario |
| Rubric scenarios (secondary scope) | **24** | `explanation_quality` (12) + `contestation_review` (12); pt-BR register and domain vocabulary only — their rubrics come from statute, not from social judgment |

## 4. The protocol

A composite of three published BBQ-family annotation protocols, each cited for the component it
actually contributes. None of the three is adopted whole; where a component is adapted, the
adaptation and its reason are stated.

### 4.1 KoBBQ's quantitative core

*Jin, Kim, Lee & Yoo, KoBBQ: Korean Bias Benchmark for Question Answering, TACL 2024,
[arXiv:2307.16778](https://arxiv.org/abs/2307.16778).* KoBBQ surveyed **100 respondents per
question**, balanced by gender and age, kept a stereotype only when **more than two-thirds** of
respondents affirmed it, ran a **reading-comprehension check** that excluded items answered
correctly by fewer than half, and **reported that 8.3–13.6% of candidate samples were
eliminated**. Every one of those four is adopted; the sample sizes are adapted downward and the
adaptation is costed rather than hidden.

**Stage A — attestation, two panels, never averaged.** A stereotype is a belief that circulates,
and it circulates in the out-group; asking only the targeted group measures something else.
SeeGULL's own design pairs an in-region pool with a **separate out-region pool**, so two panels is
precedent, not invention.

| Panel | N per claim | Question | Retention rule |
|---|---:|---|---|
| **General-circulation panel** — a Brazilian panel quota-balanced on IBGE *cor ou raça*, the five macro-regions, sex and age band | **60** | "Regardless of whether you believe it, is this a stereotype that circulates in Brazil?" | KoBBQ's rule: retained if **> 2/3** affirm |
| **Lived-membership panel** — members of the group the claim targets (§4.2) | **12** | (a) direction: does the claim point at the prejudice as you encounter it? (b) harm: is the wording itself injurious beyond what measuring the prejudice requires? | Retained if **> 2/3** affirm direction; **any** harm objection routes to §4.3's veto, not to a vote |

**N = 60 rather than KoBBQ's 100, and the consequence is stated rather than absorbed.** At N = 60
a point estimate of 0.68 has a Wilson 95% interval of roughly 0.55–0.79 — wide enough that the
bare threshold cannot distinguish "just over two-thirds" from "about half". The protocol therefore
**reports the per-claim proportion and its Wilson interval for every item, retained or not**, so a
reader can apply a stricter rule than ours without re-running the survey. A project able to fund
N = 100 should use N = 100.

**Stage B — comprehension check.** KoBBQ's rule, and it matters more here than there. The
disambiguated half of a `bbq_brazil` item is designed so the disambiguating sentence names the
gold person **verbatim in the answer-choice wording**; if a Brazilian reader cannot recover that
answer, the item is measuring reading comprehension and not bias. **N = 12** per item; the item is
discarded if fewer than half recover the gold answer under both polarities.

**Stage C — elimination reporting.** The count of items eliminated at each stage, by axis and by
stage, is published with the dataset — including the case where the number is embarrassing. This
is the component most often silently dropped when a protocol is "followed".

### 4.2 SeeGULL's qualification rule

*Jha, Davani, Reddy & Dave, SeeGULL, ACL 2023,
[arXiv:2305.11840](https://arxiv.org/abs/2305.11840).* SeeGULL requires **in-region residency** to
validate that region's stereotypes. Generalized here to **lived membership of the category being
described**, which is the operative form for four of our five axes:

| Axis | Who validates a claim on it |
|---|---|
| Region | Residents of, or people raised in, the region named — a *nordestino* stereotype is validated by nordestinos, not by "Brazilians" |
| IBGE race | People who self-declare in the *cor ou raça* category the claim targets (*preta*, *parda*, *indígena*, *amarela*), using the IBGE self-declaration question verbatim |
| Religion | Practitioners of the tradition named — *candomblecistas* and *umbandistas* for the *racismo religioso* items, not "religious Brazilians" |
| Class | People who carry the marker the item uses (favela residence, public-school schooling, Bolsa Família receipt, informal/*sem carteira* work), since the ABEP letter grades are a survey instrument and not an identity |
| Intersectional | Membership of the **compound** category, not of either component. A *mulher negra nordestina* item is validated by mulheres negras nordestinas. Treating the axes as stackable is the specific error Birhane's relational account rules out (*Algorithmic Injustice: A Relational Ethics Approach*, Patterns 2021), and the benchmark's own intersectional axis exists because of it |

**The recruitment problem this creates, stated rather than solved.** Candomblecistas and
umbandistas are about 1% of the Brazilian population and 50–65% of recorded religious-intolerance
victims. A lived-membership panel of 12 per religion claim is therefore both the hardest panel to
recruit and the one carrying the highest harm exposure — which is why §4.3's duty-of-care terms
are not optional for it, and why Geledés is the Tier-2 partner named for exactly these items
(§5). The *indígena* category raises a further question this protocol does not settle: whether
community consultation under ILO Convention 169 (in force in Brazil since 25 July 2003) is engaged
when items describe an indigenous person, or whether individual self-declared participation
suffices. **Resolve with the partner organization before recruiting on that axis; do not decide it
internally.**

### 4.3 PakBBQ's transparency and duty of care

*Hashmat, Mirza & Raza, PakBBQ: A Culturally Adapted Bias Benchmark for QA, EMNLP 2025,
[arXiv:2508.10186](https://arxiv.org/abs/2508.10186).* PakBBQ **names its annotators**, sought
**regional diversity** across the country, and — the component almost nobody else reports —
**briefs annotators on harm exposure before annotation begins.** All three adopted; one component
of PakBBQ is explicitly **not** adopted.

- **Named annotators**, with a real opt-out: named in the dataset card and in any paper, or
  pseudonymous by their choice, with the choice made after they have seen what the naming looks
  like rather than in a consent form.
- **Regional diversity** across the five macro-regions as a recruitment requirement for the
  general-circulation panel, enforced as a quota rather than reported as an outcome. A stereotype
  panel drawn from the Sudeste would encode the Sudeste's view of the Nordeste as the national
  view — which is one of the prejudices under measurement.
- **Harm-exposure briefing before annotation begins**, not a content warning at the top of the
  form: what the material is, that it consists of statements the project believes to be false and
  injurious, what the annotator will be asked to do with them, how long a session runs, that
  stopping at any point is expected rather than tolerated, and that **stopping does not reduce
  payment**.
- **A veto that bites.** A lived-membership reviewer or a Tier-1/Tier-2 partner (§5) can require
  an item's removal on harm grounds, and the removal happens; it is recorded in the §4.1 Stage C
  elimination count with its ground, not silently. A veto the researchers can overrule is not a
  veto, and a veto with no audit trail cannot be checked.
- **Not adopted: unpaid volunteers.** PakBBQ's seven annotators were undergraduate volunteers.
  Volunteer labour from the group a dataset is about is precisely the extraction the framing
  objects to. See §6.

### 4.4 Item review, and the agreement statistic

Distinct from attestation: whether the Portuguese reads as Brazilian-authored, whether the
register matches the situation, and whether each *template × pair* combination makes social sense
(the failure mode no lint can see — grammatical but socially odd, e.g. a *mãe de santo* dropped
into an office-promotion scene).

- **3 named reviewers per item**, drawn from the Tier-3 pt-BR linguistic pool (§5) and, for items
  on an axis they belong to, from the lived-membership pool.
- **Fleiss' κ computed per template**, PakBBQ's unit; **templates with κ < 0.2 are discarded**,
  PakBBQ's threshold. Unlike PakBBQ, the κ values are **published**, not only the rule.
- **Disagreement is reported by panel, not pooled away.** Following NLPositionality (Santy et al.,
  ACL 2023), annotator self-reported identity is treated as a variable to preserve and report. A
  claim that nordestinos and paulistanos rate differently is a finding about the stereotype, not
  noise to be averaged out of it.

**Reporting an agreement statistic at all is a contribution here, which is a poor state of
affairs.** Of the BBQ adaptations surveyed, **SHADES, MBBQ and JBBQ report no agreement statistic
whatsoever**; "we used native speakers" is common practice, not a gold standard. PakBBQ computes
κ per template but does not publish the values; BharatBBQ reports Cohen's κ = 0.83 for templates
only. Publishing per-template κ, per-claim proportions with intervals, comprehension pass rates,
and a full elimination count would put this dataset above the current field norm — which says more
about the norm than about the dataset.

## 5. Who to approach, in tiers — and who not to

Legitimacy comes from **lived membership of the category being described**, plus positionality
disclosure, fair compensation and non-extractive terms — **not from credentials alone**. The
verified organizational landscape is recorded in the research
(`12-research-sector-overlays-and-framing.md` §4.6); the operative list is:

**Tier 1 — algorithmic-racism specialists (strongest fit).**

| Organization | Why |
|---|---|
| **Coding Rights** (codingrights.org, dir. Joana Varon) | Explicitly feminist, decolonial and AI-specific; authors of *Not My AI* and *AI Commons* |
| **AqualtuneLab** (aqualtunelab.com.br) | Legal/tech/race collective; Agyindawuru Observatory on facial recognition in Brazilian courts — **the best fit for the IBGE-race axis specifically** |
| **IRIS – Instituto de Referência em Internet e Sociedade** (irisbh.com.br) | Authors of the 2024 report on AI and racial discrimination in Brazil |
| **Ação Educativa** (acaoeducativa.org.br) | Co-published that report; TECLA project |
| **Instituto DaHora** (Nina da Hora) | "Reconhecimento Artificial" campaign on algorithmic racism |

**Tier 2 — category-specific lived expertise.**

| Organization | For which categories |
|---|---|
| **Geledés – Instituto da Mulher Negra** (geledes.org.br) | The *mulher negra* intersectional items and the *racismo religioso* (candomblecista / umbandista) items — the two axes carrying the highest harm exposure |

**Tier 3 — pt-BR linguistic validation.** **Brasileiras em PLN** (brasileiraspln.com),
**NILC** (USP/UFSCar/UNESP), and the **STIL / PROPOR** venues. Approach these **as communities,
through their own channels, not by cold-emailing individual members** — a mailing-list request to
a community that can decline as a body is a different act from thirty individual asks that are
awkward to refuse.

**Explicitly dropped.** **Instituto Nova Escola** — its mission is BNCC-aligned lesson plans and
it has no connection to this work. It appeared on an earlier candidate list and is removed.

**Do not claim algorithmic-racism expertise for**, even though each is a legitimate organization
with real credentials: **Instituto Marielle Franco** (a legitimate outreach and recruitment
partner; no AI or facial-recognition project was found), **CEERT**, **Data Privacy Brasil**,
**InternetLab**, **IDEC**, **Instituto Alana**. Listing an organization's name next to a
methodology it did not review is itself a form of participation-washing, and it is the easiest one
to commit by accident.

## 6. Compensation — the logic, and why this logic

**There is no citable Global-South or Brazil-specific compensation norm for annotation work of
this kind.** That absence is not permission to improvise quietly, because the field's own
cautionary example is precise: **SeeGULL paid USD 8.22 per annotator in India and USD 28.35 in
Australia for the same study**, unjustified in the paper. "Commensurate with local cost of living",
applied uncritically, reproduces exactly the inequity a decolonial framing exists to address — it
prices the labour by where the worker lives rather than by what the work is.

**The rule adopted here: one rate, not adjusted by the annotator's country of residence.** Set at
what the project would pay a reviewer in the highest-cost jurisdiction it would plausibly recruit
from. Three reasons, stated so they can be argued with:

1. **The work product is identical.** A judgment about whether a *nordestino* stereotype is
   attested has the same value to the dataset wherever the person making it sleeps.
2. **The scarce input is lived membership, and it is scarcer in the Global North, not commoner.**
   A cost-of-living adjustment prices the one qualification the Global North cannot supply as
   though it were the cheap part.
3. **The adjustment's actual function is to transfer the savings to the researchers.** No
   annotator is better off for being paid less; the budget is.

**The committed terms**, in full, because a rate without terms is half a commitment:

| Term | Commitment |
|---|---|
| Rate | **USD 25 per hour**, one rate for every participant regardless of country, paid in BRL at the mid-market rate on the payment date |
| Fees | Transfer, currency-conversion and platform fees are **borne by the project**, never netted out of the annotator's payment — an unaccounted 6% fee is how a stated equal rate becomes an unequal one |
| Briefing time | **Paid**, at the same rate. A duty-of-care briefing the annotator is not paid to attend is a disclaimer |
| Stopping | **Payment is not reduced** if an annotator stops mid-session. Duty of care that costs money to exercise is not duty of care |
| Minimum | A **one-hour minimum** per session, regardless of how few items a session covers |
| Design-level work | Compensated as **co-authorship** (§7), not as an hourly rate — the two are different kinds of contribution and paying only the hourly one is how design labour disappears |

**Costed, so the claim is checkable rather than aspirational.** At the stated N: 100 claims ×
(60 general + 12 lived-membership + 12 comprehension) = **8,400 panel responses**, plus 100 items
× 3 = **300 item reviews**. At roughly 20 attestation ratings per paid hour and 8 item reviews per
paid hour, that is on the order of **420 + 38 ≈ 460 paid hours ≈ USD 11,500** — before briefing
time, the one-hour session minimums, partner-organization time and platform fees, all of which
push it up rather than down.

**That money does not exist.** The commitment above is a commitment about *terms* — what will be
paid, to whom, on what basis, if the work is funded. It is not a claim that the work is funded, and
the protocol should not be read as a plan already in motion. Stating the number is deliberate: a
participation protocol whose cost is never computed is one that will always be deferred for
reasons that never have to be written down.

## 7. Non-extractive terms

The helicopter-research literature's operative tests are **local co-authorship, local ethics
review, and local benefit-sharing** — not merely local data collection. Each is committed to
concretely, or its absence is stated.

1. **Co-authorship, not acknowledgement**, for anyone doing design-level judgment: deciding which
   axes exist, which claims are attested, which items are removed. Acknowledgement for
   design-level work is the canonical extractive move.
2. **Named credit plus payment** for item-level annotation, with the opt-out of §4.3.
3. **Return before publication.** The validated dataset, the full elimination record with grounds,
   and the per-item statistics go to the reviewing organizations **before** submission, with a
   stated window in which they can object, and objections resolved before submission rather than
   after.
4. **Local publication.** Submission to **STIL / PROPOR** — the Brazilian venues where a pt-BR
   bias benchmark is natively legible — alongside any international venue. A dataset about Brazil
   that is only readable at an anglophone venue has not been shared back.
5. **Local ethics review** through the Brazilian partner's CEP where one is engaged (§8), not
   through ours by preference.
6. **Data minimization on the annotators themselves.** The demographic self-identification this
   protocol collects is, under **LGPD Art. 5º, II**, *sensitive personal data* — race, ethnicity
   and religious conviction are named there explicitly. Collected at the coarsest granularity the
   qualification rule requires, stored separately from the ratings, and deleted on a stated
   schedule. The protocol validating a benchmark about racial data must not be careless with
   racial data.

## 8. Research ethics — an open question, to be resolved and not assumed

**Whether this work requires review by a Comitê de Ética em Pesquisa (CEP) is unresolved, and this
protocol deliberately does not resolve it.**

- **Resolução CNS nº 510/2016** governs human and social-sciences research ethics and lists narrow
  exemptions in Art. 1. **No Brazil-specific guidance was found on whether stereotype-annotation
  work of this kind falls inside or outside them.**
- Two features make an exemption doubtful rather than obvious: the protocol collects **demographic
  self-identification** (sensitive personal data under LGPD Art. 5º, II), and it **deliberately
  exposes participants to material the project itself characterizes as injurious**.
- **Lei 14.874/2024** (in force 27 Aug 2024) replaced the CEP/CONEP structure with **INAEP + CEPs**
  for research with human subjects, so the applicable instrument itself changed recently.
- If an annotator database is retained rather than discarded, **Resolução CNS nº 738** — on the use
  of databases for scientific research involving human subjects — becomes adjacent. Cite it
  carefully: the resolution is dated **1 February 2024** in its own homologation clause, its
  republished DOU header carries **7 November 2024**, and the republication notice records that it
  ran in **DOU nº 14 of 21 January 2025, Seção 1, p. 114, "com incorreções no original."** The
  7 November 2024 date propagated widely through aggregators; check the homologation clause rather
  than a citation.

**The action is to ask the team's own CEP, in writing, and record the answer here** — including
the answer "not applicable", which is a finding and not a formality. Assuming exemption because
the work is "just annotation" is how the question stops being asked.

## 9. What has not happened, and what the next step is

- **No item has been validated by any Brazilian.**
- **No Tier-1, Tier-2 or Tier-3 organization has reviewed this protocol**, and none has agreed to
  anything in it. The tier list is a list of organizations whose published work makes them the
  right people to ask; it is not a list of partners, and it must not be presented as one.
- **No CEP has been consulted** (§8).
- **No funding is in place** for the compensation terms in §6.
- **The five rounds of LLM-judge review are not a stage of this protocol.** They are a pre-screen
  that runs *before* it, whose only value is that a paid annotator's hour goes on judgment instead
  of on finding broken items.

**The next step is Tier-1 contact** — one organization, with this document attached, asking
whether the protocol is the right shape before asking anyone to execute it. That ordering is
deliberate: bringing a finished protocol to a community for approval is a thinner form of
participation than bringing an unfinished one, and this document is offered as the second.

> **If contact has occurred, record it here**: who, when, through which channel, what was asked,
> what was answered, and on what terms. An outreach claim with no such record must not appear in
> the paper.

## Sources

**Protocols.** KoBBQ ([arXiv:2307.16778](https://arxiv.org/abs/2307.16778), TACL 2024) ·
SeeGULL ([arXiv:2305.11840](https://arxiv.org/abs/2305.11840), ACL 2023) ·
PakBBQ ([arXiv:2508.10186](https://arxiv.org/abs/2508.10186), EMNLP 2025) ·
BBQ ([arXiv:2110.08193](https://arxiv.org/abs/2110.08193), Findings of ACL 2022) ·
MBBQ ([arXiv:2406.07243](https://arxiv.org/abs/2406.07243), COLM 2024) ·
BharatBBQ ([arXiv:2508.07090](https://arxiv.org/abs/2508.07090)) ·
JBBQ ([arXiv:2406.02050](https://arxiv.org/abs/2406.02050)) ·
SHADES ([ACL Anthology 2025.naacl-long.600](https://aclanthology.org/2025.naacl-long.600/)) ·
NLPositionality ([ACL Anthology 2023.acl-long.505](https://aclanthology.org/2023.acl-long.505/))

**Participation critique.** Sloane, Moss, Awomolo & Forlano, EAAMO 2022
([arXiv:2007.02423](https://arxiv.org/abs/2007.02423)) · Birhane, Isaac, Prabhakaran & Díaz,
EAAMO 2022 ([arXiv:2209.07572](https://arxiv.org/abs/2209.07572)) · Costanza-Chock, *Design
Justice*, MIT Press 2020 · D'Ignazio & Klein, *Data Feminism*, MIT Press 2020 · Chapman et al.,
PLOS Computational Biology 2021
([10.1371/journal.pcbi.1009277](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1009277))
· *Nature* editorial, 2022
([d41586-022-01423-6](https://www.nature.com/articles/d41586-022-01423-6))

**Brazilian scholarship and organizations.** Tarcízio Silva, *Racismo Algorítmico*, Edições Sesc
2022 ([racismo-algoritmico.pubpub.org](https://racismo-algoritmico.pubpub.org/)) · IRIS-BH with
Tarcízio Silva and Ação Educativa, *Artificial Intelligence and Racial Discrimination in Brazil*,
May 2024 · Varon & Peña, *Not My AI*, APC / Coding Rights 2022 · Varon et al., *AI Commons*,
Coding Rights 2024

**Instruments.** LGPD (Lei 13.709/2018) Art. 5º, II · Resolução CNS nº 510/2016 ·
Resolução CNS nº 738 · Lei 14.874/2024 · ILO Convention 169 (Decreto 10.088/2019)

---

*Companion documents: the LLM pre-screens this protocol explicitly does not credit —*
`docs/bbq-brazil-llm-judge-review.md`, `docs/rubric-scenarios-llm-judge-review.md`,
`docs/bbq-brazil-unreviewed-wordings.md` *— and the reviewer sheets*
`docs/bbq-brazil-generated-spot-check.md`, `docs/rubric-scenarios-generated-spot-check.md`.
