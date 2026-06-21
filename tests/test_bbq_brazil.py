"""Tests for the Brazil PL 2338/2023 Art. 5, III Brazil-adapted BBQ benchmark (Phase 4).

Covers the three things the structure outline requires:

1. The in-code dataset contains all three category groups — ``Race_IBGE``, ``Region`` and
   ``Intersectional`` — built from the research §9 Brazilian demographic terms.
2. Every *ambiguous*-context sample targets the Unknown-equivalent answer (a fair model must
   answer "não é possível determinar" rather than fall back on a stereotype).
3. The benchmark reuses the upstream BBQ scoring path (the ``multiple_choice()`` solver +
   ``choice()`` scorer) and that scorer flags a *stereotyped* answer as biased (incorrect) —
   verified by running the actual task end-to-end against a mock model that emits the
   stereotyped letter, so the real (reused) scorer is exercised through the real pipeline.
   A symmetric check confirms the correct (Unknown) answer is scored correct.

The benchmark is deterministic and offline (no Hugging Face download), so these tests need
no network access.
"""

from __future__ import annotations

from inspect_ai import eval as inspect_eval
from inspect_ai import Task
from inspect_ai.dataset import MemoryDataset
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import choice
from inspect_ai.scorer import CORRECT
from inspect_ai.scorer import INCORRECT
from inspect_ai.solver import multiple_choice

from vigilai.tasks.bbq_brazil.bbq_brazil import bbq_brazil
from vigilai.tasks.bbq_brazil.dataset import ALL_SCENARIOS
from vigilai.tasks.bbq_brazil.dataset import bbq_brazil_dataset
from vigilai.tasks.bbq_brazil.dataset import bbq_brazil_samples
from vigilai.tasks.bbq_brazil.dataset import CATEGORY_INTERSECTIONAL
from vigilai.tasks.bbq_brazil.dataset import CATEGORY_RACE
from vigilai.tasks.bbq_brazil.dataset import CATEGORY_REGION
from vigilai.tasks.bbq_brazil.dataset import UNKNOWN_ANSWER


def _categories_present() -> set[str]:
    return {str(sample.metadata["category"]) for sample in bbq_brazil_samples()}


def _ambiguous_samples() -> list[Sample]:
    return [
        sample
        for sample in bbq_brazil_samples()
        if sample.metadata is not None
        and sample.metadata.get("context_condition") == "ambiguous"
    ]


def _single_sample_eval(sample: Sample, answer_letter: str) -> float:
    """Run the reused BBQ scoring path on one sample with a forced model answer.

    Builds a one-sample task with the *same* solver/scorer the real ``bbq_brazil`` task uses
    (``multiple_choice()`` + ``choice()``), drives it with a mock model that emits
    ``ANSWER: <answer_letter>``, and returns the resulting accuracy. A one-sample dataset
    guarantees the forced output aligns with the sample (no ordering ambiguity).
    """
    task = Task(
        dataset=MemoryDataset([sample]),
        solver=[multiple_choice()],
        scorer=choice(),
    )
    model = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content("mockllm/model", f"ANSWER: {answer_letter}")
        ],
    )
    logs = inspect_eval(task, model=model, display="none")
    log = logs[0]
    assert log.status == "success"
    assert log.results is not None
    return log.results.scores[0].metrics["accuracy"].value


class TestCategoryGroups:
    """All three Brazil category groups required by the outline must be present."""

    def test_dataset_is_non_empty(self) -> None:
        assert len(bbq_brazil_dataset()) > 0

    def test_all_three_category_groups_present(self) -> None:
        assert _categories_present() == {
            CATEGORY_RACE,
            CATEGORY_REGION,
            CATEGORY_INTERSECTIONAL,
        }

    def test_each_category_has_scenarios(self) -> None:
        for category in (CATEGORY_RACE, CATEGORY_REGION, CATEGORY_INTERSECTIONAL):
            assert any(s.category == category for s in ALL_SCENARIOS), category

    def test_ibge_race_terms_present(self) -> None:
        """The IBGE 'cor ou raça' taxonomy (research §9.1) must be exercised."""
        groups = {
            group
            for scenario in ALL_SCENARIOS
            for group in scenario.groups
        }
        # At least the core IBGE categories + the political term "negro" appear somewhere.
        for term in ("branco", "pardo", "preto", "negro", "indígena", "amarelo"):
            assert any(term in group for group in groups), term

    def test_regional_and_intersectional_terms_present(self) -> None:
        corpus = " ".join(
            str(sample.input) for sample in bbq_brazil_samples()
        )
        assert "nordestino" in corpus  # research §9.2 regional prejudice
        assert "mulher negra" in corpus  # research §9.5 intersectional


class TestPortugueseContent:
    """Samples are rendered in Portuguese with the BBQ Context/Question framing."""

    def test_samples_use_portuguese_framing(self) -> None:
        for sample in bbq_brazil_samples():
            text = str(sample.input)
            assert "Contexto:" in text
            assert "Pergunta:" in text

    def test_portuguese_diacritics_present(self) -> None:
        corpus = " ".join(str(sample.input) for sample in bbq_brazil_samples())
        assert any(ch in corpus for ch in "ãõáéíóúâêôàç")


class TestAmbiguousTargets:
    """Ambiguous-context samples target the Unknown-equivalent answer."""

    def test_ambiguous_samples_exist(self) -> None:
        assert _ambiguous_samples()

    def test_ambiguous_target_is_unknown_choice(self) -> None:
        for sample in _ambiguous_samples():
            assert sample.choices is not None
            # The target letter must point at the Unknown-equivalent choice text.
            target_letter = str(sample.target)
            target_index = ord(target_letter) - ord("A")
            assert sample.choices[target_index] == UNKNOWN_ANSWER

    def test_unknown_choice_is_present_in_every_sample(self) -> None:
        for sample in bbq_brazil_samples():
            assert sample.choices is not None
            assert UNKNOWN_ANSWER in sample.choices


class TestReusedScorerFlagsBias:
    """The reused BBQ scorer (multiple_choice + choice) flags a stereotyped answer as
    biased on ambiguous contexts, and accepts the Unknown answer — exercised through the
    real eval pipeline against a mock model."""

    def test_stereotyped_answer_is_scored_incorrect(self) -> None:
        ambiguous = _ambiguous_samples()
        assert ambiguous
        for sample in ambiguous:
            assert sample.metadata is not None
            stereotyped_letter = str(sample.metadata["stereotyped_answer"])
            # The stereotyped pick is, by construction, not the Unknown answer.
            assert stereotyped_letter != str(sample.target)
            accuracy = _single_sample_eval(sample, stereotyped_letter)
            # A biased (stereotyped) answer in an ambiguous context is wrong.
            assert accuracy == 0.0, sample.id

    def test_unknown_answer_is_scored_correct(self) -> None:
        ambiguous = _ambiguous_samples()
        assert ambiguous
        for sample in ambiguous:
            accuracy = _single_sample_eval(sample, str(sample.target))
            assert accuracy == 1.0, sample.id

    def test_full_task_runs_end_to_end_on_mock(self) -> None:
        """The full task (default solver/scorer) runs to success under the mock model."""
        task = bbq_brazil()
        logs = inspect_eval(task, model="mockllm/model", display="none", limit=10)
        log = logs[0]
        assert log.status == "success"
        assert log.results is not None


class TestTaskMetadata:
    """The task is constructible and tagged for Brazil Art. 5, III / all_ai (so
    vigilai list --brazil files it correctly). Decorator-vs-mapping agreement for the
    'Representation — Absence of Bias' requirement is covered in test_brazil_mapping."""

    def test_task_is_constructible(self) -> None:
        task = bbq_brazil()
        assert task.dataset is not None
        assert task.scorer is not None

    def test_disambiguated_samples_target_a_named_person(self) -> None:
        """Sanity check on the disambiguated half: target is a person choice (A or B),
        never the Unknown option."""
        for sample in bbq_brazil_samples():
            assert sample.metadata is not None
            if sample.metadata.get("context_condition") == "disambiguated":
                assert str(sample.target) in {"A", "B"}
