# Sector overlay — legal verification record

**Scope:** every `AIAItem` in `src/vigilai/tasks/aia_checklist/checklist.py` that carries a
`sector`. One row per item: the instrument it is drawn from, its regulatory status, the
primary-source URL, the operative provision, and the **sourcing tier** behind the claim.

**Date of this pass:** 2026-07-25 (iteration 2, Phase 4 — finance/BACEN slice). Phase 5 appends
the health (ANVISA / CFM / ANS) and capital-markets (CVM) rows.

> ## ⚠️ Not legal advice
>
> Every mapping below is a **structural analogy for benchmark design**, not a legal opinion and
> **not legal advice**. No Brazilian sector regulator has issued a binding AI-specific rule;
> BACEN has said publicly it will not act before PL 2338/2023 is enacted, and PL 2338 does not
> name BACEN. What is recorded here is that an *adjacent, binding* obligation exists and what it
> says — never that it governs AI. Do not rely on this file for compliance purposes.

## How to read the sourcing tier

| Tier | Field value | Meaning |
|---|---|---|
| **Primary** | `primary` | The operative text was read in an official primary source (planalto.gov.br, congressonacional.leg.br, or an Internet Archive capture of the issuing body's own page). |
| **Corroborated secondary** | `corroborated_secondary` | Independent professional sources converge, but the issuing body's own text was **not** reached. Cite with the weaker sourcing stated. |
| **Open** | `open` | A material question about the instrument could not be resolved either way. Recorded as an open question, never answered. |

Machine-checked: `tests/test_aia_checklist.py::TestLegalVerificationGate` refuses any sector item
that lacks an instrument, a `https://` source URL or a tier from this vocabulary, and requires
that **both the item id and its source URL appear verbatim in this file** — so the code and this
record cannot drift.

## Access conditions during this pass (stated, because they bound what "primary" means)

- `planalto.gov.br` — **reachable**, HTTP 200, full text rendered. (doc 12 reports `ECONNRESET`
  on every attempt during the 2026-07-24 research pass; that did not reproduce here.)
- `congressonacional.leg.br` — reachable, HTTP 200.
- `www25.senado.leg.br` — reachable, HTTP 200.
- `bcb.gov.br` / `normativos.bcb.gov.br` — **not reachable**: connection timeout after 20 s on
  every request, reproducing the access problem doc 12 records. BACEN/CMN items therefore carry
  the canonical `exibenormativo` deep link, whose **resolution was confirmed** through the
  Internet Archive availability API returning a `status: 200` snapshot of that exact URL. The
  snapshot page itself is a JavaScript shell and does not render the normative text, so no
  BACEN/CMN operative text below is quoted verbatim from a page read in this pass; the operative
  readings come from the 2026-07-25 verification pass that preceded implementation, and each row
  says which.

---

## Cross-sector items (PL 2338/2023 itself)

The six `AIA_CHECKLIST` items — `who_conducts`, `timing`, `risk_benefit_documentation`,
`public_conclusions`, `ripd_joint_preparation`, `incident_notification` — are drawn from the
Senate-approved text of PL 2338/2023 (10 Dec 2024), Arts. 25-28 and Art. 44, via
`docs/task-artifacts/02-research.md` §5. Source:
<https://www25.senado.leg.br/web/atividade/materias/-/materia/157233> (HTTP 200).

---

## Finance / BACEN

### `ouvidoria_channel`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, II (*de facto* analogue) |
| **Instrument** | Res. CMN 4.860/2020, Art. 6 §2 (23 Oct 2020) |
| **Status** | `binding` |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4860> |
| **Archive** | Internet Archive snapshot `20250710112409`, status 200 |
| **Sourcing tier** | `primary` |

**Operative provision.** A mandatory *ouvidoria* for every BACEN-authorised institution, acting
as the final internal instance. Art. 6 §2 sets **10 business days** to answer a demand,
extendable **once**, with extensions capped at **10 % of the monthly volume of demands**.
Art. 22 revokes **Res. CMN 4.433/2015 and Res. CMN 4.629/2018**.

**Correction to doc 12 — the "≥1-yr mandate" claim is dropped.** doc 12's Part 1 table states the
ombudsman must have a mandate of at least one year. Res. CMN 4.860/2020 **Art. 8, III** requires
only that the *ouvidor*'s term be **stated in months** in the institution's by-laws; it sets no
minimum. Nothing in the shipped item, its cues or its description asserts a minimum term.

---

### `cadastro_positivo_criteria_disclosure`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I (*de facto* analogue) |
| **Instrument** | Lei 12.414/2011, Art. 5, IV (as amended by LC 166/2019; reg. Decreto 9.936/2019) |
| **Status** | `binding` |
| **Source URL** | <https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12414.htm> |
| **Sourcing tier** | `primary` — text read in this pass |

**Operative text (verbatim, planalto.gov.br):**

> Art. 5º São direitos do cadastrado: […] IV - conhecer os **principais elementos e critérios
> considerados para a análise de risco**, resguardado o segredo empresarial;

Related, same article: inciso II (as amended by LC 166/2019) gives free access, without
justification, to one's own record **including the credit score** — *"inclusive seu histórico e
sua nota ou pontuação de crédito"*. §3 sets **10 days** for the disclosures under incisos II
and IV.

---

### `cadastro_positivo_contestation`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, II (*de facto* analogue) |
| **Instrument** | Lei 12.414/2011, Art. 5, III (as amended by LC 166/2019) |
| **Status** | `binding` |
| **Source URL** | <https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12414.htm> |
| **Sourcing tier** | `primary` — text read in this pass |

**Operative text (verbatim, planalto.gov.br, redação da LC 166/2019):**

> III - solicitar a **impugnação** de qualquer informação sobre ele erroneamente anotada em banco
> de dados e ter, em até **10 (dez) dias**, sua correção ou seu cancelamento em **todos os bancos
> de dados que compartilharam a informação**;

(The original 2011 wording said *7 (sete) dias* and "comunicação aos bancos de dados com os quais
ele compartilhou a informação"; LC 166/2019 both lengthened the deadline and widened the
propagation duty.)

---

### `credit_model_governance`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (*de facto* analogue, partial) |
| **Instrument** | Res. BCB 303/2023, Art. 2 — Pillar 3 disclosure: companion Res. BCB 306/2023 |
| **Status** | `binding` (in force 1 Jul 2023) |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=303> |
| **Archive** | Internet Archive snapshot `20230603092815`, status 200 (and `20240113014747` for Res. BCB 306/2023) |
| **Sourcing tier** | `primary` |

**Operative provision.** Art. 2 requires **prior BACEN authorisation** to use internal credit-risk
rating systems (the IRB approach) for regulatory capital. The resolution requires the systems to
be integrated into the risk-management structure, kept documented, and staffed by personnel
qualified for their **development, validation, evaluation, updating and use**.

**Two corrections to doc 12.**

1. **Pillar 3 is not in Res. BCB 303/2023.** doc 12 attributes "mandatory Pillar 3 public
   disclosure of model information" to 303/2023. The Pillar-3 disclosure regime lives in the
   **companion Res. BCB 306/2023**. The item's `instrument` field names both and says which is
   which.
2. **`Circular BACEN 3.648/2013` is REVOKED — doc 12 is falsified.** doc 12 records it as
   "[UNVERIFIED] whether superseded … no revocation clause found". **Res. BCB 303/2023 Art. 128
   revokes it expressly**, effective 1 Jul 2023. It is cited nowhere in the shipped checklist as
   a binding instrument — only, here, as a superseded predecessor. A test
   (`test_the_revoked_predecessor_is_never_cited_as_binding`) enforces that. The status column of
   doc 12's Part 1 table should be corrected to "revoked by Res. BCB 303/2023 Art. 128 (1 Jul
   2023)".

---

### `pix_med_contestation`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, II (*de facto* analogue) |
| **Instrument** | Res. BCB 103/2021 → Res. BCB 493/2025 ("MED 2.0", mandatory 2 Feb 2026) |
| **Status** | `binding` |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=103> |
| **Archive** | Internet Archive snapshots `20260124175001` (103/2021) and `20251128023649` (493/2025), both status 200 |
| **Sourcing tier** | `primary` |

**Operative provision, with the direction stated explicitly because it is easy to invert.** The
Pix *Mecanismo Especial de Devolução* is initiated by the **payer**, through the **payer's own
PSP**. The *bloqueio cautelar* — up to **72 hours** — freezes funds **in the receiving account**
and is executed by the **receiver's PSP**. Res. BCB 493/2025 ("MED 2.0") extends blocking along
the chain of onward transfers and is mandatory from **2 February 2026**.

> **Repo note.** A scenario elsewhere in this repository had this direction backwards (Phase 3
> review finding D2, `pix_block_contest`). The item description here states the direction in
> full so the error cannot be reintroduced by paraphrase.

---

### `cybersecurity_cloud_vendor_accountability`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (*de facto* analogue) |
| **Instrument** | Res. CMN 4.893/2021 (26 Feb 2021), am. Res. CMN 5.274/2025 (+ Res. BCB 538/2025) |
| **Status** | `binding` |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4893> |
| **Archive** | Internet Archive snapshots `20250620083452` (4.893/2021), `20260115082314` (5.274/2025), `20260115084031` (Res. BCB 538/2025), all status 200 |
| **Sourcing tier** | **`corroborated_secondary`** |

**Operative provision.** A mandatory cybersecurity policy plus rules on outsourcing data
processing / storage and cloud computing; the contracting institution **remains fully responsible
for regulatory compliance** even where the infrastructure — including model infrastructure — is
outsourced. Res. CMN 4.893/2021 revoked Res. 4.658/2018 and 4.752/2019.

**Why the weaker tier.** The **2025 amendment** (Res. CMN 5.274/2025, dated 18 Dec 2025, with
compliance from 1 Mar 2026, and its companion Res. BCB 538/2025) rests on independent
professional sources that converge on the dates and the compliance deadline; **bcb.gov.br's own
text was not reached**. The 2021 base resolution is the binding anchor for the item, and nothing
in the item depends on a 2025-specific provision.

---

### `integrated_risk_management_framework`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (*de facto* analogue, scaffolding) |
| **Instrument** | Res. CMN 4.557/2017, Art. 64 + Chapter II, as amended by Res. CMN 5.076/2023 and 5.077/2023 |
| **Status** | `binding` |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=5076> |
| **Archive** | Internet Archive snapshots `20250708030410` (5.076/2023) and `20250708030415` (5.077/2023), both status 200. **Res. CMN 4.557/2017 itself has no archived `exibenormativo` snapshot**, which is why the item's `source_url` points at the amending act rather than the base text. |
| **Sourcing tier** | `primary` |

**Operative provision.** A continuous, integrated risk-management structure. **Art. 64** requires
a **single** chief risk officer (*diretor de risco*). Model **evaluation may not be carried out by
the unit that developed the model, nor by a risk-taking unit** — the closest thing in Brazilian
finance to an independent-validation duty for an automated decision system. **Chapter II** is the
*declaração de apetite por riscos* (RAS).

**Not claimed.** doc 12 notes the resolution does not appear to name *"risco de modelo"* as a
distinct risk category. Nothing here asserts that it does.

---

### `open_finance_consent_automated_credit`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I/II (partial) |
| **Instrument** | Res. Conjunta 1/2020 (CMN + BCB, 4 May 2020) + Res. BCB 32/2020 (29 Oct 2020) |
| **Status** | `binding` |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=32> |
| **Archive** | Internet Archive snapshot `20251216151150` (Res. BCB 32/2020), status 200. Res. Conjunta 1/2020 has **no** archived `exibenormativo` snapshot; the item's URL therefore points at the implementing resolution. |
| **Sourcing tier** | `primary` — for **existence and dates only** |

**What is cited: existence and dates.** Res. Conjunta 1/2020 established the Open Finance
framework on 4 May 2020; Res. BCB 32/2020 is its implementing regulation, 29 Oct 2020; Res.
Conjunta 4/2022 extended the scope. Phased rollout reached payment initiation and **automated
credit proposals**.

**What is deliberately NOT cited — do not add it later.** doc 12 marks as *do-not-cite* the claim
that Open Finance imposes **explainability or ML-audit duties**, and the 2026-07-25 verification
pass found nothing supporting it. The item carries **no explainability or model-audit cue**, and
this paragraph exists so a future pass does not "complete" the item by adding one.

---

### `fraud_data_sharing_due_process`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, II — **open question** |
| **Instrument** | Res. Conjunta 6/2023 (CMN + BCB, 23 May 2023; in force 1 Nov 2023; companion Res. BCB 343/2023) |
| **Status** | `binding` (the instrument), **open** (the right) |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20Conjunta&numero=6> |
| **Archive** | Internet Archive snapshots `20260705024927` (Res. Conjunta 6/2023) and `20250708025753` (Res. BCB 343/2023), both status 200 |
| **Sourcing tier** | **`open`** |

**Operative provision.** Standardised inter-institution sharing of fraud indicators — a shared
fraud database across the national financial system.

**The open question, left open.** Whether an individual **wrongly flagged** in that shared
database has a **codified correction right** could not be established either way: no source was
found supporting it, and none was found ruling it out. doc 12's unverified-status framing is
**correct** and is preserved rather than resolved. Consequently the benchmark item scores whether
a deployer *describes* due process around fraud flagging — it makes **no claim** that Brazilian
law requires it, and it is **not** filed as a gap item, because a gap claim would itself be
unverified.

---

## Gap-flagging items

A gap item's low score is a finding about **Brazilian law**, not about the model: it tests whether
a deployer *voluntarily exceeds* a duty that no instrument imposes. A negative claim is only
checkable if it names the nearest instrument and says what that instrument stops short of, so each
row below does.

### `human_review_gap_lgpd20` ⭐

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, III — **GAP** |
| **Nearest instrument** | LGPD (Lei 13.709/2018) Art. 20, in force as amended by Lei 13.853/2019 |
| **Status** | `gap` |
| **Source URL** | <https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm> |
| **Sourcing tier** | `primary` — text read in this pass |

**What the nearest instrument does require (verbatim, planalto.gov.br, text in force):**

> Art. 20. O titular dos dados tem direito a solicitar **a revisão** de decisões tomadas
> unicamente com base em tratamento automatizado de dados pessoais que afetem seus interesses,
> incluídas as decisões destinadas a definir o seu perfil pessoal, profissional, de consumo e de
> crédito ou os aspectos de sua personalidade. *(Redação dada pela Lei nº 13.853, de 2019)*
>
> § 1º O controlador deverá fornecer, sempre que solicitadas, **informações claras e adequadas a
> respeito dos critérios e dos procedimentos** utilizados para a decisão automatizada, observados
> os segredos comercial e industrial.
>
> § 2º Em caso de não oferecimento de informações de que trata o § 1º […] baseado na observância
> de segredo comercial e industrial, **a autoridade nacional poderá realizar auditoria** […]

**What it stops short of.** It is **silent on who or what performs the review.** *"por pessoa
natural"* stood in the original 2018 caput; **MP 869/2018** removed it; the **§3 introduced by the
2019 conversion bill** (PLV 7/2019) would have restored a conditional human-review requirement and
was **vetoed**. A second automated pass is lawful **by omission**, not by permission.

**Vetoed text and veto reason (verbatim, Mensagem nº 288, de 8 de julho de 2019, planalto.gov.br,
HTTP 200):**

> Ouvidos, os Ministérios da Economia, da Ciência, Tecnologia, Inovações e Comunicações, a
> Controladoria-Geral da União e o **Banco Central do Brasil** manifestaram-se pelo veto ao
> seguinte dispositivo: § 3º do art. 20 da Lei nº 13.709 […]
>
> "§ 3º A revisão de que trata o caput deste artigo deverá ser realizada por pessoa natural,
> conforme previsto em regulamentação da autoridade nacional, que levará em consideração a
> natureza e o porte da entidade ou o volume de operações de tratamento de dados."
>
> **Razões do veto** — "A propositura legislativa, ao dispor que toda e qualquer decisão baseada
> unicamente no tratamento automatizado seja suscetível de revisão humana, **contraria o interesse
> público**, tendo em vista que tal exigência inviabilizará os modelos atuais de planos de
> negócios de muitas empresas, notadamente das startups, bem como impacta na **análise de risco de
> crédito** e de novos modelos de negócios de instituições financeiras, gerando efeito negativo na
> **oferta de crédito** aos consumidores […] com reflexos, ainda, nos **índices de inflação** e na
> **condução da política monetária**."

Veto upheld by the Congresso Nacional on **2 October 2019** — **Veto nº 24/2019**, item
**24.19.001**: <https://www.congressonacional.leg.br/materias/vetos/-/veto/detalhe/12445>.
Câmara **261–163** to overturn (threshold 257, cleared); Senado reached **40 of the 41** required,
so the veto stood. Attribute the tally to the Congresso Nacional veto-tracking database, not to
the session *Ata*; the reported abstention count could not be corroborated and is omitted.

**Correction to doc 12's drafting-history table — binding on Phase 10.** doc 12 row 1 says the
original 14 Aug 2018 Art. 20 was *"a single caput sentence with no paragraphs"*. That is **wrong**.
§1 (transparency) and §2 (ANPD audit) were **already present in 2018, word for word as today** —
the planalto compiled text carries them with **no** "(Redação dada…)" or "(Incluído…)" annotation,
whereas the caput carries two. What MP 869/2018 changed was the **caput** (dropping *"por pessoa
natural"*); what the 2019 conversion bill added was a **new §3**, which was then vetoed. The
outcome in doc 12 is right; the mechanism as drafted is not, and Phase 10's argument rests on the
mechanism.

**The same shape recurs inside finance.** Lei 12.414/2011 Art. 5, **VI** grants the right to
*"solicitar ao consulente **a revisão de decisão realizada exclusivamente por meios
automatizados**"* — review, again **not** human review. Verified verbatim on planalto in this pass.
Two independent Brazilian instruments therefore grant a review right and neither says who performs
it, which is the single strongest support for the paper's claim that PL 2338 Art. 6, III is a
substantive increment rather than a restatement.

---

### `pix_fraud_blocking_no_analogue` ⭐

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I/II — **GAP, narrowed to contestation only** |
| **Nearest instrument** | Res. BCB 501/2025 (published 11 Sept 2025, amending Res. BCB 142/2021) |
| **Status** | `gap` |
| **Source URL** | <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?numero=501&tipo=Resolu%C3%A7%C3%A3o%20BCB> |
| **Archive** | Internet Archive snapshots `20260214132754` (Res. BCB 501/2025) and `20240301102704` (Res. BCB 142/2021), both status 200 |
| **Sourcing tier** | **`corroborated_secondary`** |

**What the nearest instrument requires.** Institutions must **reject transactions** (Pix, TED,
DOC, cards) to accounts under *"fundada suspeita"* of fraud. It sets **no objective criteria**,
delegating the definition of that suspicion to each institution's internal risk models — i.e. to
an automated adverse decision with institution-defined thresholds.

**What it stops short of: contestation.** Two independent law-firm analyses agree the resolution
**does require notifying the account holder**, and both agree that **no contestation mechanism
exists** — no appeal, no review, no deadline.

**Narrowing of doc 12's claim, deliberate.** doc 12 states the resolution *"specifies no individual
notice or contestation procedure"*. The **notice** half is not clean and is therefore **not
claimed**. The shipped gap is contestation only, and the item's cues test for a contestation route
(*contestar / recurso / revisão / desbloqueio* attached to a block or a rejection), not for notice.

**Why the weaker tier.** bcb.gov.br was not reached for the operative text; the reading rests on
secondary professional sources only. Anything the paper says about Res. BCB 501/2025 must carry
that qualification.

---

### `ai_interaction_disclosure_gap` ⭐

| | |
|---|---|
| **PL 2338 mapping** | Art. 5, I — **GAP** |
| **Nearest instrument** | CDC (Lei 8.078/1990) Art. 6, III |
| **Status** | `gap` |
| **Source URL** | <https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm> |
| **Sourcing tier** | `primary` — text read in this pass |

**What the nearest instrument requires (verbatim, planalto.gov.br):**

> Art. 6º São direitos básicos do consumidor: […] III - **a informação adequada e clara sobre os
> diferentes produtos e serviços**, com especificação correta de quantidade, características,
> composição, qualidade, tributos incidentes e preço, bem como sobre os riscos que apresentem;
> *(Redação dada pela Lei nº 12.741, de 2012)*

**What it stops short of.** It is a generic right to clear information about the **product or
service** — quantity, characteristics, composition, quality, taxes, price, risks. It says nothing
about the **automated nature of the channel** through which the service is delivered. No BACEN
rule requires disclosing that a customer is interacting with an AI rather than a person.

**A genuine, uncontradicted gap.** Nothing found in this pass or in doc 12 contradicts it. PL 2338
Art. 5, I would therefore be **new law** in Brazilian banking, not a codification of existing
practice — which is exactly why the disclosure finding is the paper's headline.

---

## Summary of corrections to `12-research-sector-overlays-and-framing.md`

Recorded here so the research document can be amended, and so the paper does not reproduce an
error this pass caught.

| # | doc 12 says | Verified position |
|---|---|---|
| 1 | Circular BACEN 3.648/2013: "no revocation clause found", `[UNVERIFIED]` whether superseded | **Falsified.** Expressly revoked by **Res. BCB 303/2023 Art. 128**, effective 1 Jul 2023. Cite only as a superseded predecessor. |
| 2 | Res. CMN 4.860/2020 requires an ombudsman with a **"≥1-yr mandate"** | **Reworded.** Art. 8, III requires only that the term be **stated in months**. No minimum exists. Claim dropped. |
| 3 | Res. BCB 303/2023 requires "mandatory Pillar 3 public disclosure" | **Reattributed.** Pillar 3 lives in the companion **Res. BCB 306/2023**. |
| 4 | Res. BCB 501/2025 "specifies no individual notice or contestation procedure" | **Narrowed.** Notice **is** required (two independent law firms). The gap is **contestation only**. |
| 5 | LGPD Art. 20 in 2018 was "a single caput sentence with no paragraphs" | **Corrected.** §1 and §2 were already there in 2018, word for word. Only the **caput** changed (MP 869/2018 dropped *"por pessoa natural"*), and a new **§3** was added in 2019 and vetoed. |
| 6 | Res. Conjunta 6/2023 — correction right for a wrongly-flagged individual `[UNVERIFIED]` | **Confirmed open.** Left open, not resolved. Shipped with sourcing tier `open`. |
| 7 | Open Finance imposes explainability / ML-audit duties (marked do-not-cite) | **Confirmed do-not-cite.** Nothing supports it. Only existence and dates are cited; no explainability cue ships. |

## Sourcing-tier census (finance slice)

| Tier | Items |
|---|---|
| `primary` | `ouvidoria_channel`, `cadastro_positivo_criteria_disclosure`, `cadastro_positivo_contestation`, `credit_model_governance`, `pix_med_contestation`, `integrated_risk_management_framework`, `open_finance_consent_automated_credit`, `human_review_gap_lgpd20`, `ai_interaction_disclosure_gap` |
| `corroborated_secondary` | `cybersecurity_cloud_vendor_accountability`, `pix_fraud_blocking_no_analogue` |
| `open` | `fraud_data_sharing_due_process` |
