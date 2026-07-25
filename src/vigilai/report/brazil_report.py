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
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from datetime import date
from dataclasses import field
from functools import lru_cache
from typing import Any

from inspect_ai.log import EvalLog
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

    @property
    def is_brazil(self) -> bool:
        """True if this task is mapped to a Brazil article (i.e. appears in the report body)."""
        return self.brazil_article is not None


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
    """

    log_dir: str
    models: list[str]
    article_groups: list[ArticleGroup]
    side_by_side: list[SideBySideRow]
    brazil_task_scores: list[TaskScore]
    eu_task_scores: list[TaskScore]
    unmapped_tasks: list[TaskScore]
    coverage_by_requirement: list[RequirementCoverage]

    # -- lookups -------------------------------------------------------------------------

    def group_for(self, article: str, scope: str | None = None) -> ArticleGroup | None:
        """Return the article group matching ``article`` (and ``scope`` if given)."""
        for group in self.article_groups:
            if group.article == article and (scope is None or group.scope == scope):
                return group
        return None

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
    total_samples = 0
    if log.results is not None:
        total_samples = log.results.total_samples
        if log.results.scores:
            # A task usually has a single score; take the first (its headline metric). The
            # standard error is read from the *same* metrics dict — a sibling of the point
            # estimate, not a competing one.
            metrics = log.results.scores[0].metrics
            metric_name, score_value = _headline_metric(metrics)
            stderr_value = _stderr_metric(metrics)
            if total_samples < _MIN_SAMPLES_FOR_STDERR:
                # Fewer than two observations: Inspect's 0 is a placeholder, not an estimate.
                stderr_value = None

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
    )


def _load_task_scores(log_dir: str) -> list[TaskScore]:
    """Read every eval log under ``log_dir`` and resolve each to a :class:`TaskScore`.

    Uses the Inspect log API (``list_eval_logs`` + ``read_eval_log(header_only=True)``); only
    the header is needed (task spec + score metrics), so this is cheap even for large runs.
    Later logs for the same task (Inspect writes one log per task per run) overwrite earlier
    ones, keeping the most recent score for a task.
    """
    infos = list_eval_logs(log_dir)
    scores_by_task: dict[str, TaskScore] = {}
    for info in infos:
        log = read_eval_log(info, header_only=True)
        task_score = _task_score_from_log(log)
        scores_by_task[task_score.task] = task_score
    return list(scores_by_task.values())


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
    )
