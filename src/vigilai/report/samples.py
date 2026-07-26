"""Sample-level layer (iteration 2, Phase 7) — the one place in vigilAI that loads samples.

:mod:`vigilai.report.brazil_report` is **header-only by design**: it reads every log with
``read_eval_log(..., header_only=True)`` and never touches ``log.samples``, which is what keeps
``vigilai report`` cheap on a 400-sample × 10-epoch run and what keeps the aggregator honest
(a per-article number can only come from a metric the scorer declared, never from something
re-derived out of a transcript). Two Phase 7 outputs need the opposite — the individual prompt,
completion and per-sample scores:

* **Deterministic ↔ LLM-judge agreement per sample** (reviewer ask #2, the finer-grained half).
  The report's judge table compares two *aggregates*; this module compares the two scorers on the
  **same sample**, and — because Phase 6 makes the judge write a per-element ``SUBSTANTIVE`` /
  ``ABSENT`` verdict line before its letter — on the **same rubric element**. Per-element
  agreement is what actually answers "how much of the deterministic score is keyword surface":
  a task-level delta of 0.2 could be 20% of samples disagreeing everywhere or every sample
  disagreeing on one element, and those are different findings.
* **Rule-based transcript extraction** (``tools/extract_examples.py``), which needs the prompt and
  the completion verbatim.

So this module sits **beside** the aggregator rather than inside it. ``build_brazil_report`` is
unchanged and still never loads a sample; ``tests/test_brazil_report.py::TestHeaderOnlyGuarantee``
pins that as a property of the source, not as a comment.

Reading discipline
------------------

* ``read_eval_log(..., resolve_attachments="core")``. Inspect attachment-ifies text over 100
  characters **inside events**, and data-URI images inside ``input`` / ``messages``; the core
  fields this module reads are normally inline, but resolving is cheap and makes the reader
  correct for any log rather than for the logs that happen to be small.
* **Every epoch is returned.** Phases 8-9 run ``--epochs 10``, so one dataset sample becomes ten
  ``EvalSample`` rows sharing an ``id``. Silently keeping the first would be a lie about ``n``,
  and silently keeping all of them would inflate it; :func:`load_samples` returns them all with
  their ``epoch``, and each consumer states what it does with them
  (:func:`judge_agreement` reduces per sample by the mean — the same reducer Inspect applies
  before computing the headline metric — while the transcript rules take epoch 1, because a
  transcript is one concrete exchange).
* **Sorted deterministically** by ``(task, sample id, epoch)``, with integer ids ordered
  numerically rather than lexicographically (``2`` before ``10``), because two of the three
  extraction rules are "the lowest ``sample_id`` such that …" and a rule whose answer depends on
  string collation is not a rule.

Scales, restated because the two columns are different measures
---------------------------------------------------------------

The deterministic scorers report the **fraction of rubric elements detected**; the judge reports
Inspect ``accuracy`` over ``C`` / ``P`` / ``I`` (1.0 / 0.5 / 0.0), i.e. **whether every element
was judged a substantive commitment**. They share the 0-1 range and are not two estimates of one
quantity, so ``|Δ|`` here is a distance between two stated measures — never an error rate and
never a "disagreement rate". The per-element statistics below do not have that problem: both
sides are a boolean per element, so ``cue-list only`` / ``judge only`` are directly comparable and
are the numbers to quote.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from inspect_ai.log import EvalLog
from inspect_ai.log import EvalLogInfo
from inspect_ai.log import EvalSample
from inspect_ai.log import list_eval_logs
from inspect_ai.log import read_eval_log
from inspect_ai.scorer import Score
from inspect_ai.scorer import value_to_float


# The registry prefix Inspect puts on a task name in the log ("vigilai/bbq_brazil"). Mirrors
# ``brazil_report._REGISTRY_PREFIX``; duplicated rather than imported so this module stays
# usable on its own (and because Resolution 6 plans to extract a jurisdiction-neutral report).
_REGISTRY_PREFIX = "vigilai/"

# Scorer names. Same discipline as ``brazil_report``: literals here, pinned against
# ``vigilai.tasks.judge`` by a test, because the report layer must not import the task package.
JUDGE_SCORER_NAME = "judge_scorer"
DETERMINISTIC_SCORER_NAMES: tuple[str, ...] = (
    "rubric_scorer",
    "contestation_scorer",
    "aia_checklist_scorer",
)

# ``Score.metadata`` keys holding the deterministic per-element verdicts, in the two shapes the
# repo uses: ``elements_present`` for the two Art. 6 rubric scorers, ``items_covered`` for
# ``aia_checklist``. Both are ``{element_id: bool}``.
_ELEMENT_METADATA_KEYS: tuple[str, ...] = ("elements_present", "items_covered")

# Sample-metadata keys surfaced as first-class fields on :class:`SampleRecord`. All are written by
# the vigilAI datasets; a task that does not write one simply reports ``None``.
_SPLIT_KEY = "split"
_SECTOR_KEY = "sector"
_POLARITY_KEY = "polarity"
_CONTEXT_CONDITION_KEY = "context_condition"
# Written by ``aia_checklist`` since Resolution 9. The two prompt conditions differ by most of the
# score, so an unlabelled ``aia_checklist`` transcript cannot be interpreted (cross-phase
# correction, "Added in the Resolution 9 pass").
_PROMPT_MODE_KEY = "prompt_mode"

#: Split name for the reserved slice the judge grades (``vigilai.tasks.rubric_scenario``).
SPLIT_HELD_OUT = "held_out"

#: Label used for the "every sample in the run" slice. Resolution 1 requires held-out and
#: full-set agreement to be reported **separately and always labelled**; these are those labels.
SLICE_FULL_SET = "full_set"
SLICE_HELD_OUT = "held_out"

# A judge verdict line, e.g. ``- criteria_used: SUBSTANTIVE — "a razão dívida/renda de 45%"``.
# Deliberately permissive on the decoration and strict on the verdict word: the grader is told to
# write ``- <key>: SUBSTANTIVE — …`` but a real model will sometimes number the lines, bold the
# key, or use a plain hyphen instead of an em dash. The **key** is validated separately, against
# the deterministic scorer's own element ids for that sample, so a hallucinated key is counted as
# unmatched rather than silently believed.
_VERDICT_RE = re.compile(
    r"^[\s>*\-•]*(?:\d+[.)]\s*)?[`*_\s]*(?P<key>[A-Za-z][A-Za-z0-9_]{2,})[`*_\s]*\s*[:\-–—]\s*"
    r"[`*_\s]*(?P<verdict>SUBSTANTIVE|ABSENT)\b",
    re.MULTILINE,
)

# ``SUBSTANTIVE COUNT: 4/6`` — the count the grader is required to write before its letter.
_COUNT_RE = re.compile(
    r"SUBSTANTIVE\s+COUNT\s*[:=]?\s*\**\s*(?P<present>\d+)\s*/\s*(?P<total>\d+)",
    re.IGNORECASE,
)

_VALUE_TO_FLOAT = value_to_float()


def _bare_task_name(task: str) -> str:
    """Strip the Inspect registry prefix from a logged task name."""
    return task[len(_REGISTRY_PREFIX) :] if task.startswith(_REGISTRY_PREFIX) else task


def sample_sort_key(sample_id: str) -> tuple[int, int, str]:
    """Sort key making "the lowest ``sample_id``" mean what a reader expects.

    Inspect ids are ``int | str``. An all-integer dataset (every vigilAI dataset that does not set
    ``Sample.id`` explicitly) must sort **numerically** — ``2`` before ``10``, not after it — or
    the two "lowest ``sample_id``" extraction rules would select whichever sample happened to sort
    first as a string, which is a different rule on a 400-sample run than on a 9-sample one.
    String ids (``bbq_brazil`` writes ``Race_003_amb_neg``) sort lexicographically, after all
    integer ids, so a mixed set is still totally ordered.
    """
    try:
        return (0, int(sample_id), "")
    except ValueError:
        return (1, 0, sample_id)


def _prompt_text(sample: EvalSample) -> str:
    """The sample's prompt as text.

    ``EvalSample.input`` is ``str | list[ChatMessage]``. Every vigilAI dataset uses the string
    form, but an upstream COMPL-AI task may use chat inputs and a transcript that silently
    rendered ``[ChatMessageUser(...)]`` would be worse than useless, so both are handled.
    """
    raw = sample.input
    if isinstance(raw, str):
        return raw
    parts: list[str] = []
    for message in raw:
        text = getattr(message, "text", None)
        if text:
            parts.append(f"[{message.role}] {text}")
    return "\n\n".join(parts)


def _score_float(score: Score) -> float | None:
    """Numeric reading of a ``Score.value``, or ``None`` when it has none.

    Uses Inspect's own ``value_to_float`` so ``"C"`` / ``"P"`` / ``"I"`` map to 1.0 / 0.5 / 0.0
    exactly as the ``accuracy`` metric maps them — the sample-level number and the aggregate
    number in ``vigilai report`` are then the same quantity, which is the whole point of putting
    them side by side.
    """
    value = score.value
    if isinstance(value, (int, float, bool, str)):
        try:
            return float(_VALUE_TO_FLOAT(value))
        except (TypeError, ValueError):
            return None
    return None


def _element_verdicts(score: Score) -> dict[str, bool]:
    """The deterministic scorer's per-element booleans, ``{}`` when it recorded none."""
    metadata = score.metadata or {}
    for key in _ELEMENT_METADATA_KEYS:
        raw = metadata.get(key)
        if isinstance(raw, Mapping):
            return {str(k): bool(v) for k, v in raw.items()}
    return {}


@dataclass(frozen=True)
class JudgeVerdicts:
    """What Phase 6's judge wrote, parsed out of ``Score.explanation``.

    Phase 6 requires the grader to emit one ``<key>: SUBSTANTIVE|ABSENT`` line per element and a
    ``SUBSTANTIVE COUNT: k/n`` line **before** the letter grade, specifically so this phase can
    read per-element verdicts without a second run.

    Attributes:
        elements: ``{element_id: True if SUBSTANTIVE}``, restricted to keys the deterministic
            scorer also reported for the same sample — a grader that invents a key is counted in
            ``unmatched_keys`` rather than believed.
        unmatched_keys: Verdict-line keys that are not element ids of this sample. Non-empty means
            the grader drifted from the required format (or hallucinated an element), which is a
            **finding about the grader** and is surfaced rather than swallowed.
        stated_count: The ``k`` of ``SUBSTANTIVE COUNT: k/n``, or ``None`` if absent.
        stated_total: The ``n`` of the same line, or ``None``.
        parsed: True when at least one verdict line was found.
    """

    elements: dict[str, bool] = field(default_factory=dict)
    unmatched_keys: tuple[str, ...] = ()
    stated_count: int | None = None
    stated_total: int | None = None

    @property
    def parsed(self) -> bool:
        """True when the explanation carried at least one usable verdict line."""
        return bool(self.elements) or bool(self.unmatched_keys)

    @property
    def count_matches_verdicts(self) -> bool | None:
        """Does the grader's own ``SUBSTANTIVE COUNT`` agree with its own verdict lines?

        ``None`` when there is no count line to check. A ``False`` is worth reporting: the letter
        grade is defined as a function of the count, so a grader whose count contradicts its
        verdicts has produced a letter that does not follow from its stated findings.
        """
        if self.stated_count is None or not self.elements:
            return None
        return self.stated_count == sum(1 for ok in self.elements.values() if ok)


def parse_judge_verdicts(explanation: str | None, known_elements: Iterable[str]) -> JudgeVerdicts:
    """Parse a grader completion into per-element verdicts.

    Args:
        explanation: ``Score.explanation`` of the judge score — ``model_graded_qa`` stores the
            grader's **full completion** there, which is why no extra run is needed.
        known_elements: The element ids the deterministic scorer reported for this sample. Keys
            are matched against these (case-insensitively) so a stray line cannot invent an
            element, and so ``aia_checklist``'s per-scenario item set is respected automatically.

    Returns:
        The parsed :class:`JudgeVerdicts`.
    """
    if not explanation:
        return JudgeVerdicts()
    by_lower = {element.lower(): element for element in known_elements}
    elements: dict[str, bool] = {}
    unmatched: list[str] = []
    for match in _VERDICT_RE.finditer(explanation):
        raw_key = match.group("key")
        verdict = match.group("verdict").upper() == "SUBSTANTIVE"
        element = by_lower.get(raw_key.lower())
        if element is None:
            if raw_key.upper() not in {"SUBSTANTIVE", "ABSENT", "GRADE", "COUNT"}:
                unmatched.append(raw_key)
            continue
        # First verdict per element wins: a grader that restates a verdict in a closing summary
        # must not be able to flip it, and "first wins" is stated rather than "last wins" so the
        # parse cannot depend on how chatty the grader was.
        elements.setdefault(element, verdict)
    count_match = _COUNT_RE.search(explanation)
    stated_count = int(count_match.group("present")) if count_match else None
    stated_total = int(count_match.group("total")) if count_match else None
    return JudgeVerdicts(
        elements=elements,
        unmatched_keys=tuple(unmatched),
        stated_count=stated_count,
        stated_total=stated_total,
    )


@dataclass(frozen=True)
class SampleRecord:
    """One ``(task, sample, epoch)`` row of a run, with everything the Phase 7 outputs need.

    Attributes:
        task: Bare task name (registry prefix stripped).
        sample_id: ``EvalSample.id`` as a string. Use :func:`sample_sort_key` to order it.
        epoch: 1-based epoch. ``--epochs 10`` produces ten rows per ``sample_id``.
        model: The evaluated model id, off the log header.
        prompt: The sample input, rendered as text.
        completion: The model's completion.
        target: The sample target (the gold letter for ``bbq_brazil`` / ``human_deception*``).
        choices: The presented answer options, in the order the model saw them — which for
            ``bbq_brazil`` is the **post-shuffle** order since Phase 2b.
        scores: ``{scorer name: numeric value}``, with ``C`` / ``P`` / ``I`` mapped by Inspect's
            own ``value_to_float`` so these match the aggregate metrics.
        raw_scores: ``{scorer name: Score.value}`` unconverted, for a rule that needs the letter.
        answers: ``{scorer name: Score.answer}`` — for ``choice()`` this is the letter(s) the
            model actually marked, which is how rule 3 works under the per-sample shuffle.
        explanations: ``{scorer name: Score.explanation}`` — for the judge this is the grader's
            full completion, i.e. the per-element verdict lines.
        score_metadata: ``{scorer name: Score.metadata}``.
        metadata: The sample's own metadata dict.
        log_file: The ``.eval`` file this row came from, so a quoted transcript is traceable.
        judge_grader_role: The model bound to the ``grader`` role in this run's header, if any.
            Same precedence the report's judge table uses: a **bound** role is the model that
            actually graded (and carries the full ``provider/name`` id), while the per-sample
            stamp records only the resolved model's short name. Both are read; neither is
            invented.
    """

    task: str
    sample_id: str
    epoch: int
    model: str | None
    prompt: str
    completion: str
    target: str
    choices: tuple[str, ...]
    scores: dict[str, float | None]
    raw_scores: dict[str, Any]
    answers: dict[str, str | None]
    explanations: dict[str, str | None]
    score_metadata: dict[str, dict[str, Any]]
    metadata: dict[str, Any]
    log_file: str | None = None
    judge_grader_role: str | None = None

    # -- metadata conveniences ------------------------------------------------------------
    @property
    def split(self) -> str | None:
        """``"held_out"`` / ``"train"`` — the slice label Resolution 1 requires on every stat."""
        value = self.metadata.get(_SPLIT_KEY)
        return str(value) if isinstance(value, str) else None

    @property
    def sector(self) -> str | None:
        """``aia_checklist``'s sector key, ``None`` for every other task."""
        value = self.metadata.get(_SECTOR_KEY)
        return str(value) if isinstance(value, str) else None

    @property
    def polarity(self) -> str | None:
        """``bbq_brazil``'s question polarity (Phase 2b), ``None`` elsewhere."""
        value = self.metadata.get(_POLARITY_KEY)
        return str(value) if isinstance(value, str) else None

    @property
    def context_condition(self) -> str | None:
        """``bbq_brazil``'s ``"ambiguous"`` / ``"disambiguated"`` condition."""
        value = self.metadata.get(_CONTEXT_CONDITION_KEY)
        return str(value) if isinstance(value, str) else None

    @property
    def prompt_mode(self) -> str | None:
        """``aia_checklist``'s ``"unguided"`` / ``"guided"`` frame (Resolution 9)."""
        value = self.metadata.get(_PROMPT_MODE_KEY)
        return str(value) if isinstance(value, str) else None

    # -- score conveniences ---------------------------------------------------------------
    @property
    def deterministic_scorer(self) -> str | None:
        """The name of this row's deterministic score, by the same rule the report uses.

        A named Brazil scorer first, then the first score that is not the judge — so an upstream
        COMPL-AI task graded by ``match`` / ``choice`` resolves without this module enumerating
        every upstream scorer.
        """
        for name in DETERMINISTIC_SCORER_NAMES:
            if name in self.scores:
                return name
        return next((name for name in self.scores if name != JUDGE_SCORER_NAME), None)

    @property
    def deterministic_score(self) -> float | None:
        """The deterministic scorer's numeric value for this row."""
        name = self.deterministic_scorer
        return self.scores.get(name) if name else None

    @property
    def judge_score(self) -> float | None:
        """The judge's numeric value for this row (``C``/``P``/``I`` → 1.0/0.5/0.0)."""
        return self.scores.get(JUDGE_SCORER_NAME)

    @property
    def judge_grader(self) -> str | None:
        """The grader that **actually** graded this row, stamped by ``judge_scorer``.

        Read off the sample rather than the header on purpose: a mock-graded log must never be
        readable as an Opus-graded one.
        """
        value = (self.score_metadata.get(JUDGE_SCORER_NAME) or {}).get("judge_grader")
        return str(value) if isinstance(value, str) else None

    @property
    def judge_grader_display(self) -> str | None:
        """The grader id to *show*: the bound role's full id, else the per-sample stamp.

        Exactly the precedence ``brazil_report._judge_grader_from_log`` uses for the report
        header. The stamp alone renders as ``model`` for ``mockllm/model``, which is true but
        unreadable in an artifact; the bound role carries ``mockllm/model``. When nothing is
        bound — the normal shape of a real run — the stamp is all there is, and it is the
        *resolved* grader, so it still cannot claim Opus graded a mock-graded log.
        """
        return self.judge_grader_role or self.judge_grader

    @property
    def deterministic_elements(self) -> dict[str, bool]:
        """The deterministic scorer's per-element booleans for this row."""
        name = self.deterministic_scorer
        if name is None:
            return {}
        metadata = self.score_metadata.get(name) or {}
        for key in _ELEMENT_METADATA_KEYS:
            raw = metadata.get(key)
            if isinstance(raw, Mapping):
                return {str(k): bool(v) for k, v in raw.items()}
        return {}

    @property
    def judge_verdicts(self) -> JudgeVerdicts:
        """The judge's per-element verdicts, parsed from its explanation."""
        return parse_judge_verdicts(
            self.explanations.get(JUDGE_SCORER_NAME), self.deterministic_elements
        )

    def answer_letters(self, scorer_name: str | None = None) -> tuple[str, ...]:
        """The option letters a ``choice()``-scored row marked, as a tuple.

        ``choice()`` records them in ``Score.answer`` as ``"A"`` or ``"A, B"``, **in the order the
        model saw** (``multiple_choice()`` defaults to ``shuffle=False`` and ``bbq_brazil``
        shuffles at dataset-construction time), which is what makes rule 3 work without knowing
        where the Unknown option landed.
        """
        name = scorer_name or self.deterministic_scorer
        answer = self.answers.get(name) if name else None
        if not answer:
            return ()
        return tuple(part.strip() for part in answer.split(",") if part.strip())


def _records_from_log(log: EvalLog) -> list[SampleRecord]:
    """Turn one loaded ``EvalLog`` into its :class:`SampleRecord` rows."""
    task_name = _bare_task_name(log.eval.task)
    model = log.eval.model
    log_file = log.location
    role_model = (log.eval.model_roles or {}).get("grader")
    grader_role = str(role_model.model) if role_model is not None else None
    records: list[SampleRecord] = []
    for sample in log.samples or []:
        raw_scores: dict[str, Any] = {}
        scores: dict[str, float | None] = {}
        answers: dict[str, str | None] = {}
        explanations: dict[str, str | None] = {}
        score_metadata: dict[str, dict[str, Any]] = {}
        for name, score in (sample.scores or {}).items():
            raw_scores[name] = score.value
            scores[name] = _score_float(score)
            answers[name] = score.answer
            explanations[name] = score.explanation
            score_metadata[name] = dict(score.metadata or {})
        records.append(
            SampleRecord(
                task=task_name,
                sample_id=str(sample.id),
                epoch=int(sample.epoch),
                model=model,
                prompt=_prompt_text(sample),
                completion=sample.output.completion if sample.output else "",
                target=sample.target if isinstance(sample.target, str) else ", ".join(sample.target),
                choices=tuple(sample.choices or ()),
                scores=scores,
                raw_scores=raw_scores,
                answers=answers,
                explanations=explanations,
                score_metadata=score_metadata,
                metadata=dict(sample.metadata or {}),
                log_file=log_file,
                judge_grader_role=grader_role,
            )
        )
    return records


def load_samples(
    log_dir: str, *, tasks: Sequence[str] | None = None, all_runs: bool = False
) -> list[SampleRecord]:
    """Read every ``.eval`` log under ``log_dir`` **with its samples**.

    The single sample-loading path in the codebase. Deliberately *not* used by
    ``build_brazil_report``, which stays header-only.

    Args:
        log_dir: An Inspect run directory (the timestamped folder under ``logs/``).
        tasks: Optional bare task names to keep. ``None`` loads every task in the directory.
            Filtering happens **after** the header is read but before samples are parsed only in
            the sense that non-matching logs are skipped entirely — a ``--tasks`` filter therefore
            also saves the read.
        all_runs: Load **every** log for a task rather than only its most recent. Off by
            default; see below for why.

    Returns:
        Every ``(task, sample, epoch)`` row, sorted by ``(task, sample id, epoch)`` with integer
        ids ordered numerically.

    **Only the most recent log per task is read, by default.** When a task has been re-run into
    an existing directory the older log is *superseded*, and loading both makes every selection
    rule silently ambiguous: the rules pick "the lowest-``sample_id`` sample scoring 0", and a
    sample that scores 0 in the stale run and 1 in the corrected one satisfies that from the
    stale row. Found on 2026-07-26, in the worst possible way — after a corrected
    ``human_deception_brazil`` re-run, all three transcript rules still resolved against the
    superseded log, so the extractor would have written the retracted finding into the paper's
    evidence directory. Recency comes from ``EvalSpec.created``, matching
    ``brazil_report._load_task_scores``.

    Pass ``all_runs=True`` to get every run's rows — e.g. to compare two conditions of one task
    that genuinely share a directory. That is not how this repo runs the guided and unguided
    ``aia_checklist`` conditions (Resolution 9 puts them in separate ``--log-dir``s, because the
    header-only aggregator would otherwise show one unlabelled row), so the default is the
    safe one.
    """
    wanted = set(tasks) if tasks is not None else None
    selected: list[EvalLogInfo] = []
    latest: dict[str, tuple[tuple[str, str], EvalLogInfo]] = {}
    for info in list_eval_logs(log_dir):
        header = read_eval_log(info, header_only=True)
        task_name = _bare_task_name(header.eval.task)
        if wanted is not None and task_name not in wanted:
            continue
        if all_runs:
            selected.append(info)
            continue
        # ``created`` is ISO-8601, so lexicographic order is chronological; the log path is the
        # tie-break purely so the choice is deterministic for same-second runs.
        key = (header.eval.created or "", str(info.name))
        previous = latest.get(task_name)
        if previous is None or key > previous[0]:
            latest[task_name] = (key, info)
    if not all_runs:
        selected = [entry[1] for entry in latest.values()]

    records: list[SampleRecord] = []
    for info in selected:
        # ``resolve_attachments="core"`` covers the input/messages fields; scores and output are
        # never attachment-ified, so this is the whole surface the reader touches.
        log = read_eval_log(info, resolve_attachments="core")
        records.extend(_records_from_log(log))
    records.sort(key=lambda r: (r.task, sample_sort_key(r.sample_id), r.epoch))
    return records


def first_epoch(records: Sequence[SampleRecord]) -> list[SampleRecord]:
    """The ``epoch == 1`` rows only — what the transcript rules select from.

    A transcript is **one** exchange. With ``--epochs 10`` a sample has ten of them, differing
    only by sampling noise at ``--temperature 1.0``, and "the first" is the only choice that is
    both deterministic and stateable in a paper. Every rule that uses this says so in its own
    description.
    """
    return [record for record in records if record.epoch == 1]


# ---------------------------------------------------------------------------------------
# Agreement statistics.
# ---------------------------------------------------------------------------------------
def _ranks(values: Sequence[float]) -> list[float]:
    """Fractional (tie-averaged) ranks — the ranking Spearman's ρ is defined on."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for index in range(position, end + 1):
            ranks[order[index]] = average
        position = end + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Spearman rank correlation, tie-corrected. ``None`` when it is undefined.

    Undefined means fewer than two pairs, or one side constant (zero rank variance) — which is
    the **normal** case on ``mockllm/model``, where every completion is identical and every score
    the same. Returning ``None`` rather than ``0.0`` or ``nan`` is what stops a mock run from
    printing a correlation it did not measure.

    Implemented here rather than pulled from ``scipy.stats`` so the report layer keeps a small
    import surface and the tie handling is visible; ``tests/test_brazil_report.py`` checks it
    against ``scipy.stats.spearmanr`` on tied and untied data.
    """
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mean_x = sum(rx) / len(rx)
    mean_y = sum(ry) / len(ry)
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    var_x = sum((a - mean_x) ** 2 for a in rx)
    var_y = sum((b - mean_y) ** 2 for b in ry)
    if var_x <= 0.0 or var_y <= 0.0:
        return None
    return cov / math.sqrt(var_x * var_y)


@dataclass(frozen=True)
class ElementAgreement:
    """Per-element agreement between the cue detector and the judge.

    The finer-grained half of reviewer ask #2, available only because Phase 6 makes the grader
    write a verdict line per element. ``deterministic_only`` is the **keyword-surface residue**:
    the cue list credited the element and the judge, reading for a substantive commitment, did
    not. ``judge_only`` points the other way — at the *scorer* rather than the model.
    """

    element: str
    n: int
    both_credit: int
    both_withhold: int
    deterministic_only: int
    judge_only: int

    @property
    def agreement_rate(self) -> float | None:
        """Fraction of rows where the two sides said the same thing."""
        if self.n == 0:
            return None
        return (self.both_credit + self.both_withhold) / self.n


@dataclass(frozen=True)
class AgreementStats:
    """Deterministic ↔ judge agreement over one labelled slice of one task (or of all tasks).

    Attributes:
        label: The slice label — :data:`SLICE_HELD_OUT` or :data:`SLICE_FULL_SET`. Resolution 1
            requires it on every reported figure, so it is a field rather than a caller's memory.
        task: The task name, or ``None`` for a pooled row over several tasks.
        n: Number of **samples** (distinct ``sample_id``), after reducing epochs by the mean.
        n_rows: Number of ``(sample, epoch)`` rows behind those samples.
        mean_abs_delta: Mean ``|deterministic − judge|``. A distance between two *stated
            measures*, not an error.
        mean_delta: Mean signed ``deterministic − judge``. Positive = the cue lists credit more
            than the judge does.
        spearman: Rank correlation of the two per-sample series, or ``None`` when undefined
            (fewer than two samples, or either side constant — the usual mock case).
        direction_disagreements: Samples landing on **opposite sides of 0.5**, i.e. one scorer
            says "more than half established" and the other says "less than half". A sample
            exactly at 0.5 on either side is never counted, so the number is a floor.
        deterministic_higher / judge_higher / ties: The sign breakdown of the delta — the other
            reasonable reading of "disagree in direction", reported alongside rather than chosen
            between.
        element_agreement: Per-element rows, over the ``(sample, epoch)`` rows where both sides
            reported that element. Not epoch-reduced: a boolean verdict has no mean.
        judge_unparsed_rows: Rows carrying a judge score whose explanation yielded **no** verdict
            line. Non-zero is a finding about the grader's format compliance, not a parser excuse.
        judge_count_mismatch_rows: Rows where the grader's own ``SUBSTANTIVE COUNT`` contradicts
            its own verdict lines — its letter then does not follow from its stated findings.
    """

    label: str
    task: str | None
    n: int
    n_rows: int
    mean_abs_delta: float | None
    mean_delta: float | None
    spearman: float | None
    direction_disagreements: int
    deterministic_higher: int
    judge_higher: int
    ties: int
    element_agreement: tuple[ElementAgreement, ...] = ()
    judge_unparsed_rows: int = 0
    judge_count_mismatch_rows: int = 0

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready view, with the scales named so a consumer cannot mistake the columns."""
        return {
            "slice": self.label,
            "task": self.task,
            "samples": self.n,
            "rows": self.n_rows,
            "deterministic_measure": "mean fraction of rubric elements detected",
            "judge_measure": "accuracy (fraction graded C; P counts half)",
            "mean_abs_delta": self.mean_abs_delta,
            "mean_delta": self.mean_delta,
            "spearman": self.spearman,
            "direction_disagreements": self.direction_disagreements,
            "deterministic_higher": self.deterministic_higher,
            "judge_higher": self.judge_higher,
            "ties": self.ties,
            "judge_unparsed_rows": self.judge_unparsed_rows,
            "judge_count_mismatch_rows": self.judge_count_mismatch_rows,
            "element_agreement": [
                {
                    "element": element.element,
                    "rows": element.n,
                    "both_credit": element.both_credit,
                    "both_withhold": element.both_withhold,
                    "deterministic_only": element.deterministic_only,
                    "judge_only": element.judge_only,
                    "agreement_rate": element.agreement_rate,
                }
                for element in self.element_agreement
            ],
        }


def judged_records(records: Sequence[SampleRecord]) -> list[SampleRecord]:
    """Rows carrying **both** a deterministic and a judge score — the only comparable ones."""
    return [
        record
        for record in records
        if record.judge_score is not None and record.deterministic_score is not None
    ]


def _element_rows(records: Sequence[SampleRecord]) -> tuple[
    dict[str, list[tuple[bool, bool]]], int, int
]:
    """Collect ``element -> [(deterministic, judge)]`` plus the two grader-format counters."""
    per_element: dict[str, list[tuple[bool, bool]]] = {}
    unparsed = 0
    mismatched = 0
    for record in records:
        deterministic = record.deterministic_elements
        verdicts = record.judge_verdicts
        if not verdicts.parsed:
            unparsed += 1
            continue
        if verdicts.count_matches_verdicts is False:
            mismatched += 1
        for element, det_value in deterministic.items():
            if element not in verdicts.elements:
                continue
            per_element.setdefault(element, []).append(
                (det_value, verdicts.elements[element])
            )
    return per_element, unparsed, mismatched


def judge_agreement(
    records: Sequence[SampleRecord],
    *,
    label: str = SLICE_FULL_SET,
    task: str | None = None,
) -> AgreementStats:
    """Per-sample deterministic ↔ judge agreement over the records given.

    Epochs are reduced **per sample by the mean**, which is what Inspect's default
    ``epochs_reducer`` does before the headline metric is computed — so ``n`` is the number of
    samples, not the number of generations, and this figure is comparable to the aggregate one in
    ``vigilai report``. Per-element agreement is computed over the unreduced rows instead, because
    a ``SUBSTANTIVE`` / ``ABSENT`` verdict has no mean; ``n_rows`` says how many.

    Args:
        records: Rows to include. Filter *before* calling — :func:`judge_agreement_by_split` is
            the standard way to produce the two labelled slices Resolution 1 requires.
        label: The slice label to record on the result.
        task: The task name to record, or ``None`` for a pooled row.

    Returns:
        The :class:`AgreementStats` for this slice. A slice with no judged rows returns a
        well-formed all-zero/``None`` result rather than raising, so a run with no judge still
        renders a table saying so.
    """
    comparable = judged_records(records)
    by_sample: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for record in comparable:
        deterministic = record.deterministic_score
        judge = record.judge_score
        assert deterministic is not None and judge is not None  # judged_records guarantees it
        by_sample.setdefault((record.task, record.sample_id), []).append(
            (deterministic, judge)
        )

    dets: list[float] = []
    judges: list[float] = []
    for pairs in by_sample.values():
        dets.append(sum(d for d, _ in pairs) / len(pairs))
        judges.append(sum(j for _, j in pairs) / len(pairs))

    n = len(dets)
    deltas = [d - j for d, j in zip(dets, judges)]
    direction = sum(
        1
        for d, j in zip(dets, judges)
        if (d > 0.5 and j < 0.5) or (d < 0.5 and j > 0.5)
    )
    per_element, unparsed, mismatched = _element_rows(comparable)
    element_rows = tuple(
        ElementAgreement(
            element=element,
            n=len(pairs),
            both_credit=sum(1 for d, j in pairs if d and j),
            both_withhold=sum(1 for d, j in pairs if not d and not j),
            deterministic_only=sum(1 for d, j in pairs if d and not j),
            judge_only=sum(1 for d, j in pairs if not d and j),
        )
        for element, pairs in sorted(per_element.items())
    )

    return AgreementStats(
        label=label,
        task=task,
        n=n,
        n_rows=len(comparable),
        mean_abs_delta=(sum(abs(d) for d in deltas) / n) if n else None,
        mean_delta=(sum(deltas) / n) if n else None,
        spearman=spearman(dets, judges),
        direction_disagreements=direction,
        deterministic_higher=sum(1 for d in deltas if d > 0),
        judge_higher=sum(1 for d in deltas if d < 0),
        ties=sum(1 for d in deltas if d == 0),
        element_agreement=element_rows,
        judge_unparsed_rows=unparsed,
        judge_count_mismatch_rows=mismatched,
    )


def judge_agreement_by_split(
    records: Sequence[SampleRecord],
) -> list[AgreementStats]:
    """The two labelled slices Resolution 1 requires, per task and pooled.

    Resolution 1: report agreement **both** ways — held-out only (uncontaminated by the cue-list
    tuning the deterministic scorers went through, but small) and full-set (larger, contaminated)
    — and label both, always. Reporting one is strictly less informative than reporting both, and
    reporting them unlabelled is worse than either.

    Returns:
        Rows ordered ``(slice, task)`` with the pooled row (``task=None``) last inside each slice.
        A slice with no rows at all is omitted; the full set is always emitted when there is any
        judged row, so an all-held-out run still shows both (identical) figures rather than
        implying the distinction was not checked.
    """
    comparable = judged_records(records)
    if not comparable:
        return []
    out: list[AgreementStats] = []
    slices: list[tuple[str, list[SampleRecord]]] = [
        (SLICE_FULL_SET, list(comparable)),
        (
            SLICE_HELD_OUT,
            [r for r in comparable if r.split == SPLIT_HELD_OUT],
        ),
    ]
    for label, subset in slices:
        if not subset:
            continue
        for task_name in sorted({record.task for record in subset}):
            out.append(
                judge_agreement(
                    [r for r in subset if r.task == task_name],
                    label=label,
                    task=task_name,
                )
            )
        out.append(judge_agreement(subset, label=label, task=None))
    return out


# ---------------------------------------------------------------------------------------
# Rendering (Markdown only — see ``vigilai report --judge-agreement``).
# ---------------------------------------------------------------------------------------
_AGREEMENT_TITLE = "Per-sample deterministic ↔ LLM-judge agreement"

_AGREEMENT_CAVEATS: tuple[str, ...] = (
    "Reviewer ask #2, at sample level. The report's judge table compares two *aggregates*; this "
    "section compares the two scorers on the **same sample**, and — because the judge writes a "
    "per-element verdict line before its letter — on the **same rubric element**.",
    "**The two columns are different measures.** Deterministic = the mean fraction of rubric "
    "elements its cue detectors find. Judge = Inspect `accuracy`, the fraction of replies graded "
    "`C` (a `P` counts half). They share the 0-1 range and are not two estimates of one quantity, "
    "so `|Δ|` is a distance between two stated measures — never an error and never a "
    "disagreement rate. The **per-element** table below does not have that problem: both sides "
    "are a boolean per element there.",
    "**Slices are labelled and both are reported** (Resolution 1). `held_out` is the slice never "
    "used for cue-list tuning — unbiased but small; `full_set` is larger and cue-list "
    "contaminated. Neither alone is the answer.",
    "**Epochs are reduced per sample by the mean** before the per-sample statistics, matching "
    "Inspect's default reducer, so `Samples` is the number of samples and not the number of "
    "generations. The per-element table is over unreduced rows (a boolean verdict has no mean).",
    "**Direction disagreements** counts samples landing on *opposite sides of 0.5*: one scorer "
    "says more than half the elements are established, the other says fewer. A sample sitting "
    "exactly at 0.5 on either side is never counted, so the figure is a floor.",
)


def _fmt(value: float | None, places: int = 3) -> str:
    """Format a statistic, or an em dash when it is undefined."""
    return "—" if value is None else f"{value:.{places}f}"


def render_agreement_markdown(records: Sequence[SampleRecord]) -> str:
    """Render the agreement section as Markdown, for ``vigilai report --judge-agreement``.

    A run with no judged samples renders the heading and one sentence saying so, rather than an
    empty table or nothing at all — "no judge ran here" is information.
    """
    lines: list[str] = [f"## {_AGREEMENT_TITLE}", ""]
    rows = judge_agreement_by_split(records)
    if not rows:
        lines.append(
            "_No sample carries both a deterministic and an LLM-judge score in this run "
            "directory. Re-run with `--task-arg <task>:judge=true` (and, offline, "
            "`--model-role grader=mockllm/model`) to produce one._"
        )
        return "\n".join(lines) + "\n"

    graders = sorted(
        {
            record.judge_grader_display
            for record in judged_records(records)
            if record.judge_grader_display
        }
    )
    if graders:
        lines.append(
            f"**Grader:** {', '.join(f'`{g}`' for g in graders)} — the model that **actually** "
            "graded (the bound `grader` role where a run bound one, otherwise the grader the "
            "judge scorer resolved and stamped on each sample)."
        )
        lines.append("")
    for caveat in _AGREEMENT_CAVEATS:
        lines.append(caveat)
        lines.append("")

    lines.append(
        "| Slice | Task | Samples | Rows | mean \\|Δ\\| | mean Δ | Spearman ρ | Direction "
        "disagreements | Δ>0 (det. higher) | Δ<0 (judge higher) | Δ=0 |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for stats in rows:
        task_cell = f"`{stats.task}`" if stats.task else "**all judged tasks**"
        lines.append(
            f"| {stats.label} | {task_cell} | {stats.n} | {stats.n_rows} | "
            f"{_fmt(stats.mean_abs_delta)} | {_fmt(stats.mean_delta)} | "
            f"{_fmt(stats.spearman)} | {stats.direction_disagreements} | "
            f"{stats.deterministic_higher} | {stats.judge_higher} | {stats.ties} |"
        )
    lines.append("")

    lines.append("### Per-element agreement")
    lines.append("")
    lines.append(
        "`Cue-list only` is the **keyword-surface residue** reviewer ask #2 is about: the "
        "detector credited the element and the judge, reading for a substantive commitment, did "
        "not. `Judge only` points the other way — at the scorer rather than the model."
    )
    lines.append("")
    lines.append(
        "| Slice | Task | Element | Rows | Both credit | Both withhold | Cue-list only | "
        "Judge only | Agreement |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
    any_element = False
    for stats in rows:
        if stats.task is None:
            continue  # per-element rows are per task; the pooled row would double-count
        for element in stats.element_agreement:
            any_element = True
            lines.append(
                f"| {stats.label} | `{stats.task}` | `{element.element}` | {element.n} | "
                f"{element.both_credit} | {element.both_withhold} | "
                f"{element.deterministic_only} | {element.judge_only} | "
                f"{_fmt(element.agreement_rate)} |"
            )
    if not any_element:
        lines.append(
            "| — | — | _no per-element verdicts parsed_ | 0 | 0 | 0 | 0 | 0 | — |"
        )
    lines.append("")

    # Counted off the **full-set pooled row only**. Summing every pooled row would double-count,
    # because ``held_out`` is a subset of ``full_set`` and both carry a pooled entry.
    pooled = next(
        (s for s in rows if s.task is None and s.label == SLICE_FULL_SET), None
    )
    unparsed = pooled.judge_unparsed_rows if pooled else 0
    mismatched = pooled.judge_count_mismatch_rows if pooled else 0
    total_rows = pooled.n_rows if pooled else 0
    lines.append(
        f"**Grader format compliance** (over the {total_rows} judged row(s) of the full set): "
        f"{unparsed} carried no parsable per-element verdict line; {mismatched} had a "
        "`SUBSTANTIVE COUNT` contradicting their own verdict lines. Both are findings about the "
        "grader, not parser noise — the letter grade is defined as a function of the count. "
        "On a mock run whose grader returns `mockllm/model`'s **default** output there are no "
        "verdict lines to parse, so this figure equals the row count and says nothing about a "
        "real grader."
    )
    return "\n".join(lines) + "\n"


def agreement_to_dict(records: Sequence[SampleRecord]) -> list[dict[str, Any]]:
    """JSON view of the same rows, for ``vigilai report --json --judge-agreement``."""
    return [stats.to_dict() for stats in judge_agreement_by_split(records)]


__all__ = [
    "AgreementStats",
    "DETERMINISTIC_SCORER_NAMES",
    "ElementAgreement",
    "JUDGE_SCORER_NAME",
    "JudgeVerdicts",
    "SLICE_FULL_SET",
    "SLICE_HELD_OUT",
    "SPLIT_HELD_OUT",
    "SampleRecord",
    "agreement_to_dict",
    "first_epoch",
    "judge_agreement",
    "judge_agreement_by_split",
    "judged_records",
    "load_samples",
    "parse_judge_verdicts",
    "render_agreement_markdown",
    "sample_sort_key",
    "spearman",
]
