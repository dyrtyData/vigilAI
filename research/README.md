# vigilAI Research Documentation

Research documentation for the Brazil AI Act Compliance Scraper Tool, compiled for the Global South AI Safety Hackathon.

## Documents

### Primary Research

| Document | Description |
|----------|-------------|
| [brazil-ai-bill-pl-2338-2023.md](./brazil-ai-bill-pl-2338-2023.md) | Comprehensive analysis of Brazil's AI Bill PL 2.338/2023 including risk tiers, human rights chapter, penalties, and compliance framework |
| [eu-ai-act-regulation-2024-1689.md](./eu-ai-act-regulation-2024-1689.md) | Full analysis of EU AI Act including prohibited practices, high-risk requirements, GPAI obligations, and implementation timeline |
| [compl-ai-framework.md](./compl-ai-framework.md) | ETH Zurich/INSAIT/LatticeFlow AI's open-source compliance evaluation framework for LLMs |
| [brazil-vs-eu-ai-act-comparison.md](./brazil-vs-eu-ai-act-comparison.md) | Detailed side-by-side comparison of both regulations with implications for vigilAI |

## Key Findings

### Brazil PL 2338/2023 Unique Features

1. **Standalone Human Rights Chapter** — Article 5 codifies 6 rights: prior information, explanation, contestation, human intervention, non-discrimination, privacy
2. **Inter-American Court Jurisdiction** — State AI deployments can be challenged at the Inter-American Court of Human Rights
3. **Strict Liability** — Providers/operators liable for high-risk AI damages regardless of fault
4. **3-Tier Risk System** — Excessive (prohibited), High (regulated), Non-high (baseline)

### COMPL-AI Adaptation Strategy

1. Fork COMPL-AI as base evaluation framework
2. Map 29+ benchmarks to Brazil's 6 rights categories
3. Add Brazil-specific metrics for explanation quality, human intervention accessibility
4. Swap EU AI Act article references to PL 2338/2023 articles
5. Create Brazil compliance report template

### Current Status

- **EU AI Act**: In force (phased from August 2024)
- **Brazil PL 2338/2023**: Senate-approved December 2024, pending Chamber of Deputies vote

## External Resources

### Official Sources

- [Brazil Bill Text (Portuguese)](https://clairk.digitalpolicyalert.org/documents/brazil-bill-on-the-use-of-artificial-intelligence-2338-2023-original-language/raw)
- [EU AI Act Official Text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng)
- [COMPL-AI GitHub](https://github.com/compl-ai/compl-ai)

### Analysis

- [Data Privacy Brasil Technical Analysis](https://www.dataprivacybr.org/en/the-artificial-intelligence-legislation-in-brazil-technical-analysis-of-the-text-to-be-voted-on-in-the-federal-senate-plenary/)
- [AI Act Explorer](https://artificialintelligenceact.eu/the-act/)

---

*Research compiled: June 2026*
*Global South AI Safety Hackathon - Latam Governance Track*
