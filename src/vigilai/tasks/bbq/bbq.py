"""EU-baseline BBQ, with two substitutions: the sigil-tolerant scorer and optional axis strata.

Everything else about the upstream ``inspect_evals.bbq`` task is reused as-is — the Hugging Face
dataset, the ``multiple_choice()`` solver, the version and metadata — via ``task_with``, which
replaces fields on the Task upstream returned rather than rebuilding it.

**Substitution 1 — the scorer.** Required for the EU↔Brazil delta to mean anything: Claude Sonnet
4.6 answers ``ANSWER: $B``, which upstream ``choice()`` cannot parse, and it did so on 315 of 1,000
``bbq`` samples and 1,628 of 4,000 ``bbq_brazil`` samples in the Phase 8 runs — different rates on
the two sides of the pair, so the defect distorts the *delta* as well as the absolutes. ``bbq`` and
``bbq_brazil`` must therefore go through the **same** parse. See :mod:`vigilai.tasks.choice_parse`
for the defect, the shapes accepted and refused, and why the fix is in the parse rather than in the
prompt.

**Substitution 2 — the dataset, and only when asked for.** ``--limit`` is global per invocation and
upstream concatenates its eleven subsets with ``Age`` first, so every EU baseline in this project
was 100 ``Age`` samples and the bias delta compared ageism in English against five Brazilian
prejudices in Portuguese. ``axes="matched"`` builds a deterministic, axis-stratified sample over the
four subsets matched to ``bbq_brazil``'s axes instead. See :mod:`vigilai.tasks.bbq.stratify` for the
defect, the axis mapping (including the Region ↔ ``Nationality`` mismatch, which is stated rather
than hidden), the drift guard and why 48 per axis rather than 50.

**The defaults preserve the previous behaviour exactly.** ``axes="upstream"`` with
``per_axis_limit=0`` hands upstream's dataset object straight through untouched, so every earlier
run remains reproducible with the same command and the stratification is purely additive.
"""

from inspect_ai import Task
from inspect_ai import task
from inspect_ai import task_with
from inspect_evals.bbq import bbq as inspect_bbq
from inspect_evals.bbq.bbq import BBQSubset

from vigilai.tasks.bbq.stratify import AXES_UPSTREAM
from vigilai.tasks.bbq.stratify import axes_for_mode
from vigilai.tasks.bbq.stratify import resolve_axes_mode
from vigilai.tasks.bbq.stratify import resolve_per_axis_limit
from vigilai.tasks.bbq.stratify import stratified_dataset
from vigilai.tasks.choice_parse import choice_sigil_tolerant


@task(
    technical_requirement="Representation — Absence of Bias",
    brazil_article="Art. 5, III",
    brazil_scope="all_ai",
)
def bbq(
    subsets: BBQSubset | list[BBQSubset] | None = None,
    shuffle: bool = False,
    axes: str = "upstream",
    per_axis_limit: int = 0,
) -> Task:
    """Upstream BBQ, scored by :func:`~vigilai.tasks.choice_parse.choice_sigil_tolerant`.

    Args:
        subsets: BBQ subset name(s), or ``None`` for all eleven. Passed through unchanged. Must be
            ``None`` when ``axes`` is not ``"upstream"`` — the two are different ways of saying the
            same thing and a silent precedence rule between them is exactly the kind of ambiguity
            that produced the age-only baseline.
        shuffle: Shuffle the *dataset* order (upstream's own kwarg — not the choice order). Passed
            through unchanged. Applied by upstream **before** any stratification, which is
            harmless because stratification selects by id rather than by position.
        axes: ``"upstream"`` (all eleven subsets, upstream's order — the default and the
            pre-existing behaviour) or ``"matched"`` (the four subsets matched to ``bbq_brazil``'s
            axes: ``Race_ethnicity``, ``Religion``, ``SES``, ``Nationality``, interleaved
            round-robin so any ``--limit`` stays balanced).
        per_axis_limit: Rows per axis. ``0`` means the mode's default — no cap under
            ``"upstream"``, :data:`~vigilai.tasks.bbq.stratify.MATCHED_PER_AXIS` (48, i.e. 192
            samples) under ``"matched"``.

    Returns:
        The Task upstream builds, with its scorer replaced and — only when a non-default ``axes`` or
        ``per_axis_limit`` is requested — its dataset replaced by the pinned stratified sample.
        ``task_with`` mutates only those fields, so the solver, ``version`` and ``metadata``
        upstream sets are preserved exactly.

    Raises:
        ValueError: If ``axes`` is unknown, ``per_axis_limit`` is negative, ``subsets`` is combined
            with a non-default ``axes``, or a pinned sample id is missing from the upstream dataset
            (the drift guard — see :func:`~vigilai.tasks.bbq.stratify.stratified_samples`).
    """
    mode = resolve_axes_mode(axes)
    effective_limit = resolve_per_axis_limit(mode, per_axis_limit)

    if mode == AXES_UPSTREAM and not effective_limit:
        # The pre-existing path, byte for byte: upstream's dataset object, untouched.
        return task_with(inspect_bbq(subsets, shuffle), scorer=choice_sigil_tolerant())

    if subsets is not None:
        raise ValueError(
            f"subsets={subsets!r} cannot be combined with axes={axes!r} / "
            f"per_axis_limit={per_axis_limit!r}: both choose which subsets to draw from. Pass "
            f"subsets alone for an ad-hoc selection, or the stratified kwargs alone for the "
            f"pinned, interleaved, per-axis-capped sample."
        )

    selected = axes_for_mode(mode)
    upstream = inspect_bbq(list(selected), shuffle)
    return task_with(
        upstream,
        dataset=stratified_dataset(upstream.dataset, selected, effective_limit),
        scorer=choice_sigil_tolerant(),
    )
