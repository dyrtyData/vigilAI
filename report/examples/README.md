# Extracted transcripts — `report/examples/`

The three transcripts the paper quotes in its main text, **selected by stated deterministic rules
from real Inspect logs** and written here by
[`tools/extract_examples.py`](../../tools/extract_examples.py). Nothing in this directory is
hand-picked, hand-written or hand-edited; re-running the tool over the same logs reproduces every
file byte for byte.

```bash
uv run python tools/extract_examples.py logs/<run> [logs/<other-run> ...] [--out report/examples] [--html]
```

The tool prints the rule it applied and the `sample_id` it selected, so the paper can cite both,
and each emitted file carries its own rule verbatim — the artifact and the paper cannot drift.

## Why rules and not judgment

For a paper whose contribution is methodological rigor, a hand-picked transcript is the easiest
possible attack: *"you found one bad answer."* A rule anyone can re-run against the same committed
logs is not that. So the rules are stated in full, they are totally ordered (every tie has an
explicit key), and a rule that finds nothing **reports that it found nothing** rather than being
relaxed until it finds something.

| # | Example | Rule |
|---|---|---|
| 1 | The hero — the disclosure pair | Same model, same `match` scorer: the lowest-`sample_id` `human_deception_brazil` sample scoring 0 whose `human_deception` counterpart at the same `sample_id` scored 1. Epoch 1 only. |
| 2 | Deterministic ↔ judge divergence | The held-out sample carrying **both** a deterministic and an LLM-judge score with the largest \|deterministic − judge\|. Epoch 1 only. Ties: lowest `sample_id`, then alphabetically first task. |
| 3 | `bbq_brazil` stereotype pick | The lowest-`sample_id` ambiguous-context `bbq_brazil` sample where the model marked exactly one option and it was **not** the Unknown one (*Não é possível determinar*). Epoch 1 only. |

Three things about those rules are worth stating here rather than leaving in the code:

- **Rule 1's pairing is positional, not semantic.** Neither dataset sets an explicit `Sample.id`,
  so Inspect numbers both 1..N and "the counterpart at the same index" is well defined — but
  `human_deception`'s prompts come from the upstream COMPL-AI Hugging Face set and are not
  translations of the Brazil ones. The emitted file prints **both** prompts in full, and flags
  each one's apparent language, precisely so a reader can judge whether the pair is the finding
  the paper claims or an artifact.
- **Rule 2's two numbers are different measures.** Deterministic = the mean fraction of rubric
  elements the cue detectors find; judge = Inspect `accuracy` over the `C`/`P`/`I` grade. Δ is a
  distance between two stated measures, never an error rate. The emitted file also carries the
  **per-element** breakdown — cue detector beside judge verdict — which is the comparison that
  actually answers "how much of the score is keyword surface".
- **Rule 3 is shuffle-safe.** Since Phase 2b every `bbq_brazil` sample carries a deterministic
  per-sample shuffle of its three options, so the Unknown option is **not** always C. The rule
  resolves it from the sample's own post-shuffle `metadata["unknown_answer"]` and cross-checks it
  against the position of *Não é possível determinar* in the presented choices; if the two
  disagree the tool **refuses** rather than guessing, because a wrong Unknown letter inverts the
  finding.

## Provenance and hygiene

- **Raw `.eval` logs stay gitignored.** Only these extracted transcripts enter the repo. Each file
  records the log's **basename**, the model id, the sample id and the epoch — never an absolute
  path (it would publish the operator's home directory and differ between machines).
- **The output is scanned for secrets before anything is written.** `scan_for_secrets` matches
  known key shapes, `*_API_KEY` / `*_SECRET` / `*_TOKEN` assignments, and — when a local `.env`
  exists — the literal values in it. A finding aborts the whole run, so a partial write can never
  leave one leaked file behind. The scan is also a test
  (`tests/test_extract_examples.py::TestSecretScanning`) and it runs over **everything committed
  in this directory**, so the check is automated in both directions rather than left to a reader.
- **`aia_checklist` transcripts always print their `prompt_mode`.** The `guided` and `unguided`
  conditions differ by most of the score, so an unlabelled one cannot be interpreted.

## Status — no real transcripts yet

**This directory currently contains only this README.** The transcripts land in **Phase 8**, the
first phase with a funded `ANTHROPIC_API_KEY`. The extractor, its rules and its output format are
complete and verified against `mockllm/model`, but a mock transcript is fixture text — every
earlier phase of this iteration wrote its mock previews to `/tmp` for exactly that reason, and
planting one in the paper's evidence directory would invite it to be cited. What is verified today
is the *machinery*; what is missing is a real model's words.

One consequence to keep in mind when Phase 8 runs it: the mock exercises every field the rules
read **except the shape of a real grader's reply**. The per-element verdict lines rule 2 prints
come out of `Score.explanation`, which is the grader's own completion, so on a mock run they are
whatever the harness authored. Whether a real Opus 4.6 grader follows the required
`<element>: SUBSTANTIVE|ABSENT` format is not knowable until the first real judge run — and the
tool reports non-compliance as a **finding about the grader** rather than degrading quietly.
