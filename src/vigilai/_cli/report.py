"""``vigilai report <log_dir>`` — render the Brazil PL 2338/2023 compliance report.

Reads an Inspect run directory (the per-model timestamped folder ``vigilai eval`` writes under
``logs/``), aggregates each task's score against its Brazil article, and prints a per-article
compliance report with the EU↔Brazil side-by-side. Markdown to stdout by default; ``--json``
emits the machine-readable view, and ``--html`` emits a self-contained, color-coded
scorecard (the Art. 28 public-conclusions AIA artifact). ``--json`` and ``--html`` are
mutually exclusive.

``--judge-agreement`` (Phase 7) adds the **per-sample** deterministic ↔ LLM-judge agreement
section. It is the one flag that leaves the header-only path: the default report reads only log
headers, while this reads every sample of every log in the directory, so it is materially slower
on a scaled run (400 samples × 10 epochs) and is opt-in for that reason.
"""

from __future__ import annotations

import json

import typer
from typing_extensions import Annotated

from vigilai.report.brazil_report import build_brazil_report
from vigilai.report.samples import agreement_to_dict
from vigilai.report.samples import load_samples
from vigilai.report.samples import render_agreement_markdown


def report_command(
    log_dir: Annotated[
        str,
        typer.Argument(
            help=(
                "Inspect run directory to report on (e.g. "
                "`logs/mockllm_model_2026-06-21T10-00-00-03-00`). Reads every `.eval` / "
                "`.json` log it contains."
            ),
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit the report as JSON instead of Markdown.",
        ),
    ] = False,
    html_output: Annotated[
        bool,
        typer.Option(
            "--html",
            help=(
                "Emit the report as a self-contained, color-coded HTML scorecard (the "
                "Art. 28 public-conclusions AIA artifact). Mutually exclusive with --json."
            ),
        ),
    ] = False,
    judge_agreement: Annotated[
        bool,
        typer.Option(
            "--judge-agreement",
            help=(
                "Append the per-sample deterministic <-> LLM-judge agreement section (mean "
                "|delta|, Spearman, direction disagreements, and the per-element breakdown), "
                "reported for the held-out slice and the full set separately. SLOWER than the "
                "default report: it reads every sample of every log, whereas the default path "
                "reads only log headers. Not available with --html."
            ),
        ),
    ] = False,
) -> None:
    """Build and print the Brazil PL 2338/2023 compliance report for a run directory.

    By default the report is rendered as Markdown (a per-article table plus the EU↔Brazil
    side-by-side). Pass ``--json`` for the machine-readable form, or ``--html`` for a
    self-contained, color-coded scorecard (a per-article dashboard with EU↔Brazil deltas,
    framed as the Art. 28 public conclusions of the Algorithmic Impact Assessment; redirect
    it to a file: ``vigilai report logs/<run> --html > scorecard.html``). ``--json`` and
    ``--html`` are mutually exclusive. The output is written to stdout via ``print`` (not
    ``rich.print``) so it can be redirected to a file or piped without markup escaping.

    ``--judge-agreement`` adds the Phase 7 per-sample agreement section. It is **not** offered
    with ``--html`` for the reason Resolution 5(c) gives for keeping transcripts out of the
    scorecard: the HTML view's job is to stand alone as the Art. 28 *public conclusions*
    artifact, and per-sample scorer agreement is evidence for the paper's methodology argument,
    not a compliance conclusion. It works with the Markdown default (appended as a section) and
    with ``--json`` (as a ``judge_agreement`` key).
    """
    if json_output and html_output:
        raise typer.BadParameter("--json and --html are mutually exclusive.")
    if judge_agreement and html_output:
        raise typer.BadParameter(
            "--judge-agreement is not available with --html: the scorecard is the Art. 28 "
            "public-conclusions artifact, and per-sample scorer agreement is paper evidence "
            "rather than a compliance conclusion. Use the Markdown default or --json."
        )

    report = build_brazil_report(log_dir)
    # Only loaded when the flag is passed — the default path stays header-only.
    records = load_samples(log_dir) if judge_agreement else []

    if json_output:
        if judge_agreement:
            # Mirrors ``BrazilComplianceReport.to_json`` exactly (``indent=2``,
            # ``ensure_ascii=False``) plus the one additive key, so the no-flag path below stays
            # byte-identical to every earlier phase's recorded JSON.
            data = report.to_dict()
            data["judge_agreement"] = agreement_to_dict(records)
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(report.to_json())
    elif html_output:
        print(report.to_html())
    else:
        markdown = report.to_markdown()
        if judge_agreement:
            markdown = f"{markdown.rstrip()}\n\n{render_agreement_markdown(records)}"
        print(markdown)
