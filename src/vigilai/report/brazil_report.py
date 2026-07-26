"""Phase 7 — Brazil PL 2338/2023 per-article compliance report (the capstone aggregator).

COMPL-AI ships **no** report aggregation (research §"No report generation": results are raw
``.eval`` / ``.json`` logs viewable via ``inspect view``). This module adds the thin layer
vigilAI needs: it reads the Inspect logs of a run directory, joins each task's score to its
Brazil PL 2338/2023 ``brazil_article`` / ``brazil_scope``, aggregates the per-task scores per
article and per scope, and renders both a Markdown and a JSON view.

Because the **whole COMPL-AI project is preserved**, the same model can be evaluated on the
mapped *original EU tasks* and the *Brazil tasks* in one run. The report surfaces that as an
**EU↔Brazil side-by-side**: for the two direct-adaptation pairs that reuse the exact same
scorer (``human_deception``↔``human_deception_brazil`` and ``bbq``↔``bbq_brazil``), the EU
score sits next to the Brazil score with their delta, so the difference isolates the
Brazil-specific content (Portuguese disclosure questions; IBGE / regional / intersectional
categories) rather than confounding scorer differences. ``explanation_quality`` and
``aia_checklist`` are **Brazil-only** rows — they have no EU/COMPL-AI counterpart, and that
absence is itself a headline finding (Brazil's Art. 6 explanation right and the AIA
obligations have no EU benchmark equivalent).

Join nuance (decorator-first, mirroring ``vigilai._cli.list._brazil_metadata``):

* Each task's ``(brazil_article, brazil_scope)`` is taken from the **task attribs recorded in
  the eval log** (``EvalSpec.task_attribs``) first. This is decorator-first and is the only
  robust source for two cases: ``explanation_quality`` (Art. 6, I via ``Interpretability``,
  also in the mapping) and especially ``aia_checklist`` (**Arts. 25-28**, a per-task tag that
  is deliberately *not* in :data:`~vigilai.brazil.mapping.TECH_REQ_TO_BRAZIL`). Using only the
  requirement→article mapping would misfile the AIA.
* If the log header lacks the attribs (e.g. an older log), we fall back to looking the task up
  in the live registry by name (``get_vigilai_tasks``) and reading its decorator attribs, then
  finally to the requirement→article mapping. The mapping is the *last* resort, never the
  first.

Standard errors (iteration 2, Phase 1)
--------------------------------------

Every scorer vigilAI runs already declares Inspect's ``stderr()`` metric alongside its point
estimate — the three custom Brazil scorers via ``@scorer(metrics=[mean(), stderr()])`` and the
reused upstream ``match`` / ``choice`` scorers via ``@scorer(metrics=[accuracy(), stderr()])`` — so
``stderr`` is present in **every** ``.eval`` log. The aggregator reads it as a *sibling* of the
headline metric (:func:`_stderr_metric`; the point-estimate resolution in :func:`_headline_metric`
is unchanged) and threads it through :class:`TaskScore` → the per-article / side-by-side / coverage
aggregates → all three renderers. Every published number therefore arrives with its own
uncertainty, straight from the tool, and no ``±`` table is hand-compiled.

Two deliberate statistical choices:

* **No partial pooling.** A group's standard error (:attr:`ArticleGroup.mean_stderr`,
  :attr:`RequirementCoverage.eu_only_stderr`) is ``None`` unless *every* scored member carries
  one — a group must never show an error bar narrower than its evidence supports.
* **Deltas add in quadrature.** The EU and Brazil sides of a pair are independent runs (different
  datasets, same scorer), so :attr:`SideBySideRow.delta_stderr` is ``sqrt(se_b² + se_eu²)``. That
  is what makes "the gap is larger than its uncertainty" a checkable claim rather than an
  assertion.

The sector overlay (iteration 2, Phase 4)
-----------------------------------------

``aia_checklist`` declares Inspect ``grouped()`` metrics on each sample's ``metadata["sector"]``
alongside its ungrouped ``mean()`` / ``stderr()``. Inspect flattens a dict-valued metric into one
``EvalScore.metrics`` entry per key, using the key **verbatim**, so with the task's
``name_template`` the real log keys are ``mean_<sector>`` and ``stderr_<sector>`` — read here by
:func:`_sector_metrics`, which is deliberately written against that *shape* rather than against a
hard-coded sector vocabulary, so this module stays jurisdiction-neutral (Resolution 6 plans to
extract a generic ``report`` command from it). The names were read out of a real mock log rather
than assumed, and ``tests/test_aia_checklist.py::TestGroupedMetricKeys`` pins them.

Gap-flagging items reach the report through the **task decorator** (``brazil_gap_items``), not
through ``Score.metadata``: sample scores are not in the log header, and
:func:`build_brazil_report` is header-only by design. The overlay section names them so a low
sector score reads as a regulatory finding — the item is one no Brazilian instrument imposes —
rather than only as a model failure. Since Phase 6 the task **also** carries
``brazil_gap_items_by_sector``, so the JSON view's per-sector list is per-sector rather than the
whole set repeated in every entry (Resolution 11 — see :func:`_gap_items_by_sector_from_attribs`).

The LLM-judge second scorer (iteration 2, Phase 6)
--------------------------------------------------

The three Brazil rubric tasks can run a **second scorer** — an LLM judge — alongside their
deterministic one (``--task-arg <task>:judge=true``). Inspect reports each scorer independently in
``EvalResults.scores``, so one log carries two scores for the same samples. That breaks an
assumption this module used to make, and the fix is the load-bearing part of Phase 6:

* **Scores are selected by scorer *name*, never by list position.** ``_task_score_from_log`` read
  ``log.results.scores[0]`` — "a task usually has a single score" — which turns the headline into
  whatever scorer happens to be first. :func:`_select_score` picks the deterministic scorer for
  ``score`` / ``stderr`` / the sector metrics and the judge for ``judge_score`` / ``judge_stderr``,
  so scorer order in the task definition cannot move a published number. A single-scorer log
  resolves exactly as it did before (the judge names are the only ones ever excluded), which is
  what keeps every pre-Phase-6 log reporting identically.
* **The two columns are different measures on the same 0-1 range.** The deterministic scorers
  report ``mean`` — the mean *fraction of rubric elements* their cue detectors find. The judge is
  ``model_graded_qa``, decorated ``@scorer(metrics=[accuracy(), stderr()])``, so it reports
  ``accuracy`` — the *fraction of replies graded C*, i.e. those where the grader judged **every**
  element a substantive procedural commitment (a ``P`` counts half). They are not two estimates of
  one quantity, so :attr:`TaskScore.judge_delta` is a **delta between two stated measures**, not an
  error and not a disagreement rate. Every renderer says so next to the number.
* **The delta's error bar is an upper bound.** Both scorers grade the *same samples in the same
  run*, so their errors are positively correlated and adding them in quadrature over-states the
  uncertainty. That is the conservative direction and it is stated wherever the number appears —
  the opposite of the ``bbq_brazil`` stderr, which is a lower bound. (The EU↔Brazil delta in
  :attr:`SideBySideRow.delta_stderr` is genuinely independent and needs no such caveat.)
"""

from __future__ import annotations

import html
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from dataclasses import field
from functools import lru_cache
from typing import Any

from inspect_ai.log import EvalLog
from inspect_ai.log import EvalScore
from inspect_ai.log import list_eval_logs
from inspect_ai.log import read_eval_log

from vigilai.brazil.mapping import brazil_article_for


# ---------------------------------------------------------------------------------------
# The nine COMPL-AI EU-AI-Act technical-requirement categories, in canonical display order.
#
# vigilAI preserves COMPL-AI's nine requirement categories unchanged; the breadth coverage map
# (Phase 10) reports Brazil compliance across *all nine*, not only the four with bespoke Brazil
# tasks — surfacing, per requirement, whether a Brazil-specific benchmark exists, and the EU-task
# score where it does not. The list is fixed (independent of which tasks a given run includes) so
# the coverage map always shows the full breadth: a requirement with no task in the run renders as
# "not yet covered" (⚪) rather than silently vanishing. Mapped requirements lead (the four with a
# Brazil article), then the remaining EU-only requirements.
# ---------------------------------------------------------------------------------------
NINE_TECHNICAL_REQUIREMENTS: tuple[str, ...] = (
    # Mapped to a Brazil PL 2338/2023 article (see TECH_REQ_TO_BRAZIL).
    "Disclosure of AI",
    "Representation — Absence of Bias",
    "Fairness — Absence of Discrimination",
    "Interpretability",
    # No direct Brazil Chapter II counterpart (EU-only requirements).
    "Robustness and Predictability",
    "Cyberattack Resilience",
    "Societal Alignment",
    "Capabilities, Performance, and Limitations",
    "Harmful Content and Toxicity",
)


# ---------------------------------------------------------------------------------------
# EU↔Brazil pairing config.
#
# Made an explicit constant (not "magic") per the structure outline: the ONLY two pairs that
# reuse the exact same scorer, so the EU↔Brazil delta is a clean measure of the Brazil-specific
# content. Maps the Brazil task name -> its EU counterpart task name. Any Brazil task not in
# this map (explanation_quality, aia_checklist) is reported as Brazil-only (no EU equivalent).
# ---------------------------------------------------------------------------------------
EU_BRAZIL_PAIRS: dict[str, str] = {
    "human_deception_brazil": "human_deception",
    "bbq_brazil": "bbq",
}

# The set of EU task names that participate in a side-by-side pair (derived from the map so the
# two never drift).
EU_PAIR_TASKS: frozenset[str] = frozenset(EU_BRAZIL_PAIRS.values())

# Brazil task names known to have NO EU/COMPL-AI counterpart. Used only to phrase the headline
# finding ("no EU equivalent"); any Brazil-tagged task absent from EU_BRAZIL_PAIRS is treated
# as Brazil-only regardless, so this is documentation rather than control flow.
BRAZIL_ONLY_TASKS: frozenset[str] = frozenset(
    {"explanation_quality", "contestation_review", "aia_checklist"}
)

# The vigilAI-authored **Brazil-specific benchmarks** — the tasks purpose-built for PL 2338/2023
# (the two same-scorer Brazil adaptations plus the Brazil-only benchmarks). Used by the
# 9-requirement coverage map to distinguish a genuine Brazil benchmark (✅) from a *preserved EU
# task* whose requirement merely maps to a Brazil article (🟡, e.g. ``fairllm`` / ``bold`` /
# ``cab`` / ``decoding_trust``). Defined here (derived from the two explicit constants above) so
# the coverage map and the headline phrasing never drift.
BRAZIL_BENCHMARK_TASKS: frozenset[str] = frozenset(EU_BRAZIL_PAIRS) | BRAZIL_ONLY_TASKS

# Inspect prefixes task names with the plugin/registry name ("vigilai/human_deception").
_REGISTRY_PREFIX = "vigilai/"

# Metric-name preference when reading a score's headline value. Upstream reused scorers report
# ``accuracy`` (match / choice); the new Brazil rubric/checklist scorers report ``mean``. We
# prefer accuracy, then mean, then fall back to the first available metric so the report never
# silently drops a score.
_METRIC_PREFERENCE: tuple[str, ...] = ("accuracy", "mean")

# The metric name Inspect's ``stderr()`` records. Read as a *sibling* of the headline metric (it is
# never a candidate for :data:`_METRIC_PREFERENCE` — a standard error is not a score).
_STDERR_METRIC = "stderr"

# Prefixes of the flattened per-group metric keys a ``grouped()`` metric writes into
# ``EvalScore.metrics``. The suffix after the prefix is the group name (here, the sector key).
#
# Verified against a real log rather than assumed: Inspect names a dict-valued metric's entries
# by the dict key **as-is** (``scorers_from_metric_list`` in ``inspect_ai/_eval/task/results.py``
# calls ``metrics_unique_key(metric_key, …)``), with **no** ``registry_log_name`` prefix — so
# ``grouped(mean(), "sector", name_template="mean_{group_name}")`` produces exactly
# ``mean_finance_bacen``. Without the template both grouped metrics would emit the bare sector
# key and the second would be silently renamed ``finance_bacen2``; the task therefore sets it.
_SECTOR_MEAN_PREFIX = "mean_"
_SECTOR_STDERR_PREFIX = "stderr_"

# Task-decorator attrib carrying the comma-separated ids of the gap-flagging checklist items
# (obligations no Brazilian instrument imposes). Read from the log header so the aggregator stays
# header-only; absent from pre-Phase-4 logs, in which case the overlay note simply omits the list.
_GAP_ITEMS_ATTRIB = "brazil_gap_items"

# The same ids **partitioned by sector**, as ``sector:id|id;sector:id`` (Phase 6, Resolution 11).
# The flat attrib above cannot say *which* sector a gap item belongs to, so the JSON view repeated
# the whole set in every sector entry — ``health_anvisa``, which has no gap item, listed five.
# A sector with no gap item is simply absent from this string, which is exactly the fix.
# Pre-Phase-6 logs do not carry it; those fall back to the flat list, i.e. to their own recorded
# behaviour, because the per-sector information genuinely is not in them.
_GAP_ITEMS_BY_SECTOR_ATTRIB = "brazil_gap_items_by_sector"
_GAP_SECTOR_SEPARATOR = ";"
_GAP_SECTOR_FIELD_SEPARATOR = ":"
_GAP_ID_SEPARATOR = "|"

# Scorer names, for name-based score selection (Phase 6). Kept as literals rather than imported
# from the task modules: the report must not depend on the task package (Resolution 6 plans to
# extract a jurisdiction-neutral ``report`` command from this file), and the same discipline
# already applies to ``_GAP_ITEMS_ATTRIB``. ``tests/test_brazil_report.py`` pins each string
# against the constant it mirrors, so the two cannot drift silently.
#
# ``_DETERMINISTIC_SCORERS`` is a *preference*, not a filter: an upstream COMPL-AI task scored by
# ``match`` / ``choice`` is not in it and must still resolve, so the fallback is "the first score
# that is not the judge". Naming the three Brazil scorers explicitly means a future task that adds
# a third scorer of its own still resolves the intended headline rather than the first one.
_DETERMINISTIC_SCORERS: tuple[str, ...] = (
    "rubric_scorer",
    "contestation_scorer",
    "aia_checklist_scorer",
)

# The registry name of ``vigilai.tasks.judge.judge_scorer`` — the one score that is never a
# headline.
_JUDGE_SCORERS: tuple[str, ...] = ("judge_scorer",)

# The Inspect model role the judge grader is bound to (``vigilai.tasks.judge.JUDGE_ROLE``). When a
# run bound it, the log header records the model **actually** used; otherwise the grader is the one
# the judge scorer's own params declare.
_JUDGE_ROLE = "grader"

# ``EvalScore.params`` keys the judge scorer records, so the grader is reproducible from the
# artifact alone even when no role was bound (the normal case for a real run — the CLI has no
# ``--model-role`` flag, and the scorer resolves its pinned default at scoring time).
_JUDGE_PARAM_GRADER = "grader"
_JUDGE_PARAM_TEMPERATURE = "grader_temperature"
_JUDGE_PARAM_SEED = "grader_seed"

# Minimum sample count for a reportable standard error. Inspect's ``stderr()`` returns a
# *placeholder* ``0`` when it has fewer than two observations to estimate from
# (``if (n - 1) < 1: return 0`` in ``inspect_ai/scorer/_metrics/std.py``). Rendering that verbatim
# would print a single-observation task as e.g. ``0.983 ± 0.000`` — reading as infinitely precise,
# which is the exact overconfidence this reporting layer exists to remove. Below two samples the
# report shows the bare point estimate instead. A genuine ``0.000`` from two or more identically
# scored samples (what ``mockllm/model`` produces) is a real estimate and *is* shown.
_MIN_SAMPLES_FOR_STDERR = 2


def _bare_task_name(task: str) -> str:
    """Strip the Inspect registry prefix from a logged task name.

    ``EvalSpec.task`` is recorded as e.g. ``"vigilai/human_deception_brazil"``; the
    EU↔Brazil pairing and the registry fall back all key off the bare ``"human_deception_brazil"``.
    """
    if task.startswith(_REGISTRY_PREFIX):
        return task[len(_REGISTRY_PREFIX) :]
    # Be tolerant of any provider/plugin prefix.
    return task.rsplit("/", 1)[-1] if "/" in task else task


@lru_cache(maxsize=1)
def _registry_attribs_by_task() -> dict[str, dict[str, Any]]:
    """Map bare task name -> its decorator attribs from the live registry.

    Used only as a fallback when a log header does not carry ``brazil_article`` (older logs).
    Cached because task discovery is comparatively expensive and the registry is static within
    a process. Imported lazily to avoid a circular import (``vigilai._cli`` registers the
    ``report`` command, which imports this module).
    """
    from vigilai._cli.utils import get_vigilai_tasks

    return {task.name: dict(task.attribs) for task in get_vigilai_tasks()}


def _resolve_brazil_metadata(
    task_name: str, task_attribs: dict[str, Any]
) -> tuple[str | None, str | None]:
    """Resolve a task's ``(brazil_article, brazil_scope)`` — decorator-first.

    Mirrors ``vigilai._cli.list._brazil_metadata`` so the report and ``vigilai list`` agree:

    1. Prefer the ``brazil_article`` / ``brazil_scope`` recorded in the **log header attribs**
       (decorator-first; the only source that files ``aia_checklist`` under Arts. 25-28).
    2. Fall back to the same task's attribs in the **live registry** (covers logs whose header
       predates the Brazil tagging).
    3. Fall back to deriving from ``technical_requirement`` via the canonical mapping.

    Returns ``(None, None)`` for a genuinely unmapped EU-only task.
    """
    # 1. Log-header decorator attribs.
    article = task_attribs.get("brazil_article")
    scope = task_attribs.get("brazil_scope")
    if article is not None:
        return article, scope

    # 2. Live-registry decorator attribs for the same task.
    registry_attribs = _registry_attribs_by_task().get(task_name, {})
    article = registry_attribs.get("brazil_article")
    scope = registry_attribs.get("brazil_scope")
    if article is not None:
        return article, scope

    # 3. requirement -> article mapping (last resort).
    requirement = task_attribs.get("technical_requirement") or registry_attribs.get(
        "technical_requirement", ""
    )
    mapped = brazil_article_for(requirement)
    if mapped is not None:
        return mapped
    return None, None


def _headline_metric(metrics: dict[str, Any]) -> tuple[str | None, float | None]:
    """Pick a score's headline (metric_name, value) from its metrics dict.

    ``metrics`` maps metric name -> object with a ``.value``. Prefers ``accuracy`` then
    ``mean`` (see :data:`_METRIC_PREFERENCE`), else the first available metric. Returns
    ``(None, None)`` if there are no metrics.
    """
    for preferred in _METRIC_PREFERENCE:
        if preferred in metrics:
            return preferred, float(metrics[preferred].value)
    for name, metric in metrics.items():
        return name, float(metric.value)
    return None, None


def _stderr_metric(metrics: dict[str, Any]) -> float | None:
    """Read a score's ``stderr`` metric from the same metrics dict as the headline value.

    ``metrics`` maps metric name -> object with a ``.value`` (the log-header
    ``EvalScore.metrics``). Returns ``None`` when the scorer declared no ``stderr()`` metric, or
    when the recorded value is not finite — Inspect reports an undefined standard error for a
    degenerate sample set, and the renderers must show a bare point estimate rather than
    ``± nan``.
    """
    metric = metrics.get(_STDERR_METRIC)
    if metric is None:
        return None
    value = float(metric.value)
    if not math.isfinite(value):
        return None
    return value


def _sector_metrics(metrics: dict[str, Any]) -> dict[str, tuple[float, float | None]]:
    """Read a score's per-sector ``grouped()`` metrics: ``sector -> (mean, stderr | None)``.

    ``metrics`` maps metric name -> object with a ``.value`` (the log-header
    ``EvalScore.metrics``). Sector entries are recognised **by shape** — a
    ``mean_<sector>`` / ``stderr_<sector>`` pair — not against a hard-coded sector list, so this
    module carries no dependency on the task's vocabulary and a Phase 5 sector appears with no
    change here.

    A sector is reported only when its *mean* is present and finite; its standard error is
    optional and dropped when non-finite, exactly as :func:`_stderr_metric` does for the headline
    value. The bare ``mean`` / ``stderr`` keys (the ungrouped headline metrics) are never sector
    entries — the prefix requires a non-empty suffix.
    """
    means: dict[str, float] = {}
    stderrs: dict[str, float] = {}
    for name, metric in metrics.items():
        for prefix, sink in (
            (_SECTOR_MEAN_PREFIX, means),
            (_SECTOR_STDERR_PREFIX, stderrs),
        ):
            if not name.startswith(prefix) or len(name) == len(prefix):
                continue
            value = float(metric.value)
            if math.isfinite(value):
                sink[name[len(prefix) :]] = value
    return {sector: (value, stderrs.get(sector)) for sector, value in sorted(means.items())}


def _gap_items_from_attribs(task_attribs: dict[str, Any]) -> tuple[str, ...]:
    """Read the gap-flagging item ids a task recorded on its decorator (``brazil_gap_items``).

    Empty for every task that declares none, and for logs written before the attrib existed —
    in which case the overlay section renders without the "these items are gaps" note rather
    than guessing.
    """
    raw = task_attribs.get(_GAP_ITEMS_ATTRIB)
    if not isinstance(raw, str) or not raw.strip():
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _gap_items_by_sector_from_attribs(
    task_attribs: dict[str, Any],
) -> dict[str, tuple[str, ...]]:
    """Read the **per-sector** gap-item ids (``brazil_gap_items_by_sector``) — Resolution 11.

    Format: ``sector:id|id;sector:id``. A sector with no gap item is absent from the string, and
    the caller must therefore treat "the task declared a mapping but not this sector" as *no gap
    items in this sector* — that distinction is the whole fix, because the previous flat attrib
    made ``health_anvisa`` (which has none) list all five.

    Returns an empty dict for a task that declares none and for a **pre-Phase-6 log**; the caller
    falls back to the flat list there, since the per-sector split genuinely is not recorded in
    those logs and inventing one would be worse than repeating the old, documented imprecision.
    """
    raw = task_attribs.get(_GAP_ITEMS_BY_SECTOR_ATTRIB)
    if not isinstance(raw, str) or not raw.strip():
        return {}
    by_sector: dict[str, tuple[str, ...]] = {}
    for entry in raw.split(_GAP_SECTOR_SEPARATOR):
        entry = entry.strip()
        if not entry or _GAP_SECTOR_FIELD_SEPARATOR not in entry:
            continue
        sector, _, ids = entry.partition(_GAP_SECTOR_FIELD_SEPARATOR)
        sector = sector.strip()
        items = tuple(
            part.strip() for part in ids.split(_GAP_ID_SEPARATOR) if part.strip()
        )
        if sector and items:
            by_sector[sector] = items
    return by_sector


def _select_score(scores: list[EvalScore], *, judge: bool) -> EvalScore | None:
    """Pick one of a task's scores **by scorer name** — never by position in the list.

    Since Phase 6 a task may declare two scorers (the deterministic one and the LLM judge), and
    Inspect reports each independently in ``EvalResults.scores``. Indexing that list — which is
    what this module used to do, with the comment *"a task usually has a single score"* — makes
    the headline score depend on the order the scorers happen to be declared in. It is a silent
    failure: the report would render a judge accuracy in the per-article compliance table with no
    error anywhere.

    Resolution order for the deterministic score:

    1. a score named by :data:`_DETERMINISTIC_SCORERS` (the three Brazil scorers);
    2. otherwise the first score that is **not** a judge — which is what keeps every upstream
       COMPL-AI task (``match``, ``choice``, and the rest) resolving exactly as before, without
       this module having to enumerate them.

    The judge is resolved by :data:`_JUDGE_SCORERS` alone: there is no "first non-deterministic"
    fallback, because guessing which of several unknown scorers is a judge would be worse than
    reporting none.

    Args:
        scores: ``log.results.scores`` — a list of ``EvalScore``.
        judge: ``True`` to select the judge score, ``False`` for the deterministic headline.

    Returns:
        The selected ``EvalScore``, or ``None`` when the run has none of that kind.
    """
    if judge:
        return next((s for s in scores if s.name in _JUDGE_SCORERS), None)
    preferred = next((s for s in scores if s.name in _DETERMINISTIC_SCORERS), None)
    if preferred is not None:
        return preferred
    return next((s for s in scores if s.name not in _JUDGE_SCORERS), None)


def _judge_grader_from_log(
    log: EvalLog, judge_score: EvalScore | None
) -> tuple[str | None, str | None]:
    """Resolve ``(grader model id, grader config)`` for the judge table header.

    "Reproducible from the artifact alone" is the requirement, and there are two places the answer
    can live, so both are read in the order that makes the rendered line *true*:

    1. **The bound ``grader`` model role**, when the run bound one (``log.eval.model_roles``). That
       is the model that actually graded — including in the test suite, where it is
       ``mockllm/model``, and a header claiming Opus had graded a mock run would be a lie in the
       published artifact.
    2. **The judge scorer's own params**, otherwise. A real run leaves the role unbound (the CLI
       has no ``--model-role`` flag) and the scorer resolves its pinned default, which the params
       record verbatim.

    The config always comes from the params, because that is the config the scorer *applies*
    (``get_model(role=…, config=…)``) whether or not a role was bound.
    """
    params: dict[str, Any] = dict(judge_score.params or {}) if judge_score else {}

    grader: str | None = None
    roles = log.eval.model_roles or {}
    role_model = roles.get(_JUDGE_ROLE)
    if role_model is not None:
        grader = str(role_model.model)
    elif isinstance(params.get(_JUDGE_PARAM_GRADER), str):
        grader = str(params[_JUDGE_PARAM_GRADER])

    config: str | None = None
    settings = [
        f"{key}={params[key]}"
        for key in (_JUDGE_PARAM_TEMPERATURE, _JUDGE_PARAM_SEED)
        if params.get(key) is not None
    ]
    if settings:
        config = ", ".join(settings)
    return grader, config


def _pooled_stderr(stderrs: list[float | None]) -> float | None:
    """Standard error of the *mean* of ``k`` independent estimates: ``sqrt(Σ seᵢ²) / k``.

    Used for both aggregate error bars (per-article means and the coverage map's EU-only mean).
    Returns ``None`` if the set is empty **or if any member lacks a standard error**: pooling over
    a partial set would yield an error bar narrower than the evidence supports, so the report
    prefers to show none at all (see the module docstring — this is a deliberate choice, not an
    oversight).
    """
    if not stderrs or any(se is None for se in stderrs):
        return None
    k = len(stderrs)
    return math.sqrt(sum(se * se for se in stderrs if se is not None)) / k


@dataclass(frozen=True)
class TaskScore:
    """A single task's resolved score plus its Brazil mapping.

    Attributes:
        task: Bare task name (registry prefix stripped), e.g. ``"bbq_brazil"``.
        brazil_article: PL 2338/2023 article, or ``None`` for an unmapped EU-only task.
        brazil_scope: ``"all_ai"`` / ``"high_risk"`` / ``None``.
        technical_requirement: The COMPL-AI EU requirement string.
        score: The headline metric value (0.0-1.0), or ``None`` if the run produced no score.
        metric_name: Which metric ``score`` came from (``"accuracy"`` or ``"mean"``).
        model: The evaluated model id.
        total_samples: Number of samples scored.
        status: The eval status (``"success"`` etc.).
        stderr: The standard error of ``score``, read from the same metrics dict (Inspect's
            ``stderr()`` metric), or ``None`` when the scorer declared none. Appended with a
            default so every existing construction is unaffected.
        sector_scores: ``sector -> (mean, stderr | None)`` from the task's ``grouped()`` metrics.
            Empty for every task that declares none (all of them but ``aia_checklist``).
        gap_items: Ids of this task's gap-flagging checklist items, from the
            ``brazil_gap_items`` decorator attrib. Empty for every other task.
        gap_items_by_sector: The same ids partitioned by sector, from
            ``brazil_gap_items_by_sector`` (Phase 6 / Resolution 11). Empty for a task that
            declares none **and** for a pre-Phase-6 log, where the split is not recorded.
        judge_score: The LLM judge's headline value for this task (Inspect ``accuracy`` — the
            fraction of replies graded ``C``), or ``None`` when the run had no judge scorer.
        judge_stderr: Standard error of ``judge_score``, suppressed below two samples exactly as
            ``stderr`` is.
        judge_metric_name: Which metric ``judge_score`` came from — ``"accuracy"``, and the
            reason the judge column is a *different measure* rather than a second estimate of
            ``score``.
        judge_grader: The grader model id, from the bound ``grader`` role if the run bound one,
            else from the judge scorer's recorded params.
        judge_grader_config: The grader sampling config as recorded by the scorer, e.g.
            ``"grader_temperature=0.0, grader_seed=42"``.
        split: The dataset slice the run used (``task_args["split"]``) — ``"held_out"`` for the
            uncontaminated judge slice, ``"all"`` for the full set. Resolution 1 requires the two
            to be reported separately and **always labelled**, so the judge table shows it.
    """

    task: str
    brazil_article: str | None
    brazil_scope: str | None
    technical_requirement: str | None
    score: float | None
    metric_name: str | None
    model: str | None
    total_samples: int
    status: str
    stderr: float | None = None
    sector_scores: dict[str, tuple[float, float | None]] = field(default_factory=dict)
    gap_items: tuple[str, ...] = ()
    gap_items_by_sector: dict[str, tuple[str, ...]] = field(default_factory=dict)
    judge_score: float | None = None
    judge_stderr: float | None = None
    judge_metric_name: str | None = None
    judge_grader: str | None = None
    judge_grader_config: str | None = None
    split: str | None = None

    @property
    def is_brazil(self) -> bool:
        """True if this task is mapped to a Brazil article (i.e. appears in the report body)."""
        return self.brazil_article is not None

    @property
    def has_judge(self) -> bool:
        """True if a judge scorer ran on this task (so it belongs in the judge table)."""
        return self.judge_score is not None

    @property
    def judge_delta(self) -> float | None:
        """``score - judge_score`` — the deterministic reading minus the judge's.

        **Positive** means the deterministic detector credits more than the judge does, i.e. the
        residual keyword surface reviewer ask #2 is about. Negative means the judge credits
        substance the cue lists miss, which is equally publishable and points at the *scorer*
        rather than the model.

        ``None`` unless both sides are present. The two are **different measures on the same 0-1
        range** — mean fraction of rubric elements detected, versus fraction of replies graded
        fully compliant — so this is a delta between two stated measures, never an error.
        """
        if self.score is None or self.judge_score is None:
            return None
        return self.score - self.judge_score

    @property
    def judge_delta_stderr(self) -> float | None:
        """Standard error of :attr:`judge_delta` — ``sqrt(se² + judge_se²)``, an **upper bound**.

        Unlike :attr:`SideBySideRow.delta_stderr`, whose two sides are independent runs, both
        scorers here grade the *same samples in the same run*. Their errors are therefore
        positively correlated and adding them in quadrature over-states the uncertainty. That is
        the conservative direction — it can only make a delta look less significant than it is —
        and the renderers say so rather than presenting it as exact.
        """
        if self.judge_delta is None or self.stderr is None or self.judge_stderr is None:
            return None
        return math.sqrt(self.stderr**2 + self.judge_stderr**2)


@dataclass
class ArticleGroup:
    """Aggregation of task scores under one ``(brazil_article, brazil_scope)``."""

    article: str
    scope: str | None
    tasks: list[TaskScore] = field(default_factory=list)

    @property
    def mean_score(self) -> float | None:
        """Mean of the member tasks' headline scores (ignoring tasks with no score)."""
        values = [t.score for t in self.tasks if t.score is not None]
        if not values:
            return None
        return sum(values) / len(values)

    @property
    def mean_stderr(self) -> float | None:
        """Standard error of :attr:`mean_score` — ``sqrt(Σ seᵢ²)/k`` over the scored members.

        ``None`` when no member is scored, or when any scored member lacks a standard error (no
        partial pooling; see :func:`_pooled_stderr`).
        """
        return _pooled_stderr([t.stderr for t in self.tasks if t.score is not None])


@dataclass
class SectorGroup:
    """One sector's slice of the overlay section — every task that scored that sector.

    Only ``aia_checklist`` declares per-sector metrics today, so a group usually holds one task;
    the shape generalises so a second sector-aware task needs no change here.

    Attributes:
        sector: The sector key exactly as the log recorded it (e.g. ``"finance_bacen"``). The
            report does not translate it: the key is the stable machine identifier, and the
            regulator names live in the section heading.
        tasks: ``(task_name, mean, stderr | None)`` per contributing task, sorted by task name.
        gap_items: The union of the contributing tasks' gap-flagging item ids, sorted.
    """

    sector: str
    tasks: list[tuple[str, float, float | None]] = field(default_factory=list)
    gap_items: tuple[str, ...] = ()

    @property
    def mean_score(self) -> float | None:
        """Mean of the contributing tasks' sector scores."""
        if not self.tasks:
            return None
        return sum(value for _, value, _ in self.tasks) / len(self.tasks)

    @property
    def mean_stderr(self) -> float | None:
        """Standard error of :attr:`mean_score`, pooled exactly as the per-article means are."""
        return _pooled_stderr([se for _, _, se in self.tasks])


@dataclass(frozen=True)
class SideBySideRow:
    """One EU↔Brazil comparison row.

    For a same-scorer pair, both ``eu_score`` and ``brazil_score`` are populated and ``delta``
    is ``brazil_score - eu_score``. For a Brazil-only task, ``eu_task`` / ``eu_score`` are
    ``None`` and ``has_eu_equivalent`` is ``False`` (the headline "no EU equivalent" finding).

    ``brazil_stderr`` / ``eu_stderr`` carry each side's standard error (appended with defaults so
    existing constructions are unaffected), and :attr:`delta_stderr` propagates them, so the delta
    itself is reported with an error bar.
    """

    brazil_task: str
    brazil_article: str | None
    brazil_scope: str | None
    brazil_score: float | None
    eu_task: str | None
    eu_score: float | None
    has_eu_equivalent: bool
    brazil_stderr: float | None = None
    eu_stderr: float | None = None

    @property
    def delta(self) -> float | None:
        """``brazil_score - eu_score`` for a paired row, else ``None``."""
        if self.eu_score is None or self.brazil_score is None:
            return None
        return self.brazil_score - self.eu_score

    @property
    def delta_stderr(self) -> float | None:
        """Standard error of :attr:`delta` — ``sqrt(brazil_stderr² + eu_stderr²)``.

        The two sides are **independent runs** (different datasets scored by the same scorer), so
        their errors add in quadrature. ``None`` when the row has no delta or either side lacks a
        standard error.
        """
        if self.delta is None or self.brazil_stderr is None or self.eu_stderr is None:
            return None
        return math.sqrt(self.brazil_stderr**2 + self.eu_stderr**2)


@dataclass(frozen=True)
class RequirementCoverage:
    """One row of the 9-requirement breadth coverage map (Phase 10).

    For each COMPL-AI technical requirement, records whether Brazil compliance is covered by a
    **Brazil-specific benchmark** (✅), by an **EU task only** (🟡 — the requirement was exercised
    in the run but only via its preserved original COMPL-AI task), or **not yet covered** (⚪ — no
    task for this requirement ran). ``brazil_article`` is the PL 2338/2023 article when one exists
    (either via the requirement→article mapping or carried on the Brazil benchmark's decorator),
    else ``None``.

    Attributes:
        requirement: The COMPL-AI ``technical_requirement`` string (one of the canonical nine).
        brazil_article: The PL 2338/2023 article this requirement maps to, or ``None``.
        has_brazil_benchmark: True if a Brazil-specific benchmark for this requirement ran.
        eu_only_score: Mean EU-task score for this requirement when there is no Brazil benchmark
            (context for an EU-only requirement that was nonetheless exercised), else ``None``.
        ran: True if any task for this requirement appeared in the run at all.
        eu_only_stderr: Standard error of ``eu_only_score``, pooled over the requirement's scored
            tasks (``None`` if absent or if any contributing task lacks one).
    """

    requirement: str
    brazil_article: str | None
    has_brazil_benchmark: bool
    eu_only_score: float | None
    ran: bool
    eu_only_stderr: float | None = None

    @property
    def status(self) -> str:
        """Coverage status: ``"brazil"`` (✅) / ``"eu_only"`` (🟡) / ``"uncovered"`` (⚪)."""
        if self.has_brazil_benchmark:
            return "brazil"
        if self.ran:
            return "eu_only"
        return "uncovered"


@dataclass
class BrazilComplianceReport:
    """The assembled Brazil PL 2338/2023 compliance report for one run directory.

    Attributes:
        log_dir: The run directory the report was built from.
        models: Sorted list of model ids found in the run (usually one).
        article_groups: Per-``(article, scope)`` aggregations, sorted by article then scope.
        side_by_side: EU↔Brazil rows — same-scorer pairs first, then Brazil-only rows.
        brazil_task_scores: The report-body Brazil benchmark scores (Brazil-mapped tasks,
            excluding the EU pair counterparts, which live in the side-by-side EU column).
        eu_task_scores: EU counterpart task scores that participate in a side-by-side pair.
        unmapped_tasks: EU-only task scores with no Brazil article (context, not scored here).
        coverage_by_requirement: The 9-requirement breadth coverage map (one row per canonical
            COMPL-AI technical requirement), in :data:`NINE_TECHNICAL_REQUIREMENTS` order.
        sector_groups: The sector overlay — one entry per sector any task reported, sorted by
            sector key. Empty for a run with no sector-aware task, in which case the overlay
            section is omitted entirely rather than rendered blank.
    """

    log_dir: str
    models: list[str]
    article_groups: list[ArticleGroup]
    side_by_side: list[SideBySideRow]
    brazil_task_scores: list[TaskScore]
    eu_task_scores: list[TaskScore]
    unmapped_tasks: list[TaskScore]
    coverage_by_requirement: list[RequirementCoverage]
    sector_groups: list[SectorGroup] = field(default_factory=list)

    # -- lookups -------------------------------------------------------------------------

    def group_for(self, article: str, scope: str | None = None) -> ArticleGroup | None:
        """Return the article group matching ``article`` (and ``scope`` if given)."""
        for group in self.article_groups:
            if group.article == article and (scope is None or group.scope == scope):
                return group
        return None

    def sector_for(self, sector: str) -> SectorGroup | None:
        """Return the overlay group for a sector key, if the run produced one."""
        for group in self.sector_groups:
            if group.sector == sector:
                return group
        return None

    @property
    def judge_rows(self) -> list[TaskScore]:
        """The tasks a judge scorer ran on, sorted by task name — the judge table's rows.

        Empty for every run without ``--task-arg <task>:judge=true``, in which case the section is
        omitted entirely rather than rendered blank (the same discipline the sector overlay uses).
        """
        return sorted(
            (t for t in self.brazil_task_scores if t.has_judge), key=lambda t: t.task
        )

    def row_for(self, brazil_task: str) -> SideBySideRow | None:
        """Return the side-by-side row for a Brazil task name, if present."""
        for row in self.side_by_side:
            if row.brazil_task == brazil_task:
                return row
        return None

    # -- rendering -----------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a plain JSON-able dict (the ``--json`` view).

        Every score is accompanied by its standard error: ``stderr`` per task, ``mean_stderr`` per
        article group, ``brazil_stderr`` / ``eu_stderr`` / ``delta_stderr`` per side-by-side row,
        and ``eu_only_stderr`` per coverage row. A ``null`` means the underlying log carried no
        usable standard error (or, for an aggregate, that not every member did).
        """
        return {
            "log_dir": self.log_dir,
            "models": self.models,
            "articles": [
                {
                    "article": group.article,
                    "scope": group.scope,
                    "mean_score": group.mean_score,
                    "mean_stderr": group.mean_stderr,
                    "tasks": [
                        {
                            "task": t.task,
                            "score": t.score,
                            "stderr": t.stderr,
                            "metric": t.metric_name,
                            "samples": t.total_samples,
                            "technical_requirement": t.technical_requirement,
                        }
                        for t in group.tasks
                    ],
                }
                for group in self.article_groups
            ],
            "eu_brazil_side_by_side": [
                {
                    "brazil_task": row.brazil_task,
                    "brazil_article": row.brazil_article,
                    "brazil_scope": row.brazil_scope,
                    "brazil_score": row.brazil_score,
                    "brazil_stderr": row.brazil_stderr,
                    "eu_task": row.eu_task,
                    "eu_score": row.eu_score,
                    "eu_stderr": row.eu_stderr,
                    "delta": row.delta,
                    "delta_stderr": row.delta_stderr,
                    "has_eu_equivalent": row.has_eu_equivalent,
                }
                for row in self.side_by_side
            ],
            "coverage_by_requirement": [
                {
                    "requirement": cov.requirement,
                    "brazil_article": cov.brazil_article,
                    "has_brazil_benchmark": cov.has_brazil_benchmark,
                    "eu_only_score": cov.eu_only_score,
                    "eu_only_stderr": cov.eu_only_stderr,
                    "ran": cov.ran,
                    "status": cov.status,
                }
                for cov in self.coverage_by_requirement
            ],
            "sector_overlay": [
                {
                    "sector": group.sector,
                    "mean_score": group.mean_score,
                    "mean_stderr": group.mean_stderr,
                    # Per sector since Phase 6 (Resolution 11). Before that this repeated every
                    # gap id in every entry, so a consumer could not tell that ``health_anvisa``
                    # has none. A pre-Phase-6 log still shows the old repeated list, because the
                    # split is not recorded in it.
                    "gap_items": list(group.gap_items),
                    "tasks": [
                        {"task": task, "score": value, "stderr": se}
                        for task, value, se in group.tasks
                    ],
                }
                for group in self.sector_groups
            ],
            "deterministic_vs_judge": [
                {
                    "task": t.task,
                    "split": t.split,
                    "samples": t.total_samples,
                    "deterministic_score": t.score,
                    "deterministic_stderr": t.stderr,
                    "deterministic_metric": t.metric_name,
                    "judge_score": t.judge_score,
                    "judge_stderr": t.judge_stderr,
                    "judge_metric": t.judge_metric_name,
                    "judge_grader": t.judge_grader,
                    "judge_grader_config": t.judge_grader_config,
                    "delta": t.judge_delta,
                    # sqrt(se² + judge_se²) — an **upper bound**: the two scorers grade the same
                    # samples, so their errors are positively correlated.
                    "delta_stderr": t.judge_delta_stderr,
                    "delta_stderr_is_upper_bound": True,
                }
                for t in self.judge_rows
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Render the report as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render the report as Markdown (the default ``vigilai report`` view)."""
        return _render_markdown(self)

    def to_html(self) -> str:
        """Render the report as a self-contained HTML compliance scorecard (``--html`` view).

        A single ``<html>`` document with inline ``<style>`` and **no external assets**
        (CSS / JS / fonts), so it opens anywhere offline and works as a judge-facing
        task-artifact preview. Framed as the Art. 28 "public conclusions" of the Algorithmic
        Impact Assessment. Pure presentation over the already-aggregated report data — no new
        aggregation logic.
        """
        return _render_html(self)


# ---------------------------------------------------------------------------------------
# Formatting helpers.
# ---------------------------------------------------------------------------------------
def _fmt_score(value: float | None) -> str:
    """Format a 0-1 score to 3 decimals, or ``"—"`` when absent."""
    return f"{value:.3f}" if value is not None else "—"


def _fmt_delta(value: float | None) -> str:
    """Format a signed delta to 3 decimals, or ``"—"`` when not applicable."""
    if value is None:
        return "—"
    return f"{value:+.3f}"


def _fmt_score_se(value: float | None, se: float | None) -> str:
    """Format a score with its standard error — e.g. ``"0.524 ± 0.112"``.

    Falls back to the **bare point estimate** when no standard error is available (never
    ``± None``), and to ``"—"`` when there is no score at all.
    """
    if value is None:
        return "—"
    if se is None:
        return f"{value:.3f}"
    return f"{value:.3f} ± {se:.3f}"


def _fmt_delta_se(value: float | None, se: float | None) -> str:
    """Format a signed delta with its propagated standard error — e.g. ``"-0.451 ± 0.118"``."""
    if value is None:
        return "—"
    if se is None:
        return f"{value:+.3f}"
    return f"{value:+.3f} ± {se:.3f}"


def _scope_suffix(scope: str | None) -> str:
    return f" ({scope})" if scope else ""


# Coverage status -> (Markdown glyph + label). Shared by the Markdown and HTML coverage maps so
# the two never drift. ✅ Brazil benchmark / 🟡 EU task only / ⚪ not yet covered.
_COVERAGE_MARK: dict[str, str] = {
    "brazil": "✅ Brazil benchmark",
    "eu_only": "🟡 EU task only",
    "uncovered": "⚪ not yet covered",
}


# The sector-overlay section's standing caveat. Shared verbatim by the Markdown and HTML
# renderers (modulo markup) so the two can never drift, and worded so the section cannot be read
# as a claim that Brazil regulates AI by sector — it does not.
_SECTOR_CAVEAT_PARTS: tuple[str, ...] = (
    "No Brazilian sector regulator has issued a binding AI-specific rule. Each overlay scores a "
    "deployment against the adjacent, binding obligations that act as *de facto* analogues to "
    "PL 2338's rights — ombudsman duties, credit-model governance, Cadastro Positivo rights — "
    "plus the cross-sector Arts. 25-28 items every sample carries.",
    "Some overlay items are **gap-flagging**: no instrument imposes them, so they test whether "
    "the deployer voluntarily exceeds the baseline, and a low score there is a finding about "
    "Brazilian law rather than about the model.",
    "Structural analogies for benchmark design — **not legal advice**. Instruments, "
    "primary-source URLs and sourcing tiers: `docs/sector-overlay-legal-verification.md`.",
)


def _render_sector_markdown(report: BrazilComplianceReport) -> list[str]:
    """The 'Sector overlay' Markdown section, or nothing when no task reported a sector."""
    if not report.sector_groups:
        return []
    lines: list[str] = []
    lines.append("## Sector overlay (BACEN / ANVISA / CVM)")
    lines.append("")
    for part in _SECTOR_CAVEAT_PARTS:
        lines.append(part)
        lines.append("")
    lines.append("| Sector | Task | Sector score ± se |")
    lines.append("|---|---|---|")
    for group in report.sector_groups:
        for task, value, se in group.tasks:
            lines.append(f"| `{group.sector}` | `{task}` | {_fmt_score_se(value, se)} |")
        if len(group.tasks) > 1:
            lines.append(
                f"| **`{group.sector}` — mean** |  | "
                f"**{_fmt_score_se(group.mean_score, group.mean_stderr)}** |"
            )
    lines.append("")
    gap_items = sorted({item for group in report.sector_groups for item in group.gap_items})
    if gap_items:
        listed = ", ".join(f"`{item}`" for item in gap_items)
        lines.append(f"**Gap-flagging items in this run:** {listed}.")
        lines.append("")
    return lines


# The judge section's standing explanation. Shared verbatim by the Markdown and HTML renderers
# (modulo markup) so the two can never drift, and worded so the delta cannot be read as an error
# rate, a disagreement rate, or a correction to the deterministic score.
_JUDGE_SECTION_TITLE = "Deterministic vs. LLM-judge (held-out)"

_JUDGE_CAVEAT_PARTS: tuple[str, ...] = (
    "Reviewer ask #2: how much of a rubric score is **keyword surface** and how much is genuine "
    "procedural reasoning. The deterministic scorer detects whether each rubric element's cues "
    "are present; the LLM judge is asked, element by element, whether the reply establishes each "
    "one as a **substantive procedural commitment** — a route the affected person could actually "
    "take, in whatever words — and grades a reply `C` only when every element clears that bar.",
    "**The two columns are different measures on the same 0-1 range, not two estimates of one "
    "quantity.** Deterministic is Inspect's `mean`: the mean *fraction of rubric elements* "
    "detected. Judge is Inspect's `accuracy`: the *fraction of replies graded `C`* (a `P` counts "
    "half). So Δ is a signed difference between two **stated measures** — a positive Δ means the "
    "detector credits more than the judge does, a negative Δ means the judge credits substance "
    "the cue lists miss. It is not an error, not a disagreement rate, and not a correction.",
    "**Δ's error bar is an upper bound.** Both scorers grade the *same samples in the same run*, "
    "so their errors are positively correlated and `sqrt(se² + judge_se²)` over-states the "
    "uncertainty. That is the conservative direction — it can only make a Δ look less significant "
    "than it is.",
    "Per-sample agreement (mean |Δ|, rank correlation, direction disagreements) needs the sample "
    "records, which this header-only aggregator deliberately never loads; it arrives in Phase 7.",
)


def _judge_grader_line(report: BrazilComplianceReport) -> str | None:
    """The grader id + config line, so the judge numbers are reproducible from the artifact alone.

    Reads what the rows actually recorded rather than a constant, so a run graded by something
    other than the pinned grader — a mock in the test suite, a future local grader — says so.
    Multiple distinct graders in one run are all listed rather than silently collapsed.
    """
    graders = sorted({t.judge_grader for t in report.judge_rows if t.judge_grader})
    configs = sorted({t.judge_grader_config for t in report.judge_rows if t.judge_grader_config})
    if not graders:
        return None
    grader_str = ", ".join(f"`{g}`" for g in graders)
    if configs:
        return f"**Grader:** {grader_str} at `{'; '.join(configs)}`, bound as model role `grader`."
    return f"**Grader:** {grader_str}, bound as model role `grader`."


def _render_judge_markdown(report: BrazilComplianceReport) -> list[str]:
    """The 'Deterministic vs. LLM-judge' Markdown section, or nothing when no judge ran."""
    rows = report.judge_rows
    if not rows:
        return []
    lines: list[str] = []
    lines.append(f"## {_JUDGE_SECTION_TITLE}")
    lines.append("")
    grader_line = _judge_grader_line(report)
    if grader_line is not None:
        lines.append(grader_line)
        lines.append("")
    for part in _JUDGE_CAVEAT_PARTS:
        lines.append(part)
        lines.append("")
    lines.append(
        "| Task | Split | Samples | Deterministic (mean element fraction) ± se | "
        "LLM-judge (accuracy: fraction graded C) ± se | Δ (deterministic − judge) ± se |"
    )
    lines.append("|---|---|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| `{row.task}` | {row.split or '—'} | {row.total_samples} | "
            f"{_fmt_score_se(row.score, row.stderr)} | "
            f"{_fmt_score_se(row.judge_score, row.judge_stderr)} | "
            f"{_fmt_delta_se(row.judge_delta, row.judge_delta_stderr)} |"
        )
    lines.append("")
    return lines


def _render_markdown(report: BrazilComplianceReport) -> str:
    lines: list[str] = []
    lines.append("# Brazil PL 2338/2023 — Compliance Report")
    lines.append("")
    model_str = ", ".join(report.models) if report.models else "(unknown)"
    lines.append(f"- **Model(s):** {model_str}")
    lines.append(f"- **Log directory:** `{report.log_dir}`")
    lines.append(
        f"- **Brazil-mapped tasks scored:** {len(report.brazil_task_scores)}"
    )
    lines.append("")
    lines.append(
        "Scores are joined to PL 2338/2023 Chapter II rights (Arts. 5-6) and the AIA "
        "obligations (Arts. 25-28) via each task's `brazil_article` tag. Higher is better "
        "(1.0 = full compliance on the benchmark)."
    )
    lines.append("")
    lines.append(
        "`± se` is the **standard error of the mean** computed by the Inspect scorer and read "
        "from this run's `.eval` logs — not hand-compiled. Per-article means pool the member "
        "errors as `sqrt(Σ seᵢ²)/k`; EU↔Brazil deltas propagate theirs as "
        "`sqrt(se_brazil² + se_eu²)` (independent runs). A score shown without `±` came from a "
        "log that carried no usable standard error, and an aggregate is shown without `±` unless "
        "every member carried one."
    )
    lines.append("")

    # -- Per-article section ------------------------------------------------------------
    lines.append("## Compliance by Brazil article")
    lines.append("")
    if report.article_groups:
        lines.append("| Brazil article | Scope | Task | EU technical requirement | Score ± se |")
        lines.append("|---|---|---|---|---|")
        for group in report.article_groups:
            for task in group.tasks:
                lines.append(
                    f"| {group.article} | {group.scope or '—'} | `{task.task}` | "
                    f"{task.technical_requirement or '—'} | "
                    f"{_fmt_score_se(task.score, task.stderr)} |"
                )
            # Per-article aggregate row (only meaningful when >1 task or for emphasis).
            lines.append(
                f"| **{group.article} — mean** | {group.scope or '—'} |  |  | "
                f"**{_fmt_score_se(group.mean_score, group.mean_stderr)}** |"
            )
    else:
        lines.append("_No Brazil-mapped tasks found in this run._")
    lines.append("")

    # -- EU↔Brazil side-by-side section -------------------------------------------------
    lines.append("## EU ↔ Brazil side-by-side")
    lines.append("")
    lines.append(
        "The two direct-adaptation pairs reuse the **exact same scorer**, so the delta "
        "isolates the Brazil-specific content. `explanation_quality` and `aia_checklist` "
        "have **no EU/COMPL-AI counterpart** — that absence is itself a finding."
    )
    lines.append("")
    lines.append(
        "| Brazil task | Brazil article | Brazil score ± se | EU task | EU score ± se | "
        "Δ (Brazil − EU) ± se |"
    )
    lines.append("|---|---|---|---|---|---|")
    for row in report.side_by_side:
        if row.has_eu_equivalent:
            eu_task = f"`{row.eu_task}`"
            eu_score = _fmt_score_se(row.eu_score, row.eu_stderr)
            delta = _fmt_delta_se(row.delta, row.delta_stderr)
        else:
            eu_task = "_no EU equivalent_"
            eu_score = "—"
            delta = "—"
        article = f"{row.brazil_article}{_scope_suffix(row.brazil_scope)}" if row.brazil_article else "—"
        lines.append(
            f"| `{row.brazil_task}` | {article} | "
            f"{_fmt_score_se(row.brazil_score, row.brazil_stderr)} | "
            f"{eu_task} | {eu_score} | {delta} |"
        )
    lines.append("")

    # -- Sector overlay section ----------------------------------------------------------
    lines.extend(_render_sector_markdown(report))

    # -- Deterministic ↔ LLM-judge section -----------------------------------------------
    lines.extend(_render_judge_markdown(report))

    # -- Coverage map section (9-requirement breadth) -----------------------------------
    lines.append("## Brazil compliance coverage map (9 requirements)")
    lines.append("")
    lines.append(
        "Brazil compliance assessed across **all nine** COMPL-AI technical requirements — not "
        "just the four with bespoke Brazil benchmarks. ✅ a Brazil-specific benchmark covers the "
        "requirement; 🟡 only the preserved EU/COMPL-AI task ran (no Brazil benchmark yet); ⚪ "
        "not covered in this run."
    )
    lines.append("")
    lines.append(
        "| EU technical requirement | Brazil article | Coverage | EU-only score ± se |"
    )
    lines.append("|---|---|---|---|")
    for cov in report.coverage_by_requirement:
        lines.append(
            f"| {cov.requirement} | {cov.brazil_article or '—'} | "
            f"{_COVERAGE_MARK[cov.status]} | "
            f"{_fmt_score_se(cov.eu_only_score, cov.eu_only_stderr)} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------
# HTML rendering (the self-contained ``--html`` scorecard).
#
# A pure presentation layer over the already-built report. No new aggregation: the same
# ``article_groups`` / ``side_by_side`` that Markdown/JSON use, rendered as a color-coded
# per-article dashboard. Self-contained (inline CSS, no external src/href), HTML-escaped
# dynamic values, deterministic ordering (guaranteed upstream by the builders).
# ---------------------------------------------------------------------------------------

# Score bands -> CSS class. Green ≥ 0.8, amber 0.5–0.8, red < 0.5, grey when absent.
_BAND_GOOD = 0.8
_BAND_WARN = 0.5


def _score_band(value: float | None) -> str:
    """Map a 0-1 score to a band CSS class: ``good`` / ``warn`` / ``bad`` / ``na``."""
    if value is None:
        return "na"
    if value >= _BAND_GOOD:
        return "good"
    if value >= _BAND_WARN:
        return "warn"
    return "bad"


def _delta_band(value: float | None) -> str:
    """Map a signed delta to a band CSS class by sign: ``good`` / ``bad`` / ``na``."""
    if value is None:
        return "na"
    if value > 0:
        return "good"
    if value < 0:
        return "bad"
    return "warn"


def _esc(value: Any) -> str:
    """HTML-escape any dynamic value (quotes included) for safe inline insertion."""
    return html.escape("" if value is None else str(value), quote=True)


# The three Markdown conventions the shared prose blocks use. Applied **after** escaping, so the
# text is safe first and marked up second — a note is authored once and rendered in both views
# rather than maintained twice.
_MD_CODE_RE = re.compile(r"`([^`]+)`")
_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_MD_EM_RE = re.compile(r"\*([^*]+)\*")


def _md_note_to_html(text: str) -> str:
    """Escape a shared prose block, then restore its ``**bold**`` / ``*em*`` / ``code`` markup."""
    escaped = _esc(text)
    escaped = _MD_CODE_RE.sub(r"<code>\1</code>", escaped)
    escaped = _MD_BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    return _MD_EM_RE.sub(r"<em>\1</em>", escaped)


_HTML_STYLE = """
:root {
  --good: #1b7f3b; --good-bg: #e4f5e9;
  --warn: #8a6100; --warn-bg: #fbf1d6;
  --bad:  #b3261e; --bad-bg:  #fae3e1;
  --na:   #5f6368; --na-bg:   #eceef1;
  --ink: #1a1a1a; --muted: #5f6368; --line: #d8dce1; --accent: #0b3d91;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--ink); margin: 0; padding: 2rem; line-height: 1.5;
  background: #f6f7f9;
}
.wrap { max-width: 1040px; margin: 0 auto; background: #fff; border: 1px solid var(--line);
  border-radius: 12px; padding: 2rem 2.25rem; }
header { border-bottom: 3px solid var(--accent); padding-bottom: 1rem; margin-bottom: 1.5rem; }
h1 { font-size: 1.55rem; margin: 0 0 .35rem; color: var(--accent); }
.caption { color: var(--muted); font-style: italic; margin: .25rem 0 .75rem; }
.meta { list-style: none; padding: 0; margin: 0; color: var(--ink); font-size: .92rem; }
.meta li { margin: .15rem 0; }
.meta code { background: #f0f1f4; padding: .1rem .3rem; border-radius: 4px; }
h2 { font-size: 1.15rem; margin: 1.8rem 0 .6rem; }
p.note { color: var(--muted); font-size: .9rem; margin: 0 0 .8rem; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { text-align: left; padding: .5rem .65rem; border-bottom: 1px solid var(--line); }
th { background: #f2f4f7; font-weight: 600; }
td.score, th.score { text-align: center; white-space: nowrap; }
code.task { background: #f0f1f4; padding: .1rem .3rem; border-radius: 4px; }
tr.mean td { font-weight: 700; background: #f8f9fb; border-top: 2px solid var(--line); }
.badge { display: inline-block; min-width: 3.4rem; text-align: center; padding: .15rem .5rem;
  border-radius: 999px; font-weight: 700; font-variant-numeric: tabular-nums; }
.badge.good { color: var(--good); background: var(--good-bg); }
.badge.warn { color: var(--warn); background: var(--warn-bg); }
.badge.bad  { color: var(--bad);  background: var(--bad-bg); }
.badge.na   { color: var(--na);   background: var(--na-bg); }
.se { color: var(--muted); font-size: .8em; font-variant-numeric: tabular-nums; }
.no-eu { color: var(--muted); font-style: italic; }
td.cov, th.cov { white-space: nowrap; }
.cov-pill { display: inline-block; padding: .15rem .55rem; border-radius: 999px;
  font-weight: 600; font-size: .85rem; }
.cov-pill.brazil    { color: var(--good); background: var(--good-bg); }
.cov-pill.eu_only   { color: var(--warn); background: var(--warn-bg); }
.cov-pill.uncovered { color: var(--na);   background: var(--na-bg); }
footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--line);
  color: var(--muted); font-size: .82rem; }
"""


# Coverage status -> (HTML pill label). The glyphs are kept (they render fine in HTML) so the
# Markdown and HTML maps read identically; the pill's CSS class colors it by status.
_COVERAGE_HTML_LABEL: dict[str, str] = {
    "brazil": "✅ Brazil benchmark",
    "eu_only": "🟡 EU task only",
    "uncovered": "⚪ not yet covered",
}


def _html_badge(value: float | None, band: str) -> str:
    """A pill badge showing a formatted score with its band color class."""
    return f'<span class="badge {band}">{_esc(_fmt_score(value))}</span>'


def _html_delta_badge(value: float | None) -> str:
    """A pill badge showing a signed delta colored by sign."""
    return f'<span class="badge {_delta_band(value)}">{_esc(_fmt_delta(value))}</span>'


def _html_se(se: float | None) -> str:
    """A muted ``± se`` sibling of a badge, or ``""`` when there is no standard error.

    Deliberately *outside* the badge: the point estimate keeps its band coloring
    (:func:`_score_band` / :func:`_delta_band` are untouched) and the error bar reads as
    subordinate to it rather than competing with it.
    """
    if se is None:
        return ""
    return f' <span class="se">{_esc(f"± {se:.3f}")}</span>'


def _render_article_table(report: BrazilComplianceReport) -> list[str]:
    rows: list[str] = []
    rows.append("<table>")
    rows.append(
        "<thead><tr>"
        "<th>Brazil article</th><th>Scope</th><th>Task</th>"
        "<th>EU technical requirement</th><th class='score'>Score ± se</th>"
        "</tr></thead>"
    )
    rows.append("<tbody>")
    if not report.article_groups:
        rows.append(
            "<tr><td colspan='5'><em>No Brazil-mapped tasks found in this run.</em></td></tr>"
        )
    for group in report.article_groups:
        for task in group.tasks:
            rows.append(
                "<tr>"
                f"<td>{_esc(group.article)}</td>"
                f"<td>{_esc(group.scope or '—')}</td>"
                f"<td><code class='task'>{_esc(task.task)}</code></td>"
                f"<td>{_esc(task.technical_requirement or '—')}</td>"
                f"<td class='score'>{_html_badge(task.score, _score_band(task.score))}"
                f"{_html_se(task.stderr)}</td>"
                "</tr>"
            )
        rows.append(
            "<tr class='mean'>"
            f"<td>{_esc(group.article)} — mean</td>"
            f"<td>{_esc(group.scope or '—')}</td>"
            "<td></td><td></td>"
            f"<td class='score'>{_html_badge(group.mean_score, _score_band(group.mean_score))}"
            f"{_html_se(group.mean_stderr)}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return rows


def _render_side_by_side_table(report: BrazilComplianceReport) -> list[str]:
    rows: list[str] = []
    rows.append("<table>")
    rows.append(
        "<thead><tr>"
        "<th>Brazil task</th><th>Brazil article</th><th class='score'>Brazil score ± se</th>"
        "<th>EU task</th><th class='score'>EU score ± se</th>"
        "<th class='score'>Δ (Brazil − EU) ± se</th>"
        "</tr></thead>"
    )
    rows.append("<tbody>")
    for row in report.side_by_side:
        article = (
            f"{row.brazil_article}{_scope_suffix(row.brazil_scope)}"
            if row.brazil_article
            else "—"
        )
        if row.has_eu_equivalent:
            eu_task_cell = f"<code class='task'>{_esc(row.eu_task)}</code>"
            eu_score_cell = _html_badge(
                row.eu_score, _score_band(row.eu_score)
            ) + _html_se(row.eu_stderr)
            delta_cell = _html_delta_badge(row.delta) + _html_se(row.delta_stderr)
        else:
            eu_task_cell = "<span class='no-eu'>no EU equivalent</span>"
            eu_score_cell = "<span class='badge na'>—</span>"
            delta_cell = "<span class='badge na'>—</span>"
        rows.append(
            "<tr>"
            f"<td><code class='task'>{_esc(row.brazil_task)}</code></td>"
            f"<td>{_esc(article)}</td>"
            f"<td class='score'>{_html_badge(row.brazil_score, _score_band(row.brazil_score))}"
            f"{_html_se(row.brazil_stderr)}</td>"
            f"<td>{eu_task_cell}</td>"
            f"<td class='score'>{eu_score_cell}</td>"
            f"<td class='score'>{delta_cell}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return rows


def _render_sector_table(report: BrazilComplianceReport) -> list[str]:
    rows: list[str] = []
    rows.append("<table>")
    rows.append(
        "<thead><tr>"
        "<th>Sector</th><th>Task</th><th class='score'>Sector score ± se</th>"
        "</tr></thead>"
    )
    rows.append("<tbody>")
    for group in report.sector_groups:
        for task, value, se in group.tasks:
            rows.append(
                "<tr>"
                f"<td><code class='task'>{_esc(group.sector)}</code></td>"
                f"<td><code class='task'>{_esc(task)}</code></td>"
                f"<td class='score'>{_html_badge(value, _score_band(value))}"
                f"{_html_se(se)}</td>"
                "</tr>"
            )
        if len(group.tasks) > 1:
            rows.append(
                "<tr class='mean'>"
                f"<td><code class='task'>{_esc(group.sector)}</code> — mean</td>"
                "<td></td>"
                f"<td class='score'>"
                f"{_html_badge(group.mean_score, _score_band(group.mean_score))}"
                f"{_html_se(group.mean_stderr)}</td>"
                "</tr>"
            )
    rows.append("</tbody></table>")
    return rows


def _render_sector_section(report: BrazilComplianceReport) -> list[str]:
    """The 'Sector overlay' HTML section, or nothing when no task reported a sector."""
    if not report.sector_groups:
        return []
    parts: list[str] = []
    parts.append("<h2>Sector overlay (BACEN / ANVISA / CVM)</h2>")
    for part in _SECTOR_CAVEAT_PARTS:
        # The shared caveat is plain prose with Markdown emphasis; escape it, then restore the
        # two markup conventions it uses so the HTML reads the same as the Markdown.
        text = _esc(part).replace("**", "").replace("*de facto*", "<em>de facto</em>")
        parts.append(f'<p class="note">{text}</p>')
    parts.extend(_render_sector_table(report))
    gap_items = sorted({item for group in report.sector_groups for item in group.gap_items})
    if gap_items:
        listed = ", ".join(f"<code class='task'>{_esc(item)}</code>" for item in gap_items)
        parts.append(
            f'<p class="note"><strong>Gap-flagging items in this run:</strong> {listed}.</p>'
        )
    return parts


def _render_judge_table(report: BrazilComplianceReport) -> list[str]:
    rows: list[str] = []
    rows.append("<table>")
    rows.append(
        "<thead><tr>"
        "<th>Task</th><th>Split</th><th class='score'>Samples</th>"
        "<th class='score'>Deterministic<br><span class='se'>mean element fraction</span></th>"
        "<th class='score'>LLM-judge<br><span class='se'>accuracy: fraction graded C</span></th>"
        "<th class='score'>Δ (deterministic − judge)</th>"
        "</tr></thead>"
    )
    rows.append("<tbody>")
    for row in report.judge_rows:
        rows.append(
            "<tr>"
            f"<td><code class='task'>{_esc(row.task)}</code></td>"
            f"<td>{_esc(row.split or '—')}</td>"
            f"<td class='score'>{row.total_samples}</td>"
            f"<td class='score'>{_html_badge(row.score, _score_band(row.score))}"
            f"{_html_se(row.stderr)}</td>"
            f"<td class='score'>{_html_badge(row.judge_score, _score_band(row.judge_score))}"
            f"{_html_se(row.judge_stderr)}</td>"
            f"<td class='score'>{_html_delta_badge(row.judge_delta)}"
            f"{_html_se(row.judge_delta_stderr)}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return rows


def _render_judge_section(report: BrazilComplianceReport) -> list[str]:
    """The 'Deterministic vs. LLM-judge' HTML section, or nothing when no judge ran."""
    if not report.judge_rows:
        return []
    parts: list[str] = []
    parts.append(f"<h2>{_esc(_JUDGE_SECTION_TITLE)}</h2>")
    grader_line = _judge_grader_line(report)
    if grader_line is not None:
        parts.append(f'<p class="note">{_md_note_to_html(grader_line)}</p>')
    for part in _JUDGE_CAVEAT_PARTS:
        parts.append(f'<p class="note">{_md_note_to_html(part)}</p>')
    parts.extend(_render_judge_table(report))
    return parts


def _render_coverage_table(report: BrazilComplianceReport) -> list[str]:
    rows: list[str] = []
    rows.append("<table>")
    rows.append(
        "<thead><tr>"
        "<th>EU technical requirement</th><th>Brazil article</th>"
        "<th class='cov'>Coverage</th><th class='score'>EU-only score ± se</th>"
        "</tr></thead>"
    )
    rows.append("<tbody>")
    for cov in report.coverage_by_requirement:
        pill = (
            f"<span class='cov-pill {cov.status}'>"
            f"{_esc(_COVERAGE_HTML_LABEL[cov.status])}</span>"
        )
        eu_only_cell = (
            _html_badge(cov.eu_only_score, _score_band(cov.eu_only_score))
            + _html_se(cov.eu_only_stderr)
            if cov.eu_only_score is not None
            else "<span class='badge na'>—</span>"
        )
        rows.append(
            "<tr>"
            f"<td>{_esc(cov.requirement)}</td>"
            f"<td>{_esc(cov.brazil_article or '—')}</td>"
            f"<td class='cov'>{pill}</td>"
            f"<td class='score'>{eu_only_cell}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return rows


def _render_html(report: BrazilComplianceReport) -> str:
    model_str = ", ".join(report.models) if report.models else "(unknown)"
    generated = date.today().isoformat()

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append(
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    parts.append("<title>Brazil PL 2338/2023 — Compliance Scorecard</title>")
    parts.append(f"<style>{_HTML_STYLE}</style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append('<div class="wrap">')

    # -- Header (Art. 28 public-conclusions framing) ------------------------------------
    parts.append("<header>")
    parts.append("<h1>Brazil PL 2338/2023 — Compliance Scorecard</h1>")
    parts.append(
        '<p class="caption">Public conclusions of the Algorithmic Impact Assessment '
        "(PL 2338/2023, Art. 28).</p>"
    )
    parts.append('<ul class="meta">')
    parts.append(f"<li><strong>Model(s):</strong> {_esc(model_str)}</li>")
    parts.append(
        f"<li><strong>Log directory:</strong> <code>{_esc(report.log_dir)}</code></li>"
    )
    parts.append(
        f"<li><strong>Brazil-mapped tasks scored:</strong> "
        f"{len(report.brazil_task_scores)}</li>"
    )
    parts.append(f"<li><strong>Generated:</strong> {_esc(generated)}</li>")
    parts.append("</ul>")
    parts.append("</header>")

    parts.append(
        '<p class="note">Scores are joined to PL 2338/2023 Chapter II rights (Arts. 5-6), '
        "the high-risk contestation / human-review rights (Art. 6, II-III), and the AIA "
        "obligations (Arts. 25-28) via each task&#39;s <code>brazil_article</code> tag. "
        "Higher is better (1.0 = full compliance on the benchmark). "
        '<span class="badge good">≥ 0.80</span> '
        '<span class="badge warn">0.50–0.80</span> '
        '<span class="badge bad">&lt; 0.50</span>'
    )
    parts.append(
        '<p class="note"><span class="se">± se</span> is the <strong>standard error of the '
        "mean</strong> computed by the Inspect scorer and read from this run&#39;s "
        "<code>.eval</code> logs — not hand-compiled. Per-article means pool the member errors "
        "as <code>sqrt(&Sigma; se&sup2;)/k</code>; EU↔Brazil deltas propagate theirs as "
        "<code>sqrt(se_brazil&sup2; + se_eu&sup2;)</code> (independent runs). A score shown "
        "without <code>±</code> came from a log carrying no usable standard error, and an "
        "aggregate is shown without one unless every member carried one.</p>"
    )

    # -- Per-article section ------------------------------------------------------------
    parts.append("<h2>Compliance by Brazil article</h2>")
    parts.extend(_render_article_table(report))

    # -- EU↔Brazil side-by-side section -------------------------------------------------
    parts.append("<h2>EU ↔ Brazil side-by-side</h2>")
    parts.append(
        '<p class="note">The two direct-adaptation pairs reuse the <strong>exact same '
        "scorer</strong>, so the delta isolates the Brazil-specific content. "
        "<code>explanation_quality</code>, <code>contestation_review</code>, and "
        "<code>aia_checklist</code> have <strong>no EU/COMPL-AI counterpart</strong> — that "
        "absence is itself a finding.</p>"
    )
    parts.extend(_render_side_by_side_table(report))

    # -- Sector overlay section ----------------------------------------------------------
    parts.extend(_render_sector_section(report))

    # -- Deterministic ↔ LLM-judge section -----------------------------------------------
    parts.extend(_render_judge_section(report))

    # -- Coverage map section (9-requirement breadth) -----------------------------------
    parts.append("<h2>Brazil compliance coverage map (9 requirements)</h2>")
    parts.append(
        '<p class="note">Brazil compliance assessed across <strong>all nine</strong> COMPL-AI '
        "technical requirements — not just the four with bespoke Brazil benchmarks. "
        '<span class="cov-pill brazil">✅ Brazil benchmark</span> '
        '<span class="cov-pill eu_only">🟡 EU task only</span> '
        '<span class="cov-pill uncovered">⚪ not yet covered</span></p>'
    )
    parts.extend(_render_coverage_table(report))

    parts.append(
        "<footer>Generated by <code>vigilai report --html</code>. Self-contained "
        "(no external assets); serves as the Art. 28 public-conclusions artifact of the "
        "Algorithmic Impact Assessment.</footer>"
    )
    parts.append("</div>")
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------------------
# Log loading.
# ---------------------------------------------------------------------------------------
def _task_score_from_log(log: EvalLog) -> TaskScore:
    """Build a :class:`TaskScore` from a single eval log (header is sufficient)."""
    spec = log.eval
    task_name = _bare_task_name(spec.task)
    attribs = dict(spec.task_attribs or {})
    article, scope = _resolve_brazil_metadata(task_name, attribs)

    score_value: float | None = None
    metric_name: str | None = None
    stderr_value: float | None = None
    sector_scores: dict[str, tuple[float, float | None]] = {}
    judge_value: float | None = None
    judge_metric_name: str | None = None
    judge_stderr_value: float | None = None
    judge_grader: str | None = None
    judge_grader_config: str | None = None
    total_samples = 0
    if log.results is not None:
        total_samples = log.results.total_samples
        # **By name, never by index.** A judge run has two scores, so ``scores[0]`` would make the
        # headline depend on the order the task happens to declare its scorers in — silently, with
        # a judge accuracy landing in the per-article compliance table. See ``_select_score``.
        deterministic = _select_score(list(log.results.scores), judge=False)
        judge = _select_score(list(log.results.scores), judge=True)
        if deterministic is not None:
            # The standard error is read from the *same* metrics dict — a sibling of the point
            # estimate, not a competing one, and so are the per-sector grouped metrics.
            metrics = deterministic.metrics
            metric_name, score_value = _headline_metric(metrics)
            stderr_value = _stderr_metric(metrics)
            sector_scores = _sector_metrics(metrics)
            if total_samples < _MIN_SAMPLES_FOR_STDERR:
                # Fewer than two observations: Inspect's 0 is a placeholder, not an estimate.
                stderr_value = None
            # The same discipline for the per-sector errors, applied as conservatively as a
            # header-only reader can: the log records the task's total sample count but **not**
            # each group's, so we drop every sector's standard error unless the run has enough
            # samples for every group to have reached two. That is exactly the case Phase 6's
            # ``split=held_out`` runs hit (one sample per sector), where Inspect's placeholder 0
            # would otherwise print a single observation as ``0.000 ± 0.000``.
            #
            # Residual, stated rather than hidden: an *unbalanced* run — say 5 samples split 4/1
            # across two sectors — passes this test while one group still has a single
            # observation. Detecting that needs the samples, and this aggregator is deliberately
            # header-only. Every dataset the repo ships is balanced across sectors by
            # construction (``aia_scenarios`` interleaves), so the case is not reachable today.
            if sector_scores and total_samples < _MIN_SAMPLES_FOR_STDERR * len(sector_scores):
                sector_scores = {
                    sector: (value, None) for sector, (value, _) in sector_scores.items()
                }
        if judge is not None:
            judge_metric_name, judge_value = _headline_metric(judge.metrics)
            judge_stderr_value = _stderr_metric(judge.metrics)
            if total_samples < _MIN_SAMPLES_FOR_STDERR:
                judge_stderr_value = None
            judge_grader, judge_grader_config = _judge_grader_from_log(log, judge)

    # The dataset slice the run used. Resolution 1 requires held-out and full-set judge agreement
    # to be reported separately and always labelled, so the label has to come off the artifact
    # rather than off the operator's memory of which command produced it.
    task_args = dict(spec.task_args or {})
    split = task_args.get("split")

    return TaskScore(
        task=task_name,
        brazil_article=article,
        brazil_scope=scope,
        technical_requirement=attribs.get("technical_requirement"),
        score=score_value,
        metric_name=metric_name,
        model=spec.model,
        total_samples=total_samples,
        status=log.status,
        stderr=stderr_value,
        sector_scores=sector_scores,
        gap_items=_gap_items_from_attribs(attribs),
        gap_items_by_sector=_gap_items_by_sector_from_attribs(attribs),
        judge_score=judge_value,
        judge_stderr=judge_stderr_value,
        judge_metric_name=judge_metric_name,
        judge_grader=judge_grader,
        judge_grader_config=judge_grader_config,
        split=str(split) if isinstance(split, str) else None,
    )


def _load_task_scores(log_dir: str) -> list[TaskScore]:
    """Read every eval log under ``log_dir`` and resolve each to a :class:`TaskScore`.

    Uses the Inspect log API (``list_eval_logs`` + ``read_eval_log(header_only=True)``); only
    the header is needed (task spec + score metrics), so this is cheap even for large runs.

    When a directory holds **more than one log for the same task** — which is what happens when
    a task is re-run into an existing ``--log-dir`` — the log with the **latest
    ``EvalSpec.created``** wins, so the report shows the most recent score for that task.

    **This used to be wrong, and silently.** The old code iterated ``list_eval_logs`` and let
    each log overwrite the previous entry, documented as "keeping the most recent score". But
    ``list_eval_logs`` defaults to ``descending=True`` — newest **first** — so last-write-wins
    kept the *oldest* log instead. Found on 2026-07-26 while re-running a single corrected task
    into its existing scaled log dir: the report would have gone on reporting the superseded
    number with no warning anywhere. Recency is now taken from ``EvalSpec.created``, which
    travels inside the log rather than depending on a listing order or on file mtimes, and the
    listing order no longer matters at all.
    """
    infos = list_eval_logs(log_dir)
    best: dict[str, tuple[str, str, TaskScore]] = {}
    for info in infos:
        log = read_eval_log(info, header_only=True)
        task_score = _task_score_from_log(log)
        # ``created`` is an ISO-8601 timestamp, so lexicographic order is chronological order.
        # The log path is the tie-break, purely so the choice is deterministic when two logs
        # for one task carry the same ``created`` (same-second runs).
        key = (log.eval.created or "", info.name)
        previous = best.get(task_score.task)
        if previous is None or key > (previous[0], previous[1]):
            best[task_score.task] = (key[0], key[1], task_score)
    return [entry[2] for entry in best.values()]


# ---------------------------------------------------------------------------------------
# Assembly.
# ---------------------------------------------------------------------------------------
def _build_article_groups(brazil_scores: list[TaskScore]) -> list[ArticleGroup]:
    """Group Brazil-mapped task scores by ``(article, scope)``, sorted for stable output."""
    groups: dict[tuple[str, str | None], ArticleGroup] = {}
    for task in brazil_scores:
        assert task.brazil_article is not None  # brazil_scores are pre-filtered
        key = (task.brazil_article, task.brazil_scope)
        if key not in groups:
            groups[key] = ArticleGroup(article=task.brazil_article, scope=task.brazil_scope)
        groups[key].tasks.append(task)

    # Sort tasks within a group by name; sort groups by (article, scope) for deterministic
    # rendering.
    for group in groups.values():
        group.tasks.sort(key=lambda t: t.task)
    return [groups[key] for key in sorted(groups, key=lambda k: (k[0], k[1] or ""))]


def _build_side_by_side(
    brazil_scores: list[TaskScore], scores_by_task: dict[str, TaskScore]
) -> list[SideBySideRow]:
    """Build EU↔Brazil rows: same-scorer pairs first, then Brazil-only rows.

    A pair row is emitted for each Brazil task in :data:`EU_BRAZIL_PAIRS`; its EU score is
    taken from the EU counterpart's run in the same log dir (``None`` if that EU task was not
    run). Every other Brazil-mapped task becomes a Brazil-only row (``has_eu_equivalent`` =
    ``False``). Both sides' standard errors ride along so the row can report
    :attr:`SideBySideRow.delta_stderr`.
    """
    paired_rows: list[SideBySideRow] = []
    brazil_only_rows: list[SideBySideRow] = []

    for task in sorted(brazil_scores, key=lambda t: t.task):
        eu_name = EU_BRAZIL_PAIRS.get(task.task)
        if eu_name is not None:
            eu_score_obj = scores_by_task.get(eu_name)
            paired_rows.append(
                SideBySideRow(
                    brazil_task=task.task,
                    brazil_article=task.brazil_article,
                    brazil_scope=task.brazil_scope,
                    brazil_score=task.score,
                    eu_task=eu_name,
                    eu_score=eu_score_obj.score if eu_score_obj else None,
                    has_eu_equivalent=True,
                    brazil_stderr=task.stderr,
                    eu_stderr=eu_score_obj.stderr if eu_score_obj else None,
                )
            )
        else:
            brazil_only_rows.append(
                SideBySideRow(
                    brazil_task=task.task,
                    brazil_article=task.brazil_article,
                    brazil_scope=task.brazil_scope,
                    brazil_score=task.score,
                    eu_task=None,
                    eu_score=None,
                    has_eu_equivalent=False,
                    brazil_stderr=task.stderr,
                    eu_stderr=None,
                )
            )

    return paired_rows + brazil_only_rows


def _build_sector_groups(scores: list[TaskScore]) -> list[SectorGroup]:
    """Group the per-sector metrics of every sector-aware task, sorted by sector then task.

    A task with no ``grouped()`` metrics contributes nothing, so a run without ``aia_checklist``
    produces an empty list and the overlay section is omitted rather than rendered blank.

    **Gap items are per sector since Phase 6 (Resolution 11).** A task that recorded
    ``brazil_gap_items_by_sector`` contributes only *that sector's* ids — and contributes **none**
    for a sector absent from its mapping, which is the fix: ``health_anvisa`` has no gap item and
    used to list all five, because the only thing in the log header was one flat string. A
    pre-Phase-6 log has no mapping and falls back to the flat list, reproducing its own recorded
    behaviour rather than inventing a split that is not in it.
    """
    groups: dict[str, SectorGroup] = {}
    gap_by_sector: dict[str, set[str]] = {}
    for task in sorted(scores, key=lambda t: t.task):
        for sector, (value, se) in sorted(task.sector_scores.items()):
            group = groups.setdefault(sector, SectorGroup(sector=sector))
            group.tasks.append((task.task, value, se))
            if task.gap_items_by_sector:
                sector_gaps: tuple[str, ...] = task.gap_items_by_sector.get(sector, ())
            else:
                sector_gaps = task.gap_items
            gap_by_sector.setdefault(sector, set()).update(sector_gaps)
    for sector, group in groups.items():
        group.gap_items = tuple(sorted(gap_by_sector.get(sector, set())))
    return [groups[sector] for sector in sorted(groups)]


def _build_coverage(all_scores: list[TaskScore]) -> list[RequirementCoverage]:
    """Build the 9-requirement breadth coverage map.

    For each canonical COMPL-AI technical requirement (always all nine, in fixed order), decide:

    * **has_brazil_benchmark** — True if a *vigilAI Brazil-specific benchmark*
      (:data:`BRAZIL_BENCHMARK_TASKS`) for this requirement ran. This deliberately excludes
      *preserved EU tasks* whose requirement merely maps to a Brazil article (``fairllm`` /
      ``bold`` / ``cab`` / ``decoding_trust``): those make the requirement "EU task only" (🟡),
      not "Brazil benchmark" (✅). It correctly credits ``contestation_review`` / ``aia_checklist``
      (requirement ``"Societal Alignment"``) to that requirement via the explicit benchmark set.
    * **brazil_article** — the article of the covering Brazil benchmark if one exists, else the
      requirement→article mapping (so the four mapped requirements still show their article even
      when only an EU task ran), else ``None``.
    * **eu_only_score** — when there is no Brazil benchmark, the mean headline score of the run's
      tasks for this requirement (context for an exercised-but-EU-only requirement), else ``None``.
      **eu_only_stderr** pools the contributing tasks' standard errors the same way
      :attr:`ArticleGroup.mean_stderr` does (``None`` unless every contributor carried one).
    * **ran** — True if any task for this requirement appeared in the run.
    """
    scores_by_req: dict[str, list[TaskScore]] = {}
    for s in all_scores:
        if s.technical_requirement:
            scores_by_req.setdefault(s.technical_requirement, []).append(s)

    coverage: list[RequirementCoverage] = []
    for requirement in NINE_TECHNICAL_REQUIREMENTS:
        req_all = scores_by_req.get(requirement, [])
        req_benchmarks = [t for t in req_all if t.task in BRAZIL_BENCHMARK_TASKS]
        has_brazil = bool(req_benchmarks)
        ran = bool(req_all)

        # Article: prefer the covering Brazil benchmark's article, else the requirement mapping.
        article: str | None = None
        if req_benchmarks:
            article = next(
                (t.brazil_article for t in req_benchmarks if t.brazil_article is not None),
                None,
            )
        if article is None:
            mapped = brazil_article_for(requirement)
            if mapped is not None:
                article = mapped[0]

        # EU-only score: mean of the requirement's run scores when there is no Brazil benchmark,
        # with the same pooled standard error the per-article means use.
        eu_only_score: float | None = None
        eu_only_stderr: float | None = None
        if not has_brazil:
            scored = [t for t in req_all if t.score is not None]
            values = [t.score for t in scored if t.score is not None]
            if values:
                eu_only_score = sum(values) / len(values)
                eu_only_stderr = _pooled_stderr([t.stderr for t in scored])

        coverage.append(
            RequirementCoverage(
                requirement=requirement,
                brazil_article=article,
                has_brazil_benchmark=has_brazil,
                eu_only_score=eu_only_score,
                ran=ran,
                eu_only_stderr=eu_only_stderr,
            )
        )
    return coverage


def build_brazil_report(log_dir: str) -> BrazilComplianceReport:
    """Build a :class:`BrazilComplianceReport` from an Inspect run directory.

    Reads every eval log under ``log_dir``, resolves each task's Brazil article/scope
    (decorator-first; see module docstring), aggregates the Brazil-mapped task scores per
    article + scope, and assembles the EU↔Brazil side-by-side (same-scorer pairs plus
    Brazil-only rows).

    Args:
        log_dir: Path to an Inspect run directory (the per-model timestamped folder under
            ``logs/`` that ``vigilai eval`` writes, or any directory of ``.eval`` / ``.json``
            logs).

    Returns:
        The assembled report, ready to render via :meth:`BrazilComplianceReport.to_markdown`
        or :meth:`BrazilComplianceReport.to_json`.
    """
    all_scores = _load_task_scores(log_dir)
    scores_by_task = {s.task: s for s in all_scores}

    # The report body is the *Brazil benchmarks*: Brazil-mapped tasks, EXCLUDING the EU pair
    # counterparts. The EU pair tasks (``human_deception`` / ``bbq``) are themselves Art. 5
    # tagged, but they belong in the EU column of the side-by-side, not double-counted in the
    # per-article compliance body — otherwise the US-centric EU benchmark would dilute the
    # Brazil article's score. They stay available in ``scores_by_task`` for the EU lookup.
    brazil_scores = [
        s for s in all_scores if s.is_brazil and s.task not in EU_PAIR_TASKS
    ]
    # EU tasks that participate in a side-by-side pair (kept for the JSON/Markdown context).
    eu_scores = [s for s in all_scores if s.task in EU_PAIR_TASKS]
    unmapped = [
        s for s in all_scores if not s.is_brazil and s.task not in EU_PAIR_TASKS
    ]

    models = sorted({s.model for s in all_scores if s.model})

    return BrazilComplianceReport(
        log_dir=log_dir,
        models=models,
        article_groups=_build_article_groups(brazil_scores),
        side_by_side=_build_side_by_side(brazil_scores, scores_by_task),
        brazil_task_scores=brazil_scores,
        eu_task_scores=eu_scores,
        unmapped_tasks=unmapped,
        coverage_by_requirement=_build_coverage(all_scores),
        sector_groups=_build_sector_groups(all_scores),
    )
