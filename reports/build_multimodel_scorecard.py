#!/usr/bin/env python3
"""Build the multi-model Brazil PL 2338/2023 compliance dossier — one self-contained HTML
document with **six pages** (one model per page).

This is a thin presentation wrapper over the library's own renderers in
``vigilai.report.brazil_report`` (``build_brazil_report`` + ``_render_article_table`` /
``_render_side_by_side_table`` / ``_render_coverage_table`` + ``_HTML_STYLE``). It introduces NO
new aggregation logic — each page is the same per-article / EU↔Brazil / coverage content the
single-model ``vigilai report --html`` scorecard emits, stitched under one ``<style>`` with a
``page-break`` between models so it prints/exports as a 6-page dossier and serves as the Art. 28
"public conclusions" artifact across the full model panel.

Run from the repo root after the six coherent runs exist locally:

    uv run python reports/build_multimodel_scorecard.py

Note: ``logs/`` is gitignored, so the exact run dirs below are local to the machine that produced
the dossier; the committed deliverable is the generated ``reports/multimodel-scorecard.html``.
"""

from __future__ import annotations

from vigilai.report.brazil_report import _HTML_STYLE
from vigilai.report.brazil_report import _render_article_table
from vigilai.report.brazil_report import _render_coverage_table
from vigilai.report.brazil_report import _render_side_by_side_table
from vigilai.report.brazil_report import build_brazil_report
from vigilai.report.brazil_report import BrazilComplianceReport


# (label, origin, access/config, log dir) for the six coherent runs behind this dossier.
MODELS: list[tuple[str, str, str, str]] = [
    (
        "Claude Haiku 4.5",
        "Anthropic (US)",
        "API · scaled (bbq@100, 10 epochs, seed 42)",
        "logs/anthropic_claude-haiku-4-5_2026-06-21T13-12-04-03-00",
    ),
    (
        "Claude Sonnet 4.6",
        "Anthropic (US)",
        "API · scaled (bbq@100, 10 epochs, seed 42)",
        "logs/anthropic_claude-sonnet-4-6_2026-06-21T14-12-21-03-00",
    ),
    (
        "Llama 3.1 8B",
        "Meta (US)",
        "local Ollama · pilot (--limit 20, 1 epoch, $0)",
        "logs/ollama_llama3.1:8b_2026-06-21T13-39-22-03-00",
    ),
    (
        "gpt-oss 20B",
        "OpenAI (US, open-weight)",
        "local Ollama · pilot (--limit 20, 1 epoch, $0)",
        "logs/ollama_gpt-oss:20b_2026-06-21T13-53-12-03-00",
    ),
    (
        "Qwen2.5 14B",
        "Alibaba (China)",
        "local Ollama · pilot (--limit 20, 1 epoch, $0)",
        "logs/ollama_qwen2.5:14b_2026-06-21T13-42-34-03-00",
    ),
    (
        "Mistral Small",
        "Mistral (France)",
        "local Ollama · pilot (--limit 20, 1 epoch, $0)",
        "logs/ollama_mistral-small:latest_2026-06-21T13-46-42-03-00",
    ),
]

OUTPUT = "reports/multimodel-scorecard.html"

# Extra CSS layered on top of the library style for the multi-page dossier.
_DOSSIER_CSS = """
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { max-width: 1040px; margin: 0 auto 2rem; background: #fff; border: 1px solid var(--line);
  border-radius: 12px; padding: 2rem 2.25rem; }
.page + .page { margin-top: 0; }
.pagenum { float: right; color: var(--muted); font-size: .82rem; font-weight: 600; }
.model-tag { display: inline-block; background: var(--accent); color: #fff; font-weight: 700;
  padding: .15rem .6rem; border-radius: 6px; font-size: .9rem; }
.finding { background: #f8f9fb; border-left: 4px solid var(--accent); padding: .6rem .9rem;
  margin: 1rem 0; font-size: .9rem; border-radius: 0 6px 6px 0; }
@media print {
  @page { size: Letter; margin: 0.7cm 0.7cm; }
  body { background: #fff; padding: 0; font-size: 6.6pt; }
  .page { border: none; border-radius: 0; page-break-after: always; page-break-inside: avoid;
    margin: 0; max-width: none; padding: 0; }
  .page:last-child { page-break-after: auto; }
  h1 { font-size: 11.5pt; }
  h2 { font-size: 8pt; margin: .35rem 0 .15rem; }
  header { padding-bottom: .25rem; margin-bottom: .35rem; }
  .caption { margin: .05rem 0 .2rem; font-size: 6.8pt; }
  .meta { font-size: 6.6pt; } .meta li { margin: .05rem 0; }
  p.note { font-size: 6.2pt; margin: 0 0 .25rem; }
  .finding { font-size: 6.6pt; padding: .3rem .5rem; margin: .35rem 0; }
  table { font-size: 6.3pt; margin: .35rem 0; }
  th, td { padding: .1rem .28rem; }
  .badge { min-width: 2.4rem; padding: .06rem .3rem; }
  .pagenum { font-size: 6.4pt; }
}
"""


def _delta_for(report: BrazilComplianceReport, brazil_task: str) -> float | None:
    for row in report.side_by_side:
        if row.brazil_task == brazil_task and row.has_eu_equivalent:
            return row.delta
    return None


_LEGEND = (
    '<span class="badge good">≥ 0.80</span> '
    '<span class="badge warn">0.50–0.80</span> '
    '<span class="badge bad">&lt; 0.50</span> &nbsp;·&nbsp; '
    '<span class="cov-pill brazil">✅ Brazil benchmark</span> '
    '<span class="cov-pill eu_only">🟡 EU task only</span> '
    '<span class="cov-pill uncovered">⚪ not covered</span>'
)


def _page(idx: int, label: str, origin: str, config: str, report: BrazilComplianceReport) -> str:
    disclosure = _delta_for(report, "human_deception_brazil")
    bias = _delta_for(report, "bbq_brazil")
    parts: list[str] = []
    parts.append('<section class="page">')
    parts.append(f'<span class="pagenum">Page {idx} / {len(MODELS)}</span>')
    parts.append("<header>")
    if idx == 1:
        # Dossier super-title + methodology note on the first page only (keeps the doc at
        # exactly 6 pages — one model each).
        parts.append(
            '<p class="caption" style="margin-bottom:.4rem">vigilAI · Brazil PL 2338/2023 — '
            "Multi-Model Compliance Dossier (6 models, same-model EU↔Brazil comparison)</p>"
        )
        parts.append(
            '<p class="note" style="margin-bottom:.6rem">Every delta below is computed '
            "<strong>within one coherent run per model</strong> (EU task vs Brazil task, same "
            "scorer) — the cleanest same-model comparison. Frontier models (Haiku, Sonnet) use "
            "the <em>scaled</em> config (10 epochs, full 44-sample <code>bbq_brazil</code>); local "
            "models use the <em>pilot</em> config (<code>--limit 20</code>, 1 epoch, so "
            "<code>bbq_brazil</code> shows 20 of 44 and small-n points are noisier). Full "
            "analysis: <code>reports/RESULTS.md</code>.</p>"
        )
    parts.append(f"<h1>{label} <span class='model-tag'>vigilAI</span></h1>")
    parts.append(
        '<p class="caption">Brazil PL 2338/2023 compliance — public conclusions of the '
        "Algorithmic Impact Assessment (Art. 28).</p>"
    )
    parts.append('<ul class="meta">')
    parts.append(f"<li><strong>Model:</strong> {origin}</li>")
    parts.append(f"<li><strong>Run:</strong> {config}</li>")
    parts.append(
        f"<li><strong>Brazil-mapped benchmarks scored:</strong> "
        f"{len(report.brazil_task_scores)} of 5</li>"
    )
    parts.append("</ul>")
    parts.append("</header>")
    parts.append(f'<p class="note">Higher is better (1.0 = full compliance). {_LEGEND}</p>')

    # Per-page headline: the two same-scorer EU↔Brazil deltas.
    dd = "n/a" if disclosure is None else f"{disclosure:+.2f}"
    bd = "n/a" if bias is None else f"{bias:+.2f}"
    parts.append(
        f'<div class="finding"><strong>EU↔Brazil deltas (same scorer):</strong> '
        f"AI-disclosure (Art. 5, I) Δ = <strong>{dd}</strong> · "
        f"bias (Art. 5, III) Δ = <strong>{bd}</strong>. "
        "Negative = less compliant on Brazil-specific content than on the EU equivalent.</div>"
    )

    parts.append("<h2>Compliance by Brazil article</h2>")
    parts.extend(_render_article_table(report))
    parts.append("<h2>EU ↔ Brazil side-by-side</h2>")
    parts.extend(_render_side_by_side_table(report))
    parts.append("<h2>Brazil compliance coverage map (9 requirements)</h2>")
    parts.extend(_render_coverage_table(report))
    parts.append("</section>")
    return "\n".join(parts)


def main() -> None:
    pages = []
    for i, (label, origin, config, log_dir) in enumerate(MODELS, start=1):
        report = build_brazil_report(log_dir)
        pages.append(_page(i, label, origin, config, report))

    doc = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>vigilAI — Brazil PL 2338/2023 Multi-Model Compliance Dossier</title>",
        f"<style>{_HTML_STYLE}{_DOSSIER_CSS}</style>",
        "</head>",
        "<body>",
    ]
    doc.extend(pages)  # exactly six pages — one model each
    doc.extend(["</body>", "</html>", ""])

    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(doc))
    print(f"wrote {OUTPUT} ({len(MODELS)} model pages)")


if __name__ == "__main__":
    main()
