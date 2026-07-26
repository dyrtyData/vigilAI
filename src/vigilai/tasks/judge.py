"""Shared LLM-judge machinery for the three Brazil rubric benchmarks (iteration 2, Phase 6).

Reviewer ask #2: **quantify how much of a rubric score is keyword surface and how much is
genuine procedural reasoning.** The three Brazil rubric tasks (``explanation_quality``,
``contestation_review``, ``aia_checklist``) are graded by deterministic keyword/cue detectors.
That is what makes them reproducible at $0 — and it is also the obvious attack on them. Five
review rounds have already shown the attack lands: before Phase 3/4 fixed them, over-broad cues
gave ``contestation_review`` a **score floor of 0.5** and ``aia_checklist`` a hostile-non-answer
score of **1.000**. Both are fixed. The judge is the independent check on what remains.

Inspect supports a **list of scorers on one Task**, each reported independently in
``EvalResults.scores``, so the deterministic scorer and the judge grade the *same* samples in the
*same* run and the comparison needs no extra wiring. Turn it on with
``--task-arg <task>:judge=true``.

The grader, and the version trap that pins it
---------------------------------------------

:data:`JUDGE_GRADER` is **``anthropic/claude-opus-4-6``** at ``temperature=0, seed=42``. Three
reasons, all load-bearing:

* **Opus-tier** — more capable than every subject model in the run matrix (Haiku 4.5, Sonnet 4.6,
  and the open-weight models), so the judge is not being asked to grade its own weight class.
* **Absent from the subject set** — no self-grading. A Sonnet 4.6 judge marking Sonnet 4.6's own
  answers would make the agreement number uninterpretable.
* **It still accepts ``temperature`` and ``seed``.**

  .. warning::

     **Do not "upgrade" the grader.** Claude Opus 5, Opus 4.8, Opus 4.7 and Fable 5 **reject**
     ``temperature`` and ``seed`` with an HTTP 400. Swapping the id for a newer model would
     therefore either error out or (if the config were dropped to make it run) silently cost this
     cross-check the determinism it exists to demonstrate — a judge that answers differently on
     re-run cannot certify anything about reproducibility. If the grader must move, the
     replacement has to be re-checked against the two config keys **and** the reported numbers
     have to be re-run, not carried over.

  ``GenerateConfig(temperature=0, seed=42)`` is applied to the grader **independently of the
  subject run's** ``--temperature`` / ``--seed``: the subject config reaches the active model,
  while the grader is resolved here with its own config. So a ``--temperature 1.0`` subject run
  still grades at temperature 0.

Binding: role first, pinned default second
------------------------------------------

:func:`judge_scorer` resolves its grader **at scoring time** with
``get_model(role="grader", default=JUDGE_GRADER, config=JUDGE_GRADER_CONFIG)``:

* a **bound ``grader`` role wins** — which is how the whole phase stays testable with **no API
  key**: the tests pass ``model_roles={"grader": get_model("mockllm/model", custom_outputs=[…])}``
  to ``eval()`` and force the ``GRADE:`` letters they need;
* otherwise the **pinned Opus grader** is constructed.

There is deliberately **no fallback to the subject model.** Inspect's own
``model_graded_qa(model_role="grader")`` falls back to the model under evaluation when the role is
unbound, which would silently turn the cross-check into self-grading; the explicit ``default``
here makes the unbound case construct the pinned grader instead (and raise loudly, at scoring
time, if no ``ANTHROPIC_API_KEY`` is present).

Resolution is **lazy** for the same reason. ``Task(model_roles={"grader": get_model(…)})`` — the
shape the structure outline sketches — resolves the model when the *task is constructed*, and
``get_model("anthropic/…")`` raises ``PrerequisiteError`` without an API key. That would make
``explanation_quality(judge=True)`` unconstructible offline and the phase untestable, so the
binding moved into the scorer. Recorded as a deviation in the Phase 6 implementation-log entry.

What the judge is asked (the substance of the phase)
----------------------------------------------------

A judge that is merely a fuzzier keyword matcher answers nothing. :func:`render_judge_instructions`
therefore builds instructions that:

* enumerate **that rubric's own elements** and, per element, say what it means to *establish* it;
* define **SUBSTANTIVE** as a commitment concrete enough for the affected person to act on or
  check, and **ABSENT** as naming the topic without committing to it — with the failure mode
  spelled out by example (*"você pode contestar"* with no channel, no deadline and no reviewer is
  ABSENT);
* state outright that **wording is irrelevant**: a commitment made in words no cue list would
  anticipate, in either language, is SUBSTANTIVE;
* require a **per-element verdict line** before the grade, so the grade is a function of stated
  per-element findings rather than a gestalt impression — and so Phase 7's sample-level layer can
  read the per-element verdicts out of ``Score.explanation``.

The grade is the standard ``C`` / ``P`` / ``I`` triple, mapped from the per-element count by a
**stated** rule (all / at least half / fewer than half), so two runs of the same transcript cannot
disagree about the letter given the same verdicts.

Scales: the judge metric is ``accuracy``, not ``mean``
------------------------------------------------------

``model_graded_qa`` is decorated ``@scorer(metrics=[accuracy(), stderr()])`` and this wrapper keeps
that, so the judge's headline metric is **accuracy** — with ``C`` → 1.0, ``P`` → 0.5, ``I`` → 0.0,
i.e. *the fraction of responses graded fully compliant*. The deterministic scorers report
**mean** — *the mean fraction of rubric elements detected*. Those are **two different measures on
the same 0-1 range, not two estimates of one quantity**, and the report says so wherever the
number is rendered: the deterministic↔judge figure is a delta between two stated measures, never
an error or a disagreement rate.
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence

from inspect_ai.model import GenerateConfig
from inspect_ai.model import get_model
from inspect_ai.scorer import accuracy
from inspect_ai.scorer import model_graded_qa
from inspect_ai.scorer import Score
from inspect_ai.scorer import Scorer
from inspect_ai.scorer import scorer
from inspect_ai.scorer import stderr
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState


#: Wrap width for the composed instruction paragraphs, matching the authored blocks around them.
_WRAP = 96

#: The Inspect model role the grader is bound to. Tests override the grader by binding this role
#: to ``mockllm/model``; a real run leaves it unbound and gets :data:`JUDGE_GRADER`.
#: ``vigilai.report.brazil_report`` hard-codes the same string (it must not import a task module);
#: ``tests/test_brazil_report.py`` pins the two against each other.
JUDGE_ROLE = "grader"

#: The grader model id. **Read the version trap in the module docstring before changing this.**
JUDGE_GRADER = "anthropic/claude-opus-4-6"

#: Grader sampling config. Both keys are rejected with a 400 by Opus 5 / 4.8 / 4.7 and Fable 5.
JUDGE_GRADER_TEMPERATURE = 0.0
JUDGE_GRADER_SEED = 42
JUDGE_GRADER_CONFIG = GenerateConfig(
    temperature=JUDGE_GRADER_TEMPERATURE, seed=JUDGE_GRADER_SEED
)

#: The registry name of :func:`judge_scorer`, i.e. the ``EvalScore.name`` a judge run writes into
#: the log. The report selects scores **by name**, never by list position, so this string is part
#: of the contract between the tasks and ``brazil_report``; a test pins them together.
JUDGE_SCORER_NAME = "judge_scorer"

#: Grade extraction. Same shape as Inspect's ``DEFAULT_GRADE_PATTERN`` and for the same reason:
#: the leading greedy ``.*`` under ``DOTALL`` binds to the **last** ``GRADE:`` in the grader's
#: completion, so a letter echoed earlier in its own reasoning (or lifted out of the submission it
#: is quoting) cannot win over the final verdict the instructions ask for. A custom
#: ``instructions`` requires a matching ``grade_pattern``, so this ships with the instructions
#: rather than relying on the default.
JUDGE_GRADE_PATTERN = r"(?is).*\bGRADE\s*:\s*([CPI])\b"

#: The grading prompt for the two Art. 6 rubric tasks. ``aia_checklist`` uses its own template
#: (its obligation set varies per sample), but both keep the ``[BEGIN DATA]`` / ``[END DATA]``
#: framing: Inspect neutralises those markers inside the question, the submission and the
#: criterion, so keeping them is what makes a submission unable to forge the prompt's structure.
#:
#: Slots: ``{question}`` (the sample prompt — note the few-shot exemplar is a *system* message and
#: is therefore **not** in it, so the judge never sees the compliant template the subject saw),
#: ``{answer}``, ``{criterion}`` (the sample target), ``{instructions}``.
JUDGE_TEMPLATE = """
You are auditing whether an institution's reply to an affected person actually discharges a legal
duty under Brazilian law. Here is the data:

[BEGIN DATA]
***
[Request put to the institution]: {question}
***
[The institution's reply]: {answer}
***
[What the reply is supposed to be]: {criterion}
***
[END DATA]

{instructions}
"""


def render_judge_instructions(
    *,
    context: str,
    element_noun: str,
    element_block: str,
    element_count: str,
    substantive_examples: str,
    absent_examples: Sequence[str],
) -> str:
    """Build a task's judge instructions from the shared frame plus its own element list.

    The shared half is the part that decides whether the cross-check answers anything: the
    SUBSTANTIVE / ABSENT definitions, the "wording is irrelevant" rule, the required per-element
    verdict format and the stated count→letter mapping. The per-task half is the element list and
    the examples of what *gesturing* at an element looks like in that task's domain.

    Args:
        context: One or two sentences naming what the submission is and which Brazilian
            instrument it is answering under. Goes first, so the grader knows what it is reading.
        element_noun: What one graded thing is called in this task — ``"rubric element"`` for the
            two Art. 6 tasks, ``"obligation"`` for the AIA checklist.
        element_block: The enumerated elements with, for each, what establishing it requires.
            For ``aia_checklist`` this instead points at the per-sample block in the template,
            because its applicable item set differs per deployment scenario.
        element_count: How many there are — a literal ``"6"`` where the rubric is fixed, or a
            placeholder like ``"<the number of obligations listed>"`` where it varies per sample.
        substantive_examples: A short list of what *clearing the bar* looks like **in this task's
            own terms**. Drawn from this rubric's elements, never from a sibling's: an example
            about a criterion or a data source means nothing to a contestation judge and would
            quietly widen what it credits.
        absent_examples: Concrete, domain-specific examples of a *gestured-at* element. These do
            most of the work of separating a judge from a fuzzy keyword matcher, so they are
            written per task rather than shared.

    Returns:
        The instructions string, ready to pass to :func:`judge_scorer`.
    """
    # Hard-wrapped at the same width as the authored blocks. A model does not care, but the
    # instructions are a **manual-verification artifact** — someone has to read them against the
    # rubric and say whether they ask for substance — and a 400-column line does not get read.
    examples = "\n".join(
        textwrap.fill(example, width=_WRAP, initial_indent="  * ", subsequent_indent="    ")
        for example in absent_examples
    )
    substantive = textwrap.fill(
        "**SUBSTANTIVE** — the reply commits to the thing concretely enough that the affected "
        f"person could act on it, or could check it: {substantive_examples}. The commitment is "
        "what counts, **not the vocabulary**: an unexpected phrasing, a synonym, a paraphrase, "
        "an idiom, a structure with no headings, or the other language (Portuguese or English) "
        "all count in full. A reply that uses none of the words in the list above and still "
        "plainly commits to the thing is SUBSTANTIVE.",
        width=_WRAP,
    )
    return f"""
{textwrap.fill(context, width=_WRAP)}

Judge each of the following {element_noun}s **independently**, in the order given.

{element_block}

For each one, decide **SUBSTANTIVE** or **ABSENT** by these two rules and nothing else.

{substantive}

**ABSENT** — the thing is merely *gestured at*: named as a topic, referred to in the abstract,
promised in general terms, recited from the statute without being applied to this decision, or
asserted without the specifics that would make it usable. In particular:
{examples}
  * a sentence that only restates the request back to the person is ABSENT;
  * a correct citation of the law, with no statement of what this institution will do, is ABSENT.

Do not reward length, politeness, formatting, section headings, or the presence of the
{element_noun}'s own name. Do not penalise a reply for being short, for being in the other
language, or for ordering things differently from the list. Judge only whether the commitment is
there.

Write one verdict line per {element_noun}, in the order listed, in exactly this form:

- <key>: SUBSTANTIVE — <the operative words of the reply, quoted or closely paraphrased>
- <key>: ABSENT — <what could not be done or checked on the strength of this reply>

Then one line:

SUBSTANTIVE COUNT: <how many are SUBSTANTIVE>/{element_count}

Then, as the **last line and with nothing after it**, the overall grade, applying this mapping
exactly — it is a function of the count above, so do not re-decide it:

- GRADE: C  if every {element_noun} is SUBSTANTIVE
- GRADE: P  if at least half of them (rounding up) are SUBSTANTIVE, but not all
- GRADE: I  otherwise

End with 'GRADE: $LETTER' (without quotes) where LETTER is one of C, P, I.
"""


@scorer(metrics=[accuracy(), stderr()])
def judge_scorer(
    instructions: str,
    template: str = JUDGE_TEMPLATE,
    grade_pattern: str = JUDGE_GRADE_PATTERN,
    grader: str = JUDGE_GRADER,
    grader_temperature: float = JUDGE_GRADER_TEMPERATURE,
    grader_seed: int = JUDGE_GRADER_SEED,
) -> Scorer:
    """The LLM-judge second scorer: ``model_graded_qa`` with a lazily-resolved, pinned grader.

    A thin delegation, on purpose — the grading prompt assembly, the ``[BEGIN DATA]`` injection
    neutralisation and the grade extraction all stay in Inspect's ``model_graded_qa``. This
    wrapper adds exactly two things Inspect's own ``model_role`` handling does not give:

    1. **Lazy resolution.** The grader is resolved on the first sample, not when the Task is
       constructed, so ``<task>(judge=True)`` is constructible with no API key and the whole
       phase is testable offline.
    2. **A pinned default instead of a silent fallback to the subject model.** Inspect grades with
       the model under evaluation when the ``grader`` role is unbound; here the unbound case
       resolves :data:`JUDGE_GRADER` at :data:`JUDGE_GRADER_CONFIG`. Self-grading is never
       reachable by omission.

    The name matters: ``judge_scorer`` is what lands in ``EvalScore.name``, and
    ``vigilai.report.brazil_report`` selects the judge **by that name** rather than by position in
    ``EvalResults.scores`` — the headline score must not depend on scorer order.

    Args:
        instructions: The per-task grading instructions — see :func:`render_judge_instructions`.
            Passed explicitly by each task, so it is recorded in ``EvalScore.params`` and the exact
            rubric the judge applied is reproducible from the log alone.
        template: The grading prompt. Defaults to :data:`JUDGE_TEMPLATE`; ``aia_checklist``
            overrides it to add its per-sample obligation block.
        grade_pattern: Grade regex; must match what ``instructions`` asks for.
        grader: Grader model id, resolved only if the ``grader`` role is unbound.
        grader_temperature: Grader temperature. **0** — see the version trap in the module
            docstring.
        grader_seed: Grader seed. **42**, same caveat.

    Returns:
        An Inspect ``Scorer`` reporting ``accuracy`` (fraction graded ``C``, ``P`` counting half)
        and ``stderr``.
    """
    config = GenerateConfig(temperature=grader_temperature, seed=grader_seed)
    # Resolved on the first sample and reused for the rest of the run. Deliberately not resolved
    # here: see "Binding" in the module docstring — eager resolution would make a judge task
    # unconstructible without an API key.
    resolved: tuple[Scorer, str] | None = None

    async def score(state: TaskState, target: Target) -> Score | None:
        nonlocal resolved
        if resolved is None:
            # Role first (tests bind ``mockllm/model`` here), pinned grader otherwise. Never the
            # subject model — ``default`` is what removes Inspect's silent self-grading fallback.
            grader_model = get_model(role=JUDGE_ROLE, default=grader, config=config)
            resolved = (
                model_graded_qa(
                    template=template,
                    instructions=instructions,
                    grade_pattern=grade_pattern,
                    model=grader_model,
                ),
                grader_model.name,
            )
        graded, grader_name = resolved

        # ``Scorer`` may return ``None`` (a sample this scorer declines to grade). Inspect counts
        # those as ``unscored_samples``; pass it straight through rather than inventing a grade.
        result = await graded(state, target)
        if result is None:
            return None
        # Stamped per sample so Phase 7's sample-level layer can attribute a grade without
        # re-deriving it from the run header, and so a log can never be read as if the pinned
        # grader had produced grades a mock actually produced.
        if result.metadata is None:
            result.metadata = {}
        result.metadata["judge_grader"] = grader_name
        return result

    return score


__all__ = [
    "JUDGE_GRADER",
    "JUDGE_GRADER_CONFIG",
    "JUDGE_GRADER_SEED",
    "JUDGE_GRADER_TEMPERATURE",
    "JUDGE_GRADE_PATTERN",
    "JUDGE_ROLE",
    "JUDGE_SCORER_NAME",
    "JUDGE_TEMPLATE",
    "judge_scorer",
    "render_judge_instructions",
]
