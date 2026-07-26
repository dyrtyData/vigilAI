"""Census the BBQ-family logs of a run: which axes were actually sampled, and the honest delta.

The tool that makes Resolution 13(f) checkable rather than assertable. Three jobs, all of them
things that were *assumed* for two iterations and turned out to be false:

1. **What the sample set actually contains.** Reads the axis (subset) and the
   (context condition × question polarity) cell of every EU ``bbq`` sample from the log itself, so
   "the EU baseline spans four matched axes in equal proportion" is a measurement rather than a
   claim. The age-only baseline was invisible for two iterations precisely because nobody printed
   this table.
2. **The empty-``Score.answer`` census.** The one-line pre-flight Resolution 13(h)(v) made
   doctrine: a reused ``multiple_choice`` scorer scores an unreadable completion ``INCORRECT`` with
   an **empty** ``Score.answer`` and no warning anywhere. Sonnet 4.6 emitted 1,628 of them on
   ``bbq_brazil``. Run this before reading any number off a BBQ log.
3. **Cluster-robust error bars and the delta.** Both BBQ datasets emit **four samples per
   scenario** (2 context conditions × 2 question polarities over one context template and one
   identity pair), so Inspect's ``stderr()`` — which assumes independence — is a **lower bound** on
   both sides of the pair. This computes the scenario-level (cluster-robust) standard error for
   each side and propagates it into the EU↔Brazil delta.

   This is stricter than the Resolution 13 measurement, which clustered the **Brazil** side only
   and used the nominal EU standard error, because the EU side was a single axis whose scenario
   structure had never been read. Both sides are clustered here.

Usage::

    uv run python tools/bbq_axis_census.py logs/iter2-matched-axes-claude-haiku-4-5 \\
                                           logs/iter2-matched-axes-claude-sonnet-4-6

    # Regenerate the committed census artifact (and its drift guard's input):
    uv run python tools/bbq_axis_census.py logs/iter2-matched-axes-* --emit docs/bbq-matched-axes-census.md

Epoch policy, stated because a sample-level consumer must state one (Phase 7's rule): the ten
``EvalSample`` rows of a ``sample_id`` are **reduced by the mean**, matching Inspect's own default
reducer, so ``n`` is samples rather than generations and the nominal standard error reproduces the
one in the log header.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from inspect_ai.log import EvalLog
from inspect_ai.log import list_eval_logs
from inspect_ai.log import read_eval_log


# The two tasks of the EU↔Brazil bias pair. Both are graded by
# ``vigilai.tasks.choice_parse.choice_sigil_tolerant``, which is what makes the delta like-for-like.
EU_TASK = "bbq"
BRAZIL_TASK = "bbq_brazil"
BBQ_TASKS = (EU_TASK, BRAZIL_TASK)

# Samples per scenario in both datasets: 2 context conditions × 2 question polarities.
SAMPLES_PER_SCENARIO = 4


def _bare_task_name(task: str) -> str:
    """Strip Inspect's ``vigilai/`` registry prefix from a task name."""
    return task.split("/")[-1]


def eu_axis(sample_id: str) -> str:
    """The BBQ subset (axis) an EU sample belongs to.

    ``combine_subsets`` builds every id as ``f"{subset}_{example_id:05d}"``, so the axis is
    everything before the final underscore. Read off the id rather than from
    ``metadata["category"]`` on purpose: the id is what ``--limit`` slices, so it is the thing that
    can silently go wrong.
    """
    return sample_id.rsplit("_", 1)[0]


def scenario_key(task: str, sample_id: str) -> str:
    """The cluster a sample belongs to — its **scenario**, shared by four samples.

    Args:
        task: Bare task name, ``"bbq"`` or ``"bbq_brazil"``.
        sample_id: The sample's id.

    Returns:
        A stable scenario identifier.

        * ``bbq_brazil`` ids are ``f"{category}_{index:03d}_{context}_{polarity}"``, so the scenario
          is the id with its **last two** components dropped — e.g. ``Class_004_ambig_neg`` →
          ``Class_004``. Dropping a suffix rather than keeping a prefix, because one category key
          contains an underscore of its own: ``Race_IBGE_000_ambig_neg``. Taking the first two
          components collapsed all twenty Race scenarios into one 80-member cluster and gave Haiku a
          cluster-robust bar of 0.0174 instead of 0.0181 — caught only by the equal-cluster-size
          assertion in :func:`census_log`, which is why that assertion is not optional.
        * ``bbq`` ids are ``f"{subset}_{example_id:05d}"`` and BBQ emits each scenario as **four
          consecutive rows** — verified against the pinned dataset revision, where
          ``Religion_00000``–``Religion_00003`` all carry
          ``answer_info == ['Jewish', 'Jewish'] / ["Can't answer", 'unknown']`` — so the scenario is
          ``f"{subset}_{example_id // 4}"``.

    Raises:
        ValueError: If ``task`` is not a BBQ-family task, or an id does not parse. Guessing a
            cluster key would silently misstate the error bar, which is the failure this whole
            module exists to stop.
    """
    if task == BRAZIL_TASK:
        parts = sample_id.split("_")
        if len(parts) < 3:
            raise ValueError(f"unparsable {BRAZIL_TASK} sample id {sample_id!r}")
        return "_".join(parts[:-2])
    if task == EU_TASK:
        axis, _, number = sample_id.rpartition("_")
        if not axis or not number.isdigit():
            raise ValueError(f"unparsable {EU_TASK} sample id {sample_id!r}")
        return f"{axis}_{int(number) // SAMPLES_PER_SCENARIO}"
    raise ValueError(f"{task!r} is not a BBQ-family task; expected one of {list(BBQ_TASKS)}")


def _numeric(value: object) -> float:
    """A ``Score.value`` as a 0/1 float.

    ``choice()`` (and therefore the sigil-tolerant wrapper) records Inspect's ``CORRECT`` /
    ``INCORRECT`` string constants ``"C"`` / ``"I"`` rather than numbers, so a bare ``float()``
    would raise. Read from the constant rather than hard-coded, so an upstream rename fails loudly.
    """
    from inspect_ai.scorer import CORRECT

    if isinstance(value, str):
        return 1.0 if value == CORRECT else 0.0
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"cannot read a numeric score from {value!r}")


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _se_of_mean(values: list[float]) -> float | None:
    """Standard error of the mean of ``values``, or ``None`` below two observations.

    ``None`` rather than Inspect's placeholder ``0``: printing ``± 0.000`` for one observation reads
    as infinitely precise, which is the overconfidence Phase 1 exists to remove.
    """
    n = len(values)
    if n < 2:
        return None
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    return math.sqrt(variance / n)


def cluster_scores(task: str, reduced: dict[str, float]) -> dict[str, list[float]]:
    """Group epoch-reduced per-sample scores by scenario.

    Args:
        task: Bare task name.
        reduced: ``{sample_id: mean score over epochs}``.

    Returns:
        ``{scenario key: [member scores]}``.
    """
    clusters: dict[str, list[float]] = defaultdict(list)
    for sample_id, value in reduced.items():
        clusters[scenario_key(task, sample_id)].append(value)
    return dict(clusters)


def check_cluster_sizes(
    clusters: dict[str, list[float]], label: str, *, allow_partial: bool = False
) -> None:
    """Refuse to compute a cluster-robust bar over unequal clusters.

    Assert the cluster structure rather than assume it. Two reasons, and the first already paid for
    itself during implementation: a wrong cluster key misstates the error bar **silently** (taking
    the first two id components made all twenty ``Race_IBGE`` scenarios one 80-member cluster and
    quietly moved Haiku's bar from 0.0181 to 0.0174), and the mean-of-cluster-means is only equal to
    the overall mean when the clusters are equal-sized.

    Args:
        clusters: The output of :func:`cluster_scores`.
        label: Something identifying, for the error message — usually the log path.
        allow_partial: Skip the check. Only for a deliberately truncated run.

    Raises:
        ValueError: If any cluster does not hold exactly :data:`SAMPLES_PER_SCENARIO` scores.
    """
    if allow_partial:
        return
    wrong = {
        key: len(values)
        for key, values in clusters.items()
        if len(values) != SAMPLES_PER_SCENARIO
    }
    if not wrong:
        return
    raise ValueError(
        f"{label}: {len(wrong)} of {len(clusters)} scenario clusters do not hold exactly "
        f"{SAMPLES_PER_SCENARIO} samples (e.g. {dict(list(wrong.items())[:3])}). Either the run "
        f"was truncated by a --limit that is not a multiple of {SAMPLES_PER_SCENARIO}, or the "
        f"sample-id scheme moved and scenario_key() no longer derives the right cluster. Pass "
        f"--allow-partial-scenarios only if you know it is the former."
    )


@dataclass(frozen=True)
class TaskCensus:
    """Everything read off one BBQ-family ``.eval`` log."""

    task: str
    model: str
    log_path: str
    task_args: dict[str, object]
    rows: int
    """``EvalSample`` rows, i.e. samples × epochs."""
    samples: int
    """Distinct ``sample_id`` values — the ``n`` behind the nominal standard error."""
    epochs: int
    scenarios: int
    """Distinct clusters — the ``n`` behind the cluster-robust standard error."""
    empty_answers: int
    """Rows whose ``Score.answer`` is empty. **Any non-zero value invalidates the numbers.**"""
    scorer: str
    accuracy: float
    nominal_se: float | None
    clustered_se: float | None
    header_accuracy: float | None
    header_se: float | None
    axis_counts: Counter[str] = field(default_factory=Counter)
    cell_counts: Counter[str] = field(default_factory=Counter)
    axis_accuracy: dict[str, float] = field(default_factory=dict)
    sample_ids: tuple[str, ...] = ()

    @property
    def design_effect(self) -> float | None:
        """Variance inflation from clustering — ``(clustered_se / nominal_se)²``."""
        if not self.nominal_se or self.clustered_se is None:
            return None
        return (self.clustered_se / self.nominal_se) ** 2


def census_log(
    log: EvalLog, log_path: str, *, allow_partial_scenarios: bool = False
) -> TaskCensus:
    """Read one BBQ-family log into a :class:`TaskCensus`.

    Args:
        log: A **fully loaded** log (samples included — the axis breakdown and the cluster-robust
            error bar are both per-sample facts that the header does not carry).
        log_path: The log's path, recorded so a published number is traceable to a file.
        allow_partial_scenarios: Downgrade the equal-cluster-size check to a no-op. Only for
            deliberately truncated runs; never for a published number.

    Returns:
        The census.

    Raises:
        ValueError: If the log carries no samples, a sample carries no score, or the scenario
            clusters are not all exactly :data:`SAMPLES_PER_SCENARIO` samples.
    """
    task = _bare_task_name(log.eval.task)
    samples = log.samples or []
    if not samples:
        raise ValueError(f"{log_path} carries no samples")

    per_sample: dict[str, list[float]] = defaultdict(list)
    axis_counts: Counter[str] = Counter()
    cell_counts: Counter[str] = Counter()
    axis_scores: dict[str, list[float]] = defaultdict(list)
    empty_answers = 0
    scorers: set[str] = set()

    for row in samples:
        scores = row.scores or {}
        if not scores:
            raise ValueError(f"{log_path} sample {row.id} carries no score")
        name, score = next(iter(scores.items()))
        scorers.add(name)
        if not (score.answer or "").strip():
            empty_answers += 1
        per_sample[str(row.id)].append(_numeric(score.value))

    # Axis / cell composition is a property of the sample set, not of the epochs, so it is counted
    # once per distinct sample id.
    seen: set[str] = set()
    for row in samples:
        sample_id = str(row.id)
        if sample_id in seen:
            continue
        seen.add(sample_id)
        metadata = row.metadata or {}
        if task == EU_TASK:
            axis_counts[eu_axis(sample_id)] += 1
        else:
            axis_counts[str(metadata.get("category", "<unrecorded>"))] += 1
        context = str(metadata.get("context_condition", "<unrecorded>"))
        polarity = str(metadata.get("question_polarity", metadata.get("polarity", "<unrecorded>")))
        # ``bbq`` records ``ambig``/``disambig`` + ``neg``/``nonneg``; ``bbq_brazil`` records
        # ``ambiguous``/``disambiguated`` + ``negative``/``non_negative``. Normalised to the short
        # forms so one table can hold both.
        cell_counts[f"{context[:8]}/{polarity[:6]}"] += 1

    reduced = {sample_id: _mean(values) for sample_id, values in per_sample.items()}
    for sample_id, value in reduced.items():
        if task == EU_TASK:
            axis_scores[eu_axis(sample_id)].append(value)
        else:
            axis_scores[str(sample_id.split("_")[0])].append(value)

    clusters = cluster_scores(task, reduced)
    check_cluster_sizes(clusters, log_path, allow_partial=allow_partial_scenarios)
    cluster_means = [_mean(values) for values in clusters.values()]

    header_accuracy: float | None = None
    header_se: float | None = None
    if log.results and log.results.scores:
        metrics = log.results.scores[0].metrics
        for candidate in ("accuracy", "mean"):
            if candidate in metrics:
                header_accuracy = float(metrics[candidate].value)
                break
        if "stderr" in metrics:
            header_se = float(metrics["stderr"].value)

    values = list(reduced.values())
    return TaskCensus(
        task=task,
        model=log.eval.model,
        log_path=log_path,
        task_args=dict(log.eval.task_args or {}),
        rows=len(samples),
        samples=len(reduced),
        epochs=log.eval.config.epochs or 1,
        scenarios=len(clusters),
        empty_answers=empty_answers,
        scorer=", ".join(sorted(scorers)),
        accuracy=_mean(values),
        nominal_se=_se_of_mean(values),
        clustered_se=_se_of_mean(cluster_means),
        header_accuracy=header_accuracy,
        header_se=header_se,
        axis_counts=axis_counts,
        cell_counts=cell_counts,
        axis_accuracy={axis: _mean(vals) for axis, vals in sorted(axis_scores.items())},
        sample_ids=tuple(sorted(reduced)),
    )


def census_run(log_dir: Path, *, allow_partial_scenarios: bool = False) -> dict[str, TaskCensus]:
    """Census every BBQ-family log in ``log_dir``, keeping the **newest** per task.

    Newest-per-task, not last-seen: ``list_eval_logs`` defaults to ``descending=True`` and a
    last-write-wins loop therefore kept the **oldest** log, which is Resolution 12(b) — the defect
    that would have gone on printing a superseded number with no warning.
    """
    newest: dict[str, tuple[str, str]] = {}
    for info in list_eval_logs(str(log_dir)):
        header = read_eval_log(info.name, header_only=True)
        task = _bare_task_name(header.eval.task)
        if task not in BBQ_TASKS:
            continue
        created = header.eval.created
        if task not in newest or created > newest[task][0]:
            newest[task] = (created, info.name)
    return {
        task: census_log(
            read_eval_log(path), path, allow_partial_scenarios=allow_partial_scenarios
        )
        for task, (_, path) in newest.items()
    }


@dataclass(frozen=True)
class Delta:
    """The EU↔Brazil bias delta, with both error bars and both significance verdicts."""

    model: str
    brazil: TaskCensus
    eu: TaskCensus

    @property
    def value(self) -> float:
        return self.brazil.accuracy - self.eu.accuracy

    def _propagated(self, clustered: bool) -> float | None:
        brazil = self.brazil.clustered_se if clustered else self.brazil.nominal_se
        eu = self.eu.clustered_se if clustered else self.eu.nominal_se
        if brazil is None or eu is None:
            return None
        return math.sqrt(brazil**2 + eu**2)

    @property
    def nominal_se(self) -> float | None:
        return self._propagated(clustered=False)

    @property
    def clustered_se(self) -> float | None:
        """The honest bar: both sides clustered on the scenario, then propagated."""
        return self._propagated(clustered=True)

    @property
    def z(self) -> float | None:
        se = self.clustered_se
        return None if not se else self.value / se
    @property
    def distinguishable(self) -> bool | None:
        """``|Δ| > 2 se`` on the **cluster-robust** bar. ``None`` if no bar could be computed."""
        z = self.z
        return None if z is None else abs(z) >= 2.0


def _fmt(value: float | None, places: int = 4) -> str:
    return "—" if value is None else f"{value:.{places}f}"


def _pm(value: float, se: float | None, places: int = 4) -> str:
    return f"{value:.{places}f}" if se is None else f"{value:.{places}f} ± {se:.{places}f}"


def render_report(runs: dict[str, dict[str, TaskCensus]]) -> str:
    """Render the census + delta tables as Markdown.

    Args:
        runs: ``{run label: {task: census}}``.

    Returns:
        The Markdown body (no title), suitable for stdout or for the committed artifact.
    """
    lines: list[str] = []

    lines.append("## What the EU `bbq` sample set actually contains")
    lines.append("")
    lines.append(
        "Read from each run's `.eval` samples, not from the task definition. This is the table "
        "whose absence let a 100-sample `Age`-only baseline stand as \"the EU bias benchmark\" for "
        "two iterations."
    )
    lines.append("")
    lines.append("| Run | `task_args` | samples | scenarios | axis breakdown | (context × polarity) cells |")
    lines.append("|---|---|---|---|---|---|")
    for label, tasks in runs.items():
        eu = tasks.get(EU_TASK)
        if eu is None:
            continue
        axes = ", ".join(f"{k} {v}" for k, v in sorted(eu.axis_counts.items()))
        cells = ", ".join(f"{k} {v}" for k, v in sorted(eu.cell_counts.items()))
        args = ", ".join(f"{k}={v!r}" for k, v in sorted(eu.task_args.items()))
        lines.append(
            f"| `{label}` | `{args}` | {eu.samples} | {eu.scenarios} | {axes} | {cells} |"
        )
    lines.append("")

    lines.append("## Empty-`Score.answer` census (the one-line pre-flight)")
    lines.append("")
    lines.append(
        "Resolution 13(h)(v) made this doctrine: a reused `multiple_choice` scorer marks an "
        "unreadable completion `INCORRECT` with an **empty** `Score.answer` and warns about "
        "nothing. **Any non-zero count invalidates every number below it.**"
    )
    lines.append("")
    lines.append("| Run | task | scorer | rows (samples × epochs) | empty `Score.answer` |")
    lines.append("|---|---|---|---|---|")
    for label, tasks in runs.items():
        for task in BBQ_TASKS:
            census = tasks.get(task)
            if census is None:
                continue
            flag = "**" if census.empty_answers else ""
            lines.append(
                f"| `{label}` | `{task}` | `{census.scorer}` | {census.rows} | "
                f"{flag}{census.empty_answers}{flag} |"
            )
    lines.append("")

    lines.append("## Scores, with both error bars")
    lines.append("")
    lines.append(
        "Both datasets emit **four samples per scenario** (2 context conditions × 2 question "
        "polarities over one context template and one identity pair), so the four are not "
        "independent and Inspect's `stderr()` is a **lower bound** on both sides. The "
        "cluster-robust column takes the scenario as the unit."
    )
    lines.append("")
    lines.append(
        "Every `accuracy` and `nominal se` below is **recomputed here from the per-row scores**, "
        "independently of Inspect, and the last column is Inspect's own header figure for the same "
        "log — they must agree, and a mismatch means one of the two reduced the epochs differently."
    )
    lines.append("")
    lines.append(
        "| Run | task | n samples | n scenarios | accuracy | nominal se | cluster-robust se "
        "| design effect | Inspect header (acc / se) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for label, tasks in runs.items():
        for task in BBQ_TASKS:
            census = tasks.get(task)
            if census is None:
                continue
            agrees = (
                census.header_accuracy is not None
                and abs(census.header_accuracy - census.accuracy) < 1e-9
                and census.header_se is not None
                and abs(census.header_se - (census.nominal_se or 0.0)) < 1e-9
            )
            mark = "" if agrees else " **MISMATCH**"
            lines.append(
                f"| `{label}` | `{task}` | {census.samples} | {census.scenarios} | "
                f"{_fmt(census.accuracy)} | {_fmt(census.nominal_se)} | "
                f"{_fmt(census.clustered_se)} | {_fmt(census.design_effect, 2)} | "
                f"{_fmt(census.header_accuracy)} / {_fmt(census.header_se)}{mark} |"
            )
    lines.append("")

    lines.append("## Per-axis accuracy")
    lines.append("")
    lines.append(
        "Reported so a reader can see whether one axis carries the aggregate. Each EU axis is "
        "**one quarter** of the sample set, so its own bar is roughly twice the aggregate's — "
        "these are directional, not per-axis findings."
    )
    lines.append("")
    for label, tasks in runs.items():
        for task in BBQ_TASKS:
            census = tasks.get(task)
            if census is None:
                continue
            breakdown = ", ".join(
                f"{axis} {value:.4f}" for axis, value in census.axis_accuracy.items()
            )
            lines.append(f"- `{label}` / `{task}`: {breakdown}")
    lines.append("")

    lines.append("## EU↔Brazil delta")
    lines.append("")
    lines.append(
        "`Δ = bbq_brazil − bbq`, same scorer on both sides. The cluster-robust bar clusters "
        "**both** sides on the scenario and then propagates as `sqrt(se_brazil² + se_eu²)`; the "
        "Resolution 13 figures clustered the Brazil side only."
    )
    lines.append("")
    lines.append(
        "| Run | Brazil ± se | EU ± se | Δ nominal ± se | **Δ cluster-robust ± se** | Δ ÷ se | distinguishable from 0 at 2 se? |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for label, tasks in runs.items():
        brazil, eu = tasks.get(BRAZIL_TASK), tasks.get(EU_TASK)
        if brazil is None or eu is None:
            continue
        delta = Delta(model=brazil.model, brazil=brazil, eu=eu)
        verdict = {True: "**yes**", False: "**no**", None: "—"}[delta.distinguishable]
        lines.append(
            f"| `{label}` | {_pm(brazil.accuracy, brazil.clustered_se)} | "
            f"{_pm(eu.accuracy, eu.clustered_se)} | "
            f"{_pm(delta.value, delta.nominal_se)} | "
            f"**{_pm(delta.value, delta.clustered_se)}** | "
            f"{_fmt(delta.z, 2)} | {verdict} |"
        )
    lines.append("")

    lines.append("## The pinned EU sample ids")
    lines.append("")
    lines.append(
        "The whole sample set, so the run is reproducible from this file alone and "
        "`tests/test_bbq_axes.py` can check the committed artifact against the code's own "
        "deterministic rule offline (the `.eval` logs are gitignored)."
    )
    lines.append("")
    id_sets = {label: tasks[EU_TASK].sample_ids for label, tasks in runs.items() if EU_TASK in tasks}
    distinct = set(id_sets.values())
    if len(distinct) == 1:
        # The determinism claim, stated as the measurement it is: every run drew the same ids.
        lines.append(
            f"**Identical across all {len(id_sets)} run(s) censused** — which is the determinism "
            "claim, measured rather than asserted. Sorted; the dataset presents them interleaved."
        )
        blocks = {"": next(iter(distinct))}
    else:
        lines.append(
            f"**WARNING: the {len(id_sets)} runs censused do NOT share one sample set** "
            f"({len(distinct)} distinct sets). The stratification is supposed to be deterministic, "
            "so this is a defect, not a variation — do not publish a delta across these runs."
        )
        blocks = dict(id_sets)
    lines.append("")
    for label, sample_ids in blocks.items():
        if label:
            lines.append(f"### `{label}`")
            lines.append("")
        lines.append("```")
        for index in range(0, len(sample_ids), 4):
            lines.append(" ".join(sample_ids[index : index + 4]))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


_ARTIFACT_HEADER = """<!--
GENERATED by `uv run python tools/bbq_axis_census.py <run dirs> --emit <this file>`.
Never hand-edited: `tests/test_bbq_axes.py::TestCommittedCensusArtifact` checks the id list in
this file against `vigilai.tasks.bbq.stratify.expected_sample_ids`, which is the code's own
deterministic sampling rule, and the counts against the pinned design.
-->

# EU `bbq` matched-axis census — what the corrected baseline actually samples

**Why this file exists.** `--limit` is global per invocation and `inspect_evals.bbq` concatenates
its eleven subsets with `Age` first, so **every EU `bbq` baseline in this project, in both
iterations, was 100 `Age` samples** — the EU↔Brazil "bias delta" compared ageism in English
against five Brazilian prejudices in Portuguese. Nothing in a standard error could have caught
that: an error bar audits precision, never construct validity. The fix is a stratified sample over
the four upstream subsets matched to `bbq_brazil`'s axes, and *this file is the evidence that the
fix took*, read back off the real logs rather than asserted from the task definition.

**The axis mapping, including the one that does not fit.** `Race_ethnicity` ↔ Race (IBGE `cor ou
raça`), `Religion` ↔ Religion, `SES` ↔ Class are direct. `Nationality` ↔ **Region is the closest
available analogue only**: Brazil's regional prejudice is *internal* (nordestino/sudestino), while
BBQ's `Nationality` is prejudice against foreigners. BBQ has no internal-regional subset, and
`bbq_brazil`'s Intersectional axis has no counterpart at all (`Race_x_SES` is excluded on purpose —
it would double-count the `Race_ethnicity` and `SES` rows already sampled). Any delta computed from
this baseline carries that mismatch.

"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("log_dirs", type=Path, nargs="+", help="Run directories to census.")
    parser.add_argument(
        "--emit",
        type=Path,
        default=None,
        help="Also write the committed Markdown artifact to this path.",
    )
    parser.add_argument(
        "--allow-partial-scenarios",
        action="store_true",
        help=(
            "Permit scenario clusters with fewer than four samples. Only for a deliberately "
            "truncated run; a published cluster-robust error bar needs equal-sized clusters."
        ),
    )
    args = parser.parse_args(argv)

    runs: dict[str, dict[str, TaskCensus]] = {}
    for log_dir in args.log_dirs:
        if not log_dir.is_dir():
            print(f"error: {log_dir} is not a directory", file=sys.stderr)
            return 2
        tasks = census_run(log_dir, allow_partial_scenarios=args.allow_partial_scenarios)
        if not tasks:
            print(f"error: no BBQ-family log under {log_dir}", file=sys.stderr)
            return 1
        runs[log_dir.name] = tasks

    body = render_report(runs)
    print(body)

    exit_code = 0
    for label, tasks in runs.items():
        for task, census in tasks.items():
            if census.empty_answers:
                print(
                    f"PRE-FLIGHT FAILED: {label}/{task} has {census.empty_answers} rows with an "
                    f"empty Score.answer — do not read its numbers.",
                    file=sys.stderr,
                )
                exit_code = 1

    if args.emit:
        args.emit.write_text(_ARTIFACT_HEADER + body + "\n", encoding="utf-8")
        print(f"\nwrote {args.emit}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
