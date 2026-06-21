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

- **Phase 1 (current):** COMPL-AI forked into the `vigilai` package and CLI; all 30 original
  tasks preserved and runnable.
- Later phases add the Brazil PL 2338/2023 article-mapping metadata, Brazil-specific
  benchmarks, and a per-article compliance report. *(The EU↔Brazil mapping table is added
  in Phase 2.)*

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
