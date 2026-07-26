"""Rule-based transcript extractor (iteration 2, Phase 7).

    uv run python tools/extract_examples.py logs/<run> [logs/<other-run> ...] [--out DIR] [--html]

Pulls the paper's three main-text transcripts out of real Inspect logs by **stated deterministic
rules**, never by hand. For a paper whose contribution is methodological rigor, a hand-picked
transcript is the easiest possible attack: "you found one bad answer". A rule that anyone can
re-run against the same logs and get the same sample is not that. So every rule here is

* **stated in full** in the emitted Markdown, in the words the paper will quote;
* **total-ordered** — every tie is broken by an explicit key, so there is no "whichever came
  first out of the dict";
* **printed at selection time** together with the ``sample_id`` it chose, so the paper can cite
  both and a reader can verify the choice against the committed log record.

What the rules depend on, and the two that are not free
-------------------------------------------------------

Rule 1 pairs ``human_deception_brazil`` with ``human_deception`` **by sample id**. Both datasets
are ordered lists whose samples carry no explicit ``Sample.id``, so Inspect numbers them 1..N and
"the counterpart at the same index" is well defined — but it is *positional*, not semantic:
``human_deception``'s prompts come from the Hugging Face set and are not a translation of
``human_deception_brazil``'s. The emitted file therefore prints **both prompts in full** and
flags the Brazil prompt's apparent language, so the manual check ("is this really the
English-denial / Portuguese-failure finding, or an artifact?") is answerable from the artifact.

Rule 3 depends on ``bbq_brazil``'s per-sample choice shuffle (Phase 2b). The Unknown option is
**no longer always C**, so "chose a named individual over *Não é possível determinar*" cannot be
"the answer was not C". It is resolved against the sample's own recorded
``metadata["unknown_answer"]`` — the post-shuffle letter, written by the dataset — and
cross-checked against the position of the Unknown option in ``Sample.choices``. If the two
disagree the tool refuses rather than guessing, because a wrong Unknown letter would invert the
finding.

Output discipline
-----------------

* Writes to ``report/examples/`` by default. **Raw ``.eval`` logs stay gitignored**; only these
  extracted transcripts enter the repo.
* **Byte-identical on re-run.** Nothing wall-clock, nothing absolute-path: the provenance block
  records the log *basename*, the model id and the sample id. Re-running over the same logs must
  produce the same bytes, and a test pins that.
* **Refuses to write anything containing a secret.** :func:`scan_for_secrets` runs over every
  rendered document before a single file is opened, matching known key shapes, ``*_API_KEY``
  names, ``.env``-style assignments, and — if a ``.env`` exists next to the repo root — the
  literal values in it. A completion that echoed a key back would otherwise walk straight into a
  committed file. Automated because "read the output and check" is not a control.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

# ``tools/`` is not a package on ``sys.path`` when run as a script from the repo root; the
# ``vigilai`` package is installed (``uv run``), so this import is the normal one.
from vigilai.report.samples import first_epoch
from vigilai.report.samples import JUDGE_SCORER_NAME
from vigilai.report.samples import load_samples
from vigilai.report.samples import sample_sort_key
from vigilai.report.samples import SampleRecord


#: Default output directory — beside the paper (``report/``), not the run archive
#: (``reports/runs/``). These are the excerpts the paper's main text quotes.
DEFAULT_OUT_DIR = "report/examples"

#: The Brazil disclosure task and its EU counterpart, the two sides of rule 1.
BRAZIL_DISCLOSURE_TASK = "human_deception_brazil"
EU_DISCLOSURE_TASK = "human_deception"

#: The ``bbq_brazil`` ambiguous-context marker and the Unknown option's text.
BBQ_TASK = "bbq_brazil"
AMBIGUOUS = "ambiguous"
UNKNOWN_ANSWER_TEXT = "Não é possível determinar"

#: The reserved slice rule 2 draws from.
SPLIT_HELD_OUT = "held_out"

# Characters that only occur in Portuguese in this corpus. Used **only** to annotate a transcript
# (never to select one), so the reader of the disclosure pair can see at a glance whether the
# Brazil side really is the Portuguese-framed prompt the paper's finding is about.
_PT_MARKERS = "ãõáéíóúâêôàçÃÕÁÉÍÓÚÂÊÔÀÇ"


# ---------------------------------------------------------------------------------------
# Secret scanning — a control, not a habit.
# ---------------------------------------------------------------------------------------
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Anthropic-style API key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}")),
    (
        "environment variable assignment naming a key/secret/token",
        re.compile(
            r"(?m)^\s*(?:export\s+)?[A-Z][A-Z0-9_]*"
            r"(?:API_KEY|_KEY|SECRET|TOKEN|PASSWORD)\s*=\s*\S+"
        ),
    ),
)


def _dotenv_values(repo_root: Path) -> list[str]:
    """Non-trivial values from a local ``.env``, if one exists.

    The strongest form of the check the outline asks for — "no ``.env`` content appears anywhere
    in the committed output" — is to read the actual ``.env`` and look for its actual values.
    ``.env`` is gitignored and absent in CI and in the environment Phase 7 was built in, where
    this degrades to a no-op; it bites on Diana's machine, which is the machine that will run the
    extractor against a funded run.
    """
    env_path = repo_root / ".env"
    if not env_path.is_file():
        return []
    values: list[str] = []
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        _, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        # Short values are things like `1`, `true`, a region name — matching those would make the
        # scanner fire on ordinary prose. Eight characters is well below any real key length.
        if len(value) >= 8:
            values.append(value)
    return values


def scan_for_secrets(text: str, *, repo_root: Path | None = None) -> list[str]:
    """Return a list of human-readable findings; empty means the text is safe to write.

    Args:
        text: The rendered document.
        repo_root: Repository root, used to locate a local ``.env``. Defaults to this file's
            parent's parent.

    Returns:
        One string per finding, naming the kind of secret and **not** quoting it.
    """
    root = repo_root if repo_root is not None else Path(__file__).resolve().parent.parent
    findings: list[str] = []
    for label, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"matched {label}")
    for value in _dotenv_values(root):
        if value in text:
            findings.append("contains a value from the local .env")
            break
    return findings


# ---------------------------------------------------------------------------------------
# Selection.
# ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Selection:
    """What a rule selected, plus everything the emitted document needs."""

    record: SampleRecord
    companion: SampleRecord | None = None
    notes: tuple[str, ...] = ()
    #: Extra ``(label, value)`` provenance rows, rendered under the standard ones.
    facts: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Rule:
    """One deterministic selection rule.

    Attributes:
        slug: Stable slug — also the output filename stem, so the paper can cite a file.
        number: The rule's number in the outline's table (1-3).
        title: Human title, as the paper will name the example.
        statement: The rule, in full, in the words the paper quotes. Rendered verbatim into the
            output so the artifact carries its own justification.
        tie_break: How ties are broken, stated separately because "deterministic" is the claim
            that most needs evidence.
        select: The implementation.
    """

    slug: str
    number: int
    title: str
    statement: str
    tie_break: str
    select: Callable[[Sequence[SampleRecord]], Selection | None]
    depends_on: tuple[str, ...] = ()


def _language_note(text: str) -> str:
    """A heuristic label for a prompt's language. **Annotation only, never selection.**"""
    return "Portuguese (accented characters present)" if any(
        ch in text for ch in _PT_MARKERS
    ) else "English (no Portuguese diacritics)"


def select_disclosure_pair(records: Sequence[SampleRecord]) -> Selection | None:
    """Rule 1 — the hero: the disclosure pair."""
    rows = first_epoch(records)
    brazil = {r.sample_id: r for r in rows if r.task == BRAZIL_DISCLOSURE_TASK}
    eu = {r.sample_id: r for r in rows if r.task == EU_DISCLOSURE_TASK}
    for sample_id in sorted(brazil, key=sample_sort_key):
        b = brazil[sample_id]
        e = eu.get(sample_id)
        if e is None:
            continue
        # "Same model, same scorer" is part of the rule, not an assumption about the log dir.
        if b.model != e.model or b.deterministic_scorer != e.deterministic_scorer:
            continue
        if b.deterministic_score == 0.0 and e.deterministic_score == 1.0:
            return Selection(
                record=b,
                companion=e,
                notes=(
                    "The two prompts are paired **by sample id**, which is positional: both "
                    "datasets are ordered lists with no explicit `Sample.id`, so Inspect numbers "
                    "them 1..N. `human_deception`'s prompts come from the upstream COMPL-AI "
                    "Hugging Face set and are **not** translations of the Brazil ones. Both "
                    "prompts are printed in full below precisely so a reader can judge whether "
                    "this pair is the finding or an artifact.",
                ),
                facts=(
                    ("Brazil prompt language (heuristic, annotation only)", _language_note(b.prompt)),
                    ("EU prompt language (heuristic, annotation only)", _language_note(e.prompt)),
                    ("Shared scorer", f"`{b.deterministic_scorer}`"),
                ),
            )
    return None


def select_judge_divergence(records: Sequence[SampleRecord]) -> Selection | None:
    """Rule 2 — deterministic ↔ judge divergence, on the held-out slice."""
    candidates = [
        r
        for r in first_epoch(records)
        if r.split == SPLIT_HELD_OUT
        and r.judge_score is not None
        and r.deterministic_score is not None
    ]
    if not candidates:
        return None

    def key(record: SampleRecord) -> tuple[float, tuple[int, int, str], str]:
        deterministic = record.deterministic_score
        judge = record.judge_score
        assert deterministic is not None and judge is not None
        # Largest |Δ| wins; ties go to the lowest sample id, then to the alphabetically first
        # task (sample ids are only unique within a task, so the task name is the final key).
        return (-abs(deterministic - judge), sample_sort_key(record.sample_id), record.task)

    chosen = min(candidates, key=key)
    verdicts = chosen.judge_verdicts
    notes = [
        "The two scores are **different measures**: the deterministic one is the fraction of "
        "rubric elements its cue detectors find; the judge's is Inspect `accuracy` over the "
        "`C`/`P`/`I` grade (1.0 / 0.5 / 0.0), i.e. whether *every* element was judged a "
        "substantive commitment. Δ is a distance between two stated measures, not an error.",
    ]
    if not verdicts.parsed:
        notes.append(
            "**The grader wrote no parsable per-element verdict line for this sample.** Phase 6 "
            "requires one per element before the letter; its absence is a finding about the "
            "grader's format compliance and is reported rather than smoothed over."
        )
    if verdicts.count_matches_verdicts is False:
        notes.append(
            "**The grader's own `SUBSTANTIVE COUNT` contradicts its own verdict lines.** The "
            "letter is defined as a function of the count, so the grade does not follow from the "
            "stated findings."
        )
    facts: list[tuple[str, str]] = [
        ("Split", f"`{chosen.split}`"),
        ("Grader (as resolved for this sample)", f"`{chosen.judge_grader or 'unrecorded'}`"),
    ]
    if chosen.prompt_mode:
        facts.append(("Prompt condition", f"`{chosen.prompt_mode}`"))
    return Selection(record=chosen, notes=tuple(notes), facts=tuple(facts))


def _unknown_letter(record: SampleRecord) -> tuple[str | None, str | None]:
    """The Unknown option's presented letter, and a refusal reason when it cannot be trusted.

    Two independent sources, and they must agree:

    1. ``metadata["unknown_answer"]`` — written by ``bbq_brazil``'s dataset **after** the
       per-sample shuffle (Phase 2b), so it is the letter as the model saw it;
    2. the position of the Unknown option's text in ``Sample.choices``, which is the order the
       model was shown.

    Disagreement means either the shuffle or the metadata is wrong, and a wrong Unknown letter
    inverts the finding — so the tool refuses instead of preferring one.
    """
    declared = record.metadata.get("unknown_answer")
    declared_letter = str(declared) if isinstance(declared, str) and declared else None
    derived_letter: str | None = None
    for index, choice in enumerate(record.choices):
        if UNKNOWN_ANSWER_TEXT.casefold() in choice.casefold():
            derived_letter = chr(ord("A") + index)
            break
    if declared_letter and derived_letter and declared_letter != derived_letter:
        return None, (
            f"sample {record.sample_id}: metadata['unknown_answer']={declared_letter!r} "
            f"disagrees with the position of {UNKNOWN_ANSWER_TEXT!r} in the presented choices "
            f"({derived_letter!r})"
        )
    letter = declared_letter or derived_letter
    if letter is None:
        return None, (
            f"sample {record.sample_id}: no metadata['unknown_answer'] and no "
            f"{UNKNOWN_ANSWER_TEXT!r} option among the presented choices"
        )
    return letter, None


def select_bbq_stereotype_pick(records: Sequence[SampleRecord]) -> Selection | None:
    """Rule 3 — the ``bbq_brazil`` ambiguous-context named-individual pick, shuffle-safe."""
    rows = [
        r
        for r in first_epoch(records)
        if r.task == BBQ_TASK and r.context_condition == AMBIGUOUS
    ]
    problems: list[str] = []
    for record in sorted(rows, key=lambda r: sample_sort_key(r.sample_id)):
        letters = record.answer_letters()
        if len(letters) != 1:
            # No option marked, or several: the model did not choose a named individual *over*
            # the Unknown option, so the rule does not fire. Recorded, not silently dropped.
            continue
        unknown, problem = _unknown_letter(record)
        if problem is not None:
            problems.append(problem)
            continue
        if unknown is None or letters[0] == unknown:
            continue
        stereotyped = record.metadata.get("stereotyped_answer")
        stereotyped_letter = str(stereotyped) if isinstance(stereotyped, str) else None
        picked_stereotype = stereotyped_letter is not None and letters[0] == stereotyped_letter
        return Selection(
            record=record,
            notes=(
                "Since Phase 2b every `bbq_brazil` sample carries a **deterministic per-sample "
                "shuffle** of its three options, so the Unknown option is *not* always C. The "
                "rule is resolved against the sample's own post-shuffle "
                "`metadata['unknown_answer']`, cross-checked against the position of "
                f"*{UNKNOWN_ANSWER_TEXT}* in the presented choices; a disagreement makes the "
                "tool refuse rather than guess.",
                "An ambiguous context licenses **no** named individual, so the gold answer is "
                "the Unknown option under both question polarities. Choosing a person is the "
                "bias signal; choosing *the stereotyped* person is the sharper one, and which "
                "of the two happened here is stated below rather than left to the reader.",
            ),
            facts=(
                ("Unknown option letter (post-shuffle)", f"`{unknown}`"),
                ("Model picked", f"`{letters[0]}`"),
                (
                    "Stereotype-congruent letter for this polarity",
                    f"`{stereotyped_letter}`" if stereotyped_letter else "unrecorded",
                ),
                (
                    "Picked the stereotype-congruent option",
                    "**yes**" if picked_stereotype else "no (the other named individual)",
                ),
                ("Question polarity", f"`{record.polarity or 'unrecorded'}`"),
                ("Category", f"`{record.metadata.get('category', 'unrecorded')}`"),
            )
            + (
                (("Refusals while scanning", "; ".join(problems)),) if problems else ()
            ),
        )
    return None


RULES: tuple[Rule, ...] = (
    Rule(
        slug="01-disclosure-pair",
        number=1,
        title="The hero — the disclosure pair",
        statement=(
            "Same model, same `match` scorer: the lowest-`sample_id` `human_deception_brazil` "
            "sample scoring 0 whose `human_deception` counterpart at the same `sample_id` "
            "scored 1. Epoch 1 only."
        ),
        tie_break=(
            "None needed — sample ids are unique within a task and the rule takes the lowest, "
            "with integer ids ordered numerically (2 before 10, not after)."
        ),
        select=select_disclosure_pair,
        depends_on=(
            "`EvalSample.id` (both tasks; positional pairing)",
            "`EvalSample.input`, `EvalSample.output.completion`",
            "`Score.value` of the shared `match` scorer",
            "`EvalSpec.model` (the rule requires the same model on both sides)",
        ),
    ),
    Rule(
        slug="02-judge-divergence",
        number=2,
        title="Deterministic ↔ judge divergence",
        statement=(
            "The held-out sample carrying **both** a deterministic and an LLM-judge score with "
            "the largest |deterministic − judge|. Epoch 1 only."
        ),
        tie_break=(
            "Lowest `sample_id` first, then the alphabetically first task name (sample ids are "
            "unique only within a task)."
        ),
        select=select_judge_divergence,
        depends_on=(
            "`EvalSample.scores` carrying two entries (the deterministic scorer and "
            "`judge_scorer`)",
            "`Score.metadata['elements_present']` / `['items_covered']` (the cue-list breakdown)",
            "`Score.explanation` of the judge (the per-element `SUBSTANTIVE`/`ABSENT` lines "
            "Phase 6 requires)",
            "`Score.metadata['judge_grader']` (the grader that actually graded)",
            "`sample.metadata['split']`",
        ),
    ),
    Rule(
        slug="03-bbq-stereotype-pick",
        number=3,
        title="`bbq_brazil` stereotype pick",
        statement=(
            "The lowest-`sample_id` ambiguous-context `bbq_brazil` sample where the model marked "
            "exactly one option and that option was **not** the Unknown one "
            f"(*{UNKNOWN_ANSWER_TEXT}*) — i.e. it chose a named individual where the context "
            "licenses none. Epoch 1 only."
        ),
        tie_break=(
            "None needed — the lowest `sample_id` among the qualifying samples, integer ids "
            "ordered numerically. A sample where the model marked no option, or more than one, "
            "does not qualify: it did not choose a person *over* the Unknown option."
        ),
        select=select_bbq_stereotype_pick,
        depends_on=(
            "`sample.metadata['unknown_answer']` (post-shuffle letter, Phase 2b)",
            "`sample.choices` (the presented order, for the cross-check)",
            "`Score.answer` of the reused `choice()` scorer (the letters the model marked)",
            "`sample.metadata['context_condition']`, `['polarity']`, `['stereotyped_answer']`",
        ),
    ),
)


# ---------------------------------------------------------------------------------------
# Rendering.
# ---------------------------------------------------------------------------------------
def _fmt_score(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def _log_name(record: SampleRecord) -> str:
    """The log file's **basename**.

    Never the absolute path: it would put the operator's home directory into a committed file and
    would make the output non-reproducible across machines.
    """
    return Path(record.log_file).name if record.log_file else "unrecorded"


def _element_table(record: SampleRecord) -> list[str]:
    """The per-element rubric-hit breakdown, cue detector beside judge verdict."""
    deterministic = record.deterministic_elements
    if not deterministic:
        return []
    verdicts = record.judge_verdicts
    lines = [
        "### Per-element breakdown",
        "",
        "| Element | Cue detector | LLM judge |",
        "|---|---|---|",
    ]
    for element, present in deterministic.items():
        judged = verdicts.elements.get(element)
        judge_cell = (
            "—" if judged is None else ("SUBSTANTIVE" if judged else "ABSENT")
        )
        lines.append(
            f"| `{element}` | {'present' if present else 'absent'} | {judge_cell} |"
        )
    lines.append("")
    if verdicts.stated_count is not None:
        lines.append(
            f"Grader's own count: **SUBSTANTIVE COUNT: {verdicts.stated_count}/"
            f"{verdicts.stated_total}**."
        )
        lines.append("")
    if verdicts.unmatched_keys:
        lines.append(
            "Verdict lines whose key is not an element of this sample "
            f"(reported, not silently dropped): {', '.join(sorted(set(verdicts.unmatched_keys)))}."
        )
        lines.append("")
    return lines


def _transcript_block(record: SampleRecord, heading: str) -> list[str]:
    """Prompt + completion + score for one sample, in fenced blocks."""
    lines = [
        f"## {heading}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Task | `{record.task}` |",
        f"| Sample id | `{record.sample_id}` |",
        f"| Epoch | {record.epoch} |",
        f"| Model | `{record.model or 'unrecorded'}` |",
        f"| Scorer | `{record.deterministic_scorer or 'none'}` |",
        f"| Score | {_fmt_score(record.deterministic_score)} |",
    ]
    if record.judge_score is not None:
        lines.append(
            f"| LLM-judge score | {_fmt_score(record.judge_score)} "
            f"(grade `{record.raw_scores.get(JUDGE_SCORER_NAME)}`) |"
        )
    if record.target:
        lines.append(f"| Target | `{record.target}` |")
    # Only for a multiple-choice sample. ``Score.answer`` means "the letters the model marked"
    # for ``choice()`` but "the completion" for the rubric scorers, so rendering it as *Marked*
    # on a rubric transcript printed the whole completion in a one-line table cell.
    if record.choices and record.answer_letters():
        lines.append(f"| Marked | `{', '.join(record.answer_letters())}` |")
    lines.append(f"| Log file | `{_log_name(record)}` |")
    lines.append("")
    if record.choices:
        lines.append("### Options as presented")
        lines.append("")
        for index, choice in enumerate(record.choices):
            lines.append(f"{chr(ord('A') + index)}. {choice}")
        lines.append("")
    lines.append("### Prompt")
    lines.append("")
    lines.append("```text")
    lines.append(record.prompt.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("### Completion")
    lines.append("")
    lines.append("```text")
    lines.append(record.completion.rstrip() or "(empty completion)")
    lines.append("```")
    lines.append("")
    lines.extend(_element_table(record))
    return lines


_BANNER = (
    "<!-- Generated by tools/extract_examples.py — do not hand-edit. Re-run the tool. -->"
)


def render_markdown(rule: Rule, selection: Selection) -> str:
    """The emitted document for one selected example."""
    record = selection.record
    lines: list[str] = [
        _BANNER,
        "",
        f"# Example {rule.number} — {rule.title}",
        "",
        "> **Selection rule (deterministic; quote this in the paper):**",
        f"> {rule.statement}",
        ">",
        f"> **Tie-break:** {rule.tie_break}",
        "",
        f"**Selected:** `{record.task}` sample `{record.sample_id}` "
        f"(epoch {record.epoch}), model `{record.model or 'unrecorded'}`.",
        "",
        "This file is machine-selected and machine-written. It is *not* the most striking "
        "transcript in the run; it is the one the stated rule picks. Re-running the tool over "
        "the same logs reproduces it byte for byte.",
        "",
    ]
    for note in selection.notes:
        lines.append(f"- {note}")
    if selection.notes:
        lines.append("")
    if selection.facts:
        lines.append("| | |")
        lines.append("|---|---|")
        for label, value in selection.facts:
            lines.append(f"| {label} | {value} |")
        lines.append("")
    lines.append("**Log fields this rule reads:** " + "; ".join(rule.depends_on) + ".")
    lines.append("")

    if selection.companion is not None:
        lines.extend(_transcript_block(record, "Brazil side"))
        lines.extend(_transcript_block(selection.companion, "EU counterpart"))
    else:
        lines.extend(_transcript_block(record, "Transcript"))
    return "\n".join(lines).rstrip() + "\n"


_HTML_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        max-width: 52rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
pre {{ background: #f6f7f9; padding: .75rem; overflow-x: auto; white-space: pre-wrap; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #d0d4da; padding: .25rem .5rem; text-align: left; }}
blockquote {{ border-left: 3px solid #8a94a6; margin-left: 0; padding-left: .75rem;
              color: #333; }}
</style></head><body>
"""


def render_html(rule: Rule, selection: Selection) -> str:
    """A minimal self-contained HTML view of the same document.

    Deliberately not a Markdown renderer: the Markdown is the artifact, and this is a
    ``<pre>``-wrapped, fully escaped copy of it for anyone who wants to open it in a browser.
    Escaping everything is what keeps a model completion from injecting markup.
    """
    body = html.escape(render_markdown(rule, selection))
    title = html.escape(f"Example {rule.number} — {rule.title}")
    return f"{_HTML_HEAD.format(title=title)}<pre>{body}</pre>\n</body></html>\n"


# ---------------------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------------------
@dataclass
class ExtractionResult:
    """What one invocation did — returned for tests, printed for humans."""

    selected: dict[str, Selection] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)
    documents: dict[str, str] = field(default_factory=dict)


def extract(
    log_dirs: Sequence[str],
    out_dir: str | Path = DEFAULT_OUT_DIR,
    *,
    write: bool = True,
    emit_html: bool = False,
    repo_root: Path | None = None,
) -> ExtractionResult:
    """Apply every rule to the records of ``log_dirs`` and (optionally) write the documents.

    Args:
        log_dirs: One or more Inspect run directories. Several are allowed so a Phase 8 operator
            can produce all three examples from the subject run and the judge run in one call.
        out_dir: Where the documents go.
        write: ``False`` renders without touching the filesystem (used by the tests and by
            ``--dry-run``).
        emit_html: Also write a ``.html`` sibling of each ``.md``.
        repo_root: Passed to :func:`scan_for_secrets`; defaults to the repo this file is in.

    Returns:
        The :class:`ExtractionResult`.

    Raises:
        SystemExit: if any rendered document trips :func:`scan_for_secrets`. Nothing is written
            in that case — not even the documents that passed.
    """
    records: list[SampleRecord] = []
    for log_dir in log_dirs:
        records.extend(load_samples(log_dir))

    result = ExtractionResult()
    for rule in RULES:
        selection = rule.select(records)
        if selection is None:
            result.missing.append(rule.slug)
            continue
        result.selected[rule.slug] = selection
        result.documents[f"{rule.slug}.md"] = render_markdown(rule, selection)
        if emit_html:
            result.documents[f"{rule.slug}.html"] = render_html(rule, selection)

    # Scan **everything** before writing **anything**: a partial write of "the safe ones" would
    # leave the repo in a state where the control had already failed once.
    findings: list[str] = []
    for name, document in result.documents.items():
        for finding in scan_for_secrets(document, repo_root=repo_root):
            findings.append(f"{name}: {finding}")
    if findings:
        raise SystemExit(
            "refusing to write — the rendered transcripts contain what looks like a secret:\n  "
            + "\n  ".join(findings)
        )

    if write:
        target = Path(out_dir)
        target.mkdir(parents=True, exist_ok=True)
        for name, document in sorted(result.documents.items()):
            path = target / name
            path.write_text(document, encoding="utf-8")
            result.written.append(path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Prints the rule applied and the ``sample_id`` selected, per rule."""
    parser = argparse.ArgumentParser(
        prog="extract_examples.py",
        description=(
            "Extract the paper's three transcripts from Inspect logs by stated deterministic "
            "rules. Prints the rule applied and the sample_id it selected."
        ),
    )
    parser.add_argument("log_dirs", nargs="+", help="Inspect run directories to read.")
    parser.add_argument(
        "--out", default=DEFAULT_OUT_DIR, help=f"Output directory (default: {DEFAULT_OUT_DIR})."
    )
    parser.add_argument("--html", action="store_true", help="Also write an HTML sibling.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Select and render, but write nothing."
    )
    args = parser.parse_args(argv)

    result = extract(
        args.log_dirs,
        out_dir=args.out,
        write=not args.dry_run,
        emit_html=args.html,
    )

    for rule in RULES:
        selection = result.selected.get(rule.slug)
        print(f"Rule {rule.number} — {rule.title}")
        print(f"  rule:      {rule.statement}")
        print(f"  tie-break: {rule.tie_break}")
        if selection is None:
            print("  SELECTED:  (nothing — no sample in these logs satisfies the rule)")
        else:
            record = selection.record
            print(
                f"  SELECTED:  task={record.task} sample_id={record.sample_id} "
                f"epoch={record.epoch} model={record.model}"
            )
            if selection.companion is not None:
                companion = selection.companion
                print(
                    f"  paired with task={companion.task} "
                    f"sample_id={companion.sample_id} epoch={companion.epoch}"
                )
        print()

    for path in result.written:
        print(f"wrote {path}")
    if args.dry_run:
        print("(dry run — nothing written)")
    if result.missing:
        print(
            "rules that selected nothing: "
            + ", ".join(result.missing)
            + "  (this is the correct behaviour when the run does not contain the "
            "required tasks/slices — the rule is not relaxed to find something)"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via ``main`` in the tests
    sys.exit(main())
