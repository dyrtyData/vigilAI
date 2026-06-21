# vigilAI

**Brazil PL 2338/2023 (AI Act) compliance evaluation for Generative AI systems.**

vigilAI is a compliance-centered LLM evaluation tool that maps model behavior to the
rights and obligations of Brazil's pending AI bill, **PL 2338/2023** — in particular the
Chapter II rights (Arts. 5-6) and the Algorithmic Impact Assessment framework (Arts. 25-28).

> **Lineage.** vigilAI is a fork of [**COMPL-AI**](https://compl-ai.org), the EU AI Act
> compliance benchmarking suite created and maintained by
> [ETH Zurich](https://www.sri.inf.ethz.ch/), [INSAIT](https://insait.ai/), and
> [LatticeFlow AI](https://latticeflow.ai/)
> ([arXiv:2410.07959](https://arxiv.org/abs/2410.07959), Apache-2.0). Like COMPL-AI, it is
> built on the UK AI Safety Institute's [Inspect AI](https://inspect.aisi.org.uk/)
> evaluation framework. The original COMPL-AI benchmark suite (30 tasks across 9 technical
> requirements) is **preserved in full** so the EU AI Act benchmarks can be run on the same
> model as the Brazil-specific benchmarks for a direct EU↔Brazil comparison.

This project was built for the **Global South AI Safety Hackathon** (Latam Governance subtrack).

## Status

- **Phase 1:** COMPL-AI forked into the `vigilai` package and CLI; all 30 original tasks
  preserved and runnable.
- **Phase 2:** Brazil PL 2338/2023 article-mapping metadata layered over the preserved EU
  technical requirements and surfaced in `vigilai list` (see the EU↔Brazil mapping below).
- **Phase 3:** `human_deception_brazil` benchmark (Art. 5, I — prior information / AI
  disclosure), with Portuguese and LGPD/PL-2338 disclosure questions, reusing the upstream
  `human_deception` scorer.
- **Phase 4 (current):** `bbq_brazil` fairness benchmark (Art. 5, III — non-discrimination),
  a Brazil-adapted BBQ covering IBGE racial categories, regional prejudice, and
  intersectional identities (see "Brazil benchmark datasets" below).
- Later phases add the explanation-quality and AIA benchmarks and a per-article compliance
  report.

## Brazil benchmark datasets

The Brazil-specific benchmarks are **self-contained and offline** (the scenarios live in
code, so mock-model evals and the test suite run deterministically with no network access).

**`bbq_brazil` (Art. 5, III).** A Brazil-adapted [BBQ](https://aclanthology.org/2022.findings-acl.165/)
(Parrish et al., ACL Findings 2022) bias benchmark in Portuguese. It reuses the *exact same*
scoring path as the upstream `bbq` task (Inspect AI's `multiple_choice()` solver +
`choice()` scorer), so the EU↔Brazil delta isolates purely the Brazil-specific content. It
covers three category groups that the US-centric upstream BBQ omits (research §6 gaps):

| Category group | Coverage (research §9) |
|---|---|
| `Race_IBGE` | IBGE "cor ou raça" categories — branco, pardo, preto, negro, indígena, amarelo |
| `Region` | Regional prejudice — nordestino, nortista, baiano vs. paulistano/carioca/sulista |
| `Intersectional` | Compound identities — mulher negra, parda nordestina, negro do Norte |

*Provenance & future-work caveat.* As of June 2026 **no Portuguese / Brazilian BBQ-style QA
bias dataset exists**, and none of the 10+ BBQ adaptations (MBBQ, KoBBQ, JBBQ, EsBBQ,
PakBBQ, BharatBBQ, …) covers Portuguese or the IBGE 5-category racial taxonomy. The
scenarios are therefore **authored for vigilAI** using the BBQ template methodology
(ambiguous + disambiguated contexts), with the demographic terms drawn from research §9.
Two existing resources **seed / anchor** the choice of realistic stereotypes but are
deliberately *not* runtime data sources:
[SHADES / BiasShades](https://huggingface.co/datasets/LanguageShades/BiasShades) (pt-BR
stereotypes; license-gated) and
[ToxSyn-PT](https://huggingface.co/datasets/ToxSyn/ToxSyn-PT) (CC BY 4.0; classification
format). Other Brazilian hate-speech corpora (HateBR, ToLD-BR, OLID-BR) are classification,
not QA, and use coarse race labels — noted as future-work resources only. **Full
native-annotator validation and a larger sample count are documented future work**; the
current set is a hand-built pilot sufficient to demonstrate the approach for the hackathon.

## EU ↔ Brazil mapping

vigilAI keeps COMPL-AI's nine EU-AI-Act `technical_requirement` categories unchanged (so
the EU benchmarks stay comparable) and tags the relevant tasks with their **Brazil PL
2338/2023** equivalent. PL 2338/2023 places its rights in **Chapter II ("Dos Direitos")**:
**Art. 5** rights apply to *all* AI systems, while **Art. 6** rights apply to *high-risk*
systems only — captured by the `brazil_scope` tag (`all_ai` vs `high_risk`). The single
source of truth for this table is [`src/vigilai/brazil/mapping.py`](src/vigilai/brazil/mapping.py).

| EU technical requirement (COMPL-AI) | Brazil PL 2338/2023 | Scope | Right | Tasks |
|---|---|---|---|---|
| Disclosure of AI | **Art. 5, I** | `all_ai` | Prior information | `human_deception`, `human_deception_brazil` |
| Representation — Absence of Bias | **Art. 5, III** | `all_ai` | Non-discrimination | `bbq`, `bbq_brazil`, `bold`, `cab` |
| Fairness — Absence of Discrimination | **Art. 5, III** | `all_ai` | Non-discrimination | `decoding_trust`, `fairllm` |
| Interpretability | **Art. 6, I** | `high_risk` | Explanation (cf. LGPD Art. 20) | `bigbench_calibration`, `triviaqa_calibration` |

The remaining EU technical requirements (Capabilities/Performance/Limitations, Robustness
and Predictability, Cyberattack Resilience, Societal Alignment, Harmful Content and
Toxicity) have **no direct Brazil Chapter II counterpart** and are listed as "no Brazil
mapping" — that absence is itself a finding. Brazil's Art. 6 explanation right and the
Algorithmic Impact Assessment obligations (Arts. 25-28) likewise have no dedicated EU
COMPL-AI benchmark; new Brazil-specific benchmarks for them are added in later phases.

```bash
# Group tasks by EU technical requirement, annotated with the Brazil mapping (default)
uv run vigilai list

# Group tasks by Brazil PL 2338/2023 article instead
uv run vigilai list --brazil
```

## Install

vigilAI targets Python 3.11-3.13 and uses [`uv`](https://docs.astral.sh/uv/).

```bash
# from the vigilAI/ directory
uv venv
uv pip install -e .
```

## CLI

```bash
# List all tasks, grouped by technical requirement
uv run vigilai list

# Run a single benchmark against a deterministic mock model (zero cost)
uv run vigilai eval mockllm/model --tasks human_deception --limit 5

# Run against a real backend (e.g. a local Ollama model, or an API provider)
uv run vigilai eval ollama/llama3.1:8b --tasks human_deception

# View a generated log
uv run inspect view
```

Run `uv run vigilai --help` (or `uv run vigilai COMMAND --help`) for full usage.

## License

Apache-2.0 (inherited from COMPL-AI). See [LICENSE](LICENSE).

## Citation

vigilAI builds directly on COMPL-AI; please cite the original work:

```bibtex
@article{complai24,
      title={COMPL-AI Framework: A Technical Interpretation and LLM Benchmarking Suite for the EU Artificial Intelligence Act},
      author={Philipp Guldimann and Alexander Spiridonov and Robin Staab and Nikola Jovanovi\'{c} and Mark Vero and Velko Vechev and Anna Gueorguieva and Mislav Balunovi\'{c} and Nikola Konstantinov and Pavol Bielik and Petar Tsankov and Martin Vechev},
      year={2024},
      eprint={2410.07959},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2410.07959},
}
```
