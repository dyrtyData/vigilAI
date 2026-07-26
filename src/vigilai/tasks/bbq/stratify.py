"""Deterministic, axis-stratified sampling for the EU ``bbq`` baseline.

The sixth broken measurement instrument of iteration 2, and the one that outranks the other
five because **no error bar could ever have caught it** (Resolution 13(f)).

The defect
----------

``--limit`` is **global per invocation**, and ``inspect_evals.bbq.combine_subsets`` concatenates
its eleven subsets in ``BBQ_SUBSET_NAMES`` order with ``Age`` **first**. So
``--limit 100`` takes ``Age_00000``–``Age_00099`` and never reaches race, gender identity,
nationality, religion, SES, disability, physical appearance or sexual orientation. Read off the
Phase 8 log header rather than inferred::

    EU bbq categories       : {'Age': 100}
    EU bbq context_condition: {'ambig': 50, 'disambig': 50}
    EU bbq question_polarity: {'neg': 50, 'nonneg': 50}

**Every EU ``bbq`` baseline in this project, in both iterations, is 100 ``Age`` samples.** So
"Brazil − EU" compared five Brazilian prejudices asked in Portuguese against **ageism asked in
English** — it varied the prejudice as well as the jurisdiction, and was therefore not a bias
comparison at all. Raising the limit would not have helped: ``Age`` alone has 3,680 rows.

Why *matched* axes rather than a stratified sample of all eleven
---------------------------------------------------------------

``bbq_brazil`` covers five axes — Race (IBGE ``cor ou raça``), Region, Religion, Class and
Intersectional. A stratified sample across all eleven BBQ subsets would put those five against
axes Brazil does not cover at all (``Age``, ``Disability_status``, ``Physical_appearance``,
``Sexual_orientation``, ``Gender_identity``), so the delta would still mix *"Brazil-specific
content"* with *"different prejudice families"* — a smaller version of the same defect.

:data:`MATCHED_AXES` therefore selects the four upstream subsets that are the closest analogues of
Brazil's axes:

=========================  ==========================  ===================================
``bbq_brazil`` axis        upstream BBQ subset         quality of the match
=========================  ==========================  ===================================
Race (IBGE)                ``Race_ethnicity``          direct
Religion                   ``Religion``                direct
Class                      ``SES``                     direct
Region                     ``Nationality``             **closest available analogue only**
Intersectional             (no counterpart)            ``Race_x_SES`` deliberately excluded
=========================  ==========================  ===================================

**The Region ↔ Nationality mismatch is stated, never hidden.** Brazil's regional prejudice is
*internal* — nordestino/sudestino, an intra-national axis produced by internal migration and
"internal orientalism" (research §9.2). BBQ has no internal-regional subset; ``Nationality`` is
prejudice against *foreigners*. It is the nearest thing in the corpus, and the paper says so.
``Race_x_SES`` is the obvious candidate for the intersectional axis and is **excluded on purpose**:
it would double-count the ``Race_ethnicity`` and ``SES`` rows this sample already contains.

Determinism
-----------

No RNG and no seed. The sample set is the **first :data:`MATCHED_PER_AXIS` rows of each axis,
selected by id** — ``f"{axis}_{i:05d}"`` for ``i`` in ``range(per_axis_limit)`` — which is a pure
function of the pinned dataset revision (``inspect_evals.bbq.BBQ_DATASET_REVISION``). Selection is
**by id and not by position**, so a change in Hugging Face row order cannot silently change the
sample set: :func:`stratified_samples` raises rather than substituting whatever happens to be
first. That is the drift guard, and it is load-bearing at task-construction time rather than only
in a test.

Balance under ``--limit``
------------------------

The selected samples are **interleaved round-robin across axes** (``axis0[0], axis1[0], axis2[0],
axis3[0], axis0[1], …``), mirroring ``bbq_brazil.dataset._interleave_by_category``. Consequences,
both pinned by tests:

* a ``--limit`` that is a multiple of **4** keeps the four axes balanced;
* a ``--limit`` that is a multiple of **16** additionally keeps the four
  (context condition × question polarity) cells balanced, because BBQ emits each scenario as four
  consecutive rows — ``(ambig, neg), (disambig, neg), (ambig, nonneg), (disambig, nonneg)``.

:data:`MATCHED_PER_AXIS` is **48, not 50**, for that second reason: 48 is a multiple of 4 so every
axis contributes exactly 12 rows to each of the four cells (192 samples = 48 per cell), whereas 50
per axis yields 52 ``neg`` against 48 ``nonneg``. ``bbq_brazil`` is exactly balanced across its own
four cells (100 each), so an off-multiple EU cut would reintroduce a composition difference on the
very comparison this module exists to make like-for-like.

Scope
-----

Nothing here changes what ``bbq`` means by default. ``axes="upstream"`` with
``per_axis_limit=0`` — the literal defaults — returns upstream's dataset object untouched.
"""

from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Sequence

from inspect_ai.dataset import Dataset
from inspect_ai.dataset import MemoryDataset
from inspect_ai.dataset import Sample
from inspect_evals.bbq.bbq import BBQ_SUBSET_NAMES
from inspect_evals.bbq.bbq import BBQSubset


# ``axes`` kwarg values. Literals, never named constants, at the ``@task`` signature —
# ``tools/generate_default_config.py`` AST-parses the default's *source text* and would otherwise
# write the identifier into ``config/default_config.yaml`` (the Phase 2 literal trap).
AXES_UPSTREAM = "upstream"
"""All eleven subsets in upstream's own order. The pre-existing behaviour, and the default."""
AXES_MATCHED = "matched"
"""Only the four subsets matched to ``bbq_brazil``'s axes, interleaved. See the module docstring."""

AXES_MODES: tuple[str, ...] = (AXES_UPSTREAM, AXES_MATCHED)

# The four upstream subsets matched to ``bbq_brazil``'s five axes. Order is the order they are
# interleaved in, and it is part of the pinned sample set — do not reorder without regenerating
# ``docs/bbq-matched-axes-census.md``.
MATCHED_AXES: tuple[BBQSubset, ...] = (
    "Race_ethnicity",
    "Religion",
    "SES",
    "Nationality",
)

# Rows taken per axis when ``axes="matched"`` and no explicit ``per_axis_limit`` is given.
# 48 rather than 50 so each axis contributes exactly 12 rows to each of the four
# (context × polarity) cells. See "Balance under ``--limit``" in the module docstring.
MATCHED_PER_AXIS = 48

# The number of consecutive rows BBQ emits per scenario: 2 context conditions × 2 question
# polarities, sharing one context template and one identity pair. Verified against the real
# dataset rather than assumed — ``Religion_00000``–``Religion_00003`` all carry
# ``answer_info == ['Jewish', 'Jewish'] / ["Can't answer", 'unknown']``.
SAMPLES_PER_SCENARIO = 4


def resolve_axes_mode(axes: str) -> str:
    """Validate the ``axes`` kwarg.

    Args:
        axes: The requested mode.

    Returns:
        ``axes`` unchanged.

    Raises:
        ValueError: If ``axes`` is not one of :data:`AXES_MODES`. Named modes only — a typo must
            fail loudly rather than degrade to the upstream default, which is exactly how the
            age-only baseline would have survived a third iteration.
    """
    if axes not in AXES_MODES:
        raise ValueError(
            f"unknown axes mode {axes!r}; expected one of {list(AXES_MODES)}. "
            f"{AXES_UPSTREAM!r} is upstream's eleven subsets in upstream's order (the default, "
            f"and what every pre-2026-07-26 EU baseline in this project used — see "
            f"vigilai.tasks.bbq.stratify); {AXES_MATCHED!r} is the four subsets matched to "
            f"bbq_brazil's axes."
        )
    return axes


def axes_for_mode(axes: str) -> tuple[BBQSubset, ...]:
    """The upstream subsets a mode selects.

    Args:
        axes: A validated mode from :data:`AXES_MODES`.

    Returns:
        :data:`MATCHED_AXES` for ``"matched"``; all eleven ``BBQ_SUBSET_NAMES`` for ``"upstream"``.
    """
    if resolve_axes_mode(axes) == AXES_MATCHED:
        return MATCHED_AXES
    return tuple(BBQ_SUBSET_NAMES)


def resolve_per_axis_limit(axes: str, per_axis_limit: int) -> int:
    """Resolve the effective per-axis row count.

    ``0`` means "unset". Under ``axes="matched"`` an unset limit resolves to
    :data:`MATCHED_PER_AXIS`, so the pinned 192-sample design is what a bare
    ``--task-arg bbq:axes=matched`` produces; under ``axes="upstream"`` it stays ``0``, i.e. the
    untouched upstream dataset.

    Args:
        axes: A validated mode from :data:`AXES_MODES`.
        per_axis_limit: Rows per axis, or ``0`` for the mode's default.

    Returns:
        The effective per-axis row count, ``0`` meaning "no cap".

    Raises:
        ValueError: If ``per_axis_limit`` is negative.
    """
    if per_axis_limit < 0:
        raise ValueError(f"per_axis_limit must be >= 0, got {per_axis_limit}")
    if per_axis_limit:
        return per_axis_limit
    return MATCHED_PER_AXIS if resolve_axes_mode(axes) == AXES_MATCHED else 0


def expected_sample_ids(
    axes: Sequence[BBQSubset], per_axis_limit: int
) -> tuple[str, ...]:
    """The pinned sample-id list, in the order the dataset presents it.

    This *is* the sampling rule: the first ``per_axis_limit`` rows of each axis by
    ``example_id``, interleaved round-robin across axes. ``combine_subsets`` builds each id as
    ``f"{subset}_{example_id:05d}"`` and every subset's ``example_id`` starts at 0 and is
    contiguous (verified against the pinned dataset revision for all four matched axes), so the
    rule is expressible in closed form and needs neither a seed nor a committed 192-line literal.

    Args:
        axes: The subsets to draw from, in interleave order.
        per_axis_limit: Rows per axis. ``0`` yields an empty tuple.

    Returns:
        ``len(axes) * per_axis_limit`` ids, interleaved so that every prefix of
        ``len(axes) * k`` holds exactly ``k`` rows per axis.
    """
    return tuple(
        f"{axis}_{index:05d}" for index in range(per_axis_limit) for axis in axes
    )


def stratified_samples(
    samples: Iterable[Sample], axes: Sequence[BBQSubset], per_axis_limit: int
) -> list[Sample]:
    """Select and interleave the pinned sample set, or raise.

    Args:
        samples: Upstream's combined samples, in any order.
        axes: The subsets to draw from, in interleave order.
        per_axis_limit: Rows per axis.

    Returns:
        The samples named by :func:`expected_sample_ids`, in that exact order. Sample objects are
        returned **unmodified** — no metadata is stamped and no prompt is rewritten, so the
        rendered prompts are byte-identical to what an unstratified run would have sent and the
        before/after comparison against the age-only baseline is clean.

    Raises:
        ValueError: If any pinned id is missing from ``samples``. **This is the drift guard.** A
            change to upstream's dataset revision, row numbering or id format makes the task
            unloadable instead of silently sampling a different set — which is the failure mode
            that produced the age-only baseline in the first place.
    """
    wanted = expected_sample_ids(axes, per_axis_limit)
    by_id = {str(sample.id): sample for sample in samples}
    missing = [sample_id for sample_id in wanted if sample_id not in by_id]
    if missing:
        raise ValueError(
            f"{len(missing)} of {len(wanted)} pinned bbq sample ids are absent from the "
            f"upstream dataset (first few: {missing[:5]}). The stratified EU baseline is pinned "
            f"by id, not by position, so this means the dataset revision or its id scheme moved: "
            f"re-verify against inspect_evals.bbq.BBQ_DATASET_REVISION and regenerate "
            f"docs/bbq-matched-axes-census.md before publishing any number from it."
        )
    return [by_id[sample_id] for sample_id in wanted]


def stratified_dataset(
    dataset: Dataset, axes: Sequence[BBQSubset], per_axis_limit: int
) -> MemoryDataset:
    """:func:`stratified_samples`, rewrapped so upstream's dataset identity survives.

    Args:
        dataset: Upstream's dataset.
        axes: The subsets to draw from, in interleave order.
        per_axis_limit: Rows per axis.

    Returns:
        A ``MemoryDataset`` carrying the pinned samples and upstream's own ``name`` and
        ``location``, so the ``.eval`` header still records where the data came from.
    """
    return MemoryDataset(
        samples=stratified_samples(dataset, axes, per_axis_limit),
        name=dataset.name,
        location=dataset.location,
    )


__all__ = [
    "AXES_MATCHED",
    "AXES_MODES",
    "AXES_UPSTREAM",
    "MATCHED_AXES",
    "MATCHED_PER_AXIS",
    "SAMPLES_PER_SCENARIO",
    "axes_for_mode",
    "expected_sample_ids",
    "resolve_axes_mode",
    "resolve_per_axis_limit",
    "stratified_dataset",
    "stratified_samples",
]
