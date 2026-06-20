# Brazil PL 2338/2023 vs EU AI Act - Detailed Comparison

## Executive Summary

Brazil's AI Bill mirrors the EU AI Act's risk-based approach but distinguishes itself through:
1. A standalone human rights chapter anchored in the Inter-American Human Rights System
2. Strict liability for AI-caused damages (not fault-based)
3. A subject/population-centered risk model rather than purely use-case-based
4. Lower penalty ceilings but with strict liability exposure

## Side-by-Side Comparison

| Dimension | EU AI Act | Brazil PL 2338/2023 |
|-----------|-----------|---------------------|
| **Status** | In force (phased from August 2024) | Senate-approved; Chamber pending |
| **Risk tiers** | 4 (unacceptable, high, limited, minimal) | 3 (excessive/prohibited, high, non-high) |
| **Risk model basis** | Primarily use-case/application | Subject/affected population centered |
| **Human rights anchor** | EU Charter of Fundamental Rights | American Convention on Human Rights + Inter-American Court jurisdiction |
| **Rights chapter structure** | Rights obligations spread across provisions | Standalone dedicated chapter (Article 5 / Chapter IV) as "backbone" |
| **Strict liability** | No (fault-based product liability framework) | Yes — strict liability for high-risk AI damages |
| **Social scoring prohibition** | Covers both public and private sector | Covers public authorities only |
| **Max penalty** | €35M or 7% global turnover | R$50M or 2% Brazilian revenue |
| **General purpose AI** | Explicit GPAI model obligations (Title V) | Technology-neutral; no "foundation model" definition |
| **Enforcement body** | EU AI Office + national market surveillance | ANPD (coordinating) + sectoral regulators |
| **Biometric ID** | Permitted with exceptions; carve-outs by member state | Restricted to specific serious crimes with judicial authorization |
| **Model size thresholds** | Explicitly regulated (10²⁵ FLOPs threshold) | Not addressed |
| **Conformity assessment** | Detailed Article 43 procedure + CE marking + EU database | Less prescriptive; future regulations will detail |
| **Extraterritorial reach** | Any AI affecting EU residents | Systems "deployed in Brazil" or affecting Brazilian residents |

## Risk Classification Comparison

### EU AI Act (4 Tiers)

| Tier | Description | Examples |
|------|-------------|----------|
| **Unacceptable** | Completely prohibited | Social scoring, subliminal manipulation, untargeted biometric scraping |
| **High** | Full compliance requirements | Biometrics, critical infrastructure, employment, education, law enforcement |
| **Limited** | Transparency only | Chatbots, deepfakes, emotion recognition |
| **Minimal** | Voluntary codes | Spam filters, recommendation systems, games |

### Brazil PL 2338/2023 (3 Tiers)

| Tier | Description | Examples |
|------|-------------|----------|
| **Excessive** | Completely prohibited | Subliminal manipulation, vulnerability exploitation, public social scoring, real-time biometric ID (with exceptions) |
| **High** | Strict regulation + AIA required | 14 enumerated categories including credit, employment, healthcare, judicial |
| **Non-High/Non-Excessive** | Baseline transparency + bias prevention | All other AI systems |

**Key difference**: Brazil lacks EU's "Limited Risk" tier — there's no middle category for transparency-only obligations.

## Prohibited Practices Comparison

| Practice | EU AI Act | Brazil PL 2338/2023 |
|----------|-----------|---------------------|
| Subliminal manipulation | ✅ Prohibited | ✅ Prohibited |
| Exploitation of vulnerabilities | ✅ Prohibited | ✅ Prohibited |
| Social scoring (public) | ✅ Prohibited | ✅ Prohibited |
| Social scoring (private) | ✅ Prohibited | ❌ Not explicitly prohibited |
| Predictive criminal risk (profiling only) | ✅ Prohibited | ⚠️ Covered under high-risk with restrictions |
| Untargeted facial scraping | ✅ Prohibited | ⚠️ Not explicitly addressed |
| Workplace emotion inference | ✅ Prohibited | ⚠️ Not explicitly addressed |
| Real-time biometric ID (law enforcement) | ⚠️ Restricted with exceptions | ⚠️ Restricted with exceptions (narrower) |
| Non-consensual intimate imagery | ✅ Prohibited (Digital Omnibus 2025) | ❌ Not explicitly addressed |

## High-Risk Categories Comparison

### Categories in Both

| Category | EU AI Act | Brazil PL 2338/2023 |
|----------|-----------|---------------------|
| Critical infrastructure | ✅ Annex III(2) | ✅ Category 1 |
| Education/vocational training | ✅ Annex III(3) | ✅ Category 2 |
| Employment decisions | ✅ Annex III(4) | ✅ Category 3 |
| Essential services access | ✅ Annex III(5) | ✅ Category 4 |
| Credit/lending | ✅ Annex III(5)(a) | ✅ Category 5 |
| Emergency dispatch | ✅ Annex III(5)(d) | ✅ Category 6 |
| Law enforcement | ✅ Annex III(6) | ✅ Categories 11-13 |
| Migration/border | ✅ Annex III(7) | ✅ Category 14 |
| Judicial assistance | ✅ Annex III(8) | ✅ Category 7 |
| Biometrics | ✅ Annex III(1) | ✅ Category 10 |

### Brazil-Specific High-Risk Categories

| Category | Brazil PL 2338/2023 | EU AI Act Equivalent |
|----------|---------------------|----------------------|
| Autonomous vehicles | ✅ Category 8 | ⚠️ Covered under product safety (Annex I) |
| Medical applications/diagnosis | ✅ Category 9 | ⚠️ Covered under medical devices (Annex I) |

## Rights Framework Comparison

### EU AI Act Rights (Distributed)

Rights are procedural obligations on providers/deployers:
- Right to information (Article 50)
- Right to explanation (via deployer instructions, Article 13)
- Right to complain to market surveillance authorities

**Enforcement**: National data protection authorities, market surveillance authorities

### Brazil PL 2338/2023 Rights (Dedicated Chapter)

Six codified rights in Article 5:

1. **Right to prior information** — Notice of AI interaction
2. **Right to explanation** — Demand system logic disclosure
3. **Right to contestation** — Challenge automated decisions
4. **Right to human intervention** — Request human review
5. **Right to non-discrimination** — Protection from bias
6. **Right to privacy** — LGPD compliance

**Enforcement**: ANPD + sectoral regulators + **Inter-American Court of Human Rights** (for State deployments)

### Critical Difference: International Enforcement

Brazil's bill cross-references the **American Convention on Human Rights** (ACHR). State AI deployments violating these rights create litigation exposure through the **Inter-American Court of Human Rights** — a supranational enforcement pathway with no EU equivalent.

The EU AI Act anchors rights in the EU Charter of Fundamental Rights, which operates within EU institutional structures only.

## Liability Comparison

| Aspect | EU AI Act | Brazil PL 2338/2023 |
|--------|-----------|---------------------|
| **Liability type** | Fault-based (product liability directive) | **Strict liability** |
| **Burden of proof** | Plaintiff must establish defect/fault | Provider/operator liable regardless of fault |
| **Defenses** | Defect defense, development risk, etc. | Only: exclusive victim fault, exclusive third-party fault, force majeure |
| **Consumer protection** | GDPR + product liability | Consumer Defense Code applies |

**Implication for compliance tools**: Brazil's strict liability means compliance failures carry higher legal risk even without proven fault.

## Governance Comparison

### EU Structure

```
EU Level:
├── AI Office (supervises GPAI)
├── European AI Board (coordinates)
├── Scientific Panel (advises)
└── Advisory Forum (stakeholders)

National Level:
├── Notifying Authorities
└── Market Surveillance Authorities
```

### Brazil Structure

```
National System (SIA):
├── ANPD (primary coordinator)
├── Sectoral Regulators (ANATEL, ANVISA, ANAC, etc.)
├── CRIA (Regulatory Cooperation Council)
└── CECIA (Expert/Scientist Committee)
```

**Key difference**: Brazil uses existing data protection authority (ANPD) as coordinator; EU created new AI Office.

## Compliance Requirements Comparison

### High-Risk AI Pre-Deployment

| Requirement | EU AI Act | Brazil PL 2338/2023 |
|-------------|-----------|---------------------|
| Risk management system | ✅ Article 9 | ✅ Implicit in AIA |
| Data governance | ✅ Article 10 | ✅ Via LGPD alignment |
| Technical documentation | ✅ Article 11 (Annex IV) | ⚠️ Less prescriptive |
| Record-keeping/logging | ✅ Article 12 (6 months) | ✅ Required |
| Instructions for use | ✅ Article 13 | ⚠️ Less prescriptive |
| Human oversight design | ✅ Article 14 | ✅ Required |
| Accuracy/robustness | ✅ Article 15 | ✅ Required |
| Impact assessment | ⚠️ Fundamental rights (deployers) | ✅ **Algorithmic Impact Assessment** (providers) |
| Conformity assessment | ✅ Detailed (Article 43) | ⚠️ Delegated to future regulation |
| Database registration | ✅ EU database | ✅ Public database (TBD) |

### Key Difference: Algorithmic Impact Assessment

Brazil requires **providers** to conduct comprehensive AIAs covering fundamental rights impacts. EU requires deployers to conduct fundamental rights impact assessments, but provider obligations focus on technical conformity.

## Penalty Comparison

| Violation Type | EU AI Act | Brazil PL 2338/2023 |
|----------------|-----------|---------------------|
| Prohibited practices | €35M / 7% global | R$50M / 2% Brazilian |
| High-risk non-compliance | €15M / 3% global | R$50M / 2% Brazilian |
| Information violations | €7.5M / 1% global | Same as above |
| Additional sanctions | - | Sandbox ban (5 years), operation suspension |

**Note**: Brazil's percentage cap (2%) is lower than EU's (up to 7%), but applies to Brazilian revenue specifically, not global turnover.

## GPAI/Foundation Model Comparison

| Aspect | EU AI Act | Brazil PL 2338/2023 |
|--------|-----------|---------------------|
| Definition | Explicit GPAI definition | Technology-neutral (no definition) |
| Model size threshold | 10²⁵ FLOPs = systemic risk | Not addressed |
| Transparency | Training data summaries required | Copyright disclosure required |
| Systemic risk | Additional obligations | N/A |
| Red-teaming | Required for systemic risk | N/A |

**Implication**: EU has specific rules for large foundation models; Brazil regulates by use-case impact regardless of model architecture.

## Implementation Timeline Comparison

| Phase | EU AI Act | Brazil PL 2338/2023 |
|-------|-----------|---------------------|
| Prohibitions | Feb 2, 2025 ✅ | 180 days after enactment |
| GPAI obligations | Aug 2, 2025 ✅ | N/A |
| Most provisions | Aug 2, 2026 | 2 years after enactment |
| High-risk (standalone) | Dec 2, 2027 | 2 years after enactment |
| High-risk (embedded) | Aug 2, 2028 | 2 years after enactment |

**Status**: EU is in active enforcement. Brazil has no effective date yet (pending Chamber vote and presidential sanction).

## Implications for vigilAI Compliance Tool

### Mappable Elements

1. **Risk tiers** — Can adapt EU's 4-tier to Brazil's 3-tier
2. **High-risk categories** — 14 categories map well to Annex III
3. **Transparency requirements** — Similar in principle
4. **Bias/fairness** — Both emphasize non-discrimination

### Brazil-Specific Elements to Add

1. **Rights compliance checker** — Dedicated module for Article 5's 6 rights
2. **Strict liability exposure assessment** — Higher stakes than EU
3. **AIA template** — Different from EU conformity assessment
4. **LGPD alignment verification** — Brazil's data protection law specifics
5. **Inter-American human rights reference** — For government deployments

### Elements to Remove/Modify from COMPL-AI

1. **GPAI-specific metrics** — Brazil doesn't define foundation models
2. **CE marking references** — Brazil has no equivalent
3. **Notified body references** — Brazil uses different conformity approach
4. **10²⁵ FLOPs threshold** — Not applicable

---

*Comparison compiled: June 2026*
*Sources: Web research via Claude Code web-search-researcher agents*
