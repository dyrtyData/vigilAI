"""Tests for the Brazil PL 2338/2023 Arts. 25-28 AIA-checklist benchmark (Phase 6).

This benchmark, like the Phase 5 ``explanation_quality`` one, has a **new custom scorer**, so
the centre of gravity is unit-testing the deterministic coverage detector directly, as the
structure outline requires:

* checklist items **load from the externalized data structure** (``AIA_CHECKLIST``), reflect
  research §5 (who conducts / timing / documentation / public conclusions / RIPD / incident),
  and the prompt is built from that same list;
* the scorer **counts covered items correctly** — a crafted full-coverage response scores 1.0,
  a sparse response scores low, and the score is exactly ``#covered / #items``;
* the scorer is genuinely **data-driven**: extending ``AIA_CHECKLIST`` (without touching the
  scorer/task code) makes the extra item scorable — this is the flexibility goal of Phase 6.

The pure helpers (``detect_items`` / ``score_checklist``) are exercised with no Inspect eval
pipeline and no model call. A separate end-to-end check drives the real ``aia_checklist`` task
through the real pipeline against ``mockllm/model`` with forced outputs, confirming the
``@scorer`` wrapper and metric wiring also work. The benchmark is deterministic and offline,
so none of this needs network access.
"""

from __future__ import annotations

import dataclasses

from inspect_ai import eval as inspect_eval
from inspect_ai import Task
from inspect_ai.dataset import MemoryDataset
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_ai.model import ModelOutput
from inspect_ai.solver import generate

from vigilai.tasks.aia_checklist.aia_checklist import aia_checklist
from vigilai.tasks.aia_checklist.aia_checklist import aia_checklist_dataset
from vigilai.tasks.aia_checklist.checklist import AIA_CHECKLIST
from vigilai.tasks.aia_checklist.checklist import aia_checklist_scorer
from vigilai.tasks.aia_checklist.checklist import AIAItem
from vigilai.tasks.aia_checklist.checklist import detect_items
from vigilai.tasks.aia_checklist.checklist import score_checklist


# A crafted, fully compliant pt-BR answer that covers all six seed checklist items: who
# conducts (Art. 25), timing (Art. 26), risk/benefit documentation (Art. 25 §1), public
# conclusions (Art. 28), RIPD joint preparation (Art. 27), and incident notification (Art. 25
# §7 / Art. 44).
FULL_COVERAGE_PT = """
A avaliação de impacto algorítmico (AIA) deve ser conduzida pelo desenvolvedor ou pelo
operador do sistema, conforme o seu papel na cadeia de IA. Ela precisa ser realizada antes da
colocação no mercado, de forma contínua ao longo do ciclo de vida e novamente após qualquer
mudança significativa no sistema. A avaliação documenta os riscos e os benefícios aos direitos
fundamentais, bem como as medidas de mitigação adotadas e a sua eficácia. As conclusões da
avaliação devem ser públicas, resguardados os segredos industrial e comercial. A AIA pode ser
elaborada em conjunto com o relatório de impacto à proteção de dados pessoais (RIPD) previsto
na LGPD. Em caso de incidente, é preciso notificar a autoridade competente, os agentes da
cadeia e as pessoas afetadas, alimentando a base de dados pública de IA de alto risco.
"""

# A crafted full-coverage answer in English, to prove the detector is multilingual rather than
# pt-BR-only.
FULL_COVERAGE_EN = """
The algorithmic impact assessment must be conducted by the developer or the applier depending
on their role in the AI chain. It must be performed before the system is placed on the market,
continuously across its lifecycle, and again after any significant change. The assessment
documents the risks and benefits to fundamental rights together with the mitigation measures
and their effectiveness. Its conclusions must be made public, trade secrets aside. The
assessment may be prepared jointly with the LGPD data protection impact report. After an
incident, the operator must notify the competent authority and the affected persons, feeding
the public database of high-risk AI.
"""

# A sparse, non-compliant answer that addresses none of the AIA obligations.
SPARSE_RESPONSE = "A inteligência artificial é uma tecnologia útil para muitas empresas."


class TestChecklistData:
    """The checklist is an externalized data structure reflecting research §5."""

    def test_checklist_is_non_empty(self) -> None:
        assert AIA_CHECKLIST

    def test_items_are_aia_item_instances(self) -> None:
        for item in AIA_CHECKLIST:
            assert isinstance(item, AIAItem)
            assert item.id and item.description and item.article
            assert item.any_of, f"{item.id} has no detection cue groups"

    def test_item_ids_are_unique(self) -> None:
        ids = [item.id for item in AIA_CHECKLIST]
        assert len(ids) == len(set(ids))

    def test_research_aia_obligations_are_represented(self) -> None:
        """The seed checklist covers the AIA obligations enumerated in research §5."""
        ids = {item.id for item in AIA_CHECKLIST}
        assert {
            "who_conducts",
            "timing",
            "risk_benefit_documentation",
            "public_conclusions",
            "ripd_joint_preparation",
            "incident_notification",
        } <= ids

    def test_items_cite_arts_25_to_28(self) -> None:
        """Every seed item is governed by one of Arts. 25-28 (the AIA articles)."""
        for item in AIA_CHECKLIST:
            assert "Art. 2" in item.article, item.id


class TestPromptBuiltFromChecklist:
    """The prompt is generated from the externalized checklist (single source of truth)."""

    def test_prompt_lists_every_item_description(self) -> None:
        dataset = aia_checklist_dataset()
        prompt = str(list(dataset)[0].input)
        for item in AIA_CHECKLIST:
            assert item.description in prompt, item.id

    def test_prompt_references_the_aia_articles(self) -> None:
        prompt = str(list(aia_checklist_dataset())[0].input)
        assert "2338" in prompt
        assert "25" in prompt and "28" in prompt

    def test_sample_metadata_records_expected_items(self) -> None:
        sample = list(aia_checklist_dataset())[0]
        assert sample.metadata is not None
        assert sample.metadata["expected_items"] == [item.id for item in AIA_CHECKLIST]


class TestPureScorer:
    """The pure detector/scorer count covered items correctly (no eval pipeline)."""

    def test_full_coverage_pt_covers_all_items(self) -> None:
        covered = detect_items(FULL_COVERAGE_PT)
        assert set(covered.keys()) == {item.id for item in AIA_CHECKLIST}
        missing = [item_id for item_id, ok in covered.items() if not ok]
        assert missing == [], f"unexpected missing items: {missing}"

    def test_full_coverage_pt_scores_one(self) -> None:
        assert score_checklist(FULL_COVERAGE_PT) == 1.0

    def test_full_coverage_en_scores_one(self) -> None:
        """Detection is multilingual: an English full answer also scores 1.0."""
        assert score_checklist(FULL_COVERAGE_EN) == 1.0

    def test_sparse_response_scores_low(self) -> None:
        score = score_checklist(SPARSE_RESPONSE)
        assert score < 0.5, score

    def test_empty_response_scores_zero(self) -> None:
        assert score_checklist("") == 0.0

    def test_score_is_fraction_of_items(self) -> None:
        """The score is exactly (#covered / #items) — fraction of checklist items covered."""
        for text in (FULL_COVERAGE_PT, SPARSE_RESPONSE, ""):
            covered = detect_items(text)
            num_covered = sum(1 for ok in covered.values() if ok)
            assert score_checklist(text) == num_covered / len(AIA_CHECKLIST)

    def test_partial_coverage_counts_exactly(self) -> None:
        """A response addressing only some items scores the matching fraction."""
        text = (
            "A avaliação deve ser feita pelo desenvolvedor antes da colocação no mercado."
        )
        covered = detect_items(text)
        # "desenvolvedor" -> who_conducts; "antes da colocacao no mercado" -> timing.
        assert covered["who_conducts"] is True
        assert covered["timing"] is True
        num_covered = sum(1 for ok in covered.values() if ok)
        assert score_checklist(text) == num_covered / len(AIA_CHECKLIST)


class TestDataDrivenExtensibility:
    """The scorer iterates whatever the checklist defines — the Phase 6 flexibility goal.

    Adding a (future ANPD) item to the checklist must make it scorable **without changing the
    scorer/task code**. We simulate that by passing an extended checklist to the same pure
    helpers and confirming the new item is detected and the denominator grows by one.
    """

    def test_extended_checklist_scores_new_item_without_code_change(self) -> None:
        new_item = AIAItem(
            id="future_anpd_item",
            article="ANPD Instrução Normativa (futura)",
            description="Item hipotético de uma futura Instrução Normativa da ANPD.",
            any_of=(("instrucao normativa futura",),),
        )
        extended = list(AIA_CHECKLIST) + [new_item]

        # The same scorer machinery now recognizes the extra item, purely from data.
        text = FULL_COVERAGE_PT + "\nAlém disso, cumprimos a instrução normativa futura."
        covered = detect_items(text, extended)
        assert covered["future_anpd_item"] is True
        # Denominator grew by one and a full answer + the new cue still scores 1.0.
        assert len(covered) == len(AIA_CHECKLIST) + 1
        assert score_checklist(text, extended) == 1.0

    def test_extended_checklist_lowers_score_when_new_item_absent(self) -> None:
        """With the extra item present in the checklist but absent from a response that
        otherwise covers the seed items, the score drops below 1.0 — proving the new item is
        actually part of the denominator."""
        new_item = AIAItem(
            id="future_anpd_item",
            article="ANPD Instrução Normativa (futura)",
            description="Item hipotético de uma futura Instrução Normativa da ANPD.",
            any_of=(("instrucao normativa futura",),),
        )
        extended = list(AIA_CHECKLIST) + [new_item]
        score = score_checklist(FULL_COVERAGE_PT, extended)
        assert score < 1.0
        assert score == len(AIA_CHECKLIST) / (len(AIA_CHECKLIST) + 1)

    def test_aia_item_is_a_plain_editable_dataclass(self) -> None:
        """An item is a frozen dataclass with exactly the editable fields — confirms the
        externalized format an editor would extend."""
        assert dataclasses.is_dataclass(AIAItem)
        field_names = {f.name for f in dataclasses.fields(AIAItem)}
        assert field_names == {"id", "article", "description", "any_of"}


def _single_sample_score(completion: str) -> float:
    """Run the real AIA scorer through the eval pipeline on one sample.

    Builds a one-sample task with the same scorer the real task uses, drives it with a mock
    model that emits ``completion``, and returns the resulting mean score. A one-sample
    dataset guarantees the forced output aligns with the sample.
    """
    sample = Sample(input="Explique a AIA.", target="n/a")
    task = Task(
        dataset=MemoryDataset([sample]),
        solver=[generate()],
        scorer=aia_checklist_scorer(),
    )
    model = get_model(
        "mockllm/model",
        custom_outputs=[ModelOutput.from_content("mockllm/model", completion)],
    )
    logs = inspect_eval(task, model=model, display="none")
    log = logs[0]
    assert log.status == "success"
    assert log.results is not None
    return log.results.scores[0].metrics["mean"].value


class TestScorerThroughPipeline:
    """The @scorer wrapper + metric wiring work end-to-end against the mock model."""

    def test_full_coverage_scores_one_through_pipeline(self) -> None:
        assert _single_sample_score(FULL_COVERAGE_PT) == 1.0

    def test_sparse_scores_low_through_pipeline(self) -> None:
        assert _single_sample_score(SPARSE_RESPONSE) < 0.5

    def test_full_task_runs_end_to_end_on_mock(self) -> None:
        """The full task (its solver + checklist scorer) runs to success under the mock
        model."""
        logs = inspect_eval(aia_checklist(), model="mockllm/model", display="none")
        log = logs[0]
        assert log.status == "success"
        assert log.results is not None


class TestTaskMetadata:
    """The task is constructible and tagged for Brazil Arts. 25-28 / high_risk.

    The decorator carries a per-task ``brazil_article`` for the EU-only "Societal Alignment"
    requirement (the AIA carve-out); the mapping-agreement invariant for this is covered in
    test_brazil_mapping.
    """

    def test_task_is_constructible(self) -> None:
        task = aia_checklist()
        assert task.dataset is not None
        assert task.scorer is not None
