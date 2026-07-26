"""Tests for the Phase 7 Brazil PL 2338/2023 compliance report aggregator.

The structure outline requires the report to:

* aggregate per-task scores **per Brazil article** (and report a per-article mean);
* **group by scope** (Art. 5 = ``all_ai`` vs Art. 6 / AIA = ``high_risk``);
* render an **EU↔Brazil side-by-side** with the correct columns — a delta for the two
  same-scorer pairs (``human_deception``↔``human_deception_brazil``, ``bbq``↔``bbq_brazil``)
  and a clear "no EU equivalent" for the Brazil-only tasks (``explanation_quality``,
  ``aia_checklist``).

Strategy: build a **fixture log dir** of real Inspect ``.eval`` logs by running tiny,
one-sample tasks — tagged with the *same* ``technical_requirement`` / ``brazil_article`` /
``brazil_scope`` decorator kwargs as the real tasks — against ``mockllm/model`` with **forced
outputs** so each task scores a known, distinct value. The report is then built from that
directory through the real ``list_eval_logs`` + ``read_eval_log`` path, so the test exercises
the genuine load/join/aggregate logic (not a hand-mocked report object). A final test runs the
**actual registered tasks** end-to-end on the mock model to prove the read path also works on
real ``vigilai eval`` output (where task names carry the ``vigilai/`` registry prefix).

Everything is deterministic and offline (mock model, in-code one-sample datasets), so no
network access is needed.
"""

from __future__ import annotations

import dataclasses
import json
import math
import statistics
from pathlib import Path
from typing import Any

import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai import Task
from inspect_ai import task
from inspect_ai.dataset import MemoryDataset
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import grouped
from inspect_ai.scorer import match
from inspect_ai.scorer import mean
from inspect_ai.scorer import scorer
from inspect_ai.scorer import Score
from inspect_ai.scorer import stderr
from inspect_ai.solver import generate

from inspect_ai._util.registry import registry_info
from typer.testing import CliRunner

from vigilai._cli import app as cli_app
from vigilai.report import samples as vigilai_report_samples
from vigilai.report.brazil_report import _DETERMINISTIC_SCORERS
from vigilai.report.brazil_report import _gap_items_by_sector_from_attribs
from vigilai.report.brazil_report import _JUDGE_ROLE
from vigilai.report.brazil_report import _JUDGE_SCORERS
from vigilai.report.brazil_report import _judge_grader_from_log
from vigilai.report.brazil_report import _sector_metrics
from vigilai.report.brazil_report import _select_score
from vigilai.report.brazil_report import _stderr_metric
from vigilai.report.brazil_report import ArticleGroup
from vigilai.report.brazil_report import build_brazil_report
from vigilai.report.brazil_report import BrazilComplianceReport
from vigilai.report.brazil_report import EU_BRAZIL_PAIRS
from vigilai.report.brazil_report import NINE_TECHNICAL_REQUIREMENTS
from vigilai.report.brazil_report import SideBySideRow
from vigilai.report.brazil_report import TaskScore
from vigilai.report.samples import agreement_to_dict
from vigilai.report.samples import DETERMINISTIC_SCORER_NAMES
from vigilai.report.samples import first_epoch
from vigilai.report.samples import JUDGE_SCORER_NAME as samples_JUDGE_SCORER_NAME
from vigilai.report.samples import judge_agreement
from vigilai.report.samples import judge_agreement_by_split
from vigilai.report.samples import load_samples
from vigilai.report.samples import parse_judge_verdicts
from vigilai.report.samples import render_agreement_markdown
from vigilai.report.samples import sample_sort_key
from vigilai.report.samples import SampleRecord
from vigilai.report.samples import spearman
from vigilai.report.samples import SPLIT_HELD_OUT as samples_SPLIT_HELD_OUT
from vigilai.tasks.aia_checklist.checklist import aia_checklist_scorer
from vigilai.tasks.contestation_review.rubric import contestation_scorer
from vigilai.tasks.contestation_review.rubric import CONTESTATION_RUBRIC
from vigilai.tasks.explanation_quality.explanation_quality import explanation_quality
from vigilai.tasks.explanation_quality.rubric import EXPLANATION_RUBRIC
from vigilai.tasks.explanation_quality.rubric import rubric_scorer
from vigilai.tasks.judge import JUDGE_GRADER
from vigilai.tasks.judge import JUDGE_GRADER_SEED
from vigilai.tasks.judge import JUDGE_GRADER_TEMPERATURE
from vigilai.tasks.judge import JUDGE_ROLE
from vigilai.tasks.judge import JUDGE_SCORER_NAME
from vigilai.tasks.judge import judge_scorer
from vigilai.tasks.rubric_scenario import SPLIT_HELD_OUT


# ---------------------------------------------------------------------------------------
# Fixture task factories.
#
# Each factory returns a one-sample Task tagged exactly like its real counterpart. The
# ``target`` is chosen so that a forced model output of "HIT" scores 1.0 and "MISS" scores 0.0
# under match() — giving us controllable, known per-task scores.
#
# The two Brazil-only tasks use a fraction-returning custom scorer (reporting ``mean``, like
# the real rubric / checklist scorers) so the report's metric-name handling (accuracy vs mean)
# is also exercised.
# ---------------------------------------------------------------------------------------
_HIT = "HIT"
_MISS = "MISS"


def _binary_task(
    name: str, requirement: str, article: str, scope: str
) -> Task:
    """A one-sample match()-scored task (reports ``accuracy``), tagged like an upstream task."""

    @task(
        name=name,
        technical_requirement=requirement,
        brazil_article=article,
        brazil_scope=scope,
    )
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset([Sample(input="q", target=_HIT)]),
            solver=[generate()],
            scorer=match(),
        )

    return _t()


@scorer(metrics=[mean(), stderr()])
def _fraction_scorer():
    """Custom scorer that returns the completion parsed as a float in [0,1] (reports ``mean``).

    Mirrors the real Brazil rubric / checklist scorers, which report a ``mean`` metric rather
    than ``accuracy`` — so the report's metric-preference logic is covered.
    """

    async def score(state, target):  # type: ignore[no-untyped-def]
        try:
            value = float(state.output.completion)
        except ValueError:
            value = 0.0
        return Score(value=value)

    return score


def _fraction_task(
    name: str, requirement: str, article: str, scope: str
) -> Task:
    """A one-sample fraction-scored task (reports ``mean``), tagged like a Brazil-only task."""

    @task(
        name=name,
        technical_requirement=requirement,
        brazil_article=article,
        brazil_scope=scope,
    )
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset([Sample(input="q", target="n/a")]),
            solver=[generate()],
            scorer=_fraction_scorer(),
        )

    return _t()


def _run_into(log_dir: str, a_task: Task, completion: str) -> None:
    """Run ``a_task`` against the mock model with a single forced output into ``log_dir``."""
    model = get_model(
        "mockllm/model",
        custom_outputs=[ModelOutput.from_content("mockllm/model", completion)],
    )
    logs = inspect_eval(a_task, model=model, display="none", log_dir=log_dir)
    assert logs[0].status == "success", f"{a_task} did not run cleanly"


@pytest.fixture(scope="module")
def fixture_report(tmp_path_factory: pytest.TempPathFactory) -> BrazilComplianceReport:
    """Build a report from a crafted fixture log dir with known, distinct per-task scores.

    Score design (forced outputs):

    * Art. 5, I  (all_ai):    human_deception 1.0 (HIT), human_deception_brazil 0.0 (MISS)
    * Art. 5, III (all_ai):   bbq 1.0 (HIT),  bbq_brazil 0.0 (MISS),  bold 0.5 (frac)
                              -> two-task article-mean check uses bbq_brazil + bold = 0.25
                              -> EU bbq is the side-by-side counterpart (not in the Brazil body)
    * Art. 6, I  (high_risk): explanation_quality 0.50 (frac)  [Brazil-only]
    * Arts. 25-28 (high_risk):aia_checklist 0.75 (frac)        [Brazil-only, via DECORATOR]

    The EU tasks (human_deception, bbq) are tagged Brazil too (they map to Art. 5 via their
    requirement), but they are the side-by-side counterparts; the report treats the
    ``_brazil`` tasks as the report body and pulls the EU score next to them.
    """
    log_dir = str(tmp_path_factory.mktemp("fixture_logs"))

    # Art. 5, I — disclosure pair.
    _run_into(
        log_dir,
        _binary_task("human_deception", "Disclosure of AI", "Art. 5, I", "all_ai"),
        _HIT,  # EU disclosure: 1.0
    )
    _run_into(
        log_dir,
        _binary_task(
            "human_deception_brazil", "Disclosure of AI", "Art. 5, I", "all_ai"
        ),
        _MISS,  # Brazil disclosure: 0.0  -> delta = 0.0 - 1.0 = -1.0
    )

    # Art. 5, III — fairness pair + an extra Brazil-mapped task (bold) to test article-mean.
    _run_into(
        log_dir,
        _binary_task(
            "bbq", "Representation — Absence of Bias", "Art. 5, III", "all_ai"
        ),
        _HIT,  # EU bbq: 1.0
    )
    _run_into(
        log_dir,
        _binary_task(
            "bbq_brazil", "Representation — Absence of Bias", "Art. 5, III", "all_ai"
        ),
        _MISS,  # Brazil bbq: 0.0  -> delta = 0.0 - 1.0 = -1.0
    )
    _run_into(
        log_dir,
        _fraction_task(
            "bold", "Representation — Absence of Bias", "Art. 5, III", "all_ai"
        ),
        "0.5",  # another Art. 5, III Brazil-mapped task -> article-mean over bbq_brazil+bold
    )

    # Art. 6, I — Brazil-only (explanation_quality), reports a fraction.
    _run_into(
        log_dir,
        _fraction_task(
            "explanation_quality", "Interpretability", "Art. 6, I", "high_risk"
        ),
        "0.5",
    )

    # Arts. 25-28 — Brazil-only AIA; article comes ONLY from the decorator (its requirement,
    # "Societal Alignment", is intentionally not in the mapping).
    _run_into(
        log_dir,
        _fraction_task(
            "aia_checklist", "Societal Alignment", "Arts. 25-28", "high_risk"
        ),
        "0.75",
    )

    return build_brazil_report(log_dir)


class TestPerArticleAggregation:
    """Scores are joined to the right Brazil article and aggregated per article."""

    def test_all_brazil_articles_present(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        articles = {g.article for g in fixture_report.article_groups}
        assert articles == {"Art. 5, I", "Art. 5, III", "Art. 6, I", "Arts. 25-28"}

    def test_art5_i_groups_only_the_brazil_disclosure_task(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        group = fixture_report.group_for("Art. 5, I")
        assert group is not None
        # The EU human_deception is a side-by-side counterpart, NOT part of the article body.
        assert [t.task for t in group.tasks] == ["human_deception_brazil"]
        assert group.mean_score == 0.0

    def test_art5_iii_article_mean_is_over_brazil_mapped_tasks(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        """Art. 5, III holds two Brazil-mapped tasks (bbq_brazil=0.0, bold=0.5); the EU bbq is
        excluded from the article body. Mean = (0.0 + 0.5) / 2 = 0.25."""
        group = fixture_report.group_for("Art. 5, III")
        assert group is not None
        assert sorted(t.task for t in group.tasks) == ["bbq_brazil", "bold"]
        assert group.mean_score == pytest.approx(0.25)

    def test_eu_counterpart_excluded_from_article_body(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        """The EU pair tasks (human_deception, bbq) must not appear as article-body tasks."""
        body_tasks = {t.task for g in fixture_report.article_groups for t in g.tasks}
        assert "bbq" not in body_tasks
        assert "human_deception" not in body_tasks

    def test_metric_name_tracked_per_task(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        """match()-scored tasks report accuracy; the fraction scorer reports mean."""
        by_task = {t.task: t for t in fixture_report.brazil_task_scores}
        assert by_task["human_deception_brazil"].metric_name == "accuracy"
        assert by_task["bbq_brazil"].metric_name == "accuracy"
        assert by_task["explanation_quality"].metric_name == "mean"
        assert by_task["aia_checklist"].metric_name == "mean"


class TestScopeGrouping:
    """Each article group carries the right Brazil scope (all_ai vs high_risk)."""

    def test_art5_groups_are_all_ai(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        for article in ("Art. 5, I", "Art. 5, III"):
            group = fixture_report.group_for(article)
            assert group is not None
            assert group.scope == "all_ai", article

    def test_art6_and_aia_groups_are_high_risk(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        for article in ("Art. 6, I", "Arts. 25-28"):
            group = fixture_report.group_for(article)
            assert group is not None
            assert group.scope == "high_risk", article

    def test_every_task_score_carries_its_scope(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        for t in fixture_report.brazil_task_scores:
            assert t.brazil_scope in ("all_ai", "high_risk")


class TestAIADecoratorJoin:
    """The critical join nuance: aia_checklist files under Arts. 25-28 via its DECORATOR.

    Its technical_requirement is "Societal Alignment", which is deliberately absent from
    TECH_REQ_TO_BRAZIL — so a mapping-only join would misfile (or drop) it. The report must
    use the decorator-recorded brazil_article from the log header.
    """

    def test_aia_filed_under_arts_25_28(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        group = fixture_report.group_for("Arts. 25-28", scope="high_risk")
        assert group is not None
        assert [t.task for t in group.tasks] == ["aia_checklist"]

    def test_aia_score_resolved(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        by_task = {t.task: t for t in fixture_report.brazil_task_scores}
        assert by_task["aia_checklist"].brazil_article == "Arts. 25-28"
        assert by_task["aia_checklist"].score == pytest.approx(0.75)
        # Its EU requirement is carried through but is NOT used to derive the article.
        assert by_task["aia_checklist"].technical_requirement == "Societal Alignment"


class TestSideBySide:
    """EU↔Brazil side-by-side columns are correct (deltas for pairs, none for Brazil-only)."""

    def test_pairs_config_is_explicit_and_minimal(self) -> None:
        """The pair set is an explicit constant of exactly the two same-scorer pairs."""
        assert EU_BRAZIL_PAIRS == {
            "human_deception_brazil": "human_deception",
            "bbq_brazil": "bbq",
        }

    def test_disclosure_pair_delta(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        row = fixture_report.row_for("human_deception_brazil")
        assert row is not None
        assert row.has_eu_equivalent is True
        assert row.eu_task == "human_deception"
        assert row.brazil_score == pytest.approx(0.0)
        assert row.eu_score == pytest.approx(1.0)
        assert row.delta == pytest.approx(-1.0)

    def test_fairness_pair_delta(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        row = fixture_report.row_for("bbq_brazil")
        assert row is not None
        assert row.has_eu_equivalent is True
        assert row.eu_task == "bbq"
        assert row.brazil_score == pytest.approx(0.0)
        assert row.eu_score == pytest.approx(1.0)
        assert row.delta == pytest.approx(-1.0)

    def test_explanation_quality_is_brazil_only(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        row = fixture_report.row_for("explanation_quality")
        assert row is not None
        assert row.has_eu_equivalent is False
        assert row.eu_task is None
        assert row.eu_score is None
        assert row.delta is None
        assert row.brazil_score == pytest.approx(0.5)

    def test_aia_checklist_is_brazil_only(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        row = fixture_report.row_for("aia_checklist")
        assert row is not None
        assert row.has_eu_equivalent is False
        assert row.eu_task is None
        assert row.delta is None

    def test_paired_rows_precede_brazil_only_rows(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        kinds = [row.has_eu_equivalent for row in fixture_report.side_by_side]
        # All True (pairs) come before all False (Brazil-only).
        assert kinds == sorted(kinds, reverse=True)

    def test_exactly_two_paired_rows(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        paired = [r for r in fixture_report.side_by_side if r.has_eu_equivalent]
        assert {r.brazil_task for r in paired} == {
            "human_deception_brazil",
            "bbq_brazil",
        }


class TestMarkdownRendering:
    """The Markdown view contains the article table and the side-by-side with its columns."""

    def test_markdown_has_both_sections(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        md = fixture_report.to_markdown()
        assert "## Compliance by Brazil article" in md
        assert "## EU ↔ Brazil side-by-side" in md

    def test_markdown_shows_aia_under_arts_25_28(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        md = fixture_report.to_markdown()
        assert "Arts. 25-28" in md
        assert "`aia_checklist`" in md

    def test_markdown_side_by_side_marks_no_eu_equivalent(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        md = fixture_report.to_markdown()
        assert "no EU equivalent" in md

    def test_markdown_shows_pair_delta(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        md = fixture_report.to_markdown()
        # The disclosure / fairness deltas are -1.000 with our fixture scores.
        assert "-1.000" in md


class TestJsonRendering:
    """The JSON view is well-formed and carries the article + side-by-side structures."""

    def test_json_is_valid_and_structured(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        data = json.loads(fixture_report.to_json())
        assert set(data.keys()) >= {
            "log_dir",
            "models",
            "articles",
            "eu_brazil_side_by_side",
        }
        assert data["models"] == ["mockllm/model"]

    def test_json_articles_carry_scores(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        data = json.loads(fixture_report.to_json())
        arts = {a["article"]: a for a in data["articles"]}
        assert arts["Arts. 25-28"]["scope"] == "high_risk"
        assert arts["Arts. 25-28"]["mean_score"] == pytest.approx(0.75)

    def test_json_side_by_side_has_delta_for_pairs(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        data = json.loads(fixture_report.to_json())
        rows = {r["brazil_task"]: r for r in data["eu_brazil_side_by_side"]}
        assert rows["bbq_brazil"]["delta"] == pytest.approx(-1.0)
        assert rows["explanation_quality"]["delta"] is None
        assert rows["explanation_quality"]["has_eu_equivalent"] is False


class TestHtmlRendering:
    """The ``--html`` view is a self-contained, color-coded Art. 28 public-conclusions doc.

    Reuses the shared ``fixture_report`` (Art. 5, I / Art. 5, III / Art. 6, I / Arts. 25-28
    with the known fixture scores). Asserts the document is well-formed and self-contained
    (no external assets), carries the Art. 28 framing + the article names + the EU↔Brazil
    delta + the "no EU equivalent" marker, color-codes score cells by band, and HTML-escapes
    dynamic values.
    """

    def test_is_self_contained_html_document(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        doc = fixture_report.to_html()
        assert "<!DOCTYPE html>" in doc
        assert "<html" in doc
        assert "</html>" in doc
        assert "<style" in doc

    def test_no_external_assets(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        """No external src/href references — the scorecard must open offline."""
        doc = fixture_report.to_html()
        # No external resource references at all (no images/scripts/stylesheets/fonts).
        assert "src=" not in doc
        assert "href=" not in doc
        assert "http://" not in doc
        assert "https://" not in doc

    def test_art28_public_conclusions_framing(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        doc = fixture_report.to_html()
        assert "Art. 28" in doc
        assert "public conclusions" in doc.lower()
        assert "Algorithmic Impact Assessment" in doc

    def test_contains_article_names(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        doc = fixture_report.to_html()
        assert "Art. 5, I" in doc
        assert "Art. 5, III" in doc
        assert "Art. 6, I" in doc
        assert "Arts. 25-28" in doc

    def test_contains_delta_and_no_eu_equivalent_marker(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        doc = fixture_report.to_html()
        # The disclosure / fairness deltas are -1.000 with the fixture scores.
        assert "-1.000" in doc
        assert "no EU equivalent" in doc

    def test_score_cells_carry_band_classes(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        """Known fixture scores map to the expected band CSS classes.

        explanation_quality=0.50 -> warn; bbq_brazil=0.0 -> bad; the EU pair scores=1.0 ->
        good. The badge markup carries both the value and its band class.
        """
        doc = fixture_report.to_html()
        assert 'class="badge bad">0.000<' in doc  # bbq_brazil / human_deception_brazil
        assert 'class="badge warn">0.500<' in doc  # explanation_quality
        assert 'class="badge good">1.000<' in doc  # EU human_deception / bbq

    def test_dynamic_values_are_escaped(self, tmp_path: Path) -> None:
        """A model id containing HTML metacharacters is escaped, not injected raw."""
        from vigilai.report.brazil_report import build_brazil_report

        log_dir = str(tmp_path / "esc_run")
        _run_into(
            log_dir,
            _binary_task(
                "human_deception_brazil", "Disclosure of AI", "Art. 5, I", "all_ai"
            ),
            _HIT,
        )
        report = build_brazil_report(log_dir)
        # Force a dynamic value with metacharacters and confirm it is escaped in the output.
        report.models = ["<script>x</script>"]
        doc = report.to_html()
        assert "<script>x</script>" not in doc
        assert "&lt;script&gt;x&lt;/script&gt;" in doc


class TestEndToEndOnRealTasks:
    """The read path works on genuine ``vigilai eval`` output (real registered tasks, mock).

    Runs the four real Brazil tasks (whose logged names carry the ``vigilai/`` registry
    prefix) on the mock model and confirms the report resolves them to the right articles via
    the log-header decorator attribs — including aia_checklist under Arts. 25-28.
    """

    def test_report_from_real_mock_run(self, tmp_path: Path) -> None:
        from vigilai.tasks.aia_checklist.aia_checklist import aia_checklist
        from vigilai.tasks.bbq_brazil.bbq_brazil import bbq_brazil
        from vigilai.tasks.explanation_quality.explanation_quality import (
            explanation_quality,
        )
        from vigilai.tasks.human_deception_brazil.human_deception_brazil import (
            human_deception_brazil,
        )

        log_dir = str(tmp_path / "real_run")
        for real_task in (
            human_deception_brazil(),
            bbq_brazil(),
            explanation_quality(),
            aia_checklist(),
        ):
            logs = inspect_eval(
                real_task, model="mockllm/model", display="none", limit=3, log_dir=log_dir
            )
            assert logs[0].status == "success"

        report = build_brazil_report(log_dir)
        articles = {g.article for g in report.article_groups}
        assert {"Art. 5, I", "Art. 5, III", "Art. 6, I", "Arts. 25-28"} <= articles

        # The registry prefix is stripped, so pairing/Brazil-only classification still works.
        assert report.row_for("aia_checklist") is not None
        assert report.row_for("aia_checklist").has_eu_equivalent is False
        assert report.row_for("explanation_quality").has_eu_equivalent is False
        # Brazil pair tasks present as side-by-side rows (EU counterparts not run -> eu_score None).
        assert report.row_for("human_deception_brazil") is not None
        assert report.row_for("bbq_brazil") is not None


@pytest.fixture(scope="module")
def coverage_report(
    tmp_path_factory: pytest.TempPathFactory,
) -> BrazilComplianceReport:
    """A focused fixture for the 9-requirement breadth coverage map (Phase 10).

    Designed to exercise all three coverage statuses:

    * **Brazil benchmark (✅):** ``bbq_brazil`` (Representation — Absence of Bias) and
      ``explanation_quality`` (Interpretability) — Brazil-specific benchmarks.
    * **EU task only (🟡):** ``fairllm`` (Fairness — Absence of Discrimination, a *mapped*
      requirement) and ``arc_challenge`` (Capabilities… an *unmapped* requirement) ran as the
      preserved EU tasks with no Brazil benchmark.
    * **Not yet covered (⚪):** every other canonical requirement (no task in the run).
    """
    log_dir = str(tmp_path_factory.mktemp("coverage_logs"))

    # Brazil benchmarks (✅).
    _run_into(
        log_dir,
        _binary_task(
            "bbq_brazil", "Representation — Absence of Bias", "Art. 5, III", "all_ai"
        ),
        _HIT,  # 1.0
    )
    _run_into(
        log_dir,
        _fraction_task(
            "explanation_quality", "Interpretability", "Art. 6, I", "high_risk"
        ),
        "0.6",
    )

    # EU-only tasks (🟡) — preserved COMPL-AI tasks with NO Brazil decorator tags. fairllm's
    # requirement (Fairness — Absence of Discrimination) maps to Art. 5, III via the
    # requirement→article mapping, but it has no Brazil-specific benchmark, so the Fairness
    # requirement row is "EU task only" with its article still derived from the mapping.
    _run_into(
        log_dir,
        _binary_task_unmapped("fairllm", "Fairness — Absence of Discrimination"),
        _HIT,  # EU-only score 1.0
    )
    # An unmapped EU-only requirement task (no Brazil article at all).
    _run_into(
        log_dir,
        _fraction_task_unmapped("arc_challenge", "Capabilities, Performance, and Limitations"),
        "0.4",
    )

    return build_brazil_report(log_dir)


def _binary_task_unmapped(name: str, requirement: str) -> Task:
    """A one-sample match()-scored EU-only task with NO Brazil article/scope decorator tags."""

    @task(name=name, technical_requirement=requirement)
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset([Sample(input="q", target=_HIT)]),
            solver=[generate()],
            scorer=match(),
        )

    return _t()


def _fraction_task_unmapped(name: str, requirement: str) -> Task:
    """A one-sample fraction-scored EU-only task with NO Brazil article/scope decorator tags."""

    @task(name=name, technical_requirement=requirement)
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset([Sample(input="q", target="n/a")]),
            solver=[generate()],
            scorer=_fraction_scorer(),
        )

    return _t()


class TestCoverageMap:
    """The 9-requirement breadth coverage map (Phase 10).

    Reports Brazil compliance across all nine COMPL-AI technical requirements: ✅ when a
    Brazil-specific benchmark covers it, 🟡 when only the preserved EU task ran, ⚪ when the
    requirement is absent from the run.
    """

    def test_lists_all_nine_requirements_in_canonical_order(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        listed = [c.requirement for c in coverage_report.coverage_by_requirement]
        assert listed == list(NINE_TECHNICAL_REQUIREMENTS)
        assert len(listed) == 9

    def test_brazil_benchmarked_requirements_flagged(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        by_req = {c.requirement: c for c in coverage_report.coverage_by_requirement}
        assert by_req["Representation — Absence of Bias"].has_brazil_benchmark is True
        assert by_req["Interpretability"].has_brazil_benchmark is True
        assert by_req["Representation — Absence of Bias"].status == "brazil"
        assert by_req["Interpretability"].status == "brazil"

    def test_eu_only_mapped_requirement_status(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        """A mapped requirement with no Brazil benchmark is 🟡 EU-only, with its EU score."""
        cov = next(
            c
            for c in coverage_report.coverage_by_requirement
            if c.requirement == "Fairness — Absence of Discrimination"
        )
        assert cov.has_brazil_benchmark is False
        assert cov.ran is True
        assert cov.status == "eu_only"
        assert cov.brazil_article == "Art. 5, III"  # via the requirement→article mapping
        assert cov.eu_only_score == pytest.approx(1.0)

    def test_eu_only_unmapped_requirement_status(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        cov = next(
            c
            for c in coverage_report.coverage_by_requirement
            if c.requirement == "Capabilities, Performance, and Limitations"
        )
        assert cov.status == "eu_only"
        assert cov.brazil_article is None
        assert cov.eu_only_score == pytest.approx(0.4)

    def test_uncovered_requirement_status(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        cov = next(
            c
            for c in coverage_report.coverage_by_requirement
            if c.requirement == "Cyberattack Resilience"
        )
        assert cov.ran is False
        assert cov.has_brazil_benchmark is False
        assert cov.status == "uncovered"
        assert cov.eu_only_score is None

    def test_societal_alignment_credited_via_decorator(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        """aia_checklist (req. 'Societal Alignment', article via decorator) makes the Societal
        Alignment requirement a ✅ Brazil benchmark even though it is unmapped."""
        cov = next(
            c
            for c in fixture_report.coverage_by_requirement
            if c.requirement == "Societal Alignment"
        )
        assert cov.has_brazil_benchmark is True
        assert cov.brazil_article == "Arts. 25-28"
        assert cov.status == "brazil"

    def test_markdown_renders_coverage_section(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        md = coverage_report.to_markdown()
        assert "## Brazil compliance coverage map (9 requirements)" in md
        # All nine requirement names appear.
        for requirement in NINE_TECHNICAL_REQUIREMENTS:
            assert requirement in md
        assert "✅ Brazil benchmark" in md
        assert "🟡 EU task only" in md
        assert "⚪ not yet covered" in md

    def test_html_renders_coverage_section(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        doc = coverage_report.to_html()
        assert "Brazil compliance coverage map (9 requirements)" in doc
        for requirement in NINE_TECHNICAL_REQUIREMENTS:
            # Requirement names with the em dash are HTML-escaped only for quotes; the dash
            # itself survives, so a plain substring check holds.
            assert requirement in doc
        assert "cov-pill brazil" in doc
        assert "cov-pill eu_only" in doc
        assert "cov-pill uncovered" in doc

    def test_json_carries_coverage(
        self, coverage_report: BrazilComplianceReport
    ) -> None:
        data = json.loads(coverage_report.to_json())
        assert "coverage_by_requirement" in data
        rows = {r["requirement"]: r for r in data["coverage_by_requirement"]}
        assert len(rows) == 9
        assert rows["Interpretability"]["has_brazil_benchmark"] is True
        assert rows["Interpretability"]["status"] == "brazil"
        assert rows["Cyberattack Resilience"]["status"] == "uncovered"


# ---------------------------------------------------------------------------------------
# Iteration 2 / Phase 1 — standard errors end-to-end.
#
# The one-sample fixtures above are deliberately left alone (many tests pin their exact scores),
# so the standard-error tests get their own fixture log dir whose tasks each run **four samples
# with varying forced outputs**. That matters: a one-sample task has a degenerate standard error,
# so only a multi-sample run proves the real Inspect-computed value is threaded from the log
# header through every aggregate into all three renderers.
# ---------------------------------------------------------------------------------------


@scorer(metrics=[mean()])
def _fraction_scorer_no_stderr():
    """Like :func:`_fraction_scorer` but declaring **only** ``mean`` — no ``stderr()`` metric.

    Models a log that carries no standard error at all, so the report must fall back to a bare
    point estimate (never ``± None``) and must refuse to pool a partial group error.
    """

    async def score(state, target):  # type: ignore[no-untyped-def]
        try:
            value = float(state.output.completion)
        except ValueError:
            value = 0.0
        return Score(value=value)

    return score


def _multi_sample_task(
    name: str,
    requirement: str,
    *,
    samples: int,
    article: str | None = None,
    scope: str | None = None,
    with_stderr: bool = True,
) -> Task:
    """A multi-sample fraction-scored task, Brazil-tagged when ``article`` is given."""
    attribs: dict[str, Any] = {"name": name, "technical_requirement": requirement}
    if article is not None:
        attribs["brazil_article"] = article
        attribs["brazil_scope"] = scope

    @task(**attribs)
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset(
                [Sample(input="q", target="n/a") for _ in range(samples)]
            ),
            solver=[generate()],
            scorer=_fraction_scorer() if with_stderr else _fraction_scorer_no_stderr(),
        )

    return _t()


def _run_samples_into(log_dir: str, a_task: Task, completions: list[str]) -> None:
    """Run ``a_task`` with one forced output per sample.

    Order-independent by design: the statistics asserted below (mean and standard error) depend
    on the *multiset* of sample scores, not on which sample received which forced output.
    """
    model = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content("mockllm/model", c) for c in completions
        ],
    )
    logs = inspect_eval(a_task, model=model, display="none", log_dir=log_dir)
    assert logs[0].status == "success", f"{a_task} did not run cleanly"


# Hand-computable expectations. Inspect's ``stderr()`` is the standard error of the mean via the
# CLT — the sample standard deviation (n-1) over sqrt(n) — so the expected values are stated as
# that formula rather than as opaque literals.
_SE_EVEN = statistics.stdev([1.0, 0.0, 1.0, 0.0]) / math.sqrt(4)  # 0.288675
_SE_SKEWED = statistics.stdev([1.0, 1.0, 1.0, 0.0]) / math.sqrt(4)  # 0.250000


def _hand_task_score(name: str, score: float | None, se: float | None) -> TaskScore:
    """A minimal hand-built :class:`TaskScore` for the pure aggregate-arithmetic tests."""
    return TaskScore(
        task=name,
        brazil_article="Art. 6, I",
        brazil_scope="high_risk",
        technical_requirement="Interpretability",
        score=score,
        metric_name="mean",
        model="mockllm/model",
        total_samples=4,
        status="success",
        stderr=se,
    )


@pytest.fixture(scope="module")
def stderr_report(tmp_path_factory: pytest.TempPathFactory) -> BrazilComplianceReport:
    """A four-samples-per-task fixture with non-zero, hand-checkable standard errors.

    Score design (forced outputs -> mean ± se):

    * Art. 5, I  (all_ai):    ``human_deception`` 0.750 ± 0.250 (EU side),
                              ``human_deception_brazil`` 0.500 ± 0.289
                              -> delta −0.250 ± 0.382 (quadrature)
    * Art. 5, III (all_ai):   ``bbq_brazil`` 0.250 ± 0.250, ``bold`` 0.500 ± 0.289
                              -> article mean 0.375 ± 0.191 (pooled). The EU ``bbq`` is *not*
                              run, so ``bbq_brazil``'s row has no delta and no delta error.
    * Art. 6, II-III:         ``contestation_review`` 0.500 with a **stderr-less** scorer
                              -> no error bar anywhere for that task.
    * EU-only requirement:    ``arc_challenge`` 0.500 ± 0.289 (unmapped) -> the coverage map's
                              EU-only row carries a pooled ±.
    """
    log_dir = str(tmp_path_factory.mktemp("stderr_logs"))

    # Art. 5, I — the disclosure pair, both sides with a real standard error.
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "human_deception",
            "Disclosure of AI",
            samples=4,
            article="Art. 5, I",
            scope="all_ai",
        ),
        ["1.0", "1.0", "1.0", "0.0"],  # 0.750 ± 0.250
    )
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "human_deception_brazil",
            "Disclosure of AI",
            samples=4,
            article="Art. 5, I",
            scope="all_ai",
        ),
        ["1.0", "0.0", "1.0", "0.0"],  # 0.500 ± 0.289
    )

    # Art. 5, III — two Brazil-mapped tasks with *different* standard errors, so the pooled
    # group formula is non-degenerate.
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "bbq_brazil",
            "Representation — Absence of Bias",
            samples=4,
            article="Art. 5, III",
            scope="all_ai",
        ),
        ["1.0", "0.0", "0.0", "0.0"],  # 0.250 ± 0.250
    )
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "bold",
            "Representation — Absence of Bias",
            samples=4,
            article="Art. 5, III",
            scope="all_ai",
        ),
        ["1.0", "1.0", "0.0", "0.0"],  # 0.500 ± 0.289
    )

    # Art. 6, II-III — scored by a scorer that declares no stderr() metric at all.
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "contestation_review",
            "Societal Alignment",
            samples=2,
            article="Art. 6, II-III",
            scope="high_risk",
            with_stderr=False,
        ),
        ["0.5", "0.5"],  # 0.500, no error bar
    )

    # An unmapped EU-only requirement, to exercise the coverage map's pooled EU-only error.
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "arc_challenge",
            "Capabilities, Performance, and Limitations",
            samples=4,
        ),
        ["1.0", "1.0", "0.0", "0.0"],  # 0.500 ± 0.289
    )

    return build_brazil_report(log_dir)


class TestStandardErrors:
    """Phase 1 — the ``stderr`` the scorers already compute reaches every published number.

    Before iteration 2 the aggregator read one headline point estimate per task and dropped the
    rest of the metrics dict, so the ``±`` figures in the write-up were compiled by hand outside
    the tool. These tests pin the whole path: log header -> :class:`TaskScore` -> per-article /
    side-by-side / coverage aggregates -> Markdown, JSON, and HTML.
    """

    # -- log header -> TaskScore --------------------------------------------------------

    def test_task_stderr_is_read_from_the_log(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        by_task = {t.task: t for t in stderr_report.brazil_task_scores}
        assert by_task["human_deception_brazil"].stderr == pytest.approx(_SE_EVEN)
        assert by_task["bbq_brazil"].stderr == pytest.approx(_SE_SKEWED)
        assert by_task["bold"].stderr == pytest.approx(_SE_EVEN)

    def test_eu_side_stderr_is_read_too(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        by_task = {t.task: t for t in stderr_report.eu_task_scores}
        assert by_task["human_deception"].stderr == pytest.approx(_SE_SKEWED)

    def test_headline_metric_resolution_is_unchanged(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        """The standard error is a *sibling* read — it must never become the point estimate."""
        by_task = {t.task: t for t in stderr_report.brazil_task_scores}
        assert by_task["human_deception_brazil"].metric_name == "mean"
        assert by_task["human_deception_brazil"].score == pytest.approx(0.5)
        assert by_task["bbq_brazil"].score == pytest.approx(0.25)

    def test_stderr_is_none_when_the_scorer_declares_none(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        by_task = {t.task: t for t in stderr_report.brazil_task_scores}
        assert by_task["contestation_review"].score == pytest.approx(0.5)
        assert by_task["contestation_review"].stderr is None

    def test_single_sample_task_reports_no_stderr(
        self, fixture_report: BrazilComplianceReport
    ) -> None:
        """A one-observation task must not print ``± 0.000`` and read as infinitely precise.

        Inspect's ``stderr()`` returns a placeholder ``0`` below two samples, so the report drops
        it — the shared one-sample ``fixture_report`` is exactly that case. This is the guard that
        keeps ``aia_checklist`` at n=1 (iteration 1's most-criticized figure) from rendering as
        the most precise number on the scorecard.
        """
        by_task = {t.task: t for t in fixture_report.brazil_task_scores}
        assert by_task["aia_checklist"].total_samples == 1
        assert by_task["aia_checklist"].stderr is None
        group = fixture_report.group_for("Arts. 25-28")
        assert group is not None
        assert group.mean_stderr is None
        md = fixture_report.to_markdown()
        assert "| 0.750 |" in md  # aia_checklist's bare point estimate
        assert "± 0.000" not in md

    def test_non_finite_stderr_is_treated_as_absent(self) -> None:
        """An undefined standard error must render as a bare estimate, never as ``± nan``."""

        class _Metric:
            def __init__(self, value: float) -> None:
                self.value = value

        assert _stderr_metric({}) is None
        assert _stderr_metric({"stderr": _Metric(float("nan"))}) is None
        assert _stderr_metric({"stderr": _Metric(float("inf"))}) is None
        assert _stderr_metric({"stderr": _Metric(0.125)}) == pytest.approx(0.125)

    # -- aggregates ---------------------------------------------------------------------

    def test_article_group_stderr_pools_member_errors(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        """Art. 5, III holds two Brazil-mapped tasks: sqrt(Σ seᵢ²)/k over both members."""
        group = stderr_report.group_for("Art. 5, III")
        assert group is not None
        assert sorted(t.task for t in group.tasks) == ["bbq_brazil", "bold"]
        assert group.mean_score == pytest.approx(0.375)
        expected = math.sqrt(_SE_SKEWED**2 + _SE_EVEN**2) / 2
        assert group.mean_stderr == pytest.approx(expected)

    def test_single_member_group_stderr_is_that_member(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        group = stderr_report.group_for("Art. 5, I")
        assert group is not None
        assert [t.task for t in group.tasks] == ["human_deception_brazil"]
        assert group.mean_stderr == pytest.approx(_SE_EVEN)

    def test_group_stderr_is_none_when_a_member_lacks_one(self) -> None:
        """No partial pooling — a group never shows an error bar its evidence can't support."""
        group = ArticleGroup(
            article="Art. 6, I",
            scope="high_risk",
            tasks=[
                _hand_task_score("with_se", 0.4, 0.1),
                _hand_task_score("without_se", 0.6, None),
            ],
        )
        assert group.mean_score == pytest.approx(0.5)
        assert group.mean_stderr is None

    def test_group_stderr_uses_the_pooled_formula(self) -> None:
        group = ArticleGroup(
            article="Art. 6, I",
            scope="high_risk",
            tasks=[
                _hand_task_score("a", 0.4, 0.1),
                _hand_task_score("b", 0.6, 0.2),
            ],
        )
        assert group.mean_stderr == pytest.approx(math.sqrt(0.1**2 + 0.2**2) / 2)

    def test_group_stderr_ignores_unscored_members(self) -> None:
        """A task that produced no score can't nullify the error bar of the ones that did."""
        group = ArticleGroup(
            article="Art. 6, I",
            scope="high_risk",
            tasks=[
                _hand_task_score("scored", 0.5, 0.1),
                _hand_task_score("unscored", None, None),
            ],
        )
        assert group.mean_stderr == pytest.approx(0.1)

    def test_empty_group_stderr_is_none(self) -> None:
        group = ArticleGroup(article="Art. 6, I", scope="high_risk", tasks=[])
        assert group.mean_score is None
        assert group.mean_stderr is None

    def test_delta_stderr_propagates_in_quadrature(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        row = stderr_report.row_for("human_deception_brazil")
        assert row is not None
        assert row.brazil_stderr == pytest.approx(_SE_EVEN)
        assert row.eu_stderr == pytest.approx(_SE_SKEWED)
        assert row.delta == pytest.approx(-0.25)
        assert row.delta_stderr == pytest.approx(math.sqrt(_SE_EVEN**2 + _SE_SKEWED**2))

    def test_delta_stderr_is_none_without_an_eu_side(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        """``bbq`` was not run, so there is no delta — and therefore no delta error."""
        row = stderr_report.row_for("bbq_brazil")
        assert row is not None
        assert row.has_eu_equivalent is True
        assert row.eu_score is None
        assert row.delta is None
        assert row.delta_stderr is None

    def test_delta_stderr_is_none_for_a_brazil_only_row(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        row = stderr_report.row_for("contestation_review")
        assert row is not None
        assert row.has_eu_equivalent is False
        assert row.delta_stderr is None

    def test_delta_stderr_is_none_when_one_side_lacks_one(self) -> None:
        row = SideBySideRow(
            brazil_task="human_deception_brazil",
            brazil_article="Art. 5, I",
            brazil_scope="all_ai",
            brazil_score=0.5,
            eu_task="human_deception",
            eu_score=1.0,
            has_eu_equivalent=True,
            brazil_stderr=0.1,
            eu_stderr=None,
        )
        assert row.delta == pytest.approx(-0.5)
        assert row.delta_stderr is None

    def test_coverage_row_carries_a_pooled_eu_only_stderr(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        cov = next(
            c
            for c in stderr_report.coverage_by_requirement
            if c.requirement == "Capabilities, Performance, and Limitations"
        )
        assert cov.status == "eu_only"
        assert cov.eu_only_score == pytest.approx(0.5)
        assert cov.eu_only_stderr == pytest.approx(_SE_EVEN)

    def test_coverage_row_without_an_eu_score_has_no_stderr(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        cov = next(
            c
            for c in stderr_report.coverage_by_requirement
            if c.requirement == "Cyberattack Resilience"
        )
        assert cov.eu_only_score is None
        assert cov.eu_only_stderr is None

    # -- renderers ----------------------------------------------------------------------

    def test_markdown_renders_score_and_delta_with_stderr(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        md = stderr_report.to_markdown()
        assert "0.500 ± 0.289" in md  # human_deception_brazil
        assert "0.750 ± 0.250" in md  # the EU side of the pair
        assert "0.375 ± 0.191" in md  # Art. 5, III pooled article mean
        assert "-0.250 ± 0.382" in md  # delta with its propagated error

    def test_markdown_labels_the_stderr_columns(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        md = stderr_report.to_markdown()
        assert "Score ± se" in md
        assert "Δ (Brazil − EU) ± se" in md
        assert "standard error of the mean" in md

    def test_markdown_renders_a_bare_estimate_without_stderr(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        """A stderr-less task shows the point estimate alone — never ``± None``/``± nan``."""
        md = stderr_report.to_markdown()
        assert "± None" not in md
        assert "± nan" not in md
        assert "| 0.500 |" in md  # contestation_review's bare cell

    def test_json_carries_stderr_keys_throughout(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        data = json.loads(stderr_report.to_json())

        arts = {a["article"]: a for a in data["articles"]}
        assert arts["Art. 5, III"]["mean_stderr"] == pytest.approx(
            math.sqrt(_SE_SKEWED**2 + _SE_EVEN**2) / 2
        )
        tasks = {t["task"]: t for t in arts["Art. 5, III"]["tasks"]}
        assert tasks["bbq_brazil"]["stderr"] == pytest.approx(_SE_SKEWED)

        rows = {r["brazil_task"]: r for r in data["eu_brazil_side_by_side"]}
        pair = rows["human_deception_brazil"]
        assert pair["brazil_stderr"] == pytest.approx(_SE_EVEN)
        assert pair["eu_stderr"] == pytest.approx(_SE_SKEWED)
        assert pair["delta_stderr"] == pytest.approx(
            math.sqrt(_SE_EVEN**2 + _SE_SKEWED**2)
        )
        assert rows["contestation_review"]["brazil_stderr"] is None
        assert rows["contestation_review"]["delta_stderr"] is None

        cov = {c["requirement"]: c for c in data["coverage_by_requirement"]}
        assert cov["Capabilities, Performance, and Limitations"][
            "eu_only_stderr"
        ] == pytest.approx(_SE_EVEN)
        assert cov["Cyberattack Resilience"]["eu_only_stderr"] is None

    def test_html_renders_stderr_as_a_subordinate_span(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        doc = stderr_report.to_html()
        # The style token exists and the error appears as a sibling of the badge...
        assert ".se {" in doc
        assert 'class="se">± 0.289<' in doc
        assert 'class="se">± 0.382<' in doc  # the propagated delta error
        # ...while the point estimate keeps its band coloring, unchanged.
        assert 'class="badge warn">0.500</span> <span class="se">± 0.289<' in doc

    def test_html_omits_the_stderr_span_when_absent(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        doc = stderr_report.to_html()
        assert "± None" not in doc
        assert "± nan" not in doc
        # contestation_review's badge is closed by its cell with no `.se` sibling.
        assert '<span class="badge warn">0.500</span></td>' in doc

    def test_html_stays_self_contained_with_stderr(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        doc = stderr_report.to_html()
        assert "src=" not in doc
        assert "href=" not in doc
        assert "http://" not in doc
        assert "https://" not in doc


# ---------------------------------------------------------------------------------------
# Phase 4 — the sector overlay.
#
# ``aia_checklist`` declares Inspect ``grouped()`` metrics on each sample's
# ``metadata["sector"]``, which Inspect flattens into ``mean_<sector>`` / ``stderr_<sector>``
# entries in the log header. The fixture below reproduces that shape with a *fixture* task
# rather than the real one, so these tests exercise the report's parsing and aggregation and
# stay green if the real checklist's item set changes. The **real** key names are pinned
# separately, against a real ``aia_checklist`` log, in
# ``tests/test_aia_checklist.py::TestGroupedMetricKeys``.
# ---------------------------------------------------------------------------------------
_GAP_ITEMS_FIXTURE = "human_review_gap_lgpd20,ai_interaction_disclosure_gap"

# Hand-computable expectations for the two fixture sectors.
_SECTOR_FIN_MEAN = 0.75
_SECTOR_FIN_SE = statistics.stdev([1.0, 1.0, 1.0, 0.0]) / math.sqrt(4)  # 0.250000
_SECTOR_HEA_MEAN = 0.5
_SECTOR_HEA_SE = statistics.stdev([1.0, 0.0, 1.0, 0.0]) / math.sqrt(4)  # 0.288675


@scorer(
    metrics=[
        mean(),
        stderr(),
        grouped(mean(), "sector", all=False, name_template="mean_{group_name}"),
        grouped(stderr(), "sector", all=False, name_template="stderr_{group_name}"),
    ]
)
def _sector_fraction_scorer():
    """A fraction scorer declaring the same metric quartet ``aia_checklist_scorer`` does."""

    async def score(state, target):  # type: ignore[no-untyped-def]
        try:
            value = float(state.output.completion)
        except ValueError:
            value = 0.0
        return Score(value=value)

    return score


def _sector_task(name: str, sectors: list[str]) -> Task:
    """A Brazil-tagged task with one sample per entry in ``sectors``, carrying that sector."""

    @task(
        name=name,
        technical_requirement="Societal Alignment",
        brazil_article="Arts. 25-28",
        brazil_scope="high_risk",
        brazil_gap_items=_GAP_ITEMS_FIXTURE,
    )
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset(
                [
                    Sample(input="q", target="n/a", metadata={"sector": sector})
                    for sector in sectors
                ]
            ),
            solver=[generate()],
            scorer=_sector_fraction_scorer(),
        )

    return _t()


def _sector_task_with_per_sector_gaps(name: str, sectors: list[str]) -> Task:
    """Like :func:`_sector_task` but also declaring ``brazil_gap_items_by_sector`` (Phase 6).

    ``health_anvisa`` is deliberately **absent** from the mapping while still appearing in the
    flat attrib — the exact shape of the Resolution 11 bug, so the fix is tested on the case that
    produced it rather than on a friendly one.
    """

    @task(
        name=name,
        technical_requirement="Societal Alignment",
        brazil_article="Arts. 25-28",
        brazil_scope="high_risk",
        brazil_gap_items=_GAP_ITEMS_FIXTURE,
        brazil_gap_items_by_sector="finance_bacen:human_review_gap_lgpd20",
    )
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset(
                [
                    Sample(input="q", target="n/a", metadata={"sector": sector})
                    for sector in sectors
                ]
            ),
            solver=[generate()],
            scorer=_sector_fraction_scorer(),
        )

    return _t()


@pytest.fixture(scope="module")
def sector_report(tmp_path_factory: pytest.TempPathFactory) -> BrazilComplianceReport:
    """A run holding one sector-aware task over two sectors, plus one sector-less task.

    Score design (forced outputs, in sample order):

    * ``finance_bacen``: 1.0, 1.0, 1.0, 0.0 -> 0.750 ± 0.250
    * ``health_anvisa``: 1.0, 0.0, 1.0, 0.0 -> 0.500 ± 0.289
    * ``explanation_quality``: no sector at all -> contributes nothing to the overlay
    """
    log_dir = str(tmp_path_factory.mktemp("sector_logs"))
    _run_samples_into(
        log_dir,
        _sector_task(
            "aia_checklist",
            ["finance_bacen"] * 4 + ["health_anvisa"] * 4,
        ),
        ["1.0", "1.0", "1.0", "0.0", "1.0", "0.0", "1.0", "0.0"],
    )
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "explanation_quality",
            "Interpretability",
            samples=4,
            article="Art. 6, I",
            scope="high_risk",
        ),
        ["1.0", "1.0", "0.0", "0.0"],
    )
    return build_brazil_report(log_dir)


class _StubMetric:
    """Minimal stand-in for ``EvalMetric`` — the parser only ever reads ``.value``."""

    def __init__(self, value: float) -> None:
        self.value = value


class TestSectorMetricParsing:
    """``_sector_metrics`` reads the flattened ``grouped()`` keys, and only those."""

    def test_parses_a_mean_stderr_pair(self) -> None:
        parsed = _sector_metrics(
            {
                "mean": _StubMetric(0.6),
                "stderr": _StubMetric(0.1),
                "mean_finance_bacen": _StubMetric(0.75),
                "stderr_finance_bacen": _StubMetric(0.25),
            }
        )
        assert parsed == {"finance_bacen": (0.75, 0.25)}

    def test_the_bare_headline_metrics_are_not_sectors(self) -> None:
        """``mean`` / ``stderr`` need a non-empty suffix to be a group key."""
        assert _sector_metrics({"mean": _StubMetric(0.6), "stderr": _StubMetric(0.1)}) == {}

    def test_a_sector_without_a_stderr_still_reports_its_mean(self) -> None:
        parsed = _sector_metrics({"mean_capital_cvm": _StubMetric(0.4)})
        assert parsed == {"capital_cvm": (0.4, None)}

    def test_a_stderr_without_a_mean_is_dropped(self) -> None:
        """A standard error with no point estimate is not a reportable sector."""
        assert _sector_metrics({"stderr_capital_cvm": _StubMetric(0.4)}) == {}

    def test_non_finite_values_are_dropped(self) -> None:
        parsed = _sector_metrics(
            {
                "mean_finance_bacen": _StubMetric(0.75),
                "stderr_finance_bacen": _StubMetric(float("nan")),
                "mean_health_anvisa": _StubMetric(float("nan")),
            }
        )
        assert parsed == {"finance_bacen": (0.75, None)}

    def test_sectors_come_back_sorted(self) -> None:
        parsed = _sector_metrics(
            {
                "mean_health_anvisa": _StubMetric(0.5),
                "mean_capital_cvm": _StubMetric(0.4),
                "mean_finance_bacen": _StubMetric(0.75),
            }
        )
        assert list(parsed) == ["capital_cvm", "finance_bacen", "health_anvisa"]


class TestSectorAggregation:
    """The overlay groups reach the report from a real log, with their error bars."""

    def test_task_score_carries_its_sector_scores(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        by_task = {t.task: t for t in sector_report.brazil_task_scores}
        aia = by_task["aia_checklist"]
        assert set(aia.sector_scores) == {"finance_bacen", "health_anvisa"}
        fin_mean, fin_se = aia.sector_scores["finance_bacen"]
        assert fin_mean == pytest.approx(_SECTOR_FIN_MEAN)
        assert fin_se == pytest.approx(_SECTOR_FIN_SE)

    def test_a_sector_less_task_carries_none(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        by_task = {t.task: t for t in sector_report.brazil_task_scores}
        assert by_task["explanation_quality"].sector_scores == {}

    def test_sector_groups_are_built_and_sorted(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        assert [g.sector for g in sector_report.sector_groups] == [
            "finance_bacen",
            "health_anvisa",
        ]

    def test_group_mean_and_pooled_stderr(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        group = sector_report.sector_for("health_anvisa")
        assert group is not None
        assert group.tasks == [
            ("aia_checklist", pytest.approx(_SECTOR_HEA_MEAN), pytest.approx(_SECTOR_HEA_SE))
        ]
        assert group.mean_score == pytest.approx(_SECTOR_HEA_MEAN)
        assert group.mean_stderr == pytest.approx(_SECTOR_HEA_SE)

    def test_gap_items_ride_in_from_the_decorator(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        """Read from the log **header** — the aggregator never loads a sample."""
        by_task = {t.task: t for t in sector_report.brazil_task_scores}
        assert by_task["aia_checklist"].gap_items == tuple(_GAP_ITEMS_FIXTURE.split(","))
        assert by_task["explanation_quality"].gap_items == ()
        group = sector_report.sector_for("finance_bacen")
        assert group is not None
        assert group.gap_items == tuple(sorted(_GAP_ITEMS_FIXTURE.split(",")))

    def test_the_headline_score_still_resolves_alongside_the_grouped_metrics(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        """The trap the outline flags: declaring grouped() must not cost the headline mean."""
        by_task = {t.task: t for t in sector_report.brazil_task_scores}
        aia = by_task["aia_checklist"]
        assert aia.metric_name == "mean"
        assert aia.score == pytest.approx(0.625)  # 5 of 8 samples scored 1.0
        assert aia.stderr is not None

    def test_a_run_without_a_sector_aware_task_has_no_overlay(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        assert stderr_report.sector_groups == []


class TestSectorRendering:
    """The overlay section renders in all three views, and is omitted when there is nothing."""

    def test_markdown_renders_the_section(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        md = sector_report.to_markdown()
        assert "## Sector overlay (BACEN / ANVISA / CVM)" in md
        assert "| `finance_bacen` | `aia_checklist` | 0.750 ± 0.250 |" in md
        assert "| `health_anvisa` | `aia_checklist` | 0.500 ± 0.289 |" in md

    def test_markdown_marks_the_gap_items(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        md = sector_report.to_markdown()
        assert "**Gap-flagging items in this run:**" in md
        assert "`human_review_gap_lgpd20`" in md
        assert "a finding about Brazilian law rather than about the model" in md

    def test_markdown_carries_the_not_legal_advice_caveat(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        md = sector_report.to_markdown()
        assert "not legal advice" in md
        assert "No Brazilian sector regulator has issued a binding AI-specific rule." in md

    def test_markdown_section_order_is_fixed(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        md = sector_report.to_markdown()
        assert (
            md.index("## EU ↔ Brazil side-by-side")
            < md.index("## Sector overlay (BACEN / ANVISA / CVM)")
            < md.index("## Brazil compliance coverage map (9 requirements)")
        )

    def test_markdown_omits_the_section_when_no_sector_ran(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        assert "Sector overlay" not in stderr_report.to_markdown()

    def test_json_carries_the_overlay(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        data = json.loads(sector_report.to_json())
        overlay = {entry["sector"]: entry for entry in data["sector_overlay"]}
        assert set(overlay) == {"finance_bacen", "health_anvisa"}
        assert overlay["finance_bacen"]["mean_score"] == pytest.approx(_SECTOR_FIN_MEAN)
        assert overlay["finance_bacen"]["mean_stderr"] == pytest.approx(_SECTOR_FIN_SE)
        assert overlay["finance_bacen"]["tasks"] == [
            {
                "task": "aia_checklist",
                "score": pytest.approx(_SECTOR_FIN_MEAN),
                "stderr": pytest.approx(_SECTOR_FIN_SE),
            }
        ]
        assert overlay["finance_bacen"]["gap_items"] == sorted(_GAP_ITEMS_FIXTURE.split(","))

    def test_json_overlay_is_empty_when_no_sector_ran(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        assert json.loads(stderr_report.to_json())["sector_overlay"] == []

    def test_html_renders_the_section_with_band_colouring_and_stderr(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        doc = sector_report.to_html()
        assert "<h2>Sector overlay (BACEN / ANVISA / CVM)</h2>" in doc
        # The point estimate keeps its band class; the error bar is the muted sibling.
        assert '<span class="badge warn">0.750</span> <span class="se">± 0.250<' in doc
        assert '<span class="badge warn">0.500</span> <span class="se">± 0.289<' in doc
        assert "<code class='task'>finance_bacen</code>" in doc

    def test_html_marks_the_gap_items(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        doc = sector_report.to_html()
        assert "<strong>Gap-flagging items in this run:</strong>" in doc
        assert "<code class='task'>human_review_gap_lgpd20</code>" in doc

    def test_html_stays_self_contained_with_the_overlay(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        doc = sector_report.to_html()
        assert "src=" not in doc
        assert "href=" not in doc
        assert "http://" not in doc
        assert "https://" not in doc

    def test_html_omits_the_section_when_no_sector_ran(
        self, stderr_report: BrazilComplianceReport
    ) -> None:
        assert "Sector overlay" not in stderr_report.to_html()


class TestSectorStandardErrorSuppression:
    """A sector error bar is dropped when the run cannot have reached two samples per group.

    Inspect's ``stderr()`` returns a **placeholder** ``0`` below two observations, so a
    ``split=held_out`` run (one sample per sector — exactly what Phase 6's judge grades) would
    otherwise print ``0.000 ± 0.000`` for a single observation. That is the overconfidence
    Phase 1 exists to remove, and it applies to the overlay too.
    """

    def test_a_one_sample_per_sector_run_shows_no_sector_stderr(
        self, tmp_path: Path
    ) -> None:
        log_dir = str(tmp_path / "held_out_logs")
        _run_samples_into(
            log_dir,
            _sector_task("aia_checklist", ["finance_bacen", "health_anvisa"]),
            ["1.0", "0.0"],
        )
        report = build_brazil_report(log_dir)
        group = report.sector_for("finance_bacen")
        assert group is not None
        assert group.tasks == [("aia_checklist", 1.0, None)]
        assert group.mean_stderr is None
        # ...and the renderers show the bare point estimate, never "± None".
        md = report.to_markdown()
        assert "| `finance_bacen` | `aia_checklist` | 1.000 |" in md
        assert "± None" not in md

    def test_a_balanced_multi_sample_run_keeps_its_sector_stderr(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        group = sector_report.sector_for("finance_bacen")
        assert group is not None
        assert group.tasks[0][2] == pytest.approx(_SECTOR_FIN_SE)


# =========================================================================================
# Iteration 2, Phase 6 — name-based scorer selection, the judge columns, and the per-sector
# gap list (Resolution 11).
#
# The cross-layer trap this phase exists to close: ``_task_score_from_log`` read
# ``log.results.scores[0]`` — literally the first scorer, with the comment "a task usually has a
# single score". Adding a judge makes that an index into a two-element list, so the **headline
# score becomes order-dependent**, silently, with a judge accuracy landing in the per-article
# compliance table and no error anywhere. Selection is by scorer **name** now, and the fixture
# below deliberately declares the judge **first** so the test would fail under the old code.
# =========================================================================================


class _StubScore:
    """Minimal stand-in for ``EvalScore`` — ``_select_score`` only ever reads ``.name``."""

    def __init__(self, name: str, **metrics: float) -> None:
        self.name = name
        self.metrics = {k: _StubMetric(v) for k, v in metrics.items()}
        self.params: dict[str, Any] = {}


class TestScorerSelectionIsByName:
    """``_select_score`` never indexes the list, in either direction."""

    def test_the_deterministic_scorer_wins_however_the_list_is_ordered(self) -> None:
        deterministic = _StubScore("rubric_scorer", mean=0.9)
        judge = _StubScore(JUDGE_SCORER_NAME, accuracy=0.2)
        for order in ([deterministic, judge], [judge, deterministic]):
            assert _select_score(order, judge=False) is deterministic
            assert _select_score(order, judge=True) is judge

    def test_all_three_brazil_scorers_are_recognised(self) -> None:
        for name in ("rubric_scorer", "contestation_scorer", "aia_checklist_scorer"):
            judge = _StubScore(JUDGE_SCORER_NAME, accuracy=0.2)
            deterministic = _StubScore(name, mean=0.9)
            assert _select_score([judge, deterministic], judge=False) is deterministic

    def test_an_upstream_single_scorer_log_resolves_exactly_as_before(self) -> None:
        """The regression that matters most: ``match`` / ``choice`` are not in the deterministic
        name list and must still resolve, or every preserved COMPL-AI task loses its score."""
        for name in ("match", "choice", "some_future_scorer"):
            only = _StubScore(name, accuracy=0.5)
            assert _select_score([only], judge=False) is only
            assert _select_score([only], judge=True) is None

    def test_the_judge_is_never_selected_as_a_headline(self) -> None:
        judge = _StubScore(JUDGE_SCORER_NAME, accuracy=0.2)
        assert _select_score([judge], judge=False) is None

    def test_no_scores_at_all(self) -> None:
        assert _select_score([], judge=False) is None
        assert _select_score([], judge=True) is None

    def test_the_report_constants_mirror_the_task_modules(self) -> None:
        """The report deliberately does not import the task package (Resolution 6 plans to extract
        a jurisdiction-neutral ``report`` command from it), so the two sets of strings are pinned
        against each other instead of shared."""
        assert _JUDGE_SCORERS == (JUDGE_SCORER_NAME,)
        assert _JUDGE_ROLE == JUDGE_ROLE
        assert set(_DETERMINISTIC_SCORERS) == {
            registry_info(rubric_scorer(EXPLANATION_RUBRIC)).name.split("/")[-1],
            registry_info(contestation_scorer(CONTESTATION_RUBRIC)).name.split("/")[-1],
            registry_info(aia_checklist_scorer()).name.split("/")[-1],
        }


# --- The judge fixture: a real two-scorer log, with the judge declared FIRST ----------------
#
# ``_judge_first_task`` puts the judge at index 0 on purpose. Under the old ``scores[0]`` code the
# per-article table would show the judge's accuracy as the compliance score.
_JUDGE_GRADES = ["GRADE: C", "GRADE: I", "GRADE: I", "GRADE: I"]  # accuracy 0.25
_JUDGE_ACCURACY = 0.25
_JUDGE_SE = statistics.stdev([1.0, 0.0, 0.0, 0.0]) / math.sqrt(4)  # 0.250000
_DETERMINISTIC_MEAN = 0.75
_DETERMINISTIC_SE = statistics.stdev([1.0, 1.0, 1.0, 0.0]) / math.sqrt(4)  # 0.250000


def _judge_first_task(name: str, article: str, scope: str) -> Task:
    """A Brazil-tagged task whose **judge is declared before** its deterministic scorer."""

    @task(
        name=name,
        technical_requirement="Interpretability",
        brazil_article=article,
        brazil_scope=scope,
    )
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset([Sample(input="q", target="n/a") for _ in range(4)]),
            solver=[generate()],
            scorer=[
                judge_scorer(
                    instructions="stub",
                    grader=JUDGE_GRADER,
                    grader_temperature=JUDGE_GRADER_TEMPERATURE,
                    grader_seed=JUDGE_GRADER_SEED,
                ),
                _fraction_scorer(),
            ],
        )

    return _t()


@pytest.fixture(scope="module")
def judge_report(tmp_path_factory: pytest.TempPathFactory) -> BrazilComplianceReport:
    """A run with one judged task (judge first in the scorer list) and one unjudged task.

    * ``explanation_quality``: deterministic 1.0/1.0/1.0/0.0 → 0.750 ± 0.250; judge C/I/I/I →
      accuracy 0.250 ± 0.250; Δ = +0.500.
    * ``contestation_review``: no judge at all → absent from the judge table.
    """
    log_dir = str(tmp_path_factory.mktemp("judge_logs"))
    subject = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content("mockllm/model", c) for c in ["1.0", "1.0", "1.0", "0.0"]
        ],
    )
    grader = get_model(
        "mockllm/model",
        custom_outputs=[ModelOutput.from_content("mockllm/model", g) for g in _JUDGE_GRADES],
    )
    logs = inspect_eval(
        _judge_first_task("explanation_quality", "Art. 6, I", "high_risk"),
        model=subject,
        model_roles={"grader": grader},
        display="none",
        log_dir=log_dir,
    )
    assert logs[0].status == "success", logs[0].error
    _run_samples_into(
        log_dir,
        _multi_sample_task(
            "contestation_review",
            "Societal Alignment",
            samples=4,
            article="Art. 6, II-III",
            scope="high_risk",
        ),
        ["1.0", "1.0", "0.0", "0.0"],
    )
    return build_brazil_report(log_dir)


class TestJudgeAggregation:
    """Both scores reach ``TaskScore``, and the deterministic one is still the headline."""

    def test_the_headline_is_the_deterministic_score_despite_the_judge_being_first(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        by_task = {t.task: t for t in judge_report.brazil_task_scores}
        row = by_task["explanation_quality"]
        assert row.metric_name == "mean"
        assert row.score == pytest.approx(_DETERMINISTIC_MEAN)
        assert row.stderr == pytest.approx(_DETERMINISTIC_SE)

    def test_the_per_article_table_shows_the_deterministic_score(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        """The end-to-end form of the same guarantee, through the rendered artifact."""
        md = judge_report.to_markdown()
        assert "| Art. 6, I | high_risk | `explanation_quality` | Interpretability | 0.750 ± 0.250 |" in md

    def test_the_judge_score_is_read_from_the_judge_scorer(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        row = {t.task: t for t in judge_report.brazil_task_scores}["explanation_quality"]
        assert row.has_judge
        assert row.judge_metric_name == "accuracy"
        assert row.judge_score == pytest.approx(_JUDGE_ACCURACY)
        assert row.judge_stderr == pytest.approx(_JUDGE_SE)

    def test_the_delta_and_its_propagated_error(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        row = {t.task: t for t in judge_report.brazil_task_scores}["explanation_quality"]
        assert row.judge_delta == pytest.approx(_DETERMINISTIC_MEAN - _JUDGE_ACCURACY)
        assert row.judge_delta_stderr == pytest.approx(
            math.sqrt(_DETERMINISTIC_SE**2 + _JUDGE_SE**2)
        )

    def test_a_task_without_a_judge_carries_none(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        row = {t.task: t for t in judge_report.brazil_task_scores}["contestation_review"]
        assert not row.has_judge
        assert row.judge_score is None
        assert row.judge_delta is None
        assert row.judge_delta_stderr is None

    def test_judge_rows_holds_only_the_judged_tasks(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        assert [t.task for t in judge_report.judge_rows] == ["explanation_quality"]

    def test_the_grader_comes_from_the_bound_role_not_the_declared_default(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        """A header claiming Opus graded a mock-graded run would be a lie in a published
        artifact, so the bound role wins over the scorer's declared default."""
        row = {t.task: t for t in judge_report.brazil_task_scores}["explanation_quality"]
        assert row.judge_grader == "mockllm/model"
        assert row.judge_grader_config == "grader_temperature=0.0, grader_seed=42"

    def test_the_declared_grader_is_used_when_no_role_was_bound(self) -> None:
        """The real-run case: the CLI leaves the role unbound and the scorer resolves its pinned
        default, which its params record verbatim."""

        class _Spec:
            model_roles = None

        class _Log:
            eval = _Spec()

        judge = _StubScore(JUDGE_SCORER_NAME, accuracy=0.2)
        judge.params = {
            "grader": JUDGE_GRADER,
            "grader_temperature": 0.0,
            "grader_seed": 42,
        }
        grader, config = _judge_grader_from_log(_Log(), judge)  # type: ignore[arg-type]
        assert grader == JUDGE_GRADER
        assert config == "grader_temperature=0.0, grader_seed=42"

    def test_the_split_label_rides_in_from_the_task_args(self, tmp_path: Path) -> None:
        """Resolution 1 reports held-out and full-set agreement separately, **always labelled**,
        so the label has to come off the artifact rather than off the operator's memory."""
        log_dir = str(tmp_path / "split_logs")
        grader = get_model(
            "mockllm/model",
            custom_outputs=[ModelOutput.from_content("mockllm/model", "GRADE: C")] * 4,
        )
        logs = inspect_eval(
            explanation_quality(split=SPLIT_HELD_OUT, judge=True),
            model="mockllm/model",
            model_roles={"grader": grader},
            display="none",
            log_dir=log_dir,
        )
        assert logs[0].status == "success", logs[0].error
        report = build_brazil_report(log_dir)
        row = report.judge_rows[0]
        assert row.split == SPLIT_HELD_OUT
        assert row.total_samples == 4
        assert "| `explanation_quality` | held_out | 4 |" in report.to_markdown()


class TestJudgeRendering:
    """The section renders in all three views, states the scales, and names the grader."""

    def test_markdown_renders_the_table(self, judge_report: BrazilComplianceReport) -> None:
        md = judge_report.to_markdown()
        assert "## Deterministic vs. LLM-judge (held-out)" in md
        assert (
            "| `explanation_quality` | — | 4 | 0.750 ± 0.250 | 0.250 ± 0.250 | +0.500 ± 0.354 |"
            in md
        )

    def test_markdown_names_the_grader_and_its_config(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        """"Reproducible from the artifact alone" — the number is worthless without the grader."""
        md = judge_report.to_markdown()
        assert "**Grader:** `mockllm/model` at `grader_temperature=0.0, grader_seed=42`" in md
        assert "bound as model role `grader`" in md

    def test_markdown_says_the_two_columns_are_different_measures(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        """The one sentence that stops the delta being read as an error rate."""
        md = judge_report.to_markdown()
        assert (
            "**The two columns are different measures on the same 0-1 range, not two estimates "
            "of one quantity.**" in md
        )
        assert "mean *fraction of rubric elements* detected" in md
        assert "*fraction of replies graded `C`*" in md
        assert "It is not an error, not a disagreement rate, and not a correction." in md

    def test_markdown_says_the_delta_error_is_an_upper_bound(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        md = judge_report.to_markdown()
        assert "**Δ's error bar is an upper bound.**" in md
        assert "same samples in the same run" in md

    def test_markdown_omits_the_section_when_no_judge_ran(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        assert "LLM-judge" not in sector_report.to_markdown()

    def test_markdown_section_order_is_fixed(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        md = judge_report.to_markdown()
        assert (
            md.index("## EU ↔ Brazil side-by-side")
            < md.index("## Deterministic vs. LLM-judge (held-out)")
            < md.index("## Brazil compliance coverage map (9 requirements)")
        )

    def test_json_carries_the_judge_rows(self, judge_report: BrazilComplianceReport) -> None:
        data = json.loads(judge_report.to_json())
        rows = {row["task"]: row for row in data["deterministic_vs_judge"]}
        assert set(rows) == {"explanation_quality"}
        row = rows["explanation_quality"]
        assert row["deterministic_score"] == pytest.approx(_DETERMINISTIC_MEAN)
        assert row["deterministic_metric"] == "mean"
        assert row["judge_score"] == pytest.approx(_JUDGE_ACCURACY)
        assert row["judge_metric"] == "accuracy"
        assert row["judge_grader"] == "mockllm/model"
        assert row["judge_grader_config"] == "grader_temperature=0.0, grader_seed=42"
        assert row["delta"] == pytest.approx(0.5)
        assert row["delta_stderr_is_upper_bound"] is True

    def test_json_judge_rows_are_empty_when_no_judge_ran(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        assert json.loads(sector_report.to_json())["deterministic_vs_judge"] == []

    def test_html_renders_the_section(self, judge_report: BrazilComplianceReport) -> None:
        doc = judge_report.to_html()
        assert "<h2>Deterministic vs. LLM-judge (held-out)</h2>" in doc
        assert '<span class="badge warn">0.750</span> <span class="se">± 0.250<' in doc
        assert '<span class="badge bad">0.250</span> <span class="se">± 0.250<' in doc
        assert '<span class="badge good">+0.500</span> <span class="se">± 0.354<' in doc

    def test_html_names_the_grader(self, judge_report: BrazilComplianceReport) -> None:
        doc = judge_report.to_html()
        assert "<strong>Grader:</strong> <code>mockllm/model</code>" in doc

    def test_html_stays_self_contained_with_the_judge_section(
        self, judge_report: BrazilComplianceReport
    ) -> None:
        doc = judge_report.to_html()
        assert "src=" not in doc
        assert "href=" not in doc
        assert "http://" not in doc
        assert "https://" not in doc

    def test_html_omits_the_section_when_no_judge_ran(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        assert "LLM-judge" not in sector_report.to_html()


class TestPerSectorGapItemsInTheReport:
    """Resolution 11 — the JSON per-sector gap list, carried in from Phase 5."""

    def test_the_parser_reads_the_attrib_format(self) -> None:
        parsed = _gap_items_by_sector_from_attribs(
            {"brazil_gap_items_by_sector": "finance_bacen:a|b;capital_cvm:c"}
        )
        assert parsed == {"finance_bacen": ("a", "b"), "capital_cvm": ("c",)}

    def test_a_pre_phase_6_log_has_no_mapping(self) -> None:
        assert _gap_items_by_sector_from_attribs({"brazil_gap_items": "a,b"}) == {}
        assert _gap_items_by_sector_from_attribs({}) == {}

    def test_malformed_entries_are_skipped_rather_than_raising(self) -> None:
        parsed = _gap_items_by_sector_from_attribs(
            {"brazil_gap_items_by_sector": ";finance_bacen:a;garbage;health_anvisa:"}
        )
        assert parsed == {"finance_bacen": ("a",)}

    def test_each_sector_gets_only_its_own_gap_items(self, tmp_path: Path) -> None:
        """The bug, and the fix: ``health_anvisa`` has no gap item and must list none."""
        log_dir = str(tmp_path / "per_sector_gap_logs")
        _run_samples_into(
            log_dir,
            _sector_task_with_per_sector_gaps(
                "aia_checklist",
                ["finance_bacen"] * 2 + ["health_anvisa"] * 2,
            ),
            ["1.0", "0.0", "1.0", "0.0"],
        )
        report = build_brazil_report(log_dir)
        finance = report.sector_for("finance_bacen")
        health = report.sector_for("health_anvisa")
        assert finance is not None and health is not None
        assert finance.gap_items == ("human_review_gap_lgpd20",)
        assert health.gap_items == ()
        overlay = {
            entry["sector"]: entry
            for entry in json.loads(report.to_json())["sector_overlay"]
        }
        assert overlay["finance_bacen"]["gap_items"] == ["human_review_gap_lgpd20"]
        assert overlay["health_anvisa"]["gap_items"] == []

    def test_a_pre_phase_6_log_keeps_its_documented_imprecision(
        self, sector_report: BrazilComplianceReport
    ) -> None:
        """The fallback is deliberate: the per-sector split genuinely is not in an older log, and
        inventing one would be worse than reproducing what that log actually recorded."""
        health = sector_report.sector_for("health_anvisa")
        assert health is not None
        assert health.gap_items == tuple(sorted(_GAP_ITEMS_FIXTURE.split(",")))


# =========================================================================================
# Phase 7 — the sample-level layer, and the header-only guarantee it must not break.
# =========================================================================================
def _record(
    *,
    task: str = "explanation_quality",
    sample_id: str = "1",
    epoch: int = 1,
    deterministic: float | None = None,
    judge: float | None = None,
    split: str | None = SPLIT_HELD_OUT,
    elements: dict[str, bool] | None = None,
    judge_explanation: str | None = None,
    grader: str | None = "mockllm/model",
) -> SampleRecord:
    """A hand-built :class:`SampleRecord` for the pure agreement-arithmetic tests."""
    scores: dict[str, float | None] = {}
    metadata: dict[str, dict[str, Any]] = {}
    explanations: dict[str, str | None] = {}
    if deterministic is not None:
        scores["rubric_scorer"] = deterministic
        metadata["rubric_scorer"] = {"elements_present": dict(elements or {})}
        explanations["rubric_scorer"] = None
    if judge is not None:
        scores[JUDGE_SCORER_NAME] = judge
        metadata[JUDGE_SCORER_NAME] = {"judge_grader": grader} if grader else {}
        explanations[JUDGE_SCORER_NAME] = judge_explanation
    return SampleRecord(
        task=task,
        sample_id=sample_id,
        epoch=epoch,
        model="mockllm/model",
        prompt="p",
        completion="c",
        target="t",
        choices=(),
        scores=scores,
        raw_scores=dict(scores),
        answers={name: None for name in scores},
        explanations=explanations,
        score_metadata=metadata,
        metadata={"split": split} if split else {},
    )


class TestSampleSorting:
    """"The lowest ``sample_id``" is a rule, so its ordering has to be one too."""

    def test_integer_ids_sort_numerically(self) -> None:
        assert sorted(["10", "9", "2"], key=sample_sort_key) == ["2", "9", "10"]

    def test_string_ids_sort_lexicographically_after_integer_ids(self) -> None:
        assert sorted(["Race_010", "3", "Class_001"], key=sample_sort_key) == [
            "3",
            "Class_001",
            "Race_010",
        ]


class TestSpearman:
    """The correlation is hand-rolled, so it is checked against ``scipy.stats``."""

    @pytest.mark.parametrize(
        "xs,ys",
        [
            ([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0]),
            ([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]),
            ([0.0, 0.5, 0.5, 1.0], [0.0, 1.0, 0.5, 0.5]),  # ties on both sides
            ([0.1, 0.9, 0.4, 0.4, 0.2], [1.0, 0.0, 0.5, 0.5, 0.5]),
        ],
    )
    def test_matches_scipy(self, xs: list[float], ys: list[float]) -> None:
        from scipy.stats import spearmanr

        expected = float(spearmanr(xs, ys).statistic)
        actual = spearman(xs, ys)
        assert actual is not None
        assert actual == pytest.approx(expected)

    def test_undefined_rather_than_zero_when_a_side_is_constant(self) -> None:
        """``mockllm/model`` answers identically every time, so this is the normal mock case —
        printing ``0.000`` would be reporting a correlation nothing measured."""
        assert spearman([0.5, 0.5, 0.5], [0.0, 0.5, 1.0]) is None

    def test_undefined_below_two_pairs(self) -> None:
        assert spearman([1.0], [1.0]) is None
        assert spearman([], []) is None


class TestJudgeVerdictParsing:
    """Phase 6 makes the grader write per-element verdicts; this is what reads them back."""

    def test_parses_the_required_format(self) -> None:
        verdicts = parse_judge_verdicts(
            "- criteria_used: SUBSTANTIVE — a ratio of 45% is named.\n"
            "- data_considered: ABSENT — no source identified.\n"
            "SUBSTANTIVE COUNT: 1/2\n"
            "GRADE: P\n",
            ["criteria_used", "data_considered"],
        )
        assert verdicts.elements == {"criteria_used": True, "data_considered": False}
        assert (verdicts.stated_count, verdicts.stated_total) == (1, 2)
        assert verdicts.count_matches_verdicts is True

    def test_tolerates_decoration_a_real_grader_adds(self) -> None:
        """Numbered, bolded, backticked, plain hyphen instead of em dash — all still the format
        the instructions asked for, and refusing them would report a grader failure that is not
        one."""
        verdicts = parse_judge_verdicts(
            "1. **criteria_used**: SUBSTANTIVE - named.\n"
            "  * `data_considered` : ABSENT – nothing.\n",
            ["criteria_used", "data_considered"],
        )
        assert verdicts.elements == {"criteria_used": True, "data_considered": False}

    def test_an_invented_key_is_reported_not_believed(self) -> None:
        verdicts = parse_judge_verdicts(
            "- criteria_used: SUBSTANTIVE — ok.\n- fairness_vibes: SUBSTANTIVE — ok.\n",
            ["criteria_used"],
        )
        assert verdicts.elements == {"criteria_used": True}
        assert verdicts.unmatched_keys == ("fairness_vibes",)

    def test_the_first_verdict_for_an_element_wins(self) -> None:
        """Stated rather than "last wins", so the parse cannot depend on how chatty the grader
        was in its closing summary."""
        verdicts = parse_judge_verdicts(
            "- criteria_used: ABSENT — nothing.\nIn summary:\n- criteria_used: SUBSTANTIVE — ok.\n",
            ["criteria_used"],
        )
        assert verdicts.elements == {"criteria_used": False}

    def test_a_count_contradicting_the_verdicts_is_detected(self) -> None:
        """The letter is defined as a function of the count, so this means the grade does not
        follow from the grader's own stated findings."""
        verdicts = parse_judge_verdicts(
            "- criteria_used: ABSENT — nothing.\nSUBSTANTIVE COUNT: 6/6\nGRADE: C\n",
            ["criteria_used"],
        )
        assert verdicts.count_matches_verdicts is False

    def test_no_explanation_parses_to_nothing(self) -> None:
        assert not parse_judge_verdicts(None, ["criteria_used"]).parsed
        assert not parse_judge_verdicts("GRADE: C", ["criteria_used"]).parsed


class TestJudgeAgreement:
    """The statistics themselves, on hand-built records with hand-computable answers."""

    def test_mean_absolute_and_signed_delta(self) -> None:
        stats = judge_agreement(
            [
                _record(sample_id="1", deterministic=1.0, judge=0.0),
                _record(sample_id="2", deterministic=0.5, judge=1.0),
                _record(sample_id="3", deterministic=0.5, judge=0.5),
            ]
        )
        assert stats.n == 3
        assert stats.mean_abs_delta == pytest.approx((1.0 + 0.5 + 0.0) / 3)
        assert stats.mean_delta == pytest.approx((1.0 - 0.5 + 0.0) / 3)

    def test_direction_disagreements_are_opposite_sides_of_the_midpoint(self) -> None:
        stats = judge_agreement(
            [
                _record(sample_id="1", deterministic=1.0, judge=0.0),   # opposite sides
                _record(sample_id="2", deterministic=0.0, judge=1.0),   # opposite sides
                _record(sample_id="3", deterministic=1.0, judge=0.75),  # same side
                _record(sample_id="4", deterministic=1.0, judge=0.5),   # midpoint: never counted
            ]
        )
        assert stats.direction_disagreements == 2

    def test_the_sign_breakdown_is_reported_alongside(self) -> None:
        """"Disagree in direction" has two reasonable readings; both are reported rather than
        one being silently chosen."""
        stats = judge_agreement(
            [
                _record(sample_id="1", deterministic=1.0, judge=0.0),
                _record(sample_id="2", deterministic=0.0, judge=1.0),
                _record(sample_id="3", deterministic=0.5, judge=0.5),
            ]
        )
        assert (stats.deterministic_higher, stats.judge_higher, stats.ties) == (1, 1, 1)

    def test_epochs_are_reduced_per_sample_by_the_mean(self) -> None:
        """Phases 8-9 run ``--epochs 10``. Counting each generation as a sample would inflate
        ``n`` tenfold; the mean is what Inspect's own default reducer applies before the headline
        metric, so the two figures stay comparable."""
        stats = judge_agreement(
            [
                _record(sample_id="1", epoch=1, deterministic=1.0, judge=0.0),
                _record(sample_id="1", epoch=2, deterministic=0.0, judge=0.0),
            ]
        )
        assert stats.n == 1
        assert stats.n_rows == 2
        assert stats.mean_delta == pytest.approx(0.5)

    def test_a_sample_scored_by_only_one_scorer_is_excluded(self) -> None:
        stats = judge_agreement(
            [
                _record(sample_id="1", deterministic=1.0, judge=0.0),
                _record(sample_id="2", deterministic=1.0),
                _record(sample_id="3", judge=1.0),
            ]
        )
        assert stats.n == 1

    def test_an_empty_slice_is_well_formed_rather_than_an_exception(self) -> None:
        stats = judge_agreement([])
        assert (stats.n, stats.n_rows) == (0, 0)
        assert stats.mean_abs_delta is None and stats.spearman is None

    def test_per_element_agreement_is_the_finer_grained_answer(self) -> None:
        """Reviewer ask #2's real question. ``deterministic_only`` is the keyword-surface
        residue: the cue list credited the element, the judge did not."""
        explanation = (
            "- criteria_used: ABSENT — nothing named.\n"
            "- contestation_path: SUBSTANTIVE — channel, deadline and reviewer given.\n"
            "SUBSTANTIVE COUNT: 1/2\nGRADE: P\n"
        )
        stats = judge_agreement(
            [
                _record(
                    sample_id="1",
                    deterministic=1.0,
                    judge=0.5,
                    elements={"criteria_used": True, "contestation_path": True},
                    judge_explanation=explanation,
                )
            ]
        )
        by_element = {row.element: row for row in stats.element_agreement}
        assert by_element["criteria_used"].deterministic_only == 1
        assert by_element["criteria_used"].agreement_rate == pytest.approx(0.0)
        assert by_element["contestation_path"].both_credit == 1
        assert by_element["contestation_path"].agreement_rate == pytest.approx(1.0)

    def test_a_judge_row_with_no_verdict_lines_is_counted_as_a_grader_finding(self) -> None:
        stats = judge_agreement(
            [
                _record(
                    sample_id="1",
                    deterministic=1.0,
                    judge=0.0,
                    elements={"criteria_used": True},
                    judge_explanation="I think this is bad. GRADE: I",
                )
            ]
        )
        assert stats.judge_unparsed_rows == 1
        assert stats.element_agreement == ()


class TestJudgeAgreementSplits:
    """Resolution 1 — held-out **and** full set, both labelled, always."""

    def _records(self) -> list[SampleRecord]:
        return [
            _record(sample_id="1", deterministic=1.0, judge=0.0, split=SPLIT_HELD_OUT),
            _record(sample_id="2", deterministic=1.0, judge=1.0, split="train"),
            _record(
                task="contestation_review",
                sample_id="1",
                deterministic=0.5,
                judge=0.0,
                split=SPLIT_HELD_OUT,
            ),
        ]

    def test_both_slices_are_emitted_and_labelled(self) -> None:
        rows = judge_agreement_by_split(self._records())
        assert {row.label for row in rows} == {"full_set", "held_out"}

    def test_each_slice_carries_a_per_task_row_and_a_pooled_row(self) -> None:
        rows = judge_agreement_by_split(self._records())
        full = [row for row in rows if row.label == "full_set"]
        assert [row.task for row in full] == [
            "contestation_review",
            "explanation_quality",
            None,
        ]
        assert full[-1].n == 3

    def test_the_held_out_slice_excludes_train_samples(self) -> None:
        rows = judge_agreement_by_split(self._records())
        held_out = next(row for row in rows if row.label == "held_out" and row.task is None)
        assert held_out.n == 2

    def test_nothing_at_all_when_no_sample_was_judged(self) -> None:
        assert judge_agreement_by_split([_record(sample_id="1", deterministic=1.0)]) == []


class TestAgreementRendering:
    """The Markdown the ``--judge-agreement`` flag prints."""

    def test_names_both_slices_and_the_grader(self) -> None:
        md = render_agreement_markdown(
            [
                _record(sample_id="1", deterministic=1.0, judge=0.0),
                _record(sample_id="2", deterministic=0.0, judge=0.0, split="train"),
            ]
        )
        assert "| full_set |" in md
        assert "| held_out |" in md
        assert "**Grader:** `mockllm/model`" in md

    def test_states_that_the_two_columns_are_different_measures(self) -> None:
        """The standing cross-phase correction: the delta is between two *stated* measures and
        must never read as an error or a disagreement rate."""
        md = render_agreement_markdown([_record(deterministic=1.0, judge=0.0)])
        assert "different measures" in md
        assert "never an error and never a" in md

    def test_states_the_epoch_reduction_and_the_midpoint_rule(self) -> None:
        md = render_agreement_markdown([_record(deterministic=1.0, judge=0.0)])
        assert "Epochs are reduced per sample by the mean" in md
        assert "opposite sides of 0.5" in md

    def test_a_run_with_no_judge_says_so_instead_of_rendering_an_empty_table(self) -> None:
        md = render_agreement_markdown([_record(deterministic=1.0)])
        assert "No sample carries both" in md
        assert "|---|" not in md

    def test_the_bound_grader_role_wins_over_the_per_sample_stamp_for_display(self) -> None:
        """Same precedence the report header uses. The stamp alone renders as ``model`` for
        ``mockllm/model`` — true, but unreadable in a published artifact."""
        record = dataclasses.replace(
            _record(deterministic=1.0, judge=0.0, grader="model"),
            judge_grader_role="mockllm/model",
        )
        assert record.judge_grader == "model"
        assert record.judge_grader_display == "mockllm/model"
        assert "**Grader:** `mockllm/model`" in render_agreement_markdown([record])

    def test_the_format_compliance_count_is_not_double_counted_across_slices(self) -> None:
        """``held_out`` is a subset of ``full_set`` and both carry a pooled row, so summing them
        would report twice as many unparsed rows as the run has."""
        records = [
            _record(sample_id="1", deterministic=1.0, judge=0.0, split=SPLIT_HELD_OUT),
            _record(sample_id="2", deterministic=1.0, judge=0.0, split=SPLIT_HELD_OUT),
        ]
        md = render_agreement_markdown(records)
        assert "over the 2 judged row(s) of the full set): 2 carried no parsable" in md

    def test_the_json_view_names_both_scales(self) -> None:
        rows = agreement_to_dict([_record(deterministic=1.0, judge=0.0)])
        assert rows
        assert rows[0]["deterministic_measure"].startswith("mean fraction")
        assert rows[0]["judge_measure"].startswith("accuracy")


class TestHeaderOnlyGuarantee:
    """The default report path must never load samples — a property, not a comment.

    Two independent checks, because either alone is weak: a runtime spy proves *this* code path
    does not, and a source-level AST sweep proves no other call site in the package can.
    """

    def test_build_brazil_report_never_reads_samples(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log_dir = str(tmp_path / "header_only_logs")
        _run_samples_into(
            log_dir,
            _multi_sample_task(
                "explanation_quality",
                "Interpretability",
                samples=4,
                article="Art. 6, I",
                scope="high_risk",
            ),
            ["1.0", "1.0", "1.0", "0.0"],
        )

        import vigilai.report.brazil_report as brazil_report

        real = brazil_report.read_eval_log
        calls: list[bool] = []

        def spy(*args: Any, **kwargs: Any) -> Any:
            calls.append(bool(kwargs.get("header_only")))
            log = real(*args, **kwargs)
            assert log.samples is None, "the aggregator received a log carrying samples"
            return log

        monkeypatch.setattr(brazil_report, "read_eval_log", spy)
        build_brazil_report(log_dir)
        assert calls, "the spy never fired — the test is not exercising the read path"
        assert all(calls), "build_brazil_report read a log without header_only=True"

    def test_no_module_but_samples_py_loads_samples(self) -> None:
        """AST sweep of the whole package: every ``read_eval_log`` call outside
        ``vigilai/report/samples.py`` must pass ``header_only=True`` literally. This is the check
        that survives a future refactor moving the read somewhere else."""
        import ast

        package = Path(vigilai_report_samples.__file__).resolve().parents[2]
        offenders: list[str] = []
        for path in sorted(package.rglob("*.py")):
            if path.name == "samples.py" and path.parent.name == "report":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                if name not in {"read_eval_log", "read_eval_log_async", "read_eval_log_samples"}:
                    continue
                header_only = next(
                    (kw for kw in node.keywords if kw.arg == "header_only"), None
                )
                if (
                    header_only is None
                    or not isinstance(header_only.value, ast.Constant)
                    or header_only.value.value is not True
                ):
                    offenders.append(f"{path.relative_to(package)}:{node.lineno}")
        assert offenders == [], (
            "these call sites load samples outside vigilai/report/samples.py, which is "
            f"supposed to be the only one: {offenders}"
        )

    def test_the_samples_module_constants_mirror_the_task_modules(self) -> None:
        """Same discipline as the report's own constants: ``samples.py`` must not import the task
        package, so the strings are pinned against it instead."""
        assert samples_JUDGE_SCORER_NAME == JUDGE_SCORER_NAME
        assert set(DETERMINISTIC_SCORER_NAMES) == set(_DETERMINISTIC_SCORERS)
        assert samples_SPLIT_HELD_OUT == SPLIT_HELD_OUT


class TestLoadSamples:
    """The reader itself, over a real log."""

    def test_reads_prompt_completion_and_scores(self, tmp_path: Path) -> None:
        log_dir = str(tmp_path / "load_logs")
        _run_samples_into(
            log_dir,
            _multi_sample_task(
                "explanation_quality",
                "Interpretability",
                samples=2,
                article="Art. 6, I",
                scope="high_risk",
            ),
            ["0.25", "0.75"],
        )
        records = load_samples(log_dir)
        assert [r.task for r in records] == ["explanation_quality"] * 2
        assert {r.completion for r in records} == {"0.25", "0.75"}
        assert all(r.prompt == "q" for r in records)
        assert {r.deterministic_score for r in records} == {0.25, 0.75}
        assert all(r.model == "mockllm/model" for r in records)
        assert all(r.log_file and r.log_file.endswith(".eval") for r in records)

    def test_the_tasks_filter_selects(self, tmp_path: Path) -> None:
        log_dir = str(tmp_path / "filter_logs")
        for name, article in (("explanation_quality", "Art. 6, I"), ("bold", "Art. 5, III")):
            _run_samples_into(
                log_dir,
                _multi_sample_task(
                    name,
                    "Interpretability",
                    samples=2,
                    article=article,
                    scope="high_risk",
                ),
                ["0.5", "0.5"],
            )
        assert {r.task for r in load_samples(log_dir)} == {"explanation_quality", "bold"}
        assert {r.task for r in load_samples(log_dir, tasks=["bold"])} == {"bold"}
        assert load_samples(log_dir, tasks=["nope"]) == []

    def test_every_epoch_is_returned_and_first_epoch_filters(self, tmp_path: Path) -> None:
        """``--epochs 10`` is Phase 8's config, so multi-epoch logs are the normal case and the
        reader must not quietly keep one row per id."""
        log_dir = str(tmp_path / "epoch_logs")
        a_task = _multi_sample_task(
            "explanation_quality",
            "Interpretability",
            samples=2,
            article="Art. 6, I",
            scope="high_risk",
        )
        model = get_model(
            "mockllm/model",
            custom_outputs=[ModelOutput.from_content("mockllm/model", "0.5") for _ in range(4)],
        )
        logs = inspect_eval(a_task, model=model, epochs=2, display="none", log_dir=log_dir)
        assert logs[0].status == "success", logs[0].error
        records = load_samples(log_dir)
        assert len(records) == 4
        assert sorted(r.epoch for r in records) == [1, 1, 2, 2]
        assert len(first_epoch(records)) == 2

    def test_records_are_sorted_deterministically(self, tmp_path: Path) -> None:
        log_dir = str(tmp_path / "sorted_logs")
        _run_samples_into(
            log_dir,
            _multi_sample_task(
                "explanation_quality",
                "Interpretability",
                samples=12,
                article="Art. 6, I",
                scope="high_risk",
            ),
            ["0.5"] * 12,
        )
        ids = [r.sample_id for r in load_samples(log_dir)]
        assert ids == [str(i) for i in range(1, 13)]  # 2 before 10, not after


class TestJudgeAgreementCli:
    """``vigilai report --judge-agreement`` — the flag, its exclusions, and its slowness."""

    def test_the_flag_appends_the_section_to_the_markdown_report(
        self, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        log_dir = str(tmp_path / "cli_judge_logs")
        _build_cli_judge_log_dir(log_dir)
        result = runner.invoke(cli_app, ["report", log_dir, "--judge-agreement"])
        assert result.exit_code == 0, result.output
        assert "## Compliance by Brazil article" in result.output
        assert "## Per-sample deterministic ↔ LLM-judge agreement" in result.output
        assert "| full_set |" in result.output

    def test_the_default_report_is_unchanged_without_the_flag(self, tmp_path: Path) -> None:
        runner = CliRunner()
        log_dir = str(tmp_path / "cli_default_logs")
        _build_cli_judge_log_dir(log_dir)
        plain = runner.invoke(cli_app, ["report", log_dir])
        assert plain.exit_code == 0, plain.output
        assert "Per-sample deterministic" not in plain.output
        assert plain.output.strip() == build_brazil_report(log_dir).to_markdown().strip()

    def test_json_gains_exactly_one_additive_key(self, tmp_path: Path) -> None:
        runner = CliRunner()
        log_dir = str(tmp_path / "cli_json_logs")
        _build_cli_judge_log_dir(log_dir)
        plain = json.loads(runner.invoke(cli_app, ["report", log_dir, "--json"]).output)
        with_flag = json.loads(
            runner.invoke(
                cli_app, ["report", log_dir, "--json", "--judge-agreement"]
            ).output
        )
        assert set(with_flag) - set(plain) == {"judge_agreement"}
        assert {row["slice"] for row in with_flag["judge_agreement"]} == {
            "full_set",
            "held_out",
        }

    def test_it_is_refused_with_html_for_a_stated_reason(self, tmp_path: Path) -> None:
        """Resolution 5(c)'s reasoning: the scorecard stands alone as the Art. 28 public
        conclusions, and scorer agreement is paper evidence, not a compliance conclusion."""
        runner = CliRunner()
        log_dir = str(tmp_path / "cli_html_logs")
        _build_cli_judge_log_dir(log_dir)
        result = runner.invoke(cli_app, ["report", log_dir, "--html", "--judge-agreement"])
        assert result.exit_code != 0
        assert "Art. 28" in result.output

    def test_json_and_html_stay_mutually_exclusive(self, tmp_path: Path) -> None:
        runner = CliRunner()
        log_dir = str(tmp_path / "cli_excl_logs")
        _build_cli_judge_log_dir(log_dir)
        result = runner.invoke(cli_app, ["report", log_dir, "--json", "--html"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_the_flag_is_documented_as_slower_than_the_default(self) -> None:
        runner = CliRunner()
        help_text = runner.invoke(cli_app, ["report", "--help"]).output
        assert "--judge-agreement" in help_text
        assert "SLOWER" in help_text or "slower" in help_text


def _build_cli_judge_log_dir(log_dir: str) -> None:
    """A two-sample judged run: one held-out sample and one training sample."""
    subject = get_model(
        "mockllm/model",
        custom_outputs=[ModelOutput.from_content("mockllm/model", "1.0") for _ in range(2)],
    )
    grader = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content(
                "mockllm/model",
                "- criteria_used: ABSENT — nothing.\nSUBSTANTIVE COUNT: 0/1\nGRADE: I",
            )
            for _ in range(2)
        ],
    )

    @task(
        name="explanation_quality",
        technical_requirement="Interpretability",
        brazil_article="Art. 6, I",
        brazil_scope="high_risk",
    )
    def _t() -> Task:
        return Task(
            dataset=MemoryDataset(
                [
                    Sample(input="q", target="n/a", metadata={"split": SPLIT_HELD_OUT}),
                    Sample(input="q", target="n/a", metadata={"split": "train"}),
                ]
            ),
            solver=[generate()],
            scorer=[
                _fraction_scorer(),
                judge_scorer(
                    instructions="stub",
                    grader=JUDGE_GRADER,
                    grader_temperature=JUDGE_GRADER_TEMPERATURE,
                    grader_seed=JUDGE_GRADER_SEED,
                ),
            ],
        )

    logs = inspect_eval(
        _t(),
        model=subject,
        model_roles={"grader": grader},
        display="none",
        log_dir=log_dir,
    )
    assert logs[0].status == "success", logs[0].error
