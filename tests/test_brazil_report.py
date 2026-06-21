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
from pathlib import Path

import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai import Task
from inspect_ai import task
from inspect_ai.dataset import MemoryDataset
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import match
from inspect_ai.scorer import mean
from inspect_ai.scorer import scorer
from inspect_ai.scorer import Score
from inspect_ai.scorer import stderr
from inspect_ai.solver import generate

from vigilai.report.brazil_report import build_brazil_report
from vigilai.report.brazil_report import BrazilComplianceReport
from vigilai.report.brazil_report import EU_BRAZIL_PAIRS


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
