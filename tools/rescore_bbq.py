#!/usr/bin/env python3
"""Re-score committed ``bbq`` / ``bbq_brazil`` logs with the sigil-tolerant parse.

Why re-score rather than re-run
-------------------------------

The completions are already in the ``.eval`` logs. Re-scoring is free, and — the substantive
reason — it holds the **generations fixed**: the only thing that changes is how an already-emitted
answer is read. Nothing about the prompt, the sampling config or the model moved, so a re-scored
number and the number it replaces are measurements of the same 5,000 generations per model.

This is only valid because the fix is in the *parse*
(:mod:`vigilai.tasks.choice_parse`). Had the fix changed the ``multiple_choice`` template, what the
model was asked would have changed and a re-run would have been mandatory.

**All four BBQ logs are re-scored — both models, both tasks — so every number in the resulting
table comes from the same parser.** Re-scoring only the affected model would leave a patched scorer
and an unpatched one sharing a table, which is the objection this tool exists to remove. Haiku
emitted zero unparsable answers, so its numbers must come back **byte-identical**; that is the
control, and this tool prints it (``--assert-unchanged``).

What it does
------------

1. Copies the whole source run directory to the destination, so the pre-fix artifact survives
   intact and ``vigilai report`` can be pointed at either. Nothing is overwritten in place.
2. For every ``.eval`` in the copy whose task is ``bbq`` or ``bbq_brazil``, re-scores with
   :func:`~vigilai.tasks.choice_parse.choice_sigil_tolerant` and ``action="overwrite"``.
3. Prints a per-log census: how many samples each parse path read, and accuracy before → after.

``action="overwrite"`` rather than ``"append"``, deliberately. Appending would leave the log with
**two** non-judge scores, and both ``brazil_report._select_score`` and
``report.samples.SampleRecord.deterministic_scorer`` resolve the deterministic score as *the first
score that is not the judge* — so an appended re-score would be silently ignored and the report
would go on printing the superseded number. The same failure mode as the Phase 8 log-directory bug.

The scorer's registry name (``choice_sigil_tolerant``) differs from upstream's (``choice``), so a
re-scored log is distinguishable from an original one by reading ``EvalScore.name`` — no prose
required.

Equivalent CLI form, for the record (it does the re-score but not the census)::

    uv run inspect score <log.eval> \\
        --scorer src/vigilai/tasks/choice_parse.py@choice_sigil_tolerant \\
        --action overwrite --output-file <out.eval>

Usage
-----

::

    uv run python tools/rescore_bbq.py logs/iter2-scaled-claude-sonnet-4-6 \\
                                       logs/iter2-rescored-claude-sonnet-4-6
    uv run python tools/rescore_bbq.py logs/iter2-scaled-claude-haiku-4-5 \\
                                       logs/iter2-rescored-claude-haiku-4-5 \\
                                       --assert-unchanged
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from inspect_ai import score
from inspect_ai.log import EvalLog
from inspect_ai.log import read_eval_log
from inspect_ai.log import write_eval_log

from vigilai.tasks.choice_parse import CHOICE_SCORER_NAME
from vigilai.tasks.choice_parse import choice_sigil_tolerant
from vigilai.tasks.choice_parse import PARSE_KEY


# The tasks this tool re-scores, by bare task name. Both, always: the EU↔Brazil delta is only a
# like-for-like comparison if the two sides are read by one parser.
RESCORED_TASKS: tuple[str, ...] = ("bbq", "bbq_brazil")


# Tolerance for the aggregate control. The per-sample check below is **exact**; the aggregates are
# compared with a tolerance because Inspect recomputes them from scratch and its own accumulation
# order differs by a couple of ULP (measured: accuracy 0.9009999999999999 -> 0.9009999999999997,
# i.e. 2e-16). Anything a patched parse could actually do to a score is many orders of magnitude
# larger than this; the smallest possible real change is one sample of 400, i.e. 2.5e-3.
_AGGREGATE_TOLERANCE = 1e-12


@dataclass(frozen=True)
class Census:
    """The before/after audit of one re-scored log."""

    task: str
    model: str
    samples: int
    empty_answer_before: int
    parse_paths: Counter[str]
    accuracy_before: float | None
    stderr_before: float | None
    accuracy_after: float | None
    stderr_after: float | None
    samples_changed: int
    """Rows whose score **value** or marked ``answer`` differs from the original. The exact
    control: it does not depend on how Inspect accumulates its aggregates."""

    @property
    def aggregate_drift(self) -> float:
        """Largest absolute change in the point estimate or its standard error."""
        drift = 0.0
        for before, after in (
            (self.accuracy_before, self.accuracy_after),
            (self.stderr_before, self.stderr_after),
        ):
            if before is not None and after is not None:
                drift = max(drift, abs(after - before))
        return drift

    @property
    def unchanged(self) -> bool:
        """True if no row's score moved and the aggregates moved only by float noise."""
        return self.samples_changed == 0 and self.aggregate_drift <= _AGGREGATE_TOLERANCE


def _bare_task_name(task: str) -> str:
    """``"vigilai/bbq_brazil"`` -> ``"bbq_brazil"``."""
    return task.rsplit("/", 1)[-1] if "/" in task else task


def _headline(log: EvalLog) -> tuple[float | None, float | None]:
    """``(accuracy, stderr)`` from a log's first score, or ``(None, None)``."""
    if log.results is None or not log.results.scores:
        return None, None
    metrics = log.results.scores[0].metrics
    accuracy = metrics.get("accuracy")
    stderr = metrics.get("stderr")
    return (
        accuracy.value if accuracy is not None else None,
        stderr.value if stderr is not None else None,
    )


def _empty_answers(log: EvalLog) -> int:
    """Count samples whose ``Score.answer`` is empty — the one-line pre-flight for this defect."""
    empty = 0
    for sample in log.samples or []:
        for sample_score in (sample.scores or {}).values():
            if not (sample_score.answer or ""):
                empty += 1
            break
    return empty


def _sample_verdicts(log: EvalLog) -> list[tuple[str, int, object, str]]:
    """``(sample_id, epoch, score value, marked answer)`` per row, in log order.

    Read from the row's *first* score, which is the only one either log has: the original carries
    ``choice`` alone and the re-score overwrites it with ``choice_sigil_tolerant`` alone.
    """
    verdicts: list[tuple[str, int, object, str]] = []
    for sample in log.samples or []:
        for sample_score in (sample.scores or {}).values():
            verdicts.append(
                (str(sample.id), int(sample.epoch), sample_score.value, sample_score.answer or "")
            )
            break
    return verdicts


def _rows_changed(before: EvalLog, after: EvalLog) -> int:
    """Rows whose score value or marked answer differs. Exact, not tolerance-based."""
    return sum(
        1 for b, a in zip(_sample_verdicts(before), _sample_verdicts(after), strict=True) if b != a
    )


def _parse_paths(log: EvalLog) -> Counter[str]:
    """Tally ``Score.metadata["answer_parse"]`` across a re-scored log."""
    paths: Counter[str] = Counter()
    for sample in log.samples or []:
        sample_score = (sample.scores or {}).get(CHOICE_SCORER_NAME)
        if sample_score is None:
            paths["<no sigil-tolerant score>"] += 1
            continue
        paths[str((sample_score.metadata or {}).get(PARSE_KEY, "<unrecorded>"))] += 1
    return paths


def rescore_log(path: Path) -> Census:
    """Re-score one ``.eval`` in place and return its before/after census."""
    original = read_eval_log(str(path))
    task = _bare_task_name(original.eval.task)
    accuracy_before, stderr_before = _headline(original)
    empty_before = _empty_answers(original)

    rescored = score(
        original,
        choice_sigil_tolerant(),
        action="overwrite",
        display="none",
        copy=True,
    )
    write_eval_log(rescored, str(path))

    accuracy_after, stderr_after = _headline(rescored)
    return Census(
        task=task,
        model=original.eval.model,
        samples=len(original.samples or []),
        empty_answer_before=empty_before,
        parse_paths=_parse_paths(rescored),
        accuracy_before=accuracy_before,
        stderr_before=stderr_before,
        accuracy_after=accuracy_after,
        stderr_after=stderr_after,
        samples_changed=_rows_changed(original, rescored),
    )


def bbq_logs(log_dir: Path) -> list[Path]:
    """Every ``.eval`` under ``log_dir`` belonging to a task in :data:`RESCORED_TASKS`."""
    found: list[Path] = []
    for path in sorted(log_dir.rglob("*.eval")):
        header = read_eval_log(str(path), header_only=True)
        if _bare_task_name(header.eval.task) in RESCORED_TASKS:
            found.append(path)
    return found


def _format(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("src", type=Path, help="Source run directory (left untouched).")
    parser.add_argument("dest", type=Path, help="Destination directory for the re-scored copy.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the destination if it already exists.",
    )
    parser.add_argument(
        "--assert-unchanged",
        action="store_true",
        help=(
            "Fail unless every re-scored log's accuracy and stderr are identical to the "
            "original. This is the control: a model that emitted no unparsable answer cannot "
            "move, so if it does, the patch is doing more than tolerating the sigil."
        ),
    )
    args = parser.parse_args(argv)

    if not args.src.is_dir():
        print(f"error: {args.src} is not a directory", file=sys.stderr)
        return 2
    if args.dest.exists():
        if not args.force:
            print(
                f"error: {args.dest} already exists (pass --force to replace)",
                file=sys.stderr,
            )
            return 2
        shutil.rmtree(args.dest)

    shutil.copytree(args.src, args.dest)
    print(f"copied {args.src} -> {args.dest}")

    targets = bbq_logs(args.dest)
    if not targets:
        print(f"error: no {'/'.join(RESCORED_TASKS)} log found under {args.dest}", file=sys.stderr)
        return 1

    censuses: list[Census] = []
    for path in targets:
        print(f"re-scoring {path.name} …", flush=True)
        censuses.append(rescore_log(path))

    print()
    print(f"scorer: {CHOICE_SCORER_NAME}   action: overwrite")
    print(
        f"{'task':12} {'n':>6} {'empty→':>7} "
        f"{'strict':>7} {'sigil':>7} {'unparsed':>9} {'rows Δ':>7} "
        f"{'acc before':>11} {'acc after':>10} {'se before':>10} {'se after':>9}"
    )
    for census in censuses:
        print(
            f"{census.task:12} {census.samples:6d} {census.empty_answer_before:7d} "
            f"{census.parse_paths.get('strict', 0):7d} "
            f"{census.parse_paths.get('sigil_tolerant', 0):7d} "
            f"{census.parse_paths.get('unparsed', 0):9d} "
            f"{census.samples_changed:7d} "
            f"{_format(census.accuracy_before):>11} {_format(census.accuracy_after):>10} "
            f"{_format(census.stderr_before):>10} {_format(census.stderr_after):>9}"
        )
        unexpected = set(census.parse_paths) - {"strict", "sigil_tolerant", "unparsed"}
        if unexpected:
            print(f"  warning: unexpected parse paths: {sorted(unexpected)}", file=sys.stderr)

    if args.assert_unchanged:
        moved = [c for c in censuses if not c.unchanged]
        if moved:
            for census in moved:
                print(
                    f"CONTROL FAILED: {census.task} — {census.samples_changed} row(s) changed, "
                    f"aggregate drift {census.aggregate_drift:.3e} "
                    f"({_format(census.accuracy_before)} -> {_format(census.accuracy_after)})",
                    file=sys.stderr,
                )
            return 1
        drift = max(c.aggregate_drift for c in censuses)
        print(
            "\ncontrol held: 0 rows changed in any log; every score value and marked answer is "
            f"identical to the original. Largest aggregate drift {drift:.3e} — Inspect's own "
            "accumulation order, not the parse."
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
