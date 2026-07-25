"""Shared scenario shape and split plumbing for the two Art. 6 rubric benchmarks.

``explanation_quality`` (Art. 6, I) and ``contestation_review`` (Art. 6, II-III) score a
free-text answer against a **deterministic 6-element rubric**. Iteration 2 Phase 3 takes both
from a 3-4 scenario pilot to **12 scenarios (4 domains × 3 variants)** with a reserved
**held-out slice of 4** that no cue list was ever tuned against, so the Phase 6 LLM judge has an
uncontaminated set to grade. This module holds everything the two tasks would otherwise
duplicate.

Why a separate module rather than the dataclass living in each ``dataset.py``: the generated
scenario literals in ``…/generated.py`` must construct the scenario class, while ``dataset.py``
imports ``GENERATED_SCENARIOS`` from that generated module. Defining the class in ``dataset``
would make the import graph a cycle, which breaks depending on which module is imported first —
the same trap ``bbq_brazil`` hit in Phase 2 and solved with
:mod:`vigilai.tasks.bbq_brazil.scenario`. Here the graph is a straight line::

    rubric_scenario  →  <task>/scenario  →  <task>/generated  →  <task>/dataset

Elicitation licences (:attr:`RubricScenario.elicits`) — the load-bearing idea
---------------------------------------------------------------------------

A rubric scorer measures *the fraction of 6 elements a response contains*. So a scenario that
cannot plausibly elicit an element depresses the score **for the wrong reason**, and — worse for
a dataset expansion — a scenario that elicits an element *better than its siblings do* silently
makes the benchmark easier, confounding "n went from 3 to 12" with "the prompts got friendlier".

Every scenario therefore records, for **each** rubric element, where its licence comes from:

* a **verbatim span** of the scenario's own text (``decision`` / ``context`` / ``request``) that
  supplies the raw material for that element; or
* :data:`FRAME_LICENCE`, meaning the element is licensed by the *task frame* — the Art. 6 / LGPD
  Art. 20 instruction in the prompt plus the few-shot exemplar — and by nothing in the scenario.

Two mechanical rules follow, both enforced by
``tools/generate_brazil_scenarios.py::rubric_scenario_problems`` and re-asserted by the tests:

1. **Every span must actually occur in the scenario text.** An expectation cannot be recorded
   without pointing at the words that license it.
2. **The frame-licensed set must be identical across all 12 scenarios of a task**
   (:func:`frame_licensed_elements`). This is the anti-confound guard, and it doubles as a
   *leakage* guard: a contestation scenario whose context named an ``ouvidoria`` would hand the
   model an element the other eleven make it supply itself, and the parity check refuses it.

The frame-licensed sets are inherited from the iteration-1 pilot rather than chosen, so the
n=3 → n=12 expansion does not move what the benchmark measures. For ``explanation_quality`` that
set is ``{"confidence_level"}``; for ``contestation_review`` it is the four elements about what
the institution must *offer* (channel, deadline, reviewer authority, outcome communication). See
each task's ``scenario.py`` for the per-task constant and the reasoning.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


# ---------------------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------------------
#
# Resolution 1 (structure outline, 2026-07-25): **4 of 12 (33 %)** per rubric task, dual-reported
# by Phase 6 — held-out-only (n=12 across the three rubric tasks, unbiased) *and* full-set (n=36,
# cue-list-contaminated but tighter), always labelled. 20 % of 12 is 2-3 samples, too few for any
# agreement statistic, and grading all 36 with the judge costs cents.
SPLIT_ALL = "all"
SPLIT_TRAIN = "train"
SPLIT_HELD_OUT = "held_out"

#: Every split name a rubric dataset accepts. Unlike ``bbq_brazil`` — which reserves nothing and
#: *raises* on ``"held_out"`` (Resolution 2) — the rubric tasks really do hold a slice back, so
#: all three names are live here.
SPLITS: tuple[str, ...] = (SPLIT_ALL, SPLIT_TRAIN, SPLIT_HELD_OUT)


def resolve_split(split: str, *, task: str) -> str:
    """Validate a split name for a rubric task, or raise naming the accepted values."""
    if split in SPLITS:
        return split
    raise ValueError(f"unknown split {split!r} for {task}; expected one of {list(SPLITS)}")


# ---------------------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------------------

#: Provenance carried by the iteration-1 pilot scenarios, so hand-authored and iteration-2 rows
#: stay distinguishable in the data itself and not only in ``git blame``.
HAND_AUTHORED_PROVENANCE = "hand-authored pilot (iteration 1)"

#: Prefix every generated row's provenance starts with, so "is this row generated?" is a string
#: test rather than a set-membership lookup.
GENERATED_PROVENANCE_PREFIX = "generated"


# ---------------------------------------------------------------------------------------
# Elicitation licences
# ---------------------------------------------------------------------------------------

#: Recorded instead of a span when a rubric element is licensed by the **task frame** (the Art. 6
#: instruction in the prompt plus the few-shot exemplar) rather than by anything in the scenario.
#: Written in pt-BR to match the scenario text it sits beside in the generated literals.
FRAME_LICENCE = "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"

#: Shortest span accepted as a licence. Anything below this is a word, not evidence.
MIN_LICENCE_SPAN = 12


@dataclass(frozen=True)
class RubricScenario:
    """A single high-stakes automated decision, scored against a 6-element rubric.

    ``decision`` is the outcome that was reached; ``context`` gives the model the concrete facts
    it can cite; ``request`` is the affected person's own words. ``domain`` tags the kind of
    decision for grouping and for the held-out balance.

    ``elicits`` is the per-element licence audit described in the module docstring: one entry per
    rubric element, in the rubric's canonical order, each mapping the element key to a verbatim
    span of this scenario's text or to :data:`FRAME_LICENCE`.

    ``reference_answer`` is a compliant answer to *this* scenario. It is **never shown to the
    model** — :func:`_prompt` in each dataset builds only from ``decision`` / ``context`` /
    ``request``, and a test pins that. It exists so "this scenario can elicit every element it is
    scored on" is a *test* rather than a claim: the generator and the suite run the real
    deterministic scorer over it and require 1.0, plus a grounding check that it reuses this
    scenario's own vocabulary instead of being boilerplate that would fit any of the twelve.
    """

    id: str
    domain: str
    decision: str
    context: str
    request: str
    elicits: tuple[tuple[str, str], ...]
    reference_answer: str
    held_out: bool = False
    provenance: str = HAND_AUTHORED_PROVENANCE

    @property
    def text(self) -> str:
        """Everything a licence span may be quoted from — the three prose fields, joined."""
        return f"{self.decision}\n{self.context}\n{self.request}"

    @property
    def is_generated(self) -> bool:
        return self.provenance.startswith(GENERATED_PROVENANCE_PREFIX)

    def licence(self, element: str) -> str:
        """The recorded licence for one rubric element.

        Raises:
            KeyError: if the element has no entry — which the validator makes impossible for any
                committed scenario, so reaching it means a hand-built test object.
        """
        for key, span in self.elicits:
            if key == element:
                return span
        raise KeyError(f"{self.id}: no elicitation licence recorded for {element!r}")


def frame_licensed_elements(scenario: RubricScenario) -> frozenset[str]:
    """The rubric elements this scenario licenses only through the task frame."""
    return frozenset(key for key, span in scenario.elicits if span == FRAME_LICENCE)


def interleave_by_domain(
    scenarios: Sequence[RubricScenario], domain_order: Sequence[str]
) -> list[RubricScenario]:
    """Round-robin the scenarios across domains, preserving order inside each domain.

    Same reasoning as ``bbq_brazil``'s category interleave: ``--limit N`` takes the **first** N
    samples, so a domain-grouped order would make any truncated run silently unbalanced. With four
    domains of three variants, every prefix of 4k scenarios holds exactly k per domain — and
    because the third variant of each domain is the held-out one, the *train* slice is exactly the
    first 8 and the held-out slice exactly the last 4.

    Raises:
        ValueError: if a scenario's domain is not in ``domain_order`` — a silent drop would shrink
            the dataset without any signal.
    """
    buckets: dict[str, list[RubricScenario]] = {
        domain: [s for s in scenarios if s.domain == domain] for domain in domain_order
    }
    unknown = [s for s in scenarios if s.domain not in buckets]
    if unknown:
        raise ValueError(f"scenario {unknown[0].id!r} has unknown domain {unknown[0].domain!r}")

    ordered: list[RubricScenario] = []
    for position in range(max((len(bucket) for bucket in buckets.values()), default=0)):
        for domain in domain_order:
            bucket = buckets[domain]
            if position < len(bucket):
                ordered.append(bucket[position])
    return ordered


def select_split(scenarios: Sequence[RubricScenario], split: str) -> list[RubricScenario]:
    """Filter scenarios by split name (``"all"`` returns every one, in order)."""
    if split == SPLIT_ALL:
        return list(scenarios)
    want_held_out = split == SPLIT_HELD_OUT
    return [s for s in scenarios if s.held_out == want_held_out]


def split_of(scenario: RubricScenario) -> str:
    """The split name stamped onto a scenario's sample metadata."""
    return SPLIT_HELD_OUT if scenario.held_out else SPLIT_TRAIN
