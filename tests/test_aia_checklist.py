"""Tests for the Brazil PL 2338/2023 Arts. 25-28 AIA-checklist benchmark.

This benchmark, like the Phase 5 ``explanation_quality`` one, has a **new custom scorer**, so
the centre of gravity is unit-testing the deterministic coverage detector directly, as the
structure outline requires:

* checklist items **load from the externalized data structure** (``AIA_CHECKLIST`` for the
  cross-sector obligations, ``SECTOR_ITEMS`` for the overlays), reflect research §5 (who conducts
  / timing / documentation / public conclusions / RIPD / incident), and the prompt is built from
  that same list;
* the scorer **counts covered items correctly** — a crafted full-coverage response scores 1.0,
  a sparse response scores low, and the score is exactly ``#covered / #items``;
* the scorer is genuinely **data-driven**: extending the checklist (without touching the
  scorer/task code) makes the extra item scorable — this is the flexibility goal the phase exists
  to prove, and Phase 5 relies on it to append two sectors as pure data.

Iteration 2, Phase 4 adds four groups of checks:

* **the sector dimension end-to-end** — ``AIAItem.sector``, ``items_for_sector``, four finance
  deployer samples, per-sample item resolution, and the *exact* ``grouped()`` metric key names
  read out of a real mock log (``TestGroupedMetricKeys``) rather than assumed;
* **the cue audit** — hostile probes that used to score and must not any more
  (``TestOverBroadCuesAreFixed``), with the recall they were protecting pinned alongside;
* **the Q8 legal-verification gate**, as a test rather than a reading exercise: every sector item
  names an instrument, carries a primary-source URL, declares a sourcing tier, and appears in
  ``docs/sector-overlay-legal-verification.md`` (``TestLegalVerificationGate``);
* **two measured properties that would otherwise be assertions** — a per-sector reference answer
  the real scorer must score 1.0 (so "every item is answerable" is proved, not hoped), and the
  **prompt-echo floor**, pinned so Phase 8 knows exactly how much of an ``aia_checklist`` score
  is the topic list coming back.

The pure helpers (``detect_items`` / ``score_checklist``) are exercised with no Inspect eval
pipeline and no model call. A separate end-to-end check drives the real ``aia_checklist`` task
through the real pipeline against ``mockllm/model`` with forced outputs, confirming the
``@scorer`` wrapper and metric wiring also work. The benchmark is deterministic and offline,
so none of this needs network access.
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest
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
from vigilai.tasks.aia_checklist.checklist import ALL_AIA_ITEMS
from vigilai.tasks.aia_checklist.checklist import detect_items
from vigilai.tasks.aia_checklist.checklist import FINANCE_ITEMS
from vigilai.tasks.aia_checklist.checklist import GAP_ITEM_IDS
from vigilai.tasks.aia_checklist.checklist import items_for_sector
from vigilai.tasks.aia_checklist.checklist import ITEM_GAP
from vigilai.tasks.aia_checklist.checklist import ITEM_STATUSES
from vigilai.tasks.aia_checklist.checklist import score_checklist
from vigilai.tasks.aia_checklist.checklist import SECTOR_CAPITAL
from vigilai.tasks.aia_checklist.checklist import SECTOR_FINANCE
from vigilai.tasks.aia_checklist.checklist import SECTOR_HEALTH
from vigilai.tasks.aia_checklist.checklist import SECTOR_ITEMS
from vigilai.tasks.aia_checklist.checklist import SECTOR_REFERENCE_ANSWERS
from vigilai.tasks.aia_checklist.checklist import SECTOR_REGIME_PT
from vigilai.tasks.aia_checklist.checklist import SECTORS
from vigilai.tasks.aia_checklist.checklist import SOURCING_TIERS
from vigilai.tasks.aia_checklist.scenario import AIA_SCENARIOS
from vigilai.tasks.aia_checklist.scenario import aia_scenarios
from vigilai.tasks.aia_checklist.scenario import DEPLOYER_PROVENANCE_PREFIX
from vigilai.tasks.aia_checklist.scenario import PROMPT_MODE_GUIDED
from vigilai.tasks.aia_checklist.scenario import PROMPT_MODE_UNGUIDED
from vigilai.tasks.aia_checklist.scenario import PROMPT_MODES
from vigilai.tasks.aia_checklist.scenario import resolve_prompt_mode
from vigilai.tasks.rubric_scenario import SPLIT_ALL
from vigilai.tasks.rubric_scenario import SPLIT_HELD_OUT
from vigilai.tasks.rubric_scenario import SPLIT_TRAIN


# A crafted, fully compliant pt-BR answer that covers all six cross-sector checklist items: who
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

# The Q8 verification record every sector item must appear in.
_VERIFICATION_DOC = (
    Path(__file__).resolve().parents[1] / "docs" / "sector-overlay-legal-verification.md"
)


class TestChecklistData:
    """The checklist is an externalized data structure reflecting research §5."""

    def test_checklist_is_non_empty(self) -> None:
        assert AIA_CHECKLIST

    def test_items_are_aia_item_instances(self) -> None:
        for item in ALL_AIA_ITEMS:
            assert isinstance(item, AIAItem)
            assert item.id and item.description and item.article
            assert item.any_of, f"{item.id} has no detection cue groups"

    def test_item_ids_are_unique(self) -> None:
        ids = [item.id for item in ALL_AIA_ITEMS]
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
        """Every cross-sector seed item is governed by one of Arts. 25-28 (the AIA articles)."""
        for item in AIA_CHECKLIST:
            assert "Art. 2" in item.article, item.id

    def test_cross_sector_items_carry_no_sector(self) -> None:
        for item in AIA_CHECKLIST:
            assert item.sector is None, item.id


class TestSectorVocabulary:
    """The sector dimension's vocabulary and the item partition it induces."""

    def test_sectors_are_the_three_regulators(self) -> None:
        assert SECTORS == (SECTOR_FINANCE, SECTOR_HEALTH, SECTOR_CAPITAL)
        assert SECTORS == ("finance_bacen", "health_anvisa", "capital_cvm")

    def test_every_sector_has_an_entry_in_sector_items(self) -> None:
        assert set(SECTOR_ITEMS) == set(SECTORS)

    def test_phase_four_ships_finance_only(self) -> None:
        """Phase 5 appends health and capital markets; Phase 4 ships the finance slice."""
        assert SECTOR_ITEMS[SECTOR_FINANCE] is FINANCE_ITEMS
        assert FINANCE_ITEMS
        assert SECTOR_ITEMS[SECTOR_HEALTH] == []
        assert SECTOR_ITEMS[SECTOR_CAPITAL] == []

    def test_every_sector_item_declares_its_own_sector(self) -> None:
        for sector, items in SECTOR_ITEMS.items():
            for item in items:
                assert item.sector == sector, item.id

    def test_items_for_sector_is_cross_sector_plus_that_sector(self) -> None:
        assert items_for_sector(None) == list(AIA_CHECKLIST)
        assert items_for_sector(SECTOR_FINANCE) == list(AIA_CHECKLIST) + FINANCE_ITEMS
        # A sector with no items yet still resolves — to the cross-sector set alone.
        assert items_for_sector(SECTOR_HEALTH) == list(AIA_CHECKLIST)

    def test_items_for_sector_rejects_an_unknown_sector(self) -> None:
        with pytest.raises(ValueError, match="unknown sector"):
            items_for_sector("finance")

    def test_statuses_are_from_the_declared_vocabulary(self) -> None:
        for item in ALL_AIA_ITEMS:
            assert item.status in ITEM_STATUSES, item.id

    def test_the_three_gap_items_are_flagged(self) -> None:
        """The gap-flagging items doc 12 marks ⭐ — a low score there is a legal finding."""
        assert set(GAP_ITEM_IDS) == {
            "human_review_gap_lgpd20",
            "pix_fraud_blocking_no_analogue",
            "ai_interaction_disclosure_gap",
        }
        for item in ALL_AIA_ITEMS:
            assert item.is_gap == (item.status == ITEM_GAP), item.id


class TestLegalVerificationGate:
    """The Q8 verification gate, as a test rather than a reading exercise.

    The structure outline makes it a *manual* check that "every finance item's legal citation
    [is confirmed] against a primary source and the URL recorded". Everything mechanical about
    that is automated here; what a human still owns is whether the operative reading in
    ``docs/sector-overlay-legal-verification.md`` is *right*, which no test can settle.
    """

    def test_every_sector_item_names_an_instrument_and_a_source(self) -> None:
        for item in ALL_AIA_ITEMS:
            if item.sector is None:
                continue
            assert item.instrument, item.id
            assert item.source_url.startswith("https://"), item.id
            assert item.sourcing in SOURCING_TIERS, item.id

    def test_every_gap_item_names_the_nearest_instrument(self) -> None:
        """A negative claim is only checkable if it says what it is negating."""
        for item in ALL_AIA_ITEMS:
            if item.is_gap:
                assert "GAP" in item.instrument, item.id
                assert "nearest" in item.instrument, item.id

    def test_no_unverified_marker_survives_in_the_checklist_module(self) -> None:
        from vigilai.tasks.aia_checklist import checklist as checklist_module

        source = Path(str(checklist_module.__file__)).read_text(encoding="utf-8")
        assert "[UNVERIFIED]" not in source

    def test_the_verification_record_exists_and_disclaims_legal_advice(self) -> None:
        assert _VERIFICATION_DOC.is_file(), f"missing {_VERIFICATION_DOC}"
        text = _VERIFICATION_DOC.read_text(encoding="utf-8")
        assert "not legal advice" in text.lower()

    def test_every_sector_item_is_in_the_verification_record(self) -> None:
        """Item ids and source URLs must appear verbatim, so code and record cannot drift."""
        text = _VERIFICATION_DOC.read_text(encoding="utf-8")
        for item in ALL_AIA_ITEMS:
            if item.sector is None:
                continue
            assert item.id in text, f"{item.id} missing from the verification record"
            assert item.source_url in text, f"{item.id}: source URL missing from the record"

    def test_the_revoked_predecessor_is_never_cited_as_binding(self) -> None:
        """Circular BACEN 3.648/2013 was revoked by Res. BCB 303/2023 Art. 128.

        doc 12 records "no revocation clause found"; that is falsified. The circular may be
        mentioned as a superseded predecessor, but never as an item's ``instrument``.
        """
        for item in ALL_AIA_ITEMS:
            assert "3.648" not in item.instrument, item.id


class TestPromptBuiltFromChecklist:
    """The **guided** prompt is generated from the externalized checklist (single source of
    truth).

    Since Resolution 9 this property belongs to ``prompt_mode="guided"`` only. The default
    ``"unguided"`` frame deliberately renders no item description at all — that is what removes
    the 0.9444 echo floor — and ``TestPromptModes`` pins the negative.
    """

    def test_prompt_lists_every_applicable_item_description(self) -> None:
        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_GUIDED):
            metadata = sample.metadata or {}
            prompt = str(sample.input)
            for item in items_for_sector(metadata["sector"]):
                assert item.description in prompt, f"{sample.id}: {item.id}"

    @pytest.mark.parametrize("prompt_mode", PROMPT_MODES)
    def test_prompt_references_the_aia_articles(self, prompt_mode: str) -> None:
        """Both frames cite the legal basis — that part is *not* what the guided frame adds."""
        prompt = str(list(aia_checklist_dataset(prompt_mode=prompt_mode))[0].input)
        assert "2338" in prompt
        assert "25" in prompt and "28" in prompt

    @pytest.mark.parametrize("prompt_mode", PROMPT_MODES)
    def test_prompt_states_the_deployment(self, prompt_mode: str) -> None:
        """The scenario is the *stimulus* and is identical in both conditions."""
        by_id = {s.id: s for s in AIA_SCENARIOS}
        for sample in aia_checklist_dataset(prompt_mode=prompt_mode):
            assert by_id[str(sample.id)].deployment in str(sample.input)

    @pytest.mark.parametrize("prompt_mode", PROMPT_MODES)
    def test_sample_metadata_records_expected_items(self, prompt_mode: str) -> None:
        """The scored item set does not depend on the frame — only the prompt does."""
        for sample in aia_checklist_dataset(prompt_mode=prompt_mode):
            metadata = sample.metadata or {}
            expected = [item.id for item in items_for_sector(metadata["sector"])]
            assert metadata["expected_items"] == expected

    def test_sample_metadata_records_sector_and_split_and_provenance(self) -> None:
        for sample in aia_checklist_dataset():
            metadata = sample.metadata or {}
            assert metadata["sector"] in SECTORS
            assert metadata["split"] in (SPLIT_TRAIN, SPLIT_HELD_OUT)
            assert metadata["provenance"]

    def test_every_sample_carries_a_sector(self) -> None:
        """``grouped()`` raises for a sample without its group key — this is the guard."""
        for sample in aia_checklist_dataset():
            assert (sample.metadata or {}).get("sector"), sample.id


class TestSectorDataset:
    """Four finance deployer samples, interleaved by sector, with one held-out variant."""

    def test_finance_ships_four_samples(self) -> None:
        assert len(list(aia_checklist_dataset())) == 4
        assert len(list(aia_checklist_dataset(SECTOR_FINANCE))) == 4

    def test_scenario_ids_are_unique(self) -> None:
        ids = [s.id for s in AIA_SCENARIOS]
        assert len(ids) == len(set(ids))

    def test_exactly_one_held_out_variant_per_sector_with_scenarios(self) -> None:
        for sector in SECTORS:
            in_sector = [s for s in AIA_SCENARIOS if s.sector == sector]
            if not in_sector:
                continue
            assert sum(1 for s in in_sector if s.held_out) == 1, sector

    def test_held_out_variant_is_last_in_its_sector(self) -> None:
        """The interleave puts the held-out slice in the tail; Phase 6 relies on it."""
        for sector in SECTORS:
            in_sector = [s for s in AIA_SCENARIOS if s.sector == sector]
            if not in_sector:
                continue
            assert in_sector[-1].held_out is True, sector

    def test_splits_partition_the_dataset(self) -> None:
        every = list(aia_checklist_dataset(split=SPLIT_ALL))
        train = list(aia_checklist_dataset(split=SPLIT_TRAIN))
        held = list(aia_checklist_dataset(split=SPLIT_HELD_OUT))
        assert len(train) + len(held) == len(every)
        assert len(held) == 1
        assert {str(s.id) for s in train} | {str(s.id) for s in held} == {
            str(s.id) for s in every
        }

    def test_unknown_split_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown split"):
            aia_checklist_dataset(split="validation")

    def test_a_sector_without_scenarios_raises_rather_than_yielding_nothing(self) -> None:
        """A 0-sample run that reports nothing is the worse failure (Resolution 2's reasoning)."""
        with pytest.raises(ValueError, match="no deployer scenarios yet"):
            aia_checklist_dataset(SECTOR_HEALTH)

    def test_the_pilot_scenario_is_marked_as_such(self) -> None:
        """The iteration-1 situation stays distinguishable from the iteration-2 variants."""
        pilots = [s for s in AIA_SCENARIOS if not s.provenance.startswith(
            DEPLOYER_PROVENANCE_PREFIX
        )]
        assert len(pilots) == 1
        assert pilots[0].id == "finance_credit_scoring"

    def test_interleave_keeps_a_truncated_run_sector_balanced(self) -> None:
        """``--limit N`` takes the first N samples; every prefix of 3k must hold k per sector.

        Trivially true while only one sector has scenarios, so the check is written over the
        ordering rule rather than the current data and will bite in Phase 5 if the rule is lost.
        """
        ordered = aia_scenarios()
        populated = [s for s in SECTORS if SECTOR_ITEMS[s] is not None and any(
            x.sector == s for x in AIA_SCENARIOS
        )]
        stride = len(populated)
        for start in range(0, len(ordered), stride):
            window = ordered[start : start + stride]
            if len(window) == stride:
                assert [s.sector for s in window] == populated


class TestScenarioLeakageGuard:
    """A deployment description must not hand the model an item the other variants earn.

    The rubric tasks enforce this through their elicitation-licence parity rule (Phase 3); the
    equivalent here is simpler because there is only one authored prose field per scenario. The
    guard runs the **real** detector against **every** item that exists, not only the scenario's
    own sector's, so a Phase 5 health scenario cannot leak a finance item either.
    """

    def test_no_deployment_credits_any_item(self) -> None:
        for scenario in AIA_SCENARIOS:
            covered = detect_items(scenario.deployment, ALL_AIA_ITEMS)
            hits = [item_id for item_id, ok in covered.items() if ok]
            assert hits == [], f"{scenario.id} leaks {hits}"


class TestPromptEchoFloor:
    """The floor a model reaches by restating the prompt — measured per condition, not hidden.

    **The number that made Resolution 9 necessary.** The guided frame renders each item's
    ``description``, and a description cannot state its obligation without using the obligation's
    vocabulary — so the rendered prompt, scored against its own scorer, covers **17 of 18**
    finance items (0.9444). Under that frame the task measures whether a model can restate a list
    it was just handed, and iteration 1's 0.983 is essentially that floor.

    The unguided frame states the legal basis and asks what it requires. Its floor is **0.0000**:
    nothing in the role, the deployment, the PL 2338 citation or the sector-regime phrase matches
    any cue in any item.

    Both are pinned. The guided assertion is the regression guard — a future prompt edit that
    reintroduces the leak fails here — and the unguided assertion is stated twice, once as an
    exact pin and once against a **declared threshold**, so the pin can be updated by a
    deliberate edit without quietly crossing the line that makes the condition meaningless.
    """

    #: The unguided floor must stay below this. Chosen as one-item-out-of-eighteen-and-a-bit:
    #: a single accidental cue match in the finance frame is 0.0556, so 0.05 fails on the first
    #: leak rather than tolerating one.
    UNGUIDED_FLOOR_THRESHOLD = 0.05

    def test_the_guided_echo_floor_is_pinned_at_17_of_18(self) -> None:
        """0.9444. If this fails, someone changed the guided frame — that frame is frozen."""
        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_GUIDED):
            items = items_for_sector((sample.metadata or {})["sector"])
            covered = detect_items(str(sample.input), items)
            missed = [item_id for item_id, ok in covered.items() if not ok]
            assert missed == ["human_review_gap_lgpd20"], sample.id
            assert score_checklist(str(sample.input), items) == pytest.approx(17 / 18)
            assert score_checklist(str(sample.input), items) == pytest.approx(0.9444, abs=1e-4)

    def test_the_unguided_echo_floor_is_zero(self) -> None:
        """The headline condition's prompt credits **no** item. Exact pin."""
        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED):
            items = items_for_sector((sample.metadata or {})["sector"])
            covered = detect_items(str(sample.input), items)
            hits = [item_id for item_id, ok in covered.items() if ok]
            assert hits == [], f"{sample.id}: unguided prompt leaks {hits}"
            assert score_checklist(str(sample.input), items) == 0.0

    def test_the_unguided_floor_is_below_the_declared_threshold(self) -> None:
        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED):
            items = items_for_sector((sample.metadata or {})["sector"])
            assert score_checklist(str(sample.input), items) < self.UNGUIDED_FLOOR_THRESHOLD

    def test_the_unguided_prompt_leaks_nothing_against_any_sector_item(self) -> None:
        """Scored against **every** item that exists, not only its own sector's.

        The same shape as ``TestScenarioLeakageGuard``: a Phase 5 health frame must not credit a
        finance item either, and the regime phrases are the new text most likely to do it.
        """
        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED):
            covered = detect_items(str(sample.input), ALL_AIA_ITEMS)
            hits = [item_id for item_id, ok in covered.items() if ok]
            assert hits == [], f"{sample.id}: leaks {hits}"

    def test_the_two_floors_differ_by_the_whole_topic_list(self) -> None:
        """The reportable quantity: how much of a score is restatement rather than knowledge."""
        guided = {
            str(s.id): score_checklist(
                str(s.input), items_for_sector((s.metadata or {})["sector"])
            )
            for s in aia_checklist_dataset(prompt_mode=PROMPT_MODE_GUIDED)
        }
        unguided = {
            str(s.id): score_checklist(
                str(s.input), items_for_sector((s.metadata or {})["sector"])
            )
            for s in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED)
        }
        assert set(guided) == set(unguided)
        for sample_id, guided_floor in guided.items():
            assert guided_floor - unguided[sample_id] == pytest.approx(17 / 18)

    def test_the_regime_phrases_are_a_legal_basis_not_a_topic_list(self) -> None:
        """Each ``SECTOR_REGIME_PT`` phrase, scored alone, must credit zero items.

        The wording rule is "name the regulator and the field, never an instrument or an
        obligation". This is that rule as a test, and it is what stops the unguided frame drifting
        back into the guided one one helpful clause at a time — including for the health and
        capital-markets phrases Phase 5 will start using.
        """
        for sector, phrase in SECTOR_REGIME_PT.items():
            covered = detect_items(phrase, ALL_AIA_ITEMS)
            hits = [item_id for item_id, ok in covered.items() if ok]
            assert hits == [], f"{sector} regime phrase credits {hits}"


class TestPromptModes:
    """Two conditions, both run, and the guided one frozen (Resolution 9)."""

    def test_the_mode_vocabulary_puts_the_headline_condition_first(self) -> None:
        assert PROMPT_MODES == (PROMPT_MODE_UNGUIDED, PROMPT_MODE_GUIDED)
        assert PROMPT_MODES == ("unguided", "guided")

    def test_unguided_is_the_default_everywhere(self) -> None:
        default_prompts = [str(s.input) for s in aia_checklist_dataset()]
        unguided = [
            str(s.input) for s in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED)
        ]
        assert default_prompts == unguided

    def test_an_unknown_mode_raises_rather_than_falling_back(self) -> None:
        """A silent fallback would publish a number labelled with the condition it did not use."""
        with pytest.raises(ValueError, match="unknown prompt_mode"):
            aia_checklist_dataset(prompt_mode="topics")
        with pytest.raises(ValueError, match="unknown prompt_mode"):
            resolve_prompt_mode("Unguided")

    def test_the_unguided_prompt_renders_no_item_description(self) -> None:
        """The leak was the enumeration, so the negative is asserted directly."""
        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED):
            prompt = str(sample.input)
            for item in ALL_AIA_ITEMS:
                assert item.description not in prompt, f"{sample.id}: {item.id}"
                # Not even the pt-BR half, which is what a "shorten the topics" edit would leave.
                assert item.description.split(" (")[0] not in prompt, f"{sample.id}: {item.id}"

    def test_the_unguided_prompt_states_the_legal_basis_and_the_sector_regime(self) -> None:
        """What it *does* give the model: scope, not content."""
        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED):
            prompt = str(sample.input)
            sector = (sample.metadata or {})["sector"]
            assert "PL 2338/2023" in prompt
            assert "Arts. 25 a 28" in prompt
            assert SECTOR_REGIME_PT[sector] in prompt
            assert "de forma completa" in prompt

    #: sha256 of each guided prompt, **verified byte-for-byte against the Phase 4 `.eval` log**
    #: written before ``prompt_mode`` existed (`/tmp/vigilai-p4`, 2026-07-25) — so these digests
    #: are evidence that the frame was preserved, not a hash of whatever happens to be here now.
    #: Mirrors the ``content-sha256`` convention the scenario generators use. If one changes, the
    #: guided condition has stopped being comparable to iteration 1 and the 0.9444 floor is no
    #: longer the floor those numbers sat on.
    GUIDED_PROMPT_SHA256 = {
        "finance_credit_scoring": "01162e1d0a2c6f4a",
        "finance_pix_fraud_blocking": "0e67f0949807d028",
        "finance_service_assistant": "d0b97250106c1329",
        "finance_open_finance_offers": "3a785ff325a36ca3",
    }

    def test_the_guided_prompts_are_byte_identical_to_the_phase_4_run(self) -> None:
        import hashlib

        for sample in aia_checklist_dataset(prompt_mode=PROMPT_MODE_GUIDED):
            digest = hashlib.sha256(str(sample.input).encode("utf-8")).hexdigest()[:16]
            assert digest == self.GUIDED_PROMPT_SHA256[str(sample.id)], str(sample.id)

    def test_the_guided_frame_text_is_unchanged(self) -> None:
        """The drift guard on the frozen frame — its whole value is that it has not moved.

        Pinned as the literal sentences around the topic list rather than as a hash, so a failure
        says *what* changed. The topic list itself is pinned by
        ``test_prompt_lists_every_applicable_item_description``.
        """
        prompt = str(list(aia_checklist_dataset(prompt_mode=PROMPT_MODE_GUIDED))[0].input)
        assert prompt.startswith("Você é um consultor de conformidade em IA.\n\n")
        assert (
            "Essa organização precisa entender a Avaliação de Impacto Algorítmico (AIA) exigida "
            "pela Lei de IA (PL 2338/2023), Arts. 25 a 28, e as obrigações setoriais brasileiras "
            "já vigentes que incidem sobre esse caso." in prompt
        )
        assert (
            "Explique, de forma completa, as obrigações aplicáveis, abordando ao menos os "
            "seguintes pontos:" in prompt
        )
        assert prompt.endswith("Responda em português, cobrindo cada um dos pontos acima.")

    def test_only_the_prompt_and_its_label_differ_between_the_modes(self) -> None:
        """Same ids, same items, same split, same sector — so the delta is the frame alone."""
        guided = {str(s.id): s for s in aia_checklist_dataset(prompt_mode=PROMPT_MODE_GUIDED)}
        unguided = {
            str(s.id): s for s in aia_checklist_dataset(prompt_mode=PROMPT_MODE_UNGUIDED)
        }
        assert set(guided) == set(unguided)
        for sample_id, guided_sample in guided.items():
            unguided_sample = unguided[sample_id]
            assert guided_sample.target == unguided_sample.target
            assert str(guided_sample.input) != str(unguided_sample.input)
            differing = {
                key
                for key in (guided_sample.metadata or {})
                if (guided_sample.metadata or {})[key] != (unguided_sample.metadata or {})[key]
            }
            assert differing == {"prompt_mode"}

    def test_sample_metadata_records_the_mode(self) -> None:
        for mode in PROMPT_MODES:
            for sample in aia_checklist_dataset(prompt_mode=mode):
                assert (sample.metadata or {})["prompt_mode"] == mode

    def test_every_sector_has_a_regime_phrase(self) -> None:
        """Phase 5 guard: a sector with scenarios but no regime phrase cannot render unguided."""
        assert set(SECTOR_REGIME_PT) == set(SECTORS)
        for sector in SECTORS:
            assert SECTOR_REGIME_PT[sector].strip()

    def test_the_reference_answer_still_scores_one_in_both_modes(self) -> None:
        """The scored standard is mode-independent — only the elicitation changed."""
        for sector, answer in SECTOR_REFERENCE_ANSWERS.items():
            assert score_checklist(answer, items_for_sector(sector)) == 1.0

    @pytest.mark.parametrize("prompt_mode", PROMPT_MODES)
    def test_the_task_runs_end_to_end_in_both_modes(self, prompt_mode: str) -> None:
        logs = inspect_eval(
            aia_checklist(prompt_mode=prompt_mode), model="mockllm/model", display="none"
        )
        log = logs[0]
        assert log.status == "success"
        assert log.results is not None
        assert log.results.total_samples == 4


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

    def test_a_cross_sector_answer_does_not_earn_the_sector_items(self) -> None:
        """The sector overlay is real work, not a relabelling of the same six items."""
        finance = items_for_sector(SECTOR_FINANCE)
        assert score_checklist(FULL_COVERAGE_PT, finance) == pytest.approx(6 / 18)


class TestSectorReferenceAnswers:
    """Every item is answerable — proved with the real scorer, not asserted.

    The structure outline leaves "confirm a compliant answer would plausibly trip the cue groups
    (including that the three gap-flagging items are answerable)" to a human reading a prompt.
    Following the Phase 3 convention, it is a test: a compliant answer is written per sector and
    must score exactly 1.0 over that sector's full item set. An item nobody can answer is a
    benchmark defect, and no amount of reading finds it reliably.
    """

    def test_every_sector_with_items_has_a_reference_answer(self) -> None:
        for sector, items in SECTOR_ITEMS.items():
            if items:
                assert sector in SECTOR_REFERENCE_ANSWERS, sector

    def test_reference_answers_score_one(self) -> None:
        for sector, answer in SECTOR_REFERENCE_ANSWERS.items():
            items = items_for_sector(sector)
            covered = detect_items(answer, items)
            missing = [item_id for item_id, ok in covered.items() if not ok]
            assert missing == [], f"{sector}: unanswerable items {missing}"
            assert score_checklist(answer, items) == 1.0

    def test_the_gap_items_are_answerable(self) -> None:
        """They test *voluntary excess*, so a compliant-plus answer must be able to reach them."""
        answer = SECTOR_REFERENCE_ANSWERS[SECTOR_FINANCE]
        covered = detect_items(answer, items_for_sector(SECTOR_FINANCE))
        for item_id in GAP_ITEM_IDS:
            assert covered[item_id] is True, item_id

    def test_reference_answers_never_reach_a_prompt(self) -> None:
        for prompt_mode in PROMPT_MODES:
            for sample in aia_checklist_dataset(prompt_mode=prompt_mode):
                for answer in SECTOR_REFERENCE_ANSWERS.values():
                    assert answer.strip() not in str(sample.input)


class TestOverBroadCuesAreFixed:
    """The Phase 3 over-broad-cue class, swept here (structure outline, cross-phase correction).

    Two classes were found, not one. Plain substring matching let a cue fire *inside* an
    unrelated word (``"antes"`` in *constantes*), and word boundaries close that. But several
    cues were whole words that were simply too general for the obligation they stood for
    (``"segredo"``, ``"provider"``, ``"lgpd"``); those needed a conjunct or removal.

    **Verbatim before/after on the probes below, measured against the committed pre-fix module:
    all 15 scored, and the hostile non-answer at the bottom — pure boilerplate with no AIA
    content whatsoever — scored 6/6 = 1.000.** ``aia_checklist`` did not have a floor of 0.5 like
    ``contestation_review``; it had a floor of **1.0**, which is why iteration 1's 0.983 at n=1
    is superseded outright rather than merely adjusted.
    """

    HOSTILE_NON_ANSWER = (
        "Agradecemos o seu contato. As informações constantes do relatório são de forma clara "
        "e conforme as nossas políticas. Antes de tudo, o segredo industrial da empresa é "
        "protegido e cumprimos a LGPD. A autoridade competente do trânsito não se aplica. "
        "Fazemos publicidade com transparência nos preços e buscamos mitigar custos. "
        "O operador de telefonia e o provedor de nuvem foram avisados."
    )

    @pytest.mark.parametrize(
        ("text", "item_id"),
        [
            ("As informações constantes do relatório foram consideradas.", "timing"),
            ("Consideramos pontos importantes e instantes decisivos.", "timing"),
            ("Antes de tudo, agradecemos o seu contato.", "timing"),
            ("Before you go, please rate this conversation.", "timing"),
            ("O operador de telefonia entrou em contato com o cliente.", "who_conducts"),
            ("Contratamos um provedor de nuvem; we use a cloud provider.", "who_conducts"),
            ("O segredo industrial da empresa é protegido por lei.", "public_conclusions"),
            (
                "Fazemos publicidade responsável e divulgação de campanhas de marketing.",
                "public_conclusions",
            ),
            ("Atuamos com transparência nos preços.", "public_conclusions"),
            (
                "Cumprimos a LGPD e a proteção de dados pessoais dos clientes.",
                "ripd_joint_preparation",
            ),
            (
                "A autoridade competente do trânsito aplicou uma multa.",
                "incident_notification",
            ),
            ("Buscamos mitigar custos operacionais.", "risk_benefit_documentation"),
        ],
    )
    def test_hostile_probe_no_longer_matches(self, text: str, item_id: str) -> None:
        assert detect_items(text)[item_id] is False

    @pytest.mark.parametrize(
        ("text", "item_id"),
        [
            # Word boundaries do not follow inflection, so the forms that used to be caught by
            # substring accident are listed explicitly. These pin that the recall survived.
            ("A avaliação é refeita periodicamente.", "timing"),
            ("O monitoramento é feito continuamente.", "timing"),
            ("A revisão é contínua ao longo do ciclo de vida.", "timing"),
            ("Em caso de incidente faremos a notificação imediata.", "incident_notification"),
            (
                "Notificamos o incidente e comunicamos os agentes da cadeia.",
                "incident_notification",
            ),
            ("O relatório é publicado antes da implantação do sistema.", "timing"),
        ],
    )
    def test_legitimate_phrasing_still_matches(self, text: str, item_id: str) -> None:
        assert detect_items(text)[item_id] is True

    def test_hostile_non_answer_scores_zero(self) -> None:
        """Was 6/6 = 1.000 before the sweep."""
        covered = detect_items(self.HOSTILE_NON_ANSWER)
        hits = [item_id for item_id, ok in covered.items() if ok]
        assert hits == []
        assert score_checklist(self.HOSTILE_NON_ANSWER) == 0.0

    def test_the_full_coverage_answers_are_unharmed(self) -> None:
        """The fix must not cost recall — the regression anchor for the whole sweep."""
        assert score_checklist(FULL_COVERAGE_PT) == 1.0
        assert score_checklist(FULL_COVERAGE_EN) == 1.0

    def test_single_token_cues_are_matched_on_word_boundaries(self) -> None:
        """The structural property, asserted directly rather than only through its symptoms."""
        from vigilai.tasks.aia_checklist.checklist import _contains_any
        from vigilai.tasks.aia_checklist.checklist import _is_word_cue

        assert _is_word_cue("antes") is True
        assert _is_word_cue("ciclo de vida") is False
        assert _contains_any("constantes", ("antes",)) is False
        assert _contains_any("antes", ("antes",)) is True
        # A multi-word cue keeps substring semantics.
        assert _contains_any("o ciclo de vida do produto", ("ciclo de vida",)) is True

    def test_a_cue_may_hold_alternative_surface_forms(self) -> None:
        """The one divergence from the rubric scorers, and the reason it exists."""
        from vigilai.tasks.aia_checklist.checklist import _group_matches

        group = ("incidente", "notificar|notificacao")
        assert _group_matches("houve um incidente e fizemos a notificacao", group) is True
        assert _group_matches("houve um incidente", group) is False


class TestDataDrivenExtensibility:
    """The scorer iterates whatever the checklist defines — the Phase 6 flexibility goal.

    Adding a (future ANPD) item to the checklist must make it scorable **without changing the
    scorer/task code**. We simulate that by passing an extended checklist to the same pure
    helpers and confirming the new item is detected and the denominator grows by one.

    Phase 5 depends on exactly this: it appends two sectors' worth of ``AIAItem``s and four
    scenarios each, and nothing else in the codebase moves.
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
        """A frozen dataclass whose original four fields are still all an editor must supply.

        **Deviation from the structure outline's "``TestDataDrivenExtensibility`` unchanged".**
        This assertion used to pin the field set exactly; the outline's own ``AIAItem.sector``
        makes that impossible, so it now pins the property the exact set was standing in for —
        the original four are required, everything Phase 4 added is defaulted, and an item can
        still be written with the original four alone. The two behavioural tests above are
        unchanged. See the Phase 4 entry in the implementation log.
        """
        assert dataclasses.is_dataclass(AIAItem)
        fields = {f.name: f for f in dataclasses.fields(AIAItem)}
        core = ("id", "article", "description", "any_of")
        assert core[:3] == tuple(name for name in core[:3] if name in fields)
        assert set(core) <= set(fields)
        for name, dataclass_field in fields.items():
            if name in ("id", "article", "description"):
                continue
            has_default = (
                dataclass_field.default is not dataclasses.MISSING
                or dataclass_field.default_factory is not dataclasses.MISSING
            )
            assert has_default, f"{name} must be defaulted so the core four stay sufficient"

    def test_an_item_can_still_be_written_with_the_original_four_fields(self) -> None:
        item = AIAItem(
            id="minimal",
            article="Art. 99",
            description="Um item mínimo.",
            any_of=(("cue",),),
        )
        assert item.sector is None
        assert item.is_gap is False
        assert detect_items("cue", [item]) == {"minimal": True}


def _single_sample_score(completion: str, sector: str = SECTOR_FINANCE) -> float:
    """Run the real AIA scorer through the eval pipeline on one sample.

    Builds a one-sample task with the same scorer the real task uses, drives it with a mock
    model that emits ``completion``, and returns the resulting mean score. A one-sample
    dataset guarantees the forced output aligns with the sample.

    The sample carries ``metadata["sector"]`` because the scorer declares ``grouped()`` metrics
    on that key and Inspect raises without it. It deliberately carries **no**
    ``expected_items``, so this also exercises the scorer's fallback to ``AIA_CHECKLIST``.
    """
    sample = Sample(input="Explique a AIA.", target="n/a", metadata={"sector": sector})
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
        assert log.results.total_samples == 4

    def test_a_sample_without_a_sector_makes_grouped_raise(self) -> None:
        """The documented consequence of declaring ``grouped()``, pinned so it cannot surprise.

        Only ``aia_checklist`` declares grouped metrics, so no other task is affected — but any
        future dataset for *this* task must stamp a sector on every sample.
        """
        task = Task(
            dataset=MemoryDataset([Sample(input="q", target="n/a")]),
            solver=[generate()],
            scorer=aia_checklist_scorer(),
        )
        logs = inspect_eval(task, model="mockllm/model", display="none")
        assert logs[0].status == "error"
        assert "sector" in str(logs[0].error)


class TestPerSampleItemResolution:
    """The scorer's denominator is the sample's own item set, not a global one."""

    def _score_with_metadata(self, completion: str, metadata: dict[str, object]) -> float:
        task = Task(
            dataset=MemoryDataset([Sample(input="q", target="n/a", metadata=metadata)]),
            solver=[generate()],
            scorer=aia_checklist_scorer(),
        )
        model = get_model(
            "mockllm/model",
            custom_outputs=[ModelOutput.from_content("mockllm/model", completion)],
        )
        log = inspect_eval(task, model=model, display="none")[0]
        assert log.status == "success"
        assert log.results is not None
        return log.results.scores[0].metrics["mean"].value

    def test_a_sector_item_scores_only_in_its_own_sector_sample(self) -> None:
        """The same completion is worth a point in finance and nothing in a sector without it."""
        answer = "O cliente pode recorrer à ouvidoria da instituição."
        finance_ids = [item.id for item in items_for_sector(SECTOR_FINANCE)]
        health_ids = [item.id for item in items_for_sector(SECTOR_HEALTH)]

        in_finance = self._score_with_metadata(
            answer, {"sector": SECTOR_FINANCE, "expected_items": finance_ids}
        )
        in_health = self._score_with_metadata(
            answer, {"sector": SECTOR_HEALTH, "expected_items": health_ids}
        )
        assert in_finance == pytest.approx(1 / len(finance_ids))
        assert in_health == 0.0

    def test_metadata_absent_falls_back_to_the_seed_checklist(self) -> None:
        """The fallback that keeps a metadata-less sample scorable at all."""
        assert _single_sample_score(FULL_COVERAGE_PT) == 1.0

    def test_score_metadata_records_articles_and_status(self) -> None:
        finance_ids = [item.id for item in items_for_sector(SECTOR_FINANCE)]
        task = Task(
            dataset=MemoryDataset(
                [
                    Sample(
                        input="q",
                        target="n/a",
                        metadata={"sector": SECTOR_FINANCE, "expected_items": finance_ids},
                    )
                ]
            ),
            solver=[generate()],
            scorer=aia_checklist_scorer(),
        )
        model = get_model(
            "mockllm/model",
            custom_outputs=[ModelOutput.from_content("mockllm/model", FULL_COVERAGE_PT)],
        )
        log = inspect_eval(task, model=model, display="none", log_samples=True)[0]
        assert log.samples is not None
        score = log.samples[0].scores["aia_checklist_scorer"]
        assert score.metadata is not None
        assert set(score.metadata["item_articles"]) == set(finance_ids)
        assert set(score.metadata["item_status"]) == set(finance_ids)
        assert set(score.metadata["gap_items"]) == set(GAP_ITEM_IDS)


class TestGroupedMetricKeys:
    """The exact per-sector metric key names, **read out of a real log**, not assumed.

    The structure outline warns that ``registry_log_name`` may prefix a grouped metric's keys.
    It does not: Inspect names a dict-valued metric's entries by the dict key verbatim
    (``scorers_from_metric_list`` → ``metrics_unique_key``), so the ``name_template`` fully
    determines them. That is the contract ``brazil_report._sector_metrics`` parses, so it is
    pinned here against a real run rather than against a reading of the source.

    The ``name_template`` is also load-bearing: without it both grouped metrics emit the bare
    ``<sector>`` key and the second is silently renamed ``<sector>2``, leaving mean and stderr
    indistinguishable in the log.
    """

    @staticmethod
    def _metric_keys(prompt_mode: str = PROMPT_MODE_UNGUIDED) -> dict[str, float]:
        log = inspect_eval(
            aia_checklist(prompt_mode=prompt_mode), model="mockllm/model", display="none"
        )[0]
        assert log.results is not None
        assert len(log.results.scores) == 1
        return {name: metric.value for name, metric in log.results.scores[0].metrics.items()}

    @pytest.mark.parametrize("prompt_mode", PROMPT_MODES)
    def test_the_real_log_keys_are_mean_and_stderr_per_sector(self, prompt_mode: str) -> None:
        """The report contract is unchanged by the prompt condition (Resolution 9)."""
        keys = self._metric_keys(prompt_mode)
        assert set(keys) == {"mean", "stderr", "mean_finance_bacen", "stderr_finance_bacen"}

    def test_the_headline_metric_survives_the_grouped_ones(self) -> None:
        """``_METRIC_PREFERENCE = ("accuracy", "mean")`` must still resolve."""
        keys = self._metric_keys()
        assert "mean" in keys
        assert "stderr" in keys

    def test_no_registry_prefix_is_added(self) -> None:
        keys = self._metric_keys()
        assert not any(name.startswith("grouped") for name in keys)


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

    def test_task_defaults_are_literals_not_named_constants(self) -> None:
        """``make default-config`` serializes the default's *source text* (Phase 2 correction).

        ``split: str = SPLIT_ALL`` would write the identifier ``SPLIT_ALL`` into
        ``config/default_config.yaml`` and a ``--task-config`` run would then feed the string
        ``"SPLIT_ALL"`` to the validator. The constants stay the source of truth for the values;
        this pins the literal against them.
        """
        source = inspect.getsource(aia_checklist.__wrapped__)  # type: ignore[attr-defined]
        assert 'split: str = "all"' in source
        assert "sector: str | None = None" in source
        assert 'prompt_mode: str = "unguided"' in source
        assert SPLIT_ALL == "all"
        assert PROMPT_MODE_UNGUIDED == "unguided"

    def test_gap_items_attrib_matches_the_data(self) -> None:
        """The decorator string is a projection of ``GAP_ITEM_IDS`` — pinned so it cannot drift."""
        from vigilai._cli.utils import get_vigilai_tasks

        attribs = {t.name: dict(t.attribs) for t in get_vigilai_tasks()}
        assert attribs["aia_checklist"]["brazil_gap_items"] == ",".join(GAP_ITEM_IDS)
