# EU AI Act (Regulation 2024/1689) - Comprehensive Research

## Overview

The EU AI Act (Regulation 2024/1689) is the world's first comprehensive mandatory AI law, entered into force August 1, 2024, with a phased rollout through 2030. It uses a risk-tiered framework with hard prohibitions, strict high-risk requirements, lighter transparency obligations, and voluntary guidance for minimal-risk systems.

## Official Text

| Source | URL |
|--------|-----|
| EUR-Lex Official | https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng |
| PDF Version | https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689 |
| AI Act Explorer (Future of Life Institute) | https://artificialintelligenceact.eu/the-act/ |

The official text was published in the Official Journal of the EU on **12 July 2024** and entered into force on **1 August 2024**. The Act has 113 Articles organized into 13 Chapters, plus 13 Annexes.

## Risk Classification Tiers

The Act defines **four risk tiers**:

### Tier 1 — Unacceptable Risk (Prohibited, Article 5)

Banned outright since February 2, 2025. Fines up to €35M or 7% of global turnover.

### Tier 2 — High Risk (Annex I and Annex III, Articles 6–51)

Subject to full compliance requirements before market placement. Two tracks:
- **Annex I**: AI embedded in regulated products (medical devices, machinery, vehicles) — follow existing sector conformity procedures
- **Annex III**: Standalone AI systems across 8 domains

### Tier 3 — Limited Risk (Article 50)

Transparency obligations only — must disclose that the user is interacting with AI. Applies to chatbots, deepfakes, emotion recognition (in non-banned contexts), AI-generated content.

### Tier 4 — Minimal Risk

No mandatory requirements. Encouraged to follow voluntary codes of conduct. Covers spam filters, recommendation systems, AI-enabled video games.

## Prohibited AI Practices (Article 5)

Eight categories are banned (enforceable since February 2, 2025):

1. **Subliminal/manipulative techniques** — AI using methods "beyond a person's consciousness" to distort behavior causing significant harm

2. **Exploitation of vulnerabilities** — Targeting age, disability, or socioeconomic status to materially distort behavior

3. **Social scoring systems** — Evaluating/classifying people by social behavior or personality traits when scores lead to unjustified detrimental treatment

4. **Predictive criminal risk assessment** — Systems predicting offenses "based solely on profiling," with no factual link to criminal activity (exception: human-assessment support based on objective facts is permitted)

5. **Untargeted facial image scraping** — AI creating databases from internet or CCTV facial images without targeting

6. **Emotion inference** — Inferring emotions in workplaces or educational institutions (exception: medical or safety-certified systems)

7. **Biometric categorization** — Inferring race, political opinions, religion, sexual orientation, or union membership from biometrics (exception: filtering lawfully acquired datasets)

8. **Real-time biometric identification (law enforcement)** — Use in public spaces, with narrow exceptions:
   - Searching trafficking/missing persons victims
   - Preventing imminent terrorism threats
   - Locating suspects for crimes carrying 4+ year sentences
   - Requires prior judicial/administrative authorization plus annual reporting

**Digital Omnibus addition (2025):** A new prohibition banning AI that generates or manipulates intimate imagery without consent (including CSAM), applying from December 2, 2026.

## High-Risk AI Systems — Annex III Categories

Eight domains with specific use cases:

| Domain | Examples |
|--------|----------|
| **1. Biometrics** | Remote biometric ID systems; biometric categorization; emotion recognition |
| **2. Critical Infrastructure** | Safety components in energy grids, water systems, road traffic, digital infrastructure |
| **3. Education & Vocational Training** | Admission decisions; test scoring; behavioral monitoring during exams; educational level assessment |
| **4. Employment & Worker Management** | CV screening/recruitment; performance monitoring; promotion/termination decisions |
| **5. Essential Services & Benefits** | Public assistance eligibility; creditworthiness evaluation; health/life insurance risk assessment; emergency call dispatch |
| **6. Law Enforcement** | Victimization/offending risk assessment; polygraph-equivalents; evidence reliability; criminal profiling |
| **7. Migration, Asylum & Border Control** | Security/health risk assessment at borders; asylum examination assistance; biometric ID at entry points |
| **8. Administration of Justice & Democratic Processes** | Judicial decision assistance; systems influencing election or referendum outcomes |

**Important carve-out**: Systems on Annex III are NOT high-risk if they "do not pose a significant risk of harm to individuals' health, safety or fundamental rights, including by not materially influencing the outcome of decision-making."

## High-Risk AI System Requirements (Articles 9–15)

### For Providers

| Article | Requirement |
|---------|-------------|
| **Article 9 — Risk Management System** | Continuous, iterative process throughout the lifecycle; identify/analyze/evaluate known and reasonably foreseeable risks; test effectiveness of risk mitigation measures |
| **Article 10 — Data Governance** | Training, validation, and testing datasets must be relevant, representative, and free from errors; address biases; appropriate data collection practices |
| **Article 11 — Technical Documentation** | Before market placement; demonstrate compliance with requirements; content specified in Annex IV |
| **Article 12 — Record-Keeping** | Automatic logging of events throughout the system lifecycle; logs retained for at least 6 months |
| **Article 13 — Transparency to Deployers** | Provide instructions for use including intended purpose, performance levels, limitations, human oversight measures, maintenance requirements |
| **Article 14 — Human Oversight** | Design must allow natural persons to effectively oversee the system; ability to interrupt, override, or shut down |
| **Article 15 — Accuracy, Robustness, and Cybersecurity** | Achieve appropriate accuracy levels; resilience to errors; protection against adversarial attacks |

### For Deployers

- Implement human oversight per provider instructions
- Monitor actual use against intended purpose
- Maintain logs generated by the system
- Inform and train staff who operate the system
- Notify providers and authorities if serious risks emerge
- Conduct fundamental rights impact assessments (public sector deployers)

### Conformity Assessment (Article 43)

- **Annex III point 1 (biometrics)**: Choose between internal control OR third-party notified body review
- **Annex III points 2–8**: Internal control conformity assessment (no notified body required)
- **Annex I systems**: Follow relevant product-specific EU legislation (notified bodies typically required)
- Must register in the EU AI database before deployment

## Transparency Obligations (Article 50, GPAI Articles 53–55)

### Limited-Risk Transparency (Article 50)

Applies from August 2, 2026 (extended by Digital Omnibus to December 2, 2026 for pre-August 2026 systems):

- **Chatbots**: Inform users they are interacting with AI
- **Deepfakes/synthetic content**: Label content as AI-generated
- **AI-generated text about public interest matters**: Label as AI-generated
- **Emotion recognition or biometric categorization**: Notify affected persons

### GPAI Model Obligations (Chapter V, Articles 53–55)

In force August 2, 2025. All GPAI providers must:

- Prepare and maintain technical documentation (Annex XI format)
- Publish a summary of training data content (Annex XII)
- Comply with EU copyright law (honor opt-outs under the text and data mining exception)
- Share information with downstream providers to enable their compliance
- Register models in the EU database

### Systemic-Risk GPAI Models

Those trained with >10²⁵ FLOPs, as notified to AI Office or designated by Commission:

- Notify the European Commission
- Conduct adversarial testing (red-teaming)
- Assess and mitigate systemic risks
- Track, document, and report serious incidents
- Implement enhanced cybersecurity measures

The **GPAI Code of Practice** (final version: July 10, 2025) is a voluntary compliance mechanism covering three chapters: Transparency, Copyright, and Safety & Security.

## AI Literacy (Article 4)

In force since February 2, 2025; enforcement begins August 2, 2026. Applies to all providers and deployers regardless of risk tier. No minimum certification standard; proportionate approach based on role and risk. Requires documenting what training was undertaken.

## Governance Structure

### EU Level

| Body | Role |
|------|------|
| **AI Office** | Core implementation node; supervises GPAI models; investigates infringements; develops guidance |
| **European AI Board** | Representatives from all Member States; advises on consistent application |
| **Scientific Panel** | Independent AI experts; advises on GPAI systemic risks |
| **Advisory Forum** | Multi-stakeholder body representing industry, civil society, academia |

### National Level

- **Notifying Authorities**: Designate and supervise notified bodies
- **Market Surveillance Authorities (MSAs)**: Enforce compliance for non-GPAI AI systems

### Enforcement Split

- **National MSAs**: Prohibited practices, high-risk AI, limited-risk transparency (for non-GPAI)
- **AI Office/European Commission**: GPAI model obligations and systemic risk

## Penalties (Article 99)

Three-tier penalty structure (enforceable as of August 2, 2025 for GPAI; August 2, 2026 for most other provisions):

| Violation | Maximum Fine |
|-----------|-------------|
| Prohibited AI practices (Article 5) | €35M or 7% of global annual turnover |
| Non-compliance with high-risk/GPAI obligations | €15M or 3% of global annual turnover |
| Supplying incorrect/incomplete information | €7.5M or 1% of global annual turnover |

For SMEs and startups, the lower of the two amounts applies.

## Implementation Timeline (Updated with Digital Omnibus)

| Date | Provisions Taking Effect |
|------|--------------------------|
| **Aug 1, 2024** | Act enters into force; no requirements apply yet |
| **Feb 2, 2025** | Article 5 prohibitions + Article 4 AI literacy obligation |
| **May 2, 2025** | GPAI Code of Practice finalized |
| **Aug 2, 2025** | GPAI model obligations (Ch. V); governance bodies operational; penalty framework active |
| **Dec 2, 2026** | Article 50 transparency for systems placed before Aug 2, 2026 (Digital Omnibus extension) |
| **Aug 2, 2026** | Most remaining provisions; Article 50 for new systems; AI sandboxes operational |
| **Dec 2, 2027** | Annex III standalone high-risk system obligations (extended by Digital Omnibus) |
| **Aug 2, 2028** | Annex I embedded high-risk system obligations (extended by Digital Omnibus) |
| **Dec 31, 2030** | Large-scale EU IT systems (Eurodac, SIS, VIS, etc.) must comply |
| **2028–2031** | Commission biennial/quadrennial review cycles |

## Additional Resources

| Resource | URL |
|----------|-----|
| EUR-Lex Official Text | https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng |
| AI Act Explorer | https://artificialintelligenceact.eu/ai-act-explorer/ |
| AI Act Service Desk | https://ai-act-service-desk.ec.europa.eu/en |
| Article 5: Prohibited Practices | https://artificialintelligenceact.eu/article/5/ |
| Annex III: High-Risk Systems | https://artificialintelligenceact.eu/annex/3/ |
| Article 99: Penalties | https://artificialintelligenceact.eu/article/99/ |
| Implementation Timeline | https://artificialintelligenceact.eu/implementation-timeline/ |
| GPAI Code of Practice | https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai |
| Digital Omnibus Breakdown (Gibson Dunn) | https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/ |

---

*Research compiled: June 2026*
*Sources: Web research via Claude Code web-search-researcher agent*
