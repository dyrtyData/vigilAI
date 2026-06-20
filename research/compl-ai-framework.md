# COMPL-AI Framework - ETH Zurich / INSAIT / LatticeFlow AI

## Overview

COMPL-AI is an open-source framework that translates the EU AI Act's regulatory language into measurable technical requirements for LLMs, then provides a benchmarking suite to test them. Published October 2024 by ETH Zurich, INSAIT, and LatticeFlow AI. Built on the [Inspect](https://inspect.ai/) evaluation framework.

## Key Resources

| Resource | URL |
|----------|-----|
| GitHub Repository | https://github.com/compl-ai/compl-ai |
| INSAIT Announcement | https://insait.ai/compl-ai/ |
| arXiv Paper | https://arxiv.org/abs/2410.07959 |
| Public Leaderboard | https://compl-ai.org |
| MLOps Community Blog | https://home.mlops.community/public/blogs/evaluate-your-llm-for-technical-compliance-with-compl-ai |

## Six EU AI Act Principles Covered

Each principle maps to multiple technical requirements (18 total):

1. **Human Agency and Oversight** — Can humans effectively supervise/override the model?
2. **Technical Robustness and Safety** — Resistance to adversarial inputs, consistency
3. **Privacy and Data Governance** — Avoiding privacy-violating outputs
4. **Transparency** — Disclosing AI nature, calibrated confidence
5. **Diversity, Non-Discrimination, and Fairness** — Avoiding demographic bias
6. **Societal and Environmental Well-being** — Avoiding harmful, toxic, or democratic-process-undermining outputs

## Benchmarks Used (29+ total)

| Category | Benchmarks | What They Measure |
|----------|------------|-------------------|
| **Capabilities** | MMLU Pro, SWE Bench, AIME 2025 | General reasoning, coding, math |
| **Robustness** | MMLU contrast sets, BoolQ contrast sets | Stability under input perturbations |
| **Non-discrimination/Fairness** | BBQ, BOLD, RedditBias, CAB | Demographic bias in outputs |
| **Harmful content** | RealToxicityPrompts, AdvBench | Toxic/harmful generation rates |
| **Transparency/Calibration** | Logit calibration benchmarks, self-check consistency | Confidence alignment, AI-identity disclosure |
| **Interpretability** | Multiple-choice reasoning tasks | Reasoning transparency |
| **Cybersecurity** | Cyberattack resilience benchmarks | Resistance to misuse for attacks |
| **Privacy** | Privacy-violating output detection | PII/sensitive data exposure |

## Models Evaluated

12 prominent LLMs from OpenAI, Meta, Google, Anthropic, and Alibaba at launch. Leaderboard on HuggingFace maintained with ongoing evaluations.

**Notable finding**: DeepSeek models showed critical compliance gaps in cybersecurity and fairness.

## Key Findings from Initial Evaluation

- Models scored ~50% on cybersecurity and fairness benchmarks
- Harmful content/toxicity: generally strong (models already optimized here)
- Copyright protection and user privacy: hardest to benchmark reliably
- No model achieved full compliance across all 6 principles

## How to Use

```bash
# Install
pip install compl-ai

# Authenticate with HuggingFace (if needed)
huggingface-cli login

# Run evaluation
complai eval openai/gpt-4o-mini -t mmlu_pro -l 5

# Results → JSON → upload to compl-ai.org for full compliance report
```

**Supported providers**: OpenAI, Anthropic, HuggingFace Hub, vLLM

Results are displayed sample-by-sample via Inspect AI VS Code extension.

## Relevance to vigilAI / Brazil PL 2338/2023

### Direct Applicability

COMPL-AI's framework is built for the EU AI Act, which Brazil's PL 2338/2023 heavily mirrors. The six principles map well to Brazil's requirements:

| COMPL-AI Principle | Brazil PL 2338/2023 Equivalent |
|-------------------|-------------------------------|
| Human Agency and Oversight | Right to human intervention, Right to contestation |
| Technical Robustness and Safety | High-risk system requirements |
| Privacy and Data Governance | LGPD alignment requirement |
| Transparency | Right to explanation, Right to prior information |
| Diversity, Non-Discrimination, and Fairness | Right to non-discrimination |
| Societal and Environmental Well-being | Algorithmic Impact Assessment requirements |

### Adaptations Needed for Brazil

1. **Rights-focused metrics**: Brazil's bill emphasizes individual rights more than EU. May need additional benchmarks for:
   - Explanation quality (not just calibration)
   - Contestation pathway clarity
   - Human intervention accessibility

2. **Inter-American Human Rights alignment**: Brazil's unique cross-reference to ACHR may require additional evaluation criteria

3. **Strict liability considerations**: Brazil's strict liability regime means compliance failures have different legal weight

4. **LGPD-specific privacy tests**: While GDPR-aligned, LGPD has some differences worth capturing

### Recommended Approach

1. **Fork COMPL-AI** as the base evaluation framework
2. **Map benchmarks** to Brazil's 6 rights categories (Article 5)
3. **Add Brazil-specific metrics** for:
   - Explanation completeness (per Right to Explanation requirements)
   - Human intervention pathway testing
   - LGPD compliance checks
4. **Swap legal text references** from EU AI Act articles to PL 2338/2023 articles
5. **Create Brazil compliance report template** reflecting the bill's structure

## Technical Architecture

COMPL-AI uses a modular architecture:

```
compl-ai/
├── benchmarks/          # Evaluation datasets
├── metrics/             # Compliance metric definitions
├── evaluators/          # Model evaluation runners
├── reports/             # Report generation
└── inspect_ai/          # Integration with Inspect framework
```

The 18 technical requirements are mapped to specific benchmarks in the codebase. The full mapping table is in the arXiv paper and as code in the repository.

---

*Research compiled: June 2026*
*Sources: Web research via Claude Code web-search-researcher agent*
