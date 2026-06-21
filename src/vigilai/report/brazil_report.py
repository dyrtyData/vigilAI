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
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from functools import lru_cache
from typing import Any

from inspect_ai.log import EvalLog
from inspect_ai.log import list_eval_logs
from inspect_ai.log import read_eval_log

from vigilai.brazil.mapping import brazil_article_for


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

# Inspect prefixes task names with the plugin/registry name ("vigilai/human_deception").
_REGISTRY_PREFIX = "vigilai/"

# Metric-name preference when reading a score's headline value. Upstream reused scorers report
# ``accuracy`` (match / choice); the new Brazil rubric/checklist scorers report ``mean``. We
# prefer accuracy, then mean, then fall back to the first available metric so the report never
# silently drops a score.
_METRIC_PREFERENCE: tuple[str, ...] = ("accuracy", "mean")


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


@dataclass(frozen=True)
class SideBySideRow:
    """One EU↔Brazil comparison row.

    For a same-scorer pair, both ``eu_score`` and ``brazil_score`` are populated and ``delta``
    is ``brazil_score - eu_score``. For a Brazil-only task, ``eu_task`` / ``eu_score`` are
    ``None`` and ``has_eu_equivalent`` is ``False`` (the headline "no EU equivalent" finding).
    """

    brazil_task: str
    brazil_article: str | None
    brazil_scope: str | None
    brazil_score: float | None
    eu_task: str | None
    eu_score: float | None
    has_eu_equivalent: bool

    @property
    def delta(self) -> float | None:
        """``brazil_score - eu_score`` for a paired row, else ``None``."""
        if self.eu_score is None or self.brazil_score is None:
            return None
        return self.brazil_score - self.eu_score


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
    """

    log_dir: str
    models: list[str]
    article_groups: list[ArticleGroup]
    side_by_side: list[SideBySideRow]
    brazil_task_scores: list[TaskScore]
    eu_task_scores: list[TaskScore]
    unmapped_tasks: list[TaskScore]

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
        """Serialize the report to a plain JSON-able dict (the ``--json`` view)."""
        return {
            "log_dir": self.log_dir,
            "models": self.models,
            "articles": [
                {
                    "article": group.article,
                    "scope": group.scope,
                    "mean_score": group.mean_score,
                    "tasks": [
                        {
                            "task": t.task,
                            "score": t.score,
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
                    "eu_task": row.eu_task,
                    "eu_score": row.eu_score,
                    "delta": row.delta,
                    "has_eu_equivalent": row.has_eu_equivalent,
                }
                for row in self.side_by_side
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Render the report as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render the report as Markdown (the default ``vigilai report`` view)."""
        return _render_markdown(self)


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


def _scope_suffix(scope: str | None) -> str:
    return f" ({scope})" if scope else ""


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

    # -- Per-article section ------------------------------------------------------------
    lines.append("## Compliance by Brazil article")
    lines.append("")
    if report.article_groups:
        lines.append("| Brazil article | Scope | Task | EU technical requirement | Score |")
        lines.append("|---|---|---|---|---|")
        for group in report.article_groups:
            for task in group.tasks:
                lines.append(
                    f"| {group.article} | {group.scope or '—'} | `{task.task}` | "
                    f"{task.technical_requirement or '—'} | {_fmt_score(task.score)} |"
                )
            # Per-article aggregate row (only meaningful when >1 task or for emphasis).
            lines.append(
                f"| **{group.article} — mean** | {group.scope or '—'} |  |  | "
                f"**{_fmt_score(group.mean_score)}** |"
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
        "| Brazil task | Brazil article | Brazil score | EU task | EU score | Δ (Brazil − EU) |"
    )
    lines.append("|---|---|---|---|---|---|")
    for row in report.side_by_side:
        if row.has_eu_equivalent:
            eu_task = f"`{row.eu_task}`"
            eu_score = _fmt_score(row.eu_score)
            delta = _fmt_delta(row.delta)
        else:
            eu_task = "_no EU equivalent_"
            eu_score = "—"
            delta = "—"
        article = f"{row.brazil_article}{_scope_suffix(row.brazil_scope)}" if row.brazil_article else "—"
        lines.append(
            f"| `{row.brazil_task}` | {article} | {_fmt_score(row.brazil_score)} | "
            f"{eu_task} | {eu_score} | {delta} |"
        )
    lines.append("")
    return "\n".join(lines)


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
    total_samples = 0
    if log.results is not None:
        total_samples = log.results.total_samples
        if log.results.scores:
            # A task usually has a single score; take the first (its headline metric).
            metric_name, score_value = _headline_metric(log.results.scores[0].metrics)

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
    ``False``).
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
                )
            )

    return paired_rows + brazil_only_rows


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
    )
