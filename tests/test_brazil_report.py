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

from vigilai.report.brazil_report import _sector_metrics
from vigilai.report.brazil_report import _stderr_metric
from vigilai.report.brazil_report import ArticleGroup
from vigilai.report.brazil_report import build_brazil_report
from vigilai.report.brazil_report import BrazilComplianceReport
from vigilai.report.brazil_report import EU_BRAZIL_PAIRS
from vigilai.report.brazil_report import NINE_TECHNICAL_REQUIREMENTS
from vigilai.report.brazil_report import SideBySideRow
from vigilai.report.brazil_report import TaskScore


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
