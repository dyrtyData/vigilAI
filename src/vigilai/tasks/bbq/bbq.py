"""EU-baseline BBQ, with one substitution: the sigil-tolerant ``choice()`` wrapper.

Everything about the upstream ``inspect_evals.bbq`` task is reused as-is — the Hugging Face
dataset, the ``multiple_choice()`` solver, the version and metadata — via ``task_with``, which
replaces one field on the Task upstream returned rather than rebuilding it.

The one substitution is the scorer, and it is **required for the EU↔Brazil delta to mean
anything**: Claude Sonnet 4.6 answers ``ANSWER: $B``, which upstream ``choice()`` cannot parse, and
it did so on 315 of 1,000 ``bbq`` samples and 1,628 of 4,000 ``bbq_brazil`` samples in the Phase 8
runs — different rates on the two sides of the pair, so the defect distorts the *delta* as well as
the absolutes. ``bbq`` and ``bbq_brazil`` must therefore go through the **same** parse.
See :mod:`vigilai.tasks.choice_parse` for the defect, the shapes accepted and refused, and why the
fix is in the parse rather than in the prompt.
"""

from inspect_ai import Task
from inspect_ai import task
from inspect_ai import task_with
from inspect_evals.bbq import bbq as inspect_bbq
from inspect_evals.bbq.bbq import BBQSubset

from vigilai.tasks.choice_parse import choice_sigil_tolerant


@task(
    technical_requirement="Representation — Absence of Bias",
    brazil_article="Art. 5, III",
    brazil_scope="all_ai",
)
def bbq(
    subsets: BBQSubset | list[BBQSubset] | None = None, shuffle: bool = False
) -> Task:
    """Upstream BBQ, scored by :func:`~vigilai.tasks.choice_parse.choice_sigil_tolerant`.

    Args:
        subsets: BBQ subset name(s), or ``None`` for all eleven. Passed through unchanged.
        shuffle: Shuffle the *dataset* order (upstream's own kwarg — not the choice order).
            Passed through unchanged.

    Returns:
        The Task upstream builds, with its scorer replaced. ``task_with`` mutates only the scorer,
        so the dataset, solver, ``version`` and ``metadata`` upstream sets are preserved exactly.
    """
    return task_with(inspect_bbq(subsets, shuffle), scorer=choice_sigil_tolerant())
