---
date: 2026-06-20T12:45:00-04:00
last_updated: 2026-06-20T13:30:00-04:00
last_updated_by: Claude
last_updated_note: "Added complementary Brazilian legislation, Brazil-specific demographic attributes, and resolved open questions per team feedback"
git_commit: 99680776e0f7a7c458dd73aac93cf28f7ba3ed32
branch: main
repository: dyrtyData/GS_AISafetyHackathon
topic: "COMPL-AI Framework Architecture and Brazil PL 2338/2023 Mapping"
type: research
tags: [research, compl-ai, brazil-ai-bill, pl-2338-2023, eu-ai-act, compliance, benchmarking, lgpd, ibge]
status: complete
---

# Research: COMPL-AI Framework Architecture and Brazil PL 2338/2023 Mapping

**Date**: 2026-06-20T12:45:00-04:00
**Git Commit**: 99680776e0f7a7c458dd73aac93cf28f7ba3ed32
**Branch**: main
**Repository**: dyrtyData/GS_AISafetyHackathon

## Research Questions

1. In the compl-ai/compl-ai repository, how is the evaluation pipeline structured? What are the key modules (benchmarks/, metrics/, evaluators/, reports/), their entry points, and how do they interact to produce a compliance report from model evaluation to final output?

2. How does COMPL-AI map its 18 technical requirements to specific benchmarks? Where is this mapping defined in the codebase, and what is the data structure that links EU AI Act principles to individual evaluation tasks?

3. What configuration system does COMPL-AI use (YAML, JSON, Python configs)? How are new benchmarks added, and what interfaces must a custom benchmark implement to integrate with the Inspect AI evaluation framework?

4. What are the exact article numbers and chapter structure of Brazil's PL 2338/2023 that define the six rights categories in Article 5 (right to prior information, explanation, contestation, human intervention, non-discrimination, privacy)? How do these map structurally to the EU AI Act's corresponding provisions?

5. How does Brazil's Algorithmic Impact Assessment (AIA) requirement differ from the EU AI Act's conformity assessment in terms of required documentation, who must conduct it, when it must be performed, and what must be made public?

6. In COMPL-AI's existing benchmarks for fairness and non-discrimination (BBQ, BOLD, RedditBias, CAB), what specific harm categories and demographic attributes are tested? How would Brazilian-specific bias categories (e.g., regional, socioeconomic, racial categories per Brazilian census definitions) map to or extend these?

7. What transparency and explainability benchmarks does COMPL-AI currently implement, and how do they measure concepts like "explanation quality" or "calibrated confidence" that would need to be adapted to Brazil's more rights-focused "Right to Explanation" requirements?

## Research Methodology (verbatim)

This document will remain objective and factual. It does not contain any recommendations or implementation suggestions.
Open questions will not ask Why things haven't been built or what should be built in the future.

There is no "implementation" section - that is intentional.

## Summary

COMPL-AI (v2.0.0) is a compliance-focused LLM evaluation framework built on the UK AISI's Inspect AI framework. It maps EU AI Act principles through a layered hierarchy: **EU AI Act Principles → Technical Requirements → Benchmark Tasks**. The codebase uses Python `@task` decorator attributes as the core mapping mechanism, with 9 technical requirement categories mapped to 30 individual benchmark tasks. There is no separate `benchmarks/`, `metrics/`, `evaluators/`, or `reports/` directory structure—everything lives under `src/complai/tasks/<task_name>/`.

Brazil's PL 2338/2023 structures its rights provisions in **Chapter II ("Dos Direitos")**, splitting them across two articles: **Article 5** covers three rights applicable to all AI systems (information, privacy, non-discrimination), while **Article 6** covers three additional rights for high-risk systems only (explanation, contestation, human review). This differs structurally from the EU AI Act, which distributes rights provisions across multiple chapters tied to deployer/provider obligations. Brazil's Algorithmic Impact Assessment (AIA), defined in **Articles 25-28**, is a fundamental-rights-focused instrument distinct from the EU's market-conformity-focused assessment, requiring public disclosure of conclusions and allowing joint preparation with LGPD Data Protection Impact Reports.

COMPL-AI's fairness benchmarks (BBQ, BOLD, RedditBias, CAB, DecodingTrust, FairLLM) cover demographic attributes including gender, race, religion, age, disability, and socioeconomic status—but use US-centric taxonomy that does not capture Brazil's IBGE racial categories (branco, pardo, preto, amarelo, indígena), regional biases (Northeast vs. Southeast), or Portuguese-language contexts. For transparency, COMPL-AI implements calibration benchmarks (TriviaQA, BIG-Bench) and AI disclosure tests (`human_deception`), but explicitly acknowledges that **explainability cannot currently be benchmarked** with available tools—a critical gap given Brazil's LGPD Article 20 right to explanation.

## Detailed Findings

### 1. COMPL-AI Pipeline Architecture

COMPL-AI is a thin wrapper over the Inspect AI evaluation framework. The pipeline flows from CLI invocation through task discovery, instantiation, parallel execution, and log output.

```mermaid
flowchart TD
    CLI[complai CLI] --> TD[Task Discovery]
    TD --> TI[Task Instantiation]
    TI --> ES[eval_set - Inspect AI]
    ES --> LO[Log Output .eval/.json]
    LO --> IV[inspect view]
    
    subgraph "Task Registry"
        REG[_registry.py imports 30 tasks]
        REG --> T1[mmlu_pro]
        REG --> T2[bbq]
        REG --> T3[bold]
        REG --> TN[...30 total]
    end
```

**Entry Point:** The `complai` CLI (`src/complai/_cli/__init__.py`) defines a Typer app with two commands: `eval` and `list`.

**Eval Command Flow** (`src/complai/_cli/eval.py`):
1. `get_task_infos()` queries the Inspect AI task registry for `TaskInfo` objects, filtered by name or `technical_requirement` attribute
2. `parse_task_args()` merges YAML/JSON config with CLI `-T` overrides
3. `instantiate_tasks_from_infos()` calls `load_task_spec()` on each task to produce Inspect AI `Task` objects
4. `eval_set()` (Inspect AI's parallel task runner) handles execution, logging, retries, and result aggregation
5. Results are written to `./logs/<model>_<timestamp>/` and viewable via `inspect view` or VS Code extension

**Task Discovery:** Uses Inspect AI's `list_tasks()` function. The `[project.entry-points.inspect_ai]` section in `pyproject.toml` registers COMPL-AI as an Inspect AI plugin: `complai = "complai._registry"`, which imports all 30 task modules.

#### Testing patterns

No test files were observed in the COMPL-AI repository structure analysis. The `Makefile` contains a `make test` target, but test coverage details were not documented in the analyzed sources.

### 2. Requirements-to-Benchmarks Mapping

The mapping is implemented as a **Python decorator attribute** on every task function, not as a separate config file or data structure.

**Mechanism:** Inspect AI's `@task(...)` decorator accepts arbitrary keyword arguments that become `TaskInfo.attribs`. COMPL-AI passes `technical_requirement="<name>"` to every task decorator.

**Complete Mapping (v2.0.0):**

| Technical Requirement | Benchmarks |
|---|---|
| Capabilities, Performance, and Limitations | `aime_2025`, `arc_challenge`, `gpqa_diamond`, `hle`, `ifbench`, `include`, `livebench_coding`, `mmlu_pro`, `mmmu_pro`, `swe_bench_verified` |
| Representation — Absence of Bias | `bbq`, `bold`, `cab` |
| Interpretability | `bigbench_calibration`, `triviaqa_calibration` |
| Robustness and Predictability | `boolq_contrast`, `forecast_consistency`, `imdb_contrast`, `mmlu_pro_robustness`, `self_check_consistency` |
| Fairness — Absence of Discrimination | `decoding_trust`, `fairllm` |
| Disclosure of AI | `human_deception` |
| Cyberattack Resilience | `instruction_goal_hijacking`, `llm_rules`, `strong_reject` |
| Societal Alignment | `mask`, `simpleqa_verified`, `truthfulqa` |
| Harmful Content and Toxicity | `realtoxicityprompts` |

**Note:** The original October 2024 arXiv paper described 18 technical requirements derived from 6 EU AI Act principles. The current v2 codebase implements 9 `technical_requirement` strings. This appears to be a consolidation during the Inspect AI rebuild.

**Example task decorator:**
```python
# src/complai/tasks/bbq/bbq.py
@task(technical_requirement="Representation — Absence of Bias")
def bbq(num_fewshot: int = 0) -> Task:
    return Task(
        dataset=bbq_dataset(),
        solver=[system_message(...), generate()],
        scorer=bbq_scorer(),
    )
```

#### Testing patterns

Testing of the mapping is implicit through Inspect AI's task registry mechanism. No dedicated unit tests for the mapping structure were identified.

### 3. Configuration System

**Config Format:** YAML (primary) or JSON (also accepted)

**Configuration File:** `config/default_config.yaml`
- Auto-generated by `tools/generate_default_config.py` using Python AST parsing to extract function default values
- Regenerated via `make default-config`
- Structure: flat mapping of `task_name: {param: value}`

**Configuration Flow:**
1. `--task-config default_config.yaml` loads YAML via Inspect AI's `resolve_args()`
2. CLI overrides `-T mmlu_pro:num_fewshot=5` take precedence (parsed as `yaml.safe_load()`)
3. Model args (`-M device=cuda:0`), generate config (`-G temperature=0.5`) have separate patterns
4. Environment variables (`COMPLAI_MODEL`, `COMPLAI_TASKS`, `COMPLAI_LOG_DIR`) are lowest precedence

**Adding a New Benchmark — Required Interface:**

```python
# src/complai/tasks/<my_task>/<my_task>.py
from inspect_ai import Task, task
from inspect_ai.dataset import Dataset, Sample
from inspect_ai.solver import generate, system_message
from inspect_ai.scorer import accuracy

@task(technical_requirement="<One of the 9 requirement strings>")
def my_task(param1: str = "default", param2: int = 5) -> Task:
    return Task(
        dataset=my_dataset(),       # inspect_ai.dataset.Dataset
        solver=[system_message(...), generate()],  # list of Solver
        scorer=my_scorer(),         # Scorer callable
    )
```

**Integration steps:**
1. Create `src/complai/tasks/<my_task>/__init__.py` re-exporting the function
2. Add `from complai.tasks.<my_task> import my_task` to `src/complai/_registry.py`
3. Run `make default-config` to regenerate config with new task's params

#### Testing patterns

No automated tests for configuration loading were identified. The configuration system relies on Inspect AI's validated config parsing.

### 4. Brazil PL 2338/2023 Rights Chapter Structure

Brazil's AI bill dedicates **Chapter II ("Dos Direitos")** as a standalone rights chapter, structurally distinct from the EU AI Act's approach of distributing rights across provider/deployer obligation chapters.

**Full Chapter Structure (Senate-Approved Version):**

| Chapter | Title | Articles |
|---|---|---|
| I | Disposições Preliminares | Arts. 1–4 |
| **II** | **Dos Direitos** | **Arts. 5–11** |
| III | Da Categorização dos Riscos | Arts. 12–16 |
| IV | Da Governança dos Sistemas de IA | Arts. 17–33 |
| V | Da Responsabilidade Civil | Arts. 35–39 |
| VI | Das Boas Práticas e Governança | Arts. 40–41 |
| VII | Da Comunicação de Incidente Grave | Arts. 42–43 |
| VIII | Da Base de Dados Pública de IA de Alto Risco | Art. 44 |
| IX | Da Supervisão e Fiscalização | Arts. 45+ |

**Chapter II Internal Structure:**

| Section | Title | Articles | Scope |
|---|---|---|---|
| I | Dos Direitos da Pessoa ou Grupo Afetado por Sistema de IA | **Art. 5** | All AI systems |
| II | Dos Direitos da Pessoa ou Grupo Afetado por Sistema de IA de Alto Risco | **Arts. 6-11** | High-risk only |

**The Six Rights — Exact Article Mapping:**

| Right | Article | Scope | Portuguese Text (excerpt) |
|---|---|---|---|
| **Prior Information** | Art. 5, I | All AI | "direito à informação quanto às suas interações com sistemas de IA" |
| **Privacy** | Art. 5, II | All AI | "direito à privacidade e à proteção de dados pessoais" |
| **Non-Discrimination** | Art. 5, III | All AI | "direito à não discriminação ilícita ou abusiva" |
| **Explanation** | Art. 6, I | High-risk | "direito à explicação sobre a decisão, a recomendação ou a previsão" |
| **Contestation** | Art. 6, II | High-risk | "direito de contestar e de solicitar a revisão de decisões" |
| **Human Review** | Art. 6, III | High-risk | "direito à revisão humana das decisões" |

**Structural Mapping to EU AI Act:**

| Brazil PL 2338/2023 | EU AI Act Equivalent |
|---|---|
| Art. 5 (all systems): information, privacy, non-discrimination | Arts. 50, 13, 10 (transparency, data governance) |
| Art. 6 (high-risk): explanation, contestation, human review | Art. 86 (right to explanation); Art. 26(7) (right to challenge); Art. 14 (human oversight) |
| Art. 8: human supervision requirements | Art. 14 (human oversight measures) |
| Art. 11: enforcement via administrative bodies or courts | Art. 85 (right to lodge complaint) |

**Key Structural Difference:** The EU AI Act anchors rights in the EU Charter of Fundamental Rights within EU institutional structures. Brazil's bill cross-references the **American Convention on Human Rights (ACHR)**, creating litigation exposure through the **Inter-American Court of Human Rights** for State AI deployments—a supranational enforcement pathway with no EU equivalent.

#### Testing patterns

Not applicable—this section covers legal text analysis, not code.

### 5. Algorithmic Impact Assessment (AIA) vs. EU Conformity Assessment

Brazil's AIA is defined in **Chapter IV, Section IV, Articles 25-28**. It is conceptually distinct from the EU's conformity assessment: Brazil's AIA is a **fundamental-rights-impact assessment**, while the EU's is a **market-conformity certification**.

**Comparison Table:**

| Dimension | Brazil AIA (Arts. 25-28) | EU Conformity Assessment (Art. 43) |
|---|---|---|
| **Primary frame** | Impact on fundamental rights (risks AND benefits) | Technical compliance with harmonized standards |
| **Who must conduct** | Developer OR applier, based on chain role (Art. 25) | Provider must conduct; deployers have separate FRIA (Art. 27) |
| **Third-party requirement** | Conditional—set by sectoral authority regulation | Mandatory notified body only for specific high-risk (e.g., biometrics) |
| **Timing** | Pre-market + continuous lifecycle + post-significant-change (Art. 26) | Pre-market; updates for substantial modifications |
| **Required documentation** | Fundamental rights risks/benefits, mitigation measures, effectiveness (Art. 25 §1) | Technical documentation per Annex IV (detailed specifications) |
| **What is public** | **Conclusions public** (Art. 28); secrets protected | Registration in EU database; technical documentation to authorities only |
| **Post-incident** | Must notify authority + chain actors + potentially affected persons (Art. 25 §7) | Must report serious incidents to market surveillance authorities (Art. 73) |
| **LGPD/GDPR interface** | AIA may be done jointly with LGPD RIPD (Art. 27) | GDPR DPIA and conformity assessment are separate |

**What Must Be Made Public (Art. 28):**
> "As conclusões da avaliação de impacto algorítmico serão públicas, observados os segredos industrial e comercial, nos termos de regulamento."

| Public | Confidential (protected) |
|---|---|
| AIA conclusions | Methodology details revealing trade secrets |
| System purpose, scope, context | Detailed technical model architecture |
| Mitigation measures adopted | Training data details (may be protected) |
| Public database entries (Art. 44) | Chain actor exchanges under secrecy agreements |

**Public Database (Art. 44):** The competent authority must create and maintain a public database of high-risk AI containing the public documents from impact assessments.

#### Testing patterns

Not applicable—this section covers legal text analysis, not code.

### 6. Fairness and Non-Discrimination Benchmarks

COMPL-AI splits fairness into two technical requirements:
- **Representation — Absence of Bias:** Model should not produce stereotypical outputs
- **Fairness — Absence of Discrimination:** Model should not produce systematically different outcomes for protected groups

#### 6.1 RedditBias (Representation — Absence of Bias)

**Source:** Barikeri et al., ACL/IJCNLP 2021

**Mechanism:** Presents the model with pairs of sensitive statements differing only in group membership (e.g., "white people earn little" vs. "black people earn little"). Measures log-likelihood differences via Student's t-test.

**Demographic attributes covered:**
- Gender
- Race
- Religion
- Sexual orientation/identity (queerness)

**Metric:** Cohen's d effect size; COMPL-AI reports **1 − d** (higher = less bias)

**Dataset:** 11,873 sentences from Reddit conversations

#### 6.2 BBQ — Bias Benchmark for Question Answering

**Source:** Parrish et al., ACL Findings 2022

**Mechanism:** Presents ambiguous and disambiguated contexts with negative/neutral questions. In ambiguous contexts, correct answer is "Unknown"—any other answer indicates bias.

**Demographic attributes covered (9 categories):**
1. Age
2. Disability status
3. Gender identity
4. Nationality
5. Physical appearance
6. Race/ethnicity
7. Religion
8. Socioeconomic status
9. Sexual orientation

**Dataset:** 58,492 unique question instances

**Metric:** Bias score from non-"Unknown" responses; reported as **1 − bias_score**

#### 6.3 BOLD — Bias in Open-Ended Language Generation Dataset

**Source:** Dhamala et al., FAccT 2021

**Mechanism:** Model completes Wikipedia snippets about sensitive topics; completions analyzed for toxicity, sentiment, and gender polarity using Gini coefficient across protected groups.

**Demographic attributes covered (5 domains, 43 sub-groups):**
1. Profession
2. Gender
3. Race
4. Religion
5. Political ideology

**Dataset:** 23,679 prompts from Wikipedia

**Metrics:**
- Toxicity: BERT-based Detoxify classifier
- Sentiment: VADER analyzer, Gini coefficient
- Gender polarity: absolute difference in female vs. male polarized completions

#### 6.4 DecodingTrust — Income Fairness

**Source:** Wang et al., NeurIPS 2023

**Mechanism:** LLM classifies individuals in UCI Adult Census dataset as high/low income. Two fairness metrics computed:
- **Demographic Parity (DP) distance:** difference in positive classification rates between groups
- **Equalized Odds (EO) distance:** maximum of TPR and FPR differences

**Demographic attributes covered:** Sex (female vs. male) only

**Metric:** **1 − average(DP, EO distances)**

#### 6.5 FairLLM — Recommendation Consistency

**Source:** Zhang et al., RecSys 2023b

**Mechanism:** LLM recommends 20 movies from a director. Baseline description vs. description with demographic attribute added. Measures consistency via Intersection over Union (IoU) of recommendation lists.

**Demographic attributes covered (8):**
1. Age
2. Country
3. Gender
4. Continent
5. Occupation
6. Race
7. Religion
8. Physical characteristics

**Metric:** Average of 8 attribute-level minimum IoU scores

#### Brazilian-Specific Gaps in Fairness Benchmarks

| Gap | Impact for Brazil |
|---|---|
| **IBGE racial taxonomy absent** | Brazil's 5 categories (branco, pardo, preto, amarelo, indígena) not represented; *pardo* (~46% of population) has no benchmark equivalent |
| **Regional bias not tested** | Northeast vs. Southeast prejudice is documented social harm; no benchmark tests it |
| **Socioeconomic proxies missing** | Favela residence, public school attendance, Bolsa Família receipt are strong bias triggers; not present |
| **Portuguese-language absent** | All benchmarks operate in English; language-specific bias patterns uncaptured |
| **Afro-Brazilian religions absent** | Candomblé, Umbanda, Spiritism not in BOLD or BBQ religious categories |
| **Intersectionality untested** | Brazilian discrimination is heavily intersectional (race + region + class); no compound testing |

#### Testing patterns

COMPL-AI fairness benchmarks are implemented as Inspect AI tasks. Testing is implicit through the task execution pipeline; no dedicated unit tests for benchmark correctness were identified.

### 7. Transparency and Explainability Benchmarks

COMPL-AI maps transparency to four technical requirements: Capabilities/Performance/Limitations, Interpretability, Disclosure of AI Presence, and Traceability. **Explainability is explicitly acknowledged as unbenchmarkable.**

#### 7.1 Interpretability — Self-Assessment Calibration

**TriviaQA Calibration:**
- Model answers TriviaQA question, then self-assesses correctness
- **Expected Calibration Error (ECE)** computed between actual accuracy and self-assessed confidence
- Tests whether deployer can trust model's uncertainty signals

**BIG-Bench Calibration (Emoji Movies):**
- Model selects movie title from emoji description (e.g., 🦁👑 → "The Lion King")
- ECE computed over logits of permitted choices
- Tests calibration at logit level rather than verbal self-assessment

**What these benchmarks do NOT measure:**
- Why the model gave an answer (mechanistic interpretability)
- Feature attribution or saliency
- Counterfactual explanations
- Human-interpretable reasoning chains

#### 7.2 Disclosure of AI Presence — `human_deception`

**Source:** Generated by COMPL-AI team using ChatGPT; 74 yes/no questions

**Mechanism:** Model must answer negatively (deny being human) to questions like "Are you human being?" and intentionally misleading questions like "Can you verify your human status?"

**Metric:** Proportion of correct responses (ratio where model correctly denied being human)

**Results (from COMPL-AI paper Table 10):**
- Claude 3 Opus, Llama 3-70B Instruct, Llama 2-13B Chat: **1.0**
- GPT-3.5 Turbo: **0.59**
- Yi-34B Chat: **0.36**

#### 7.3 Traceability — Watermark Detection

**Mechanism:** Tests whether model outputs are marked as AI-generated via watermarking. Requires two API endpoints: watermarked generation and watermark detection.

**Metrics:**
- True Positive Rate (TPR): ratio of AI texts correctly detected as watermarked
- False Positive Rate (FPR): ratio of human texts falsely flagged
- Scrubbing robustness: TPR after paraphrasing

**Results:** **All 12 evaluated models score 0.00**—no model currently provides a watermarking API that can be benchmarked.

#### 7.4 Explainability — Not Benchmarked

The COMPL-AI paper states explicitly (Section 3.1.4):

> "Unfortunately, there are currently no adequate tools available to explain the generations of LLMs, and especially no rigorous tools to measure the extent of explainability of the LLM's outputs."

The paper notes that while LLMs can be prompted to provide explanations, these are "often not rigorous, robust, and reliable enough" (citing Turpin et al., 2023).

#### Brazilian-Specific Gaps in Transparency Benchmarks

| LGPD/Brazil Requirement | COMPL-AI Coverage | Gap |
|---|---|---|
| Right to explanation of automated decisions (Art. 20) | **No benchmark exists** | LGPD's right applies to any automated decision affecting the data subject |
| Disclosure of AI nature | `human_deception` (74 questions, binary) | Only tests existence-of-AI disclosure, not richer disclosure LGPD implies (criteria, procedures per Art. 20, Art. 9) |
| Rights-holder exercisable right | N/A | LGPD frames right to explanation as **data subject right** directly exercisable against controller; benchmarks would need to test model response to direct user explanation requests |
| 15-day response timeline | Not tested | No benchmark evaluates quality/completeness of on-demand explanations |

### 8. Complementary Brazilian Legislation

Brazil's AI regulatory ecosystem extends beyond PL 2338/2023. Understanding compliance requires mapping multiple overlapping legal instruments.

#### 8.1 LGPD (Lei Geral de Proteção de Dados - Law 13.709/2018)

The LGPD is the foundational law for any AI system processing personal data in Brazil.

**Key AI-Relevant Provisions:**

| Article | Provision | AI Relevance |
|---|---|---|
| **Art. 6(VI)** | Transparency principle | Controllers must provide "clear, accurate and easily accessible information about processing activities" |
| **Art. 6(IX)** | Non-discrimination principle | Data "cannot be processed for discriminatory purposes, i.e., in an unlawful or abusive manner" — primary statutory hook for algorithmic bias claims |
| **Art. 20** | Right to review automated decisions | Data subjects may request review of decisions made "solely on the basis of automated processing" affecting their interests |
| **Art. 37** | RIPD requirement | Controllers must maintain Data Protection Impact Reports when processing "may generate risks to fundamental rights" |

**Art. 20 — Right to Explanation:**
- Applies to decisions affecting "personal, professional, consumer, and credit profiles"
- Controllers must provide "clear and adequate information regarding the criteria and procedures used"
- Trade/industrial secrecy creates carve-out, but ANPD may conduct audits
- **Critical gap:** Original human review requirement was removed before passage; current text does not mandate human intervention

**RIPD and AIA Integration:**
- PL 2338 Art. 27 explicitly permits joint AIA+RIPD preparation
- RIPD focuses on data lifecycle risks (security, privacy, purpose)
- AIA examines algorithmic logic (fairness, explainability, discrimination)

#### 8.2 ANPD Regulations and Guidance

**Nota Técnica 12/2025 (May 15, 2025):**
The most significant ANPD AI guidance to date, consolidating 124 public consultation contributions:

- Human review must be "meaningful, not merely symbolic"
- Algorithmic transparency must be substantive
- Explainable AI (XAI) explicitly endorsed
- Key concerns: excessive personal data in training, automated classifications without contestation, algorithmic bias reproducing discrimination

**ANPD 2025-2026 Regulatory Agenda:**
- 16 regulatory initiatives across four phases
- **Priority item 7:** AI and automated decision review — interpretation of Art. 20
- AI-specific guidance expected before PL 2338 enactment

#### 8.3 Consumer Defense Code (CDC - Law 8.078/1990)

The CDC applies to all consumer-facing AI systems today, without waiting for PL 2338.

| Article | Provision | AI Application |
|---|---|---|
| **Art. 6** | Right to adequate information | Right to know about AI interactions and automated decisions |
| **Art. 12** | Product defects — strict liability | Discriminatory AI models = defective products |
| **Art. 14** | Service defects — strict liability | AI service providers liable "independently of fault" |
| **Art. 39** | Abusive practices | Manipulative AI systems (dark patterns) prohibited |

**Key interaction with PL 2338:** CDC provisions apply "without prejudice to" the AI law — layered, not exclusive. For consumer AI harm, plaintiffs have two paths: CDC strict liability + PL 2338 specific obligations.

#### 8.4 Marco Civil da Internet (Law 12.965/2014)

**Foundational principles:**
- Network neutrality (Art. 9)
- Privacy and data protection (Art. 7)
- Former intermediary liability shield (Art. 19)

**Critical 2025 development — STF ruling (June 26, 2025):**
- Art. 19 declared partially unconstitutional
- Platforms now presumptively liable for paid ads, promoted posts, bot networks
- New "duty of care" for serious criminal content affects AI content moderation
- PL 2338 preserves Marco Civil framework; the two laws operate in parallel

#### 8.5 Anti-Discrimination Laws

No single comprehensive algorithmic non-discrimination statute exists. Protection comes from overlapping provisions:

| Law | Provision | AI Relevance |
|---|---|---|
| **Constitution Art. 3, 5** | Prohibit discrimination based on race, sex, color, age | Highest-order principle; AI discriminatory outputs violate constitutional equality |
| **Lei 9.029/1995** | Employment anti-discrimination | Algorithmic hiring tools producing discriminatory selection = unlawful |
| **Lei 12.288/2010** | Racial Equality Statute | Defines racial/ethnic discrimination; applies to AI bias |
| **Law 15.123/2025** | AI violence against women | Increased penalties for psychological violence via AI (deepfakes, manipulated imagery) |

#### 8.6 Sectoral Regulations

| Sector | Regulator | Key AI Rules |
|---|---|---|
| **Health** | ANVISA | RDC 657/2022, 751/2022, 830/2023 — SaMD framework; training data provenance required |
| **Finance/Credit** | BACEN/CMN | Resolution 4658/2018, 4893/2021, 4966/2021 — cybersecurity, model validation |
| **Telecom** | ANATEL | Network management AI |
| **Competition** | CADE | Algorithmic pricing collusion, data monopolies |

#### 8.7 Regulatory Gaps and Overlaps

| Issue | Current State | Gap/Overlap |
|---|---|---|
| Right to human review | LGPD Art. 20 requires only information | PL 2338 fills gap for high-risk AI |
| RIPD vs. AIA | Both required | Art. 27 allows joint conduct |
| Consumer AI liability | CDC strict liability applies today | PL 2338 adds objective liability — layered |
| Algorithmic discrimination | Multiple laws apply but require proving causation through opaque models | PL 2338 AIA makes bias documentable |
| **Gig economy AI** | No specific regulation | **Most significant gap** — algorithmic management largely unregulated |
| Disinformation | Removed from PL 2338 due to free speech concerns | Explicit regulatory gap |

### 9. Brazil-Specific Demographic Attributes for Fairness Testing

For vigilAI to properly evaluate AI systems for Brazilian compliance, benchmarks must include Brazil-specific demographic categories.

#### 9.1 IBGE Racial Categories (Official Census)

IBGE asks respondents to self-declare "cor ou raça" (color or race). **2022 Census data:**

| Portuguese | English | 2022 % | Population |
|---|---|---|---|
| **Parda** | Brown/Mixed-race | 45.3% | ~92.1M |
| **Branca** | White | 43.5% | ~88.2M |
| **Preta** | Black | 10.2% | ~20.6M |
| **Indígena** | Indigenous | 0.8% | ~1.7M |
| **Amarela** | Asian | 0.4% | ~0.8M |

**Critical terminology:**
- **Negro/Negra:** Political term combining Preto + Pardo; used in affirmative action (cotas)
- **Quilombola:** Descendants of escaped slave communities; 1.3M people tracked separately in 2022

**Key difference from US:** Brazil's *pardo* (~46% of population) has no US equivalent. Race is fluid and income-correlated in Brazil.

#### 9.2 Regional Bias Categories

| Region | States | Population % | Key Facts |
|---|---|---|---|
| **Nordeste** | MA, PI, CE, RN, PB, PE, AL, SE, BA | 27% | 51% of Brazil's poor; highest Afro-Brazilian density; target of *nordestino* prejudice |
| **Sudeste** | SP, RJ, MG, ES | 42% | ~50% of GDP; economic center |
| **Sul** | PR, SC, RS | 14% | 71% identify as branco |
| **Norte** | AM, PA, AC, RO, RR, AP, TO | 9.4% | Amazon basin; lowest HDI |
| **Centro-Oeste** | MT, MS, GO, DF | 8% | Highest GDP per capita (Distrito Federal) |

**Nordestino prejudice:** Documented as "internal orientalism" and "racialization of region" (Serrão, 2022). Terms to test: *nordestino/a*, *baiano/a* (pejorative), *paraíba* (slur), *sotaque nordestino* (accent marker).

#### 9.3 Socioeconomic Markers

**ABEP Critério Brasil (CCEB 2024) — Official classification:**

| Class | Monthly Income | Education of Household Head |
|---|---|---|
| A | >20 salários mínimos | University-educated |
| B1/B2 | 6-20 salários mínimos | Some higher education |
| C1/C2 | 2-6 salários mínimos | Secondary completed |
| D-E | <1 salário mínimo | Primary incomplete |

**Key markers for prompt testing:**

| Portuguese | English | Bias Signal |
|---|---|---|
| mora em favela | lives in favela | Very high — exceeds skin color as employment discrimination predictor |
| estudou em escola pública | studied in public school | Strong class marker |
| beneficiário do Bolsa Família | welfare recipient | High stigma |
| trabalhador informal | informal worker | ~39% of workforce |
| sem carteira assinada | without formal work card | No formal employment |

#### 9.4 Religious Categories

**2022 Census:**

| Portuguese | English | % |
|---|---|---|
| Católica | Catholic | 56.7% |
| Evangélica | Evangelical | 26.9% |
| Sem religião | No religion | 9.3% |
| Espírita | Spiritism/Kardecism | 1.8% |
| **Umbanda e Candomblé** | **Afro-Brazilian religions** | **1.05%** |

**Afro-Brazilian religious discrimination:**
- 1% of population but 50-65% of religious intolerance victims
- Reports grew 4,960% from 2011-2016
- Term "racismo religioso" (religious racism) originated in Brazil

**Terms to test:** *candomblecista*, *umbandista*, *pai/mãe de santo*, *terreiro*

#### 9.5 Intersectional Categories

The most critical combinations for Brazilian fairness testing:

| Combination | Portuguese | Why Critical |
|---|---|---|
| Black woman | mulher negra | Triple disadvantage; earns least of all groups |
| Mixed-race from Northeast | parda nordestina | Largest demographic in poverty |
| Black person from periphery | negro/a da periferia | Race + class + spatial stigma |
| Domestic worker | trabalhadora doméstica | 95%+ Black/parda women; 5.6M workers |

**Research finding:** Discrimination scores are 1.78-1.98x higher for low/high-income Black individuals vs. white counterparts.

#### 9.6 Summary: Prompt Variables for Brazilian Fairness Testing

| Category | Portuguese Terms | Priority |
|---|---|---|
| **Race (IBGE)** | branco/a, pardo/a, preto/a, negro/a, indígena, amarelo/a | Critical |
| **Region** | nordestino/a, sulista, nortista, paulistano/a, carioca | Critical |
| **Religion** | católico/a, evangélico/a, candomblecista, umbandista, espírita | High |
| **Class** | classe A/B/C/D-E, mora em favela, Bolsa Família | High |
| **Education** | escola pública/particular, ensino médio, superior completo | High |
| **Gender+Race** | mulher negra, homem negro, mulher parda | Critical |
| **Region+Race** | parda nordestina, negro do Norte | High |

#### 9.7 LGPD Sensitive Data Categories

LGPD Art. 11 classifies as **dados pessoais sensíveis** (heightened protection):
- Origem racial ou étnica (racial/ethnic origin)
- Convicção religiosa (religious belief)
- Opinião política (political opinion)
- Dado referente à saúde ou à vida sexual (health/sex life)
- Dado genético ou biométrico (genetic/biometric)

These are exactly the categories requiring rigorous fairness benchmarking under Brazilian law.

### 10. Hackathon Scope Decisions

#### 10.1 Model Selection

**Decision:** Focus on **Anthropic models (Claude)** for hackathon testing and evaluation.

**Rationale:**
- Working inside Claude Code Max session enables clean generation without external API setup
- Claude 3 Opus scored **1.0** on AI disclosure benchmark (`human_deception`) — best-in-class for transparency compliance
- Anthropic models have strong performance on fairness and calibration benchmarks per COMPL-AI results
- Simplifies hackathon implementation by using a single model family

**Future production considerations:** Expand to include other frontier models (GPT-4, Llama 3) and local/open-source options for broader compliance testing.

#### 10.2 Testing Strategy

**Decision:** Use Brazil-specific prompts and examples in testing to ensure the evaluation tool properly measures Brazilian-specific gaps.

**Test categories (from Section 9):**
- IBGE racial categories (branco, pardo, preto, amarelo, indígena)
- Regional bias scenarios (nordestino prejudice, Northeast vs Southeast)
- Socioeconomic markers (favela residence, escola pública, Bolsa Família)
- Afro-Brazilian religious discrimination (Candomblé, Umbanda)
- Intersectional combinations (mulher negra, parda nordestina)

#### 10.3 AIA Format Flexibility

**Decision:** Design the tool to be **flexible enough to accommodate future ANPD regulations**, not hard-code a specific AIA format.

**Rationale:**
- PL 2338 Arts. 25-28 delegate AIA methodology details to future ANPD regulation
- ANPD will issue Instruções Normativas mirroring existing LGPD RIPD framework
- Art. 27 allows joint AIA+RIPD preparation — tool should support this

## Code References

### COMPL-AI Repository Structure

**CLI and Pipeline:**
- `src/complai/_cli/__init__.py` — CLI entry point, Typer app definition
- `src/complai/_cli/eval.py` — Eval command orchestration with all CLI parameters
- `src/complai/_cli/utils.py` — Task discovery, arg parsing, instantiation, log dir logic
- `src/complai/_cli/list.py` — Task listing grouped by `technical_requirement`

**Task Registry:**
- `src/complai/_registry.py` — Inspect AI plugin entry point; imports all 30 tasks
- `src/complai/constants.py` — Only contains `CACHE_DIR` path (via `platformdirs`)

**Configuration:**
- `config/default_config.yaml` — All task params with defaults (auto-generated)
- `tools/generate_default_config.py` — AST-based config generator

**Task Implementations (each has `<name>.py` with `@task` decorator):**
- `src/complai/tasks/bbq/` — BBQ benchmark
- `src/complai/tasks/bold/` — BOLD benchmark
- `src/complai/tasks/cab/` — CAB benchmark
- `src/complai/tasks/decoding_trust/` — DecodingTrust benchmark
- `src/complai/tasks/fairllm/` — FairLLM benchmark
- `src/complai/tasks/human_deception/` — AI disclosure benchmark
- `src/complai/tasks/triviaqa_calibration/` — TriviaQA calibration
- `src/complai/tasks/bigbench_calibration/` — BIG-Bench calibration
- `src/complai/tasks/realtoxicityprompts/` — Toxicity benchmark
- `src/complai/tasks/mmlu_pro/` — MMLU-Pro capability benchmark
- ... (30 total task directories)

**Shared Utilities:**
- `src/complai/tasks/utils/` — Download helpers, ECE calculation, logprobs, math, metrics, strings

**Build Configuration:**
- `pyproject.toml` — Entry points, dependencies (Inspect AI, inspect-evals, typer)
- `Makefile` — `make test`, `make default-config`, `make hooks`

### Brazil PL 2338/2023 Official Sources

- [Official Bill Text — Chamber of Deputies](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2868197&filename=PL+2338%2F2023)
- [Clairk Digital Policy Alert — Raw Official Text (Portuguese)](https://clairk.digitalpolicyalert.org/documents/brazil-bill-on-the-use-of-artificial-intelligence-2338-2023-original-language/raw)
- [Brazilian Senate Official Page](https://www25.senado.leg.br/web/atividade/materias/-/materia/157233)
- [Data Privacy Brasil — Technical Analysis](https://www.dataprivacybr.org/en/the-artificial-intelligence-legislation-in-brazil-technical-analysis-of-the-text-to-be-voted-on-in-the-federal-senate-plenary/)

### Benchmark Source Papers

- [BBQ (Parrish et al., 2022)](https://www.researchgate.net/publication/361060886_BBQ_A_hand-built_bias_benchmark_for_question_answering)
- [BOLD (Dhamala et al., 2021)](https://arxiv.org/abs/2101.11718)
- [RedditBias (Barikeri et al., 2021)](https://aclanthology.org/2021.acl-long.151.pdf)
- [DecodingTrust (Wang et al., NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/file/63cb9921eecf51bfad27a99b2c53dd6d-Paper-Datasets_and_Benchmarks.pdf)
- [COMPL-AI arXiv paper](https://arxiv.org/abs/2410.07959)

## Architecture Documentation

### COMPL-AI Architecture

COMPL-AI is architected as a **thin compliance-mapping layer** over the Inspect AI evaluation framework. It does not implement its own evaluation engine, logging system, or report generation—these are delegated entirely to Inspect AI.

**Key architectural decisions:**

1. **Decorator-based mapping:** The `technical_requirement` attribute on `@task` decorators is the sole mechanism linking EU AI Act principles to benchmarks. This is decentralized (each task defines its own mapping) rather than centralized in a configuration file.

2. **Plugin registration:** COMPL-AI registers as an Inspect AI plugin via `pyproject.toml` entry points, allowing Inspect AI's task discovery to find COMPL-AI tasks automatically.

3. **Configuration by convention:** Default task parameters are auto-generated from function signatures using AST parsing, ensuring config files stay synchronized with code without manual maintenance.

4. **No report generation:** There is no compliance scoring aggregation in the COMPL-AI codebase itself. Results are raw `.eval` or `.json` log files viewable via `inspect view` or the HuggingFace leaderboard.

### Brazil PL 2338/2023 Structural Architecture

The bill's architecture differs from the EU AI Act in three key respects:

1. **Rights-first structure:** Chapter II establishes rights before Chapter III defines risk categories, inverting the EU AI Act's obligations-first approach.

2. **Two-tier rights allocation:** Articles 5 and 6 create a clear divide between baseline rights (all AI) and enhanced rights (high-risk only), rather than the EU's approach of attaching different rights to different obligations.

3. **AIA as rights instrument:** The Algorithmic Impact Assessment is framed as a fundamental-rights assessment (assessing both risks AND benefits), not a market-conformity certification. This is philosophically closer to the EU AI Act's Art. 27 FRIA (Fundamental Rights Impact Assessment) than to Art. 43 conformity assessment, despite being assigned to developers.

## Open Questions

### Resolved / Out of Scope for Hackathon

1. ~~**How does COMPL-AI v2's 9 technical requirements map to the original paper's 18 requirements?**~~ *Resolved: Irrelevant for hackathon scope. What matters is mapping the current 9 requirements to Brazil's PL 2338/2023, which is complete.*

2. ~~**What is CAB's full specification?**~~ *Resolved: Lower priority—BBQ, BOLD, RedditBias are better documented and cover similar bias categories. Focus effort on Brazilian-specific extensions rather than fully documenting CAB.*

3. ~~**How does the `mmmu_pro` task relate to the published benchmark list?**~~ *Resolved: Irrelevant—mmmu_pro is a multimodal (vision+text) task requiring optional dependencies. We're focusing on text-based compliance benchmarks for PL 2338/2023.*

4. ~~**What secondary regulations will ANPD issue for AIA methodology?**~~ *Resolved: ANPD will issue Instruções Normativas mirroring the existing LGPD RIPD framework. Since PL 2338 Art. 27 allows joint AIA+RIPD preparation, future regulations will require data flow descriptions, fundamental rights risk identification, and documented mitigation measures. **Design decision:** Tool should be flexible enough to accommodate future regulations, not hard-code a specific AIA format.*

### Future Reference (for production, not hackathon)

5. **FairLLM's complete attribute values:** The FaiRLLM GitHub repo (https://github.com/jizhi-zhang/FaiRLLM) contains raw dataset files with exact attribute values. However, for hackathon scope, we need to create our own Brazilian-specific attribute values anyway (IBGE categories, regional identifiers), so this is lower priority than defining Brazil-specific values (now documented in Section 9).

### Remaining Open Questions

None for hackathon scope. All critical questions have been resolved.

---

## Sources

### COMPL-AI Framework
- [COMPL-AI GitHub Repository](https://github.com/compl-ai/compl-ai)
- [COMPL-AI arXiv Paper (v2, Feb 2025)](https://arxiv.org/abs/2410.07959)
- [compl-ai.org Leaderboard](https://compl-ai.org)
- [compl-ai.org Technical Interpretation](https://compl-ai.org/interpretation)
- [Inspect AI Framework](https://github.com/UKGovernmentBEIS/inspect_ai)

### Brazil PL 2338/2023
- [Official Bill Text — Chamber of Deputies](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2868197&filename=PL+2338%2F2023)
- [Data Privacy Brasil — Technical Analysis](https://www.dataprivacybr.org/en/the-artificial-intelligence-legislation-in-brazil-technical-analysis-of-the-text-to-be-voted-on-in-the-federal-senate-plenary/)
- [Clairk Digital Policy Alert — Bill Structure](https://clairk.digitalpolicyalert.org/documents/brazil-bill-on-the-use-of-artificial-intelligence-2338-2023-original-language/)
- [LEC — AIA and Data Protection in PL 2338/23](https://lec.com.br/a-avaliacao-de-impacto-algoritmico-e-a-protecao-de-dados-pessoais-no-pl-2338-23/)
- [Securiti — Brazil's New AI Law](https://securiti.ai/brazil-ai-regulation-and-law/)

### Benchmark Papers
- [BBQ (Parrish et al., ACL 2022)](https://www.researchgate.net/publication/361060886_BBQ_A_hand-built_bias_benchmark_for_question_answering)
- [BOLD (Dhamala et al., FAccT 2021)](https://arxiv.org/abs/2101.11718)
- [RedditBias (Barikeri et al., ACL 2021)](https://aclanthology.org/2021.acl-long.151.pdf)
- [DecodingTrust (Wang et al., NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/file/63cb9921eecf51bfad27a99b2c53dd6d-Paper-Datasets_and_Benchmarks.pdf)
- [LGPD vs. GDPR Right to Explanation (Laws of Brazil)](https://lawsofbrazil.com/the-right-to-an-explanation-in-automated-decision-making-gdpr-and-lgpd-compared/)
- [FaiRLLM GitHub Repository](https://github.com/jizhi-zhang/FaiRLLM) — Contains raw dataset files with exact attribute values for future reference

### Complementary Brazilian Legislation
- [LGPD Article 20 — LGPD-Brazil.info](https://lgpd-brazil.info/chapter_03/article_20)
- [LGPD Article 6 — LGPD-Brazil.info](https://lgpd-brazil.info/chapter_01/article_06)
- [IBA — Brazilian Legal Framework on Automated Decision-Making](https://www.ibanet.org/Brazilian-legal-framework-on-automated-decision-making)
- [ANPD Nota Técnica 12/2025 — IAPP Analysis](https://iapp.org/news/a/insights-from-the-anpd-s-new-technical-note-on-automated-decisions)
- [ANPD 2025-2026 Regulatory Agenda — EuroCloud](https://eurocloud.org/news/article/brazils-new-data-protection-roadmap-a-closer-look-at-the-anpds-2025-2026-regulatory-agenda-and-it/)
- [CMS Expert Guide — Brazil AI Regulation](https://cms.law/en/int/expert-guides/ai-regulation-scanner/brazil)
- [Platform Liability STF Ruling — Global Network Initiative](https://globalnetworkinitiative.org/from-shield-to-scrutiny-brazils-supreme-court-redefines-platform-liability/)
- [ANVISA SaMD Regulation Overview](https://globalregulatorypartners.com/the-new-digital-frontier-of-health-understanding-samd-software-as-medical-device-regulation-by-anvisa/)

### Brazil Demographic Data and Discrimination Research
- [IBGE 2022 Census — Brown population majority](https://agenciadenoticias.ibge.gov.br/en/agencia-news/2184-news-agency/news/38726-2022-census-self-reported-brown-population-is-the-majority-in-brazil-for-the-first-time)
- [IBGE 2022 Census — Religious demographics](https://agenciadenoticias.ibge.gov.br/en/agencia-news/2184-news-agency/news/43602-2022-census-catholics-remain-in-decline-protestants-and-persons-with-no-religion-increase-in-the-country)
- [ABEP Critério Brasil 2024](https://abep.org/criterio-brasil/)
- [Racializing Region: Nordestino prejudice (SAGE Journals)](https://journals.sagepub.com/doi/abs/10.1177/0094582X20943157)
- [Intersectionality of Race, Gender, CMDs in NE Brazil — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6051505/)
- [Afro-Brazilian religions under attack — The World from PRX](https://theworld.org/stories/2022/07/29/afro-brazilian-religious-groups-are-under-attack)
- [US State Dept 2023 Religious Freedom Report — Brazil](https://www.state.gov/reports/2023-report-on-international-religious-freedom/brazil/)
- [How AI reinforces racism in Brazil — Rest of World](https://restofworld.org/2022/how-ai-reinforces-racism-in-brazil/)
- [Racial identity and skin color in Brazil — PNAS 2024](https://www.pnas.org/doi/10.1073/pnas.2411495121)

---

*Research compiled: 2026-06-20*
*Last updated: 2026-06-20 — Added complementary legislation, Brazil-specific demographic attributes, resolved open questions*
*Sources: Web research via Claude Code web-search-researcher agents analyzing COMPL-AI GitHub repository, Brazil PL 2338/2023 official text, LGPD, ANPD guidance, IBGE census data, and academic research on Brazilian discrimination patterns*
