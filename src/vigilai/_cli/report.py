"""``vigilai report <log_dir>`` — render the Brazil PL 2338/2023 compliance report.

Reads an Inspect run directory (the per-model timestamped folder ``vigilai eval`` writes under
``logs/``), aggregates each task's score against its Brazil article, and prints a per-article
compliance report with the EU↔Brazil side-by-side. Markdown to stdout by default; ``--json``
emits the machine-readable view, and ``--html`` emits a self-contained, color-coded
scorecard (the Art. 28 public-conclusions AIA artifact). ``--json`` and ``--html`` are
mutually exclusive.
"""

from __future__ import annotations

import typer
from typing_extensions import Annotated

from vigilai.report.brazil_report import build_brazil_report


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
) -> None:
    """Build and print the Brazil PL 2338/2023 compliance report for a run directory.

    By default the report is rendered as Markdown (a per-article table plus the EU↔Brazil
    side-by-side). Pass ``--json`` for the machine-readable form, or ``--html`` for a
    self-contained, color-coded scorecard (a per-article dashboard with EU↔Brazil deltas,
    framed as the Art. 28 public conclusions of the Algorithmic Impact Assessment; redirect
    it to a file: ``vigilai report logs/<run> --html > scorecard.html``). ``--json`` and
    ``--html`` are mutually exclusive. The output is written to stdout via ``print`` (not
    ``rich.print``) so it can be redirected to a file or piped without markup escaping.
    """
    if json_output and html_output:
        raise typer.BadParameter("--json and --html are mutually exclusive.")

    report = build_brazil_report(log_dir)
    if json_output:
        print(report.to_json())
    elif html_output:
        print(report.to_html())
    else:
        print(report.to_markdown())
