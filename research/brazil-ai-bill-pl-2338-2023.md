# Brazil AI Bill PL 2.338/2023 - Comprehensive Research

## Overview

Brazil's AI Bill PL 2338/2023 is a comprehensive, risk-based AI regulatory framework approved by the Federal Senate on December 10, 2024. As of June 2026, it remains pending in the Chamber of Deputies, where amendments are expected — particularly around biometric surveillance carve-outs. The bill distinguishes itself from the EU AI Act most sharply through: (1) a standalone "Rights of Affected Persons" chapter anchored explicitly in the Inter-American Human Rights System; (2) strict liability for AI-caused damages (not fault-based); and (3) a subject/population-centered risk model rather than purely use-case-based.

## Official Text and Authoritative Sources

| Source | URL | Description |
|--------|-----|-------------|
| Clairk / Digital Policy Alert | https://clairk.digitalpolicyalert.org/documents/brazil-bill-on-the-use-of-artificial-intelligence-2338-2023-original-language/raw | Raw Official Text (Portuguese) |
| Data Privacy Brasil Research | https://www.dataprivacybr.org/en/the-artificial-intelligence-legislation-in-brazil-technical-analysis-of-the-text-to-be-voted-on-in-the-federal-senate-plenary/ | Technical Analysis of Senate Plenary Text |
| OECD.AI | https://oecd.ai/en/dashboards/policy-initiatives/bill-no-2338-of-2023 | Bill tracker entry |
| L.O. Baptista Advogados | https://www.baptista.com.br/draft-bill-of-legislation-proposing-the-new-brazilian-artificial-intelligence-act-overview-of-the-proposal-and-next-steps/?lang=en | Law firm overview with unofficial English translation reference |

An unofficial English translation is circulated by Brazilian law firms under the filename `PL_23382023_Senado_ENG_VF.pdf`.

## Risk Classification System

The bill establishes a **three-tier framework**:

### Tier 1 — Excessive Risk (Prohibited outright)

Four specific categories are banned:

1. **Subliminal manipulation** — AI systems using subliminal techniques to induce behavior harmful to a person's health or safety
2. **Exploitation of vulnerabilities** — Systems that exploit vulnerabilities of specific groups (based on age, disability, or socioeconomic condition) to cause harm
3. **Public social scoring** — Public authority use of AI for universal social scoring that determines access to goods and services based on social behavior or personality
4. **Real-time biometric ID** — Real-time remote biometric identification in public spaces — permitted only for:
   - (a) serious crimes carrying sentences over 2 years
   - (b) searches for missing persons
   - (c) active criminal apprehension
   - Requires prior judicial authorization

### Tier 2 — High-Risk (Strictly regulated)

The bill enumerates **14 specific high-risk application categories**:

1. Critical infrastructure management (traffic, power, water)
2. Education and vocational training selection
3. Employment decisions (hiring, promotion, termination, working conditions)
4. Essential service access (public and private)
5. Credit scoring and lending decisions
6. Emergency services dispatch prioritization
7. Judicial and administrative fact-finding assistance
8. Autonomous vehicles
9. Medical applications and diagnosis
10. Biometric identification systems
11. Criminal risk assessment
12. Crime analytics and policing
13. Evidence credibility evaluation (judicial contexts)
14. Migration and border control

Regulatory authorities may designate additional systems as high-risk based on: large-scale impact, effects on fundamental rights, potential for economic or moral damage, effects on vulnerable populations, irreversible consequences, transparency limitations, and processing of sensitive data.

### Tier 3 — Non-High/Non-Excessive Risk

Subject to general baseline obligations only (transparency, safe operation, bias prevention measures).

## The Standalone Human Rights Chapter — Article 5 and Chapter IV

This is the bill's most distinctive structural element. The bill dedicates a specific chapter — described as the bill's "backbone" — to the **rights of persons affected by AI systems**. Article 5 codifies six categories of rights:

### 1. Right to Prior Information
Users must be notified when interacting with an AI system, including:
- The provider's identity
- Data categories used
- Security measures
- How to exercise their rights

### 2. Right to Explanation
Affected persons can demand information about:
- System logic
- The degree of AI contribution to a decision
- Data sources
- How to challenge decisions
- Available human review options

### 3. Right to Contestation
Persons subject to consequential automated decisions receive clarity on:
- How the system works
- Who the operator is
- The AI's role
- What data was used
- What safeguards are in place

### 4. Right to Human Intervention
Includes rights to:
- Correct inaccurate data
- Request anonymization
- Challenge inappropriate data processing

### 5. Right to Non-Discrimination
Protection against both direct and indirect discriminatory bias based on protected characteristics.

### 6. Right to Privacy
All personal data processing must comply with Brazil's LGPD (Lei Geral de Proteção de Dados).

For **high-risk systems specifically**, additional layered rights apply:
- The right to a detailed explanation of the decision
- The right to contest and seek review of that decision
- The right to request human oversight or determination

### What Makes This Unique vs. the EU AI Act

The EU AI Act treats affected-person rights largely as procedural obligations imposed on deployers; enforcement pathways run through national data protection authorities. Brazil's bill formally cross-references the **Inter-American Human Rights System** — specifically Brazil's status as a State Party to the American Convention on Human Rights (ACHR) and its acceptance of the contentious jurisdiction of the **Inter-American Court of Human Rights**. This means State AI deployments that violate these rights create treaty-body exposure via the Inter-American Court — a litigation pathway with no direct EU parallel.

## Transparency Requirements

All AI providers and operators must:

- Notify users of AI interactions and the identity of the provider
- Provide "sufficient, objective, clear, and accessible information" about system operations and decision-making procedures
- Disclose methods available for individuals to exercise their rights
- Publish summaries of algorithmic impact assessments publicly (with trade secret protections)
- Mark synthetic content (deepfakes, AI-generated media) with verifiable identifiers
- Disclose in "easily accessible summaries" which copyright-protected materials were used in model training

## Algorithmic Impact Assessment (AIA)

Mandatory for all high-risk systems before market introduction (and on an ongoing basis). Must be conducted by qualified professionals and document:

1. **Preparation and scoping**
2. **Risk recognition** (known and foreseeable harms to fundamental rights)
3. **Mitigation measures deployed**
4. **Monitoring mechanisms** (continuous and iterative)
5. **System logic, testing results, training procedures, quality controls, and transparency measures**

The AIA must be made publicly accessible, though trade secrets may be protected. This is structurally distinct from the EU AI Act's conformity assessment (which is more technical/standards-based) and from GDPR Data Protection Impact Assessments (which focus on personal data, not broader rights impacts).

## Governance and Oversight Structure

The bill creates the **National System for AI Regulation and Governance (Sistema Nacional de Regulação e Governança de IA — SIA)**:

| Body | Role |
|------|------|
| **ANPD** (Autoridade Nacional de Proteção de Dados) | Primary coordinating enforcement body. Authority to investigate, inspect, issue guidance, levy penalties, and report annually. |
| **Sectoral regulators** | Retain jurisdiction in their domains: ANATEL (telecoms), ANVISA (health), ANAC (aviation), Banco Central (finance), CVM (securities), etc. |
| **CRIA** (Regulatory Cooperation Council) | Issues cross-sector guidelines and resolves conflicts between ANPD and sectoral regulators |
| **CECIA** (Expert and Scientist Committee) | Technical and scientific advisory body |

Key governance design feature: ANPD coordinates without centralizing all enforcement — sector-specific regulators maintain their substantive jurisdiction.

For **government high-risk AI systems** specifically, additional obligations apply:
- Prior public consultation
- Interoperable interfaces
- Public preliminary assessments
- Mandatory discontinuation if risks cannot be mitigated

## Penalties and Enforcement

### Administrative Sanctions

Graduated sanctions applied by ANPD and sectoral regulators:

- Written notice of offense
- **Fines up to R$50,000,000 (~USD $10 million) per offense**, or **2% of annual gross Brazilian revenue**, whichever is higher
- Public disclosure of the offense
- Restriction on regulatory sandbox participation for up to **5 years**
- Partial or complete suspension of AI system operations
- Prohibition on database processing

### Civil Liability

AI suppliers and operators face **strict liability** (regardless of fault) for damages caused by high-risk AI systems. This is a significant departure from the EU AI Act's more fault-based product liability approach.

Exceptions apply only for:
- Exclusive victim fault
- Exclusive third-party fault
- Force majeure

The Consumer Defense Code applies to all consumer-facing AI damage claims.

### Penalty Determination Factors

- Infraction gravity
- Good faith
- Economic advantage gained
- Economic situation of the violator
- Damage extent
- Degree of cooperation
- Governance quality
- Proportionality
- Prior sanctions history
- Risk-minimization mechanisms adopted

## General-Purpose AI / Foundation Models

The bill takes a deliberate **technology-neutral stance**. The drafters concluded it was not appropriate to define specific technologies like "foundational models" or "generative AI" in the statutory text, given the pace of technological change. Generative AI and general-purpose systems are subject to mandatory risk assessments, but obligations are framed by use-case impact rather than model architecture.

## Implementation Timeline

| Milestone | Date | Status |
|-----------|------|--------|
| Bill introduced in Senate | May 3, 2023 | Complete |
| CTIA (Senate AI Commission) final report | December 5, 2024 | Complete |
| Senate plenary approval | December 10, 2024 | Complete |
| Transmitted to Chamber of Deputies | March 17, 2025 | Complete |
| Referred to special committee in Chamber | March-April 2025 | Complete |
| Chamber vote | TBD | **Pending** |
| Presidential sanction | TBD | Pending |
| Entry into force (general provisions) | 2 years after enactment | Pending |
| Generative AI, prohibited uses, copyright | 180 days after enactment | Pending |

**As of June 2026**: No effective date exists. The bill has not been enacted. Civil society concerns about biometric surveillance exceptions and foundation model transparency are driving expected amendments in the Chamber.

## Compliance Framework (Pre-Compliance Obligations)

No official government compliance checklist has been published (the bill is not yet law). However, based on the bill's text:

### For All AI Systems Available in Brazil

Including foreign companies affecting Brazilian users (extraterritorial scope):

- [ ] Self-classify the AI system by risk tier before market placement
- [ ] Implement transparency notices for users
- [ ] Align all personal data processing with LGPD
- [ ] Establish bias prevention and data management procedures
- [ ] Disclose training data copyright use (per simplified summaries requirement)

### For High-Risk Systems — Mandatory Pre-Deployment

- [ ] Conduct full Algorithmic Impact Assessment (AIA)
- [ ] Document system logic, training data, performance testing (robustness, accuracy, reliability, coverage)
- [ ] Establish human oversight mechanisms with defined competencies
- [ ] Create automatic operation logging/recording
- [ ] Implement explainability measures
- [ ] Register system in the public database of high-risk AI (once the authority creates it)
- [ ] Bias elimination procedures and regular bias testing

### For High-Risk Government AI — Additional

- [ ] Prior public consultation
- [ ] Access control documentation
- [ ] Representative dataset certification
- [ ] Public publication of preliminary assessments
- [ ] Interoperable interfaces

### Ongoing Obligations

- [ ] Continuous lifecycle assessment
- [ ] Incident reporting for severe harms
- [ ] Cooperation with ANPD audits
- [ ] Maintain traceability for updates, retraining, and model modifications

### Exemptions

- AI developed for personal/non-commercial use
- National defense systems
- Research activities
- Open-source systems (unless classified as high-risk by design)

## Additional Resources

| Resource | URL |
|----------|-----|
| Data Privacy Brasil — Technical Analysis | https://www.dataprivacybr.org/en/the-artificial-intelligence-legislation-in-brazil-technical-analysis-of-the-text-to-be-voted-on-in-the-federal-senate-plenary/ |
| Securiti.ai — Brazil AI Regulation Deep Dive | https://securiti.ai/brazil-ai-regulation-and-law/ |
| Nathaly Calixto — 2026 Complete Analysis | https://nathalycalixto.com/brazil-ai-regulation-complete-analysis-2026/ |
| CIPL Comments (January 2024 PDF) | https://www.informationpolicycentre.com/uploads/5/7/1/0/57104281/cipl_comments_on_brazilian_senate_bill_no._2338__5_january_2024_.pdf |
| Policy Review — Brazilian Experience | https://policyreview.info/articles/news/road-regulation-artificial-intelligence-brazilian-experience/1737 |
| Digital Policy Alert — Official Text | https://clairk.digitalpolicyalert.org/documents/brazil-bill-on-the-use-of-artificial-intelligence-2338-2023-original-language/ |
| Regulations.ai — Entry | https://regulations.ai/regulations/RAI-BR-NA-PL23382-2023 |
| CGM Law — Senate Approval Summary | https://cgmlaw.com.br/en/brazilian-bill-regulating-the-use-of-artificial-intelligence-is-approved-by-senate-and-goes-to-the-chamber-of-deputies/ |
| AI Elsewhere — Global Implications | https://www.aielsewhere.com/p/the-precedents-brazils-ai-bill-could |
| Adeptiv AI — Compliance Guide | https://adeptiv.ai/brazil-artificial-intelligence-act/ |
| Nemko — AI Governance Brazil 2025 | https://digital.nemko.com/regulations/ai-governance-brazil |
| Academia.edu — Examination of Draft Bill | https://www.academia.edu/121506440/Regulation_of_artificial_intelligence_in_Brazil_examination_of_Draft_Bill_no_2338_2023_ |

## Gaps and Limitations

1. **No official English translation** from the Brazilian government exists. The circulated unofficial translation (`PL_23382023_Senado_ENG_VF.pdf`) is from law firms and has not been verified against the final December 2024 Senate vote version.

2. **Chamber of Deputies text may change**: The version passed by the Senate is not the final law. The Chamber can amend any provision. Biometric surveillance rules and foundation model transparency are the most likely targets.

3. **No secondary regulations yet**: The SIA, ANPD guidance, sectoral implementation rules, and sector-specific technical standards have not been published because the bill is not yet enacted.

4. **No official compliance checklist**: All compliance frameworks circulating are private-sector or civil society interpretations.

5. **Implementation timeline is entirely contingent**: "2 years after enactment" for most provisions means no compliance deadline can be calculated until presidential signature, which has no confirmed date.

---

*Research compiled: June 2026*
*Sources: Web research via Claude Code web-search-researcher agent*
