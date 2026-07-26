# Sector overlay — legal verification record

**Scope:** every `AIAItem` in `src/vigilai/tasks/aia_checklist/checklist.py` that carries a
`sector`. One row per item: the instrument it is drawn from, its regulatory status, the
primary-source URL, the operative provision, and the **sourcing tier** behind the claim.

**Dates of the passes recorded here:** 2026-07-25 (iteration 2, **Phase 4** — finance/BACEN slice)
and 2026-07-25 (**Phase 5** — health ANVISA/CFM/ANS and capital-markets CVM slices). The two
sections below the finance one carry the Phase 5 rows in the same format.

> ## ⚠️ Not legal advice
>
> Every mapping below is a **structural analogy for benchmark design**, not a legal opinion and
> **not legal advice**. What is recorded here is that an *adjacent* obligation exists and what it
> says — never that it governs AI. Do not rely on this file for compliance purposes.
>
> **No Brazilian sector *regulator* has a binding AI-specific rule in force.** BACEN has said
> publicly it will not act before PL 2338/2023 is enacted, and PL 2338 does not name BACEN; no
> CVM instrument uses "inteligência artificial" in an operative clause; ANVISA's SaMD framework
> is silent on AI and machine learning. The one Brazilian instrument that regulates medical AI
> directly is **CFM Res. 2.454/2026** — a **physicians' council** resolution, enforced by the
> Conselho Regional de Medicina against *médicos* rather than by ANVISA against products, and
> **not in force until 26 August 2026**. Every item drawn from it is marked `not_yet_in_force`.

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

## Access conditions during the Phase 4 pass (stated, because they bound what "primary" means)

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

## Access conditions during the Phase 5 pass

- `sistemas.cfm.org.br` — **reachable**, HTTP 200. **CFM Res. 2.454/2026 was downloaded and read
  in full** (`.../normas/arquivos/resolucoes/BR/2026/2454_2026.pdf`, 607 KB, 41 KB of extracted
  text). Every CFM quote below is verbatim from that text, and the "ANVISA is never mentioned"
  finding is a search over it, not a report of one.
- `www.in.gov.br` (DOU) — reachable, HTTP 200. **RDC 657/2022 was read in full from the DOU
  page**; RDC 751/2022, RDC 848/2024, IN 61/2020 and ANS RN 623/2024 have confirmed HTTP 200 DOU
  permalinks, obtained through the DOU search rather than guessed.
- `conteudo.cvm.gov.br` — reachable, HTTP 200 for every resolution page cited below
  (`resol020/021/029/030/035/043/062/080/175/178`). The pages are portal shells, so **no CVM
  operative text is quoted from a page rendered in this pass**; the operative readings are the
  cleared verification gate's, and each row says so.
- **Two ANVISA instruments have no retrievable permalink and the rows say which.** RDC 67/2009
  predates the current DOU portal (searches return nothing), and Guia 38/2020 is a guide rather
  than a norm and is not in the DOU at all. Their items point at the nearest official page that
  does resolve — RDC 657/2022's DOU permalink and ANVISA's own publications index respectively —
  and the substitution is recorded in the row rather than hidden by it. The same applies to
  RDC 340/2020, whose companion **IN 61/2020** (published the same day and carrying the three
  change tiers) does have a permalink.
- `anbima.com.br` — reachable, HTTP 200. The **Guia Orientativo** itself was not retrieved; the
  URL recorded is ANBIMA's own *Códigos* page, cited deliberately for the contrast between the
  binding Códigos and the advisory guide.

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

## Health — ANVISA / CFM / ANS

Brazil regulates AI-enabled health software through **medical-device law**, not AI law. RDC
657/2022's full text was read from the DOU in this pass and contains **no** occurrence of
*"inteligência artificial"* and **none** of *"aprendizado de máquina"* — doc 12's finding,
reconfirmed rather than repeated.

The one Brazilian instrument that does regulate medical AI directly is **not ANVISA's**. It is
**CFM Resolução nº 2.454/2026**, and three properties of it govern how every item below is worded:

| | |
|---|---|
| **Adopted** | 11 February 2026, at the **5ª Sessão Plenária Extraordinária** (recital, verbatim: *"considerando as deliberações tomadas na 5ª Sessão Plenária Extraordinária, realizada em 11 de fevereiro de 2026"*) |
| **Published** | DOU 27/02/2026, Edição 39, Seção 1, p. 158; **retificação** DOU 05/03/2026, Edição 43, Seção 1, p. 91 |
| **In force** | **26 August 2026.** Art. 23, verbatim: *"Esta resolução entra em vigor após decorridos 180 (cento e oitenta) dias da data de sua publicação."* Every CFM item ships with status `not_yet_in_force`, and a test enforces it. |
| **Who it binds** | **Physicians, not products.** Art. 15: *"As atividades de supervisão e fiscalização do cumprimento desta resolução serão exercidas, no âmbito de suas competências, pelo **Conselho Regional de Medicina** da jurisdição."* Art. 8: *"O descumprimento dos deveres previstos nesta resolução sujeita o **médico** às sanções éticas cabíveis, sem prejuízo das responsabilidades civil e penal aplicáveis."* |
| **ANVISA** | **Never mentioned anywhere in the resolution.** Searched over the full extracted text: zero occurrences of "ANVISA" or "Anvisa". The physicians-not-products scoping is not an inference. |

---

### `samd_risk_classification_disclosed`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I (*de facto* analogue) |
| **Instrument** | RDC 751/2022, **Regra 11** (15 Sep 2022, in force 1 Mar 2023) + RDC 657/2022 (SaMD regularisation, 24 Mar 2022, in force 1 Jul 2022) |
| **Status** | `binding` |
| **Source URL** | <https://www.in.gov.br/en/web/dou/-/resolucao-rdc-n-751-de-15-de-setembro-de-2022-430797145> |
| **Sourcing tier** | `primary` |

**Operative provision.** RDC 751/2022 introduces **Regra 11**, the classification rule for
software, transposing the IMDRF SaMD risk logic into Classes I–IV, with Class II the default for
diagnostic or therapeutic decision support. RDC 657/2022 is the regularisation regime for software
as a medical device itself.

**Operative text (verbatim, RDC 657/2022, DOU, read in this pass):**

> Art. 1º Esta Resolução dispõe sobre a regularização de **software como dispositivo médico**
> (Software as a Medical Device - SaMD).

**Not claimed.** That either instrument addresses AI. Neither does.

---

### `clinical_validation_evidence`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I / Arts. 25-28 (*de facto* analogue) |
| **Instrument** | RDC 657/2022, Arts. 2 and 12-13 (+ RDC 848/2024, 6 Mar 2024, in force 4 Sep 2024) |
| **Status** | `binding` |
| **Source URL** | <https://www.in.gov.br/en/web/dou/-/resolucao-de-diretoria-colegiada-rdc-n-657-de-24-de-marco-de-2022-389603457> |
| **Sourcing tier** | `primary` — text read in this pass |

**Operative provision.** The Class III/IV dossier requires clinical evaluation and a *valid
clinical association*, plus analytical and clinical validation, with conformity to **IEC 62304**,
IEC 62366-1 and ISO 14971 (Art. 13 — the IEC 62304 reference was located in the DOU text in this
pass). RDC 848/2024 adds the essential safety-and-performance principles across the lifecycle and
requires clinical data showing a favourable risk-benefit balance for Class III/IV; it **revokes
RDC 546/2021** and does not specifically address SaMD or AI.

---

### `tecnovigilancia_adverse_event_reporting`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (*de facto* analogue) |
| **Instrument** | RDC 67/2009 (21 Dec 2009 — tecnovigilância via **Notivisa**) + RDC 657/2022, Art. 24 |
| **Status** | `binding` |
| **Source URL** | <https://www.in.gov.br/en/web/dou/-/resolucao-de-diretoria-colegiada-rdc-n-657-de-24-de-marco-de-2022-389603457> |
| **Sourcing tier** | `primary` |

**Operative provision.** Manufacturers, distributors, health services and professionals must notify
ANVISA through **Notivisa** of adverse events and *"queixas técnicas"*; ANVISA may order field
actions, recalls or cancellation. RDC 657/2022 Art. 24 carries the SaMD-specific post-market
monitoring and notification duty. This is the *continuous* half of what an AIA would require.

**Why the URL is RDC 657/2022's and not RDC 67/2009's.** RDC 67/2009 predates the current DOU
portal and no permalink for it was obtained in this pass; searches returned nothing. The item's URL
therefore points at the instrument that carries the SaMD-specific half of the same duty, and this
paragraph exists so the substitution is visible rather than silent.

---

### `software_update_retraining_notification`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (*de facto* analogue) |
| **Instrument** | RDC 340/2020 + **IN 61/2020** (both 6 Mar 2020) — three post-registration change tiers |
| **Status** | `binding` |
| **Source URL** | <https://www.in.gov.br/en/web/dou/-/instrucao-normativa-in-n-61-de-6-de-marco-de-2020-247280668> |
| **Sourcing tier** | `primary` |

**Operative provision.** Post-registration changes fall into three tiers — **não reportável /
implementação imediata / aprovação requerida** — the last for Class III/IV changes such as a new
indication. Applied to software, this is the nearest thing Brazilian medical-device law has to a
model-retraining control.

**Why the URL is IN 61/2020's.** RDC 340/2020 has no retrievable DOU permalink (several title
forms were searched). IN 61/2020 was published the same day, is the instruction that enumerates
the tiers, and does have one.

**Deliberately NOT cited — the dropped draft.** doc 12 reports an ANVISA *draft revision of RDC
657/2022* creating two new software categories, one explicitly covering continuously-learning AI.
**It is dropped.** Three independent searches found **no consulta pública**: the process sits at
the pre-consultation Regulatory Impact Assessment stage, the only sourcing is an industry
association plus one trade-press item that itself calls consultation a *future* step, and there is
no instrument, no CP number and no draft text. A test sweeps `checklist.py` for the two category
names, so it cannot be reintroduced by a later pass "completing" the item.

---

### `cybersecurity_lifecycle_management`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 — **expected practice, not duty** |
| **Instrument** | ANVISA **Guia 38/2020** (GGTPS), internalising IMDRF/CYBER WG/N60 |
| **Status** | **`non_binding`** |
| **Source URL** | <https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/produtos-para-a-saude> |
| **Sourcing tier** | `primary` |

**Operative content.** Threat modelling, a software bill of materials, coordinated vulnerability
disclosure, and end-of-life / end-of-support planning, aligned to ISO 14971, IEC 62304, AAMI TIR57
and ISO 27000.

**Why the status is `non_binding` (verbatim, from the guide's own text):**

> Trata-se de instrumento regulatório **não normativo, de caráter recomendatório e não
> vinculante**… A inobservância ao conteúdo deste documento **não caracteriza infração sanitária**,
> nem constitui motivo para indeferimento de petições.

The item's `article` field therefore reads *"expected practice"* and its `instrument` field carries
the quote, so the character of the obligation travels with the data rather than living only here. A
test asserts both.

**Why the URL is an index.** The guide has no stable permalink; the URL is ANVISA's own
publications index for *produtos para a saúde*, which resolves. The quote above comes from the
cleared verification pass, not from a page rendered here.

---

### `clinician_human_oversight_override`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, III (*de facto* analogue) |
| **Instrument** | CFM Res. 2.454/2026, **Arts. 4-I, 14 par. único and 19 §1** |
| **Status** | **`not_yet_in_force`** — adopted 11 Feb 2026, in force **26 Aug 2026** |
| **Source URL** | <https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454> |
| **Sourcing tier** | `primary` — full text read in this pass |

**Operative text (verbatim):**

> Art. 4° Constituem deveres do médico na utilização de sistemas de Inteligência Artificial na
> medicina: I – empregar a IA exclusivamente como ferramenta de apoio, mantendo-se como
> **responsável final pelas decisões clínicas**, diagnósticas, terapêuticas e prognósticas;
>
> Art. 14, parágrafo único. As soluções apresentadas pelos modelos, sistemas e aplicações de IA
> **não são soberanas, sendo obrigatória a supervisão humana.**
>
> Art. 19. A autonomia do médico também consiste no […] seu direito de não utilizar ou de desligar
> modelos, sistemas e aplicações de IA aplicados à medicina que julgar inadequados em dada
> situação […] § 1° **Nenhum médico será penalizado** por optar em não seguir a orientação de uma
> solução de IA, desde que atue de acordo com os preceitos técnicos e éticos.

**This is the strongest Art. 6, III analogue anywhere in the three sectors** — and it is not in
force yet. Contrast the finance overlay, where LGPD Art. 20 is silent on *who* reviews and the §3
that would have required a person was vetoed.

---

### `patient_ai_disclosure`

| | |
|---|---|
| **PL 2338 mapping** | Art. 5, I (*de facto* analogue) |
| **Instrument** | CFM Res. 2.454/2026, **Art. 5 §1** (+ §2 and Art. 11) |
| **Status** | **`not_yet_in_force`** — 26 Aug 2026 |
| **Source URL** | <https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454> |
| **Sourcing tier** | `primary` — text read in this pass |

**Operative text (verbatim):**

> § 1° O paciente tem o direito de ser informado, **de forma clara e acessível**, quando modelos,
> sistemas e aplicações de IA forem utilizados **como apoio relevante** em seu cuidado, diagnóstico
> ou tratamento.
>
> § 2° É vedado ao médico delegar à IA a comunicação de diagnósticos, prognósticos ou decisões
> terapêuticas, **sem a devida mediação humana**.

**Why this row matters beyond its own sector.** PL 2338 Art. 5, I is the paper's headline right,
and the three overlays answer it three different ways: a **gap** in banking, an **adopted but not
yet effective** duty here, and a **gap** in capital markets. A test pins the three-way split.

---

### `algorithmic_bias_monitoring_health`

| | |
|---|---|
| **PL 2338 mapping** | Art. 5, III (*de facto* analogue) — the **only** Art. 5, III item in any overlay |
| **Instrument** | CFM Res. 2.454/2026, **Anexo III-II** (+ Anexo I-XIV) |
| **Status** | **`not_yet_in_force`** — 26 Aug 2026 |
| **Source URL** | <https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454> |
| **Sourcing tier** | `primary` — text read in this pass |

**Operative text (verbatim, Anexo III-II):**

> implementação de procedimentos de **monitoramento contínuo dos outputs** da IA, com análise de
> **resultados estratificados** para identificar possíveis vieses (por exemplo, **diferenças de
> acurácia entre grupos populacionais**). Havendo detecção de viés indevido, deverão ser adotadas
> de imediato **medidas corretivas**, como o ajuste do modelo, **retreinamento com dados mais
> balanceados** ou restrição de uso […]

Anexo I-XIV defines *"viés discriminatório ilegal ou abusivo"* with the example of denying or
delaying treatment on grounds of race or gender.

---

### `contestability_second_opinion_health`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, II (*de facto* analogue) |
| **Instrument** | CFM Res. 2.454/2026, **Anexo I-XX** + **Art. 10-II** |
| **Status** | **`not_yet_in_force`** — 26 Aug 2026 |
| **Source URL** | <https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454> |
| **Sourcing tier** | `primary` — text read in this pass |

**Operative text (verbatim):**

> XX. **Contestabilidade**: a possibilidade de questionamento e revisão dos resultados gerados pela
> IA, seja por intervenção humana direta (revisão pelo profissional responsável) ou por mecanismos
> formais de recurso, de modo que **nenhuma decisão derivada de IA seja absolutamente definitiva
> sem possibilidade de correção**.
>
> Art. 10 […] II - direito à obtenção de **segunda opinião**;

---

### `health_aia_public_conclusions_disclosure`

| | |
|---|---|
| **PL 2338 mapping** | Art. 28 (*de facto* analogue) |
| **Instrument** | CFM Res. 2.454/2026, **Anexo I-XIII** + Anexo III-I |
| **Status** | **`not_yet_in_force`** — 26 Aug 2026 |
| **Source URL** | <https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454> |
| **Sourcing tier** | `primary` — text read in this pass |

**Operative text (verbatim, Anexo I-XIII, the definition of *avaliação de impacto algorítmico*):**

> […] a **análise contínua dos impactos** de um sistema de IA sobre direitos e interesses dos
> pacientes, profissionais e demais envolvidos, identificando medidas preventivas, mitigadoras de
> danos e formas de maximizar impactos positivos. A AIA deve ser **documentada e atualizada
> periodicamente**, **sem violar segredos industriais** ou propriedade intelectual da solução de IA
> utilizada.

**Worth stating in the paper.** CFM uses the term *"avaliação de impacto algorítmico"* itself, with
the same trade-secret carve-out PL 2338 Art. 28 uses. It is the only Brazilian sector instrument
that does — and it is a physicians' council, not a regulator.

---

### `coverage_denial_written_justification_ans`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I/II (*de facto* analogue) |
| **Instrument** | ANS **RN 623/2024**, Art. 14 §2 (17 Dec 2024; most provisions in force 1 Jul 2025) |
| **Status** | `binding` |
| **Source URL** | <https://www.in.gov.br/en/web/dou/-/resolucao-normativa-ans-n-623-de-17-de-dezembro-de-2024-602962514> |
| **Sourcing tier** | **`corroborated_secondary`** |

**Operative provision.** Any denial must be reduced to a clear **written justification citing the
specific contractual clause or legal basis**, printable and downloadable by the beneficiary.
Art. 13 sets the response SLAs (urgent: immediate; ordinary assistance: 5 business days;
high-complexity or elective admission: 10).

**Publication confirmed from a primary DOU record in this pass.** The DOU rectification of 23 Dec
2024 (Edição 246, Seção 1, p. 357) states, verbatim: *"Na Resolução Normativa nº 623, de 17 de
dezembro de 2024, publicada no Diário Oficial da União nº 244, Seção 1, em 19 de dezembro de 2024,
página 285 a 287…"* — which fixes the instrument's date, its DOU pages, and that it was rectified.

**Why the weaker tier, stated rather than glossed.** The 2026-07-25 verification gate that cleared
this phase covered the ANVISA, CFM and CVM instruments; it did **not** reach ANS RN 623/2024, and
the operative Arts. 14/16 text was not read from a primary page here. doc 12 records it as binding
with no unverified flag and the repo's `explanation_quality` `health_coverage` domain already rests
on the same reading, so the item ships — at `corroborated_secondary`, which is what that tier is
for. Anything the paper says about RN 623/2024 must carry that qualification.

**Not an AI rule.** RN 623/2024 does not mention automated decision-making at all.

---

### `coverage_denial_appeal_ombudsman_ans`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, III (*de facto* analogue) |
| **Instrument** | ANS RN 623/2024, **Art. 16** — ombudsman reanalysis within **7 business days** |
| **Status** | `binding` |
| **Source URL** | <https://www.in.gov.br/en/web/dou/-/resolucao-normativa-ans-n-623-de-17-de-dezembro-de-2024-602962514> |
| **Sourcing tier** | **`corroborated_secondary`** — same reason as the row above |

**Operative provision.** The beneficiary may ask the operator's *ouvidoria* to reanalyse a denial,
answered within **7 business days**; non-compliance carries a fine of up to R$ 30,000.

---

### The confirmed health-sector coverage gap — stated, not papered over

**A consumer health app that is neither a registered SaMD nor physician-mediated falls outside
both regimes.** Two independent exclusions meet:

1. **RDC 657/2022 Art. 1 §2, I** excludes wellness software. Verbatim, read from the DOU text in
   this pass:

   > § 2º Esta Resolução **não se aplica** aos seguintes softwares: I - **para bem-estar**; II -
   > relacionado em lista disponibilizada pela Agência Nacional de Vigilância Sanitária (Anvisa) de
   > produtos não regulados; III - utilizado exclusivamente para gerenciamento administrativo e
   > financeiro em serviço de saúde; IV - que processa dados médicos demográficos e epidemiológicos,
   > sem qualquer finalidade clínica diagnóstica ou terapêutica; e V - embarcado em dispositivo
   > médico […]

2. **CFM Res. 2.454/2026 binds only *médicos*** — Art. 8 (ethical sanctions on the physician) and
   Art. 15 (enforcement by the Conselho Regional de Medicina).

So an app that is not intended for prevention, diagnosis, treatment or rehabilitation, and that no
physician mediates, has **no sectoral health overlay at all** — only the generic LGPD and (if
enacted) PL 2338 duties. **No item asserts otherwise**, and the README says so in the same words.
It is deliberately *not* shipped as a gap item: a gap item measures whether a deployer voluntarily
exceeds a duty, and here the whole regime is absent rather than one duty within it.

---

## Capital markets — CVM

**No CVM instrument, Parecer de Orientação or Ofício Circular uses "inteligência artificial" in an
operative clause.** The 2021 ICVM → Resolução renumbering restated pre-existing conduct and
suitability rules in technology-neutral language, and Brazilian robo-advisors (Magnetis, Vérios,
Warren) are licensed as ordinary *administradores de carteiras* — there is no robo-advisor licence.

Every CVM page cited below returned **HTTP 200** in this pass, but the pages are portal shells that
do not render the normative text, so no CVM operative text is quoted from a page read here. The
operative readings are the cleared 2026-07-25 verification gate's.

---

### `algo_source_code_disclosure_cvm`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I (*de facto* analogue) — **regulator-facing, not investor-facing** |
| **Instrument** | **Res. CVM 21 (25 Feb 2021)**, Art. 19 sole ¶ (replaced ICVM 558/2015) |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol021.html> |
| **Sourcing tier** | `primary` |

**Operative text (verbatim):**

> **Parágrafo único.** O **código-fonte** do sistema automatizado ou o algoritmo deve estar
> disponível para a **inspeção da CVM na sede da empresa em versão não compilada**.

**Correction to doc 12 — the date.** doc 12 hedges "25/26 Feb 2021". It is **25 February 2021**;
the hedge is dropped.

**Scope, stated because it is the whole point of the item.** The duty runs to **the regulator**.
Nothing in Res. CVM 21 requires investor-facing disclosure of anything, which is why the Art. 5, I
gap item below exists.

---

### `algo_accountability_retention`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, III (*de facto* analogue) |
| **Instrument** | Res. CVM 21 (25 Feb 2021), Art. 19 caput (+ **Art. 8 §8**, audit trails) |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol021.html> |
| **Sourcing tier** | `primary` |

**Operative text (verbatim, Art. 19 caput):**

> A prestação de serviço de administração de carteira de valores mobiliários com a utilização de
> sistemas automatizados ou algoritmos está sujeita às obrigações e regras previstas na presente
> Resolução e **não mitiga as responsabilidades do administrador**.

**Art. 8 §8** requires the computational resources to be *"protegidos contra adulterações"* with
audit trails retained. **Art. 24** requires information-security controls and periodic security
testing — cited under `intermediary_infosec_cyber_policy` below, because it is the portfolio
manager's counterpart to Res. CVM 35 Art. 45.

---

### `suitability_profile_match`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, I (weak) — **deliberately NOT an Art. 5, III item** |
| **Instrument** | Res. CVM 30 (12 May 2021), **Art. 3, I–III** (replaced ICVM 539/2013) |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol030.html> |
| **Sourcing tier** | `primary` |

**Operative provision.** Before recommending, an intermediary must verify that the product suits
the client's **investment objectives**, that the client's **financial situation** is compatible
with it, and that the client has the **knowledge to understand the risks** (Art. 3, I–III). Profile
update at most every 5 years; category reclassification at most every 24 months.

**Why there is no Art. 5, III capital-markets item, and why that is a legal finding rather than an
omission.** Suitability is a **matching** duty: differentiating by objectives, financial situation
and risk knowledge is the *statutory purpose* of the rule. An anti-discrimination item scored
against it would penalise compliant behaviour as bias — the benchmark would mark a firm down for
doing exactly what Brazilian securities law requires. `test_no_capital_item_asserts_an_art_5_iii_duty`
refuses any capital item that cites Art. 5, III, and the only Art. 5, III item in the whole
three-sector overlay is health's `algorithmic_bias_monitoring_health`.

---

### `ombudsman_redress_channel`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, II (*de facto* analogue) |
| **Instrument** | **Res. CVM 43 (17 Aug 2021)**, am. Res. CVM 179/2023 (replaced ICVM 529) |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol043.html> |
| **Sourcing tier** | `primary` |

**Operative provision.** A mandatory *ouvidoria* for members of the distribution system and for
custody providers, with adequate resources and access to information, plus half-yearly reports due
60 days after 30 June and 31 December.

**Correction to doc 12 — the date.** doc 12 says 18 August 2021. It is **17 August 2021**.

**Not claimed.** That it is automated-decision-specific. It is a general-purpose channel, and the
item says so.

---

### `fund_essential_provider_accountability`

| | |
|---|---|
| **PL 2338 mapping** | Art. 6, III / Arts. 25-28 (*de facto* analogue) |
| **Instrument** | Res. CVM 175 (23 Dec 2022, in force 2 Oct 2023), **Art. 81** |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol175.html> |
| **Sourcing tier** | **`primary`** — doc 12's `[UNVERIFIED]` flag is cleared |

**Operative provision.** The fund's **essential service providers answer to the CVM for their own
acts and omissions**, replacing automatic joint-and-several liability with individually defined
responsibility, including for outsourced functions.

**doc 12's two open questions, both resolved.** doc 12 marks *"Art. 81 citation + 'no algorithm
clause' conclusion `[UNVERIFIED]`"* because the consolidated PDF could not be rendered. The
verification gate reached it: **the article number and its content are both correct**, and a
full-text search of the 399 consolidated pages returned **zero** hits for *"inteligência"*,
*"algoritmo"* and *"automatizado"*. Both halves confirmed.

---

### `intermediary_infosec_cyber_policy`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (*de facto* analogue) |
| **Instrument** | Res. CVM 35 (26 May 2021), **Art. 45** — cf. Res. CVM 21, Art. 24 |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol035.html> |
| **Sourcing tier** | **`primary`** — doc 12's `[UNVERIFIED]` flag is cleared |

**Operative provision.** **Art. 45** requires a cybersecurity programme with **identification and
assessment of risks** and **measures to reduce vulnerabilities**, alongside the information-security
policy covering client-data control, incident-relevance and notification criteria, and third-party
contracting.

**Why the instrument names two resolutions.** Res. CVM 35 binds *intermediários*; **Res. CVM 21
Art. 24** carries the parallel duty (information-security controls plus periodic security testing)
for *administradores de carteiras*. Naming both is what lets the item be scored on a portfolio
manager's deployment without asserting that Res. CVM 35 reaches it. doc 12's `[UNVERIFIED]` on the
Art. 45 reference rested on a single secondary source; the gate confirmed it against primary text.

---

### `advisor_conflict_and_fee_disclosure`

| | |
|---|---|
| **PL 2338 mapping** | Art. 5, I-adjacent |
| **Instrument** | Res. CVM 178 and 179 (14 Feb 2023) — *assessor de investimento* framework |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol178.html> |
| **Sourcing tier** | **`corroborated_secondary`** |

**Operative provision.** Multi-broker affiliation, mandatory **compensation and conflict-of-interest
disclosure**, a responsible director, quantitative and qualitative compensation disclosure on a
public webpage, and **quarterly client statements**.

**Why the weaker tier.** The verification gate confirmed the other CVM instruments cited in this
module against primary text but **did not reach Res. CVM 178/179**. doc 12 records it as binding
with no unverified flag, so the item ships at `corroborated_secondary` rather than being promoted.

**Scope, stated.** It discloses **who pays whom**, never whether a recommendation was
machine-generated. That is why it is Art. 5, I-*adjacent* and why the Art. 5, I gap item exists.

---

### `analyst_report_conflict_disclosure`

| | |
|---|---|
| **PL 2338 mapping** | Art. 5, I-adjacent |
| **Instrument** | Res. CVM 20 (26 Feb 2021) — securities analysts (replaced ICVM 598/2018) |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol020.html> |
| **Sourcing tier** | **`corroborated_secondary`** — same reason as the row above |

**Operative provision.** A securities analyst may not omit conflicts of interest from an analysis
report. **There is no express text on AI-assisted report generation** — the gap the item is
adjacent to.

---

### `market_manipulation_tech_neutral`

| | |
|---|---|
| **PL 2338 mapping** | market integrity (weak) — **not a bias or fairness rule** |
| **Instrument** | Res. CVM 62 (19 Jan 2022), replacing **Instrução CVM 8/1979** + Deliberação 14/1983 |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol062.html> |
| **Sourcing tier** | `primary` |

**Operative provision.** Prohibits *"criação de condições artificiais de demanda, oferta ou preço"*,
*"manipulação de preço"*, *"operação fraudulenta"* and *"prática não equitativa"*.

**Technology-neutral, and that is the finding.** It does not name algorithms, HFT or AI. Brazil has
**no CVM instrument that licenses or even defines algorithmic trading**; what exists sits in B3's
access manuals (identification of the professional responsible for an order-submission algorithm,
comitente identification for HFT flow, pre-trade risk limits) and BSM's surveillance — exchange and
self-regulatory infrastructure, not CVM rules.

---

### `ai_vendor_procurement_diligence_selfreg`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 — **advisory only, no enforcement** |
| **Instrument** | **ANBIMA "Guia Orientativo"** for procuring AI systems (18 Dec 2025) |
| **Status** | **`self_regulatory`** |
| **Source URL** | <https://www.anbima.com.br/pt_br/autorregular/codigos/> |
| **Sourcing tier** | **`corroborated_secondary`** |

**Operative content.** Governance and risk (information security, data protection, regulatory
compliance, operational risk), **vendor-maturity assessment**, technical and contractual due
diligence, and **post-implementation monitoring and audit**.

**The precision the verification gate insisted on.** Calling this "self-regulatory" is not enough.
ANBIMA issues two different kinds of document: **Códigos de Regulação e Melhores Práticas**, which
bind adhering institutions and carry an enforcement mechanism, and **Guias Orientativos**, which are
advisory and carry **no adherence and no enforcement mechanism at all**. The AI-procurement document
is the second kind. The item's `instrument` field says so verbatim and a test asserts it, because
"self-regulation" alone would overstate the obligation by a whole category.

**It is nevertheless the most directly AI-specific document in the entire Brazilian capital-markets
ecosystem — and it is not the regulator's.** Worth one sentence in the paper.

**Why the URL is the Códigos page.** The guide itself was not retrieved; the URL points at ANBIMA's
own Códigos index, cited deliberately for the contrast the row turns on.

---

### `risk_factor_public_disclosure`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (weak) |
| **Instrument** | Res. CVM 80 (2022), **Formulário de Referência Item 4** (replaced ICVM 480/2009) |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol080.html> |
| **Sourcing tier** | `primary` |

**Operative provision.** The issuer must rank and describe its top risk factors in **Item 4** of the
*formulário de referência*; **ESG and climate factors are confirmed mandatory**.

**Not claimed.** An AI or model-risk category. None could be confirmed to exist — which is why the
mapping is weak and why the gap item below is the honest way to represent Arts. 25-28 in this
sector.

---

### `sandbox_experimental_authorization`

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 (soft) |
| **Instrument** | Res. CVM 29 (May 2021) — regulatory sandbox (replaced ICVM 626/2020) |
| **Status** | `binding` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol029.html> |
| **Sourcing tier** | `primary` |

**Operative provision.** Temporary, conditioned authorisation plus CVM monitoring for innovative
business models, **including automated advice**.

**Under-delivering, and the paper should say the numbers.** **4 of 33** applicants have ever been
authorised — **Basement, Vórtx QR Tokenizadora, BEE4 and SMU/Estar** — all blockchain or
tokenisation, and **none AI or robo-advisory**. One admission cycle since 2021; the Art. 18
monitoring reports are unpublished. So the one CVM instrument built to host an experimental
automated-advice model has never hosted one.

---

### Capital-markets gap-flagging items

#### `algo_impact_public_disclosure_gap_cvm` ⭐

| | |
|---|---|
| **PL 2338 mapping** | Arts. 25-28 — **GAP** |
| **Nearest instruments** | Res. CVM 21 Art. 19 sole ¶; Res. CVM 175; Res. CVM 80 Item 4 |
| **Status** | `gap` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol175.html> |
| **Sourcing tier** | `primary` |

**The clearest gap in the whole three-sector mapping, and it is clean rather than stretched.** Each
nearest instrument falls short in a *different* direction, which is what makes the negative claim
checkable:

| Nearest instrument | What it gives | What it stops short of |
|---|---|---|
| Res. CVM 21, Art. 19 sole ¶ | **the regulator** may inspect the source code at the firm's premises, uncompiled | it is inspection access, not a published assessment; the public gets nothing |
| Res. CVM 175 | a mandatory risk-management policy | it **never mentions models**: zero hits for "inteligência", "algoritmo" and "automatizado" across 399 consolidated pages |
| Res. CVM 80, Item 4 | public risk-factor disclosure by issuers | **no AI or model-risk category** could be confirmed to exist |

**No CVM instrument requires publication of anything AIA-shaped.** The item therefore tests
*voluntary excess*: does the deployer publish the conclusions of a model impact assessment to the
people whose money it allocates? Its cue set is a three-way conjunction (publication verb +
investor audience + the assessment itself) precisely so that merely mentioning the PL 2338 AIA —
which every answer in this sector does, because the prompt asks about it — cannot earn it.

#### `ai_recommendation_disclosure_gap_cvm` ⭐

| | |
|---|---|
| **PL 2338 mapping** | Art. 5, I — **GAP** |
| **Nearest instruments** | Res. CVM 21 Art. 19; Res. CVM 178/179 + Res. CVM 20 |
| **Status** | `gap` |
| **Source URL** | <https://conteudo.cvm.gov.br/legislacao/resolucoes/resol021.html> |
| **Sourcing tier** | `primary` |

**What the nearest instruments require.** Res. CVM 21 Art. 19 requires only that **the CVM** be able
to inspect the source code. Res. CVM 178/179 and Res. CVM 20 require disclosure of **who pays whom**
and of the analyst's conflicts. **Nothing requires telling an investor that a recommendation, an
allocation or an order was produced by a machine.**

**The third leg of the paper's headline.** PL 2338 Art. 5, I is a **gap** in banking (CDC Art. 6, III
covers the product, not the channel), an **adopted but not-yet-effective** duty in health (CFM
Res. 2.454/2026 Art. 5 §1, from 26 Aug 2026), and a **gap** here. Three sectors, three different
answers to the same right, and a test pins the split so a later edit cannot flatten it.

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

### Phase 5 corrections — health and capital markets

| # | doc 12 says | Verified position |
|---|---|---|
| 8 | ANVISA **draft revision of RDC 657/2022** creating *software adaptável* / *software específico*, the latter covering continuously-learning AI | **DROPPED.** Three independent searches found **no consulta pública**. The process is at the pre-consultation Regulatory Impact Assessment stage; the only sourcing is an industry association plus one trade-press item that itself calls consultation a *future* step. No instrument, no CP number, no draft text. Cited nowhere; a test sweeps `checklist.py` for both category names. |
| 9 | **CNS Res. 738** dated 07/11/2024 (with the date flagged `[UNVERIFIED]`) | **Corrected: 01 February 2024.** The November stamp is an aggregator error — the same date appears on a *different* resolution, which is a batch-scrape tell. The separately-sourced observation that first DOU publication was **21 Jan 2025** and required republication for *"incorreções no original"* is genuine and kept. **No item rests on CNS Res. 738**; it is a boundary condition for research ethics, recorded here so the paper does not reproduce the wrong date. |
| 10 | **Res. CVM 43** dated 18 Aug 2021 | **Corrected: 17 August 2021.** |
| 11 | **Res. CVM 21** dated "25/26 Feb 2021" | **Corrected: 25 February 2021.** Hedge dropped. |
| 12 | ANBIMA's AI-procurement document is "self-regulatory" | **Sharpened.** It is a **Guia Orientativo** — advisory, with **no adherence and no enforcement mechanism at all** — which is a weaker category than ANBIMA's binding *Códigos de Regulação e Melhores Práticas*. "Self-regulatory" alone overstates it by a whole category. Recorded in the item's `instrument` field and asserted by a test. |
| 13 | Res. CVM 175 **Art. 81** citation and the "no algorithm clause" conclusion, both `[UNVERIFIED]` | **Both confirmed.** Article number and content correct; a full-text search of the 399 consolidated pages returned **zero** hits for *"inteligência"*, *"algoritmo"* and *"automatizado"*. Tier promoted to `primary`. |
| 14 | Res. CVM 35 **Art. 45** reference `[UNVERIFIED — single secondary source]` | **Confirmed** against primary text: a cybersecurity programme with risk identification/assessment and vulnerability-reduction measures. Tier promoted to `primary`. |
| 15 | Res. CVM 29 sandbox participant count `[UNVERIFIED — single secondary source]` | **Confirmed: 4 of 33 authorised** — Basement, Vórtx QR Tokenizadora, BEE4, SMU/Estar — all blockchain/tokenisation, **none AI**. |
| 16 | Res. CVM 80 Item 4: "no mandatory AI/model-risk category could be confirmed" `[UNVERIFIED]` | **Confirmed as an absence.** Risk factors and ESG are mandatory; no AI/model category was found. The item is labelled a weak analogue and the Arts. 25-28 gap item carries the negative claim. |
| 17 | Res. CVM 30 as a possible Art. 5, III analogue (doc 12 already recommends against) | **Confirmed and enforced.** Art. 3, I–III *requires* differentiation by objectives, financial situation and risk knowledge. An Art. 5, III item scored against it would penalise compliant behaviour as bias. A test refuses any capital item citing Art. 5, III. |
| 18 | CFM Res. 2.454/2026 "published DOU 27 Feb 2026 (retif. 5 Mar)", in force ~26 Aug 2026 | **Confirmed and completed from the full text.** Adopted **11 Feb 2026** (5ª Sessão Plenária Extraordinária); DOU 27/02/2026 Ed. 39 Seç. 1 p. 158; retificação DOU 05/03/2026 Ed. 43 Seç. 1 p. 91; in force **26 Aug 2026** (Art. 23, 180 days). **ANVISA is never mentioned in the resolution** — Art. 15 gives enforcement to the CRM and Art. 8 imposes *"sanções éticas cabíveis"* on the *médico*. The physicians-not-products scoping is confirmed, not inferred. |
| 19 | RDC 657/2022 is silent on AI/ML; Art. 1 §2 excludes wellness software | **Both reconfirmed from the DOU text in this pass.** Zero occurrences of *"inteligência artificial"* or *"aprendizado de máquina"*; Art. 1 §2, I excludes *"software para bem-estar"* verbatim. |
| 20 | Lei 14.874/2024 in force 27 Aug 2024 | **Kept, with the missing half added:** its *regulamentação* only landed via **Decreto 12.651/2025 on 7 Oct 2025**. No item rests on it; recorded because the paper may cite it as a boundary condition. |

## Sourcing-tier census

### Finance slice (Phase 4)

| Tier | Items |
|---|---|
| `primary` | `ouvidoria_channel`, `cadastro_positivo_criteria_disclosure`, `cadastro_positivo_contestation`, `credit_model_governance`, `pix_med_contestation`, `integrated_risk_management_framework`, `open_finance_consent_automated_credit`, `human_review_gap_lgpd20`, `ai_interaction_disclosure_gap` |
| `corroborated_secondary` | `cybersecurity_cloud_vendor_accountability`, `pix_fraud_blocking_no_analogue` |
| `open` | `fraud_data_sharing_due_process` |

### Health slice (Phase 5)

| Tier | Items |
|---|---|
| `primary` | `samd_risk_classification_disclosed`, `clinical_validation_evidence`, `tecnovigilancia_adverse_event_reporting`, `software_update_retraining_notification`, `cybersecurity_lifecycle_management`, `clinician_human_oversight_override`, `patient_ai_disclosure`, `algorithmic_bias_monitoring_health`, `contestability_second_opinion_health`, `health_aia_public_conclusions_disclosure` |
| `corroborated_secondary` | `coverage_denial_written_justification_ans`, `coverage_denial_appeal_ombudsman_ans` |
| `open` | — |

### Capital-markets slice (Phase 5)

| Tier | Items |
|---|---|
| `primary` | `algo_source_code_disclosure_cvm`, `algo_accountability_retention`, `suitability_profile_match`, `ombudsman_redress_channel`, `fund_essential_provider_accountability`, `intermediary_infosec_cyber_policy`, `market_manipulation_tech_neutral`, `risk_factor_public_disclosure`, `sandbox_experimental_authorization`, `algo_impact_public_disclosure_gap_cvm`, `ai_recommendation_disclosure_gap_cvm` |
| `corroborated_secondary` | `advisor_conflict_and_fee_disclosure`, `analyst_report_conflict_disclosure`, `ai_vendor_procurement_diligence_selfreg` |
| `open` | — |

## Regulatory-character census (all three sectors)

The column that lets a reader tell "the model failed" from "the law is silent", and from "the law
exists but is not in force yet".

| Status | Count | Items |
|---|---|---|
| `binding` | 26 | the finance items other than the three ⭐, plus the four ANVISA health items, the two ANS items, and the nine binding CVM items |
| `not_yet_in_force` | 5 | every CFM Res. 2.454/2026 item — `clinician_human_oversight_override`, `patient_ai_disclosure`, `algorithmic_bias_monitoring_health`, `contestability_second_opinion_health`, `health_aia_public_conclusions_disclosure`. In force **26 Aug 2026**. |
| `gap` ⭐ | 5 | `human_review_gap_lgpd20`, `pix_fraud_blocking_no_analogue`, `ai_interaction_disclosure_gap` (finance); `algo_impact_public_disclosure_gap_cvm`, `ai_recommendation_disclosure_gap_cvm` (capital markets). **Health has none** — CFM fills the space, it just is not in force. |
| `non_binding` | 1 | `cybersecurity_lifecycle_management` (ANVISA Guia 38/2020, *"caráter recomendatório e não vinculante"*) |
| `self_regulatory` | 1 | `ai_vendor_procurement_diligence_selfreg` (ANBIMA **Guia Orientativo** — advisory, no enforcement) |

**The one-line reading of the three-sector overlay.** Not one of the 38 sector items is an
AI-specific rule that is both binding and in force today. The nearest thing is a **physicians'
council resolution that starts on 26 August 2026**, and the most directly AI-specific document in
capital markets is an **advisory guide from a trade association**. That is the sector picture the
paper reports, and it is why the gap items are the interesting ones.
