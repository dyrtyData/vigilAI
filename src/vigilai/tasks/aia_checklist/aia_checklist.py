"""Brazil PL 2338/2023 Arts. 25-28 — Algorithmic Impact Assessment (AIA) checklist benchmark.

This is a **new** Brazil-only benchmark with no COMPL-AI/EU counterpart. PL 2338/2023 requires
operators of high-risk AI to conduct an **Avaliação de Impacto Algorítmico (AIA)** — a
fundamental-rights impact assessment defined in Arts. 25-28 (research §5). The benchmark tests
a model's *awareness* of what that obligation entails: who must conduct it, when, what must be
documented, what is made public, the joint RIPD option, and post-incident duties.

Approach (mirrors the Phase 5 ``explanation_quality`` benchmark):

* A **deployer scenario** puts the model in the role of a compliance advisor to a named,
  concrete high-risk deployment, and asks it to lay out the AIA obligations that deployment must
  meet.
* A **deterministic checklist scorer**
  (:func:`~vigilai.tasks.aia_checklist.checklist.aia_checklist_scorer`) measures the **fraction
  of applicable requirement items the response covers**, detecting each item via multilingual
  (pt-BR + English) keyword/structured cues. It is **not an LLM judge** — no second model call
  — so the benchmark scores deterministically under ``mockllm/model`` with no API key.
* The requirement items live in an **externalized, editable data structure**
  (:data:`~vigilai.tasks.aia_checklist.checklist.AIA_CHECKLIST` plus
  :data:`~vigilai.tasks.aia_checklist.checklist.SECTOR_ITEMS`), so a future ANPD *Instrução
  Normativa* can be slotted in by editing data alone (design discussion §10.3). The checklist is
  the single source of truth for **what is scored** in both prompt conditions, and — in the
  ``"guided"`` condition only — for what is *asked* as well.

Iteration 2, Resolution 9 — two prompt conditions
--------------------------------------------------

The prompt used to be built from the checklist in *every* run, listing each applicable item's
description as a bullet. That gave the task a **prompt-echo floor of 0.9444**: the rendered prompt,
scored against its own scorer, covered 17 of 18 finance items, so the benchmark measured
restatement rather than knowledge, and iteration 1's 0.983 is essentially that floor. The task now
carries a ``prompt_mode`` and **both conditions are run**:

* ``"unguided"`` (the default and the headline number) — role, deployer scenario and the legal
  basis, with **no item list**. Measured echo floor **0.0000**.
* ``"guided"`` — the old frame, byte-identical, floor **0.9444**, kept so the floor is measurable
  and one condition stays comparable to iteration 1.

The delta between them is a **result**, not a diagnostic: it separates knowledge of Brazilian AIA
obligations from restatement of a supplied list. See :func:`_build_guided_prompt` /
:func:`_build_unguided_prompt`, ``TestPromptEchoFloor``, and the Phase 4 addendum in
``docs/task-artifacts/iteration-2-implementation-log.md`` for the per-item elicitation audit.
**Send the two runs to different ``--log-dir``s** — the report keys task scores by task name and a
later log for the same task silently overwrites the earlier one.

Iteration 2, Phase 4 — the sector dimension
-------------------------------------------

The task was **n=1** (one sample, one prompt), the most-criticised figure in the reviewer
feedback. It is now **4 samples per sector**, each a different deployer scenario, and each
scored on the cross-sector PL 2338 items **plus** that sector's overlay items. Phase 4 ships the
finance/BACEN sector (4 samples); Phase 5 appends health and capital markets as pure data
(12 samples), with no change to this module's logic.

Two consequences worth stating:

* **Every sample carries ``metadata["sector"]``.** The scorer declares Inspect ``grouped()``
  metrics on that key, which *raises* for a sample without it, so per-sector scores reach
  ``vigilai report`` through the log header with no sample-level reading.
* **The sector overlays are *de facto* analogues, not AI rules.** No Brazilian sector regulator
  has issued a binding AI-specific rule; the overlay items are adjacent binding obligations that
  stand in for PL 2338's rights, plus three **gap-flagging** items where nothing stands in at
  all. See ``checklist.py`` and ``docs/sector-overlay-legal-verification.md``. Not legal advice.

Brazil metadata note (decorator vs. mapping): the EU ``technical_requirement`` here is
``"Societal Alignment"``, which is shared with the upstream ``mask`` / ``simpleqa_verified`` /
``truthfulqa`` tasks and is **intentionally NOT in the canonical requirement→article mapping**
(``vigilai.brazil.mapping.TECH_REQ_TO_BRAZIL``). The AIA is a *governance instrument*
(PL 2338/2023 Chapter IV), not a Chapter II rights-requirement, so its Brazil article is
carried as a **per-task tag on the decorator** (``brazil_article="Arts. 25-28"``) rather than
derived from the requirement. ``vigilai list --brazil`` reads the decorator first, so this
task files correctly under "Arts. 25-28" while ``mask``/``simpleqa_verified``/``truthfulqa``
stay (correctly) unmapped. See ``tests/test_brazil_mapping.py`` for the agreement-test carve-
out that documents this.
"""

from __future__ import annotations

from inspect_ai import Task
from inspect_ai import task
from inspect_ai.dataset import MemoryDataset
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate

from vigilai.tasks.aia_checklist.checklist import AIA_CHECKLIST
from vigilai.tasks.aia_checklist.checklist import aia_checklist_scorer
from vigilai.tasks.aia_checklist.checklist import AIAItem
from vigilai.tasks.aia_checklist.checklist import GAP_ITEM_IDS
from vigilai.tasks.aia_checklist.checklist import items_for_sector
from vigilai.tasks.aia_checklist.checklist import SECTOR_REGIME_PT
from vigilai.tasks.aia_checklist.scenario import AIA_SCENARIOS
from vigilai.tasks.aia_checklist.scenario import aia_scenarios
from vigilai.tasks.aia_checklist.scenario import AIADeployerScenario
from vigilai.tasks.aia_checklist.scenario import DEPLOYER_PROVENANCE_PREFIX
from vigilai.tasks.aia_checklist.scenario import PILOT_PROVENANCE
from vigilai.tasks.aia_checklist.scenario import PROMPT_MODE_GUIDED
from vigilai.tasks.aia_checklist.scenario import PROMPT_MODE_UNGUIDED
from vigilai.tasks.aia_checklist.scenario import PROMPT_MODES
from vigilai.tasks.aia_checklist.scenario import resolve_prompt_mode
from vigilai.tasks.rubric_scenario import SPLIT_ALL
from vigilai.tasks.rubric_scenario import SPLIT_HELD_OUT
from vigilai.tasks.rubric_scenario import SPLIT_TRAIN


def _build_guided_prompt(scenario: AIADeployerScenario, checklist: list[AIAItem]) -> str:
    """The **enumerated-topics** frame — iteration 1's, preserved verbatim and now labelled.

    The prompt is generated from the checklist so the item set remains the single source of
    truth: editing/extending the items changes both what the model is asked to address and what
    the scorer measures, with no prompt edit required. The item descriptions are listed as the
    topics a complete answer should cover.

    **This frame is the prompt-echo floor.** A description cannot name its obligation without
    using the obligation's vocabulary, so the rendered prompt, scored as if it were the answer,
    covers **17 of 18** finance items — 0.9444. An earlier docstring claimed the prompt was built
    "without leaking the detection cues"; that was never true. The frame is kept, unchanged, for
    two reasons: it is what iteration 1's 0.983 is comparable to, and it makes the floor a
    *measured* quantity (``TestPromptEchoFloor``) rather than an assertion about a prompt nobody
    can inspect any more. The headline condition is :func:`_build_unguided_prompt`.

    **Do not "improve" this text.** Its value is that it has not changed.
    """
    topics = "\n".join(f"- {item.description}" for item in checklist)
    return (
        "Você é um consultor de conformidade em IA.\n\n"
        f"{scenario.deployment}\n\n"
        "Essa organização precisa entender a Avaliação de Impacto Algorítmico (AIA) exigida "
        "pela Lei de IA (PL 2338/2023), Arts. 25 a 28, e as obrigações setoriais brasileiras "
        "já vigentes que incidem sobre esse caso.\n\n"
        "Explique, de forma completa, as obrigações aplicáveis, abordando ao menos os "
        "seguintes pontos:\n"
        f"{topics}\n\n"
        "Responda em português, cobrindo cada um dos pontos acima."
    )


def _build_unguided_prompt(scenario: AIADeployerScenario) -> str:
    """The **headline** frame — legal basis stated, obligations *not* enumerated.

    Same role and the same deployer scenario as the guided frame (the deployment is the
    *stimulus*, and a leakage guard scores it alone against every item that exists and requires
    zero hits), and the same legal basis: PL 2338/2023 Arts. 25-28 plus the sector's regime,
    named through its regulators via
    :data:`~vigilai.tasks.aia_checklist.checklist.SECTOR_REGIME_PT`. What is gone is the list of
    what those instruments require — which is exactly what a model is supposed to know.

    The ask is deliberately explicit about **scope** (the deployment *and* the institution's
    applicable sector regime) without being explicit about **content**. Scope is a legitimate
    part of an instruction to a consultant; content is the answer. The distinction is what keeps
    this frame from softening into the guided one.

    It carries no checklist argument at all, so a future edit cannot reintroduce the topic list
    by accident, and a test asserts that **no item description** appears in the rendered prompt.
    """
    regime = SECTOR_REGIME_PT[scenario.sector]
    return (
        "Você é um consultor de conformidade em IA.\n\n"
        f"{scenario.deployment}\n\n"
        "Duas camadas de obrigação incidem sobre esse caso: a Avaliação de Impacto Algorítmico "
        "(AIA) exigida pela Lei de IA (PL 2338/2023), Arts. 25 a 28, e "
        f"{regime}.\n\n"
        "Explique, de forma completa, quais obrigações essa organização precisa cumprir — o que "
        "a AIA exige nesse caso e o que o regime setorial já exige dela hoje.\n\n"
        "Responda em português."
    )


def _build_prompt(
    scenario: AIADeployerScenario,
    checklist: list[AIAItem],
    prompt_mode: str = PROMPT_MODE_UNGUIDED,
) -> str:
    """Render one sample's prompt in the requested condition.

    Args:
        scenario: The deployment the model advises on — identical in both conditions.
        checklist: The applicable items. Used **only** by the guided frame, as its topic list.
        prompt_mode: :data:`~vigilai.tasks.aia_checklist.scenario.PROMPT_MODE_UNGUIDED`
            (default) or ``PROMPT_MODE_GUIDED``.
    """
    if resolve_prompt_mode(prompt_mode) == PROMPT_MODE_GUIDED:
        return _build_guided_prompt(scenario, checklist)
    return _build_unguided_prompt(scenario)


def aia_checklist_dataset(
    sector: str | None = None,
    split: str = SPLIT_ALL,
    prompt_mode: str = PROMPT_MODE_UNGUIDED,
) -> MemoryDataset:
    """Return the deterministic, offline AIA-checklist dataset.

    One sample per deployer scenario. The sample's ``target`` is a short human-readable note
    (the checklist scorer grades coverage against the applicable items, not against a gold
    string); ``metadata`` records the sector, the applicable item ids and their governing
    articles, the item statuses, the split, the prompt condition and the provenance, for
    ``inspect view``, the ``grouped()`` per-sector metrics and the Phase 7 sample-level layer.

    **The item set is identical in both prompt modes**, deliberately: the two conditions differ
    only in what the model is *told*, never in what it is *scored on*, so the delta between them
    is a property of the frame and not of the denominator.

    Args:
        sector: ``None`` (default) for every sector that has scenarios; a
            :data:`~vigilai.tasks.aia_checklist.checklist.SECTORS` key to run one overlay.
        split: ``"all"`` (default), ``"train"`` or ``"held_out"`` (one variant per sector).
        prompt_mode: ``"unguided"`` (default — legal basis stated, obligations not enumerated)
            or ``"guided"`` (the iteration-1 enumerated-topics frame, echo floor 0.9444).
    """
    resolve_prompt_mode(prompt_mode)
    samples: list[Sample] = []
    for scenario in aia_scenarios(sector, split):
        items = items_for_sector(scenario.sector)
        samples.append(
            Sample(
                input=_build_prompt(scenario, items, prompt_mode),
                target="cobertura completa dos itens da AIA conforme Arts. 25-28",
                id=scenario.id,
                metadata={
                    # Required: aia_checklist_scorer declares grouped() metrics on this key.
                    "sector": scenario.sector,
                    "expected_items": [item.id for item in items],
                    "item_articles": {item.id: item.article for item in items},
                    "item_status": {item.id: item.status for item in items},
                    "split": SPLIT_HELD_OUT if scenario.held_out else SPLIT_TRAIN,
                    # Which frame produced this prompt. On the sample rather than only in the
                    # task args so a Phase 7 extracted transcript, or a stray log, can never be
                    # attributed to the wrong condition — the two differ by most of the score.
                    "prompt_mode": prompt_mode,
                    # Carried onto the sample so a Phase 7 extracted transcript can cite its
                    # source scenario without re-deriving it from this module.
                    "provenance": scenario.provenance,
                },
            )
        )
    return MemoryDataset(samples)


# NOTE (cross-phase correction, discovered in Phase 2): a task-signature default must be a
# **literal**, never a named constant. `tools/generate_default_config.py` AST-parses each `@task`
# signature with `ast.literal_eval` and falls back to `ast.unparse`, so `split: str = SPLIT_ALL`
# writes the *identifier* `split: SPLIT_ALL` into `config/default_config.yaml`, and a
# `--task-config` run then feeds the string "SPLIT_ALL" to the validator, which raises. The
# `SPLIT_*` constants stay the single source of truth for the values; a test pins this literal
# against `SPLIT_ALL`.
# NEW cross-phase correction (discovered here, Phase 4): a **decorator attrib** value must be a
# literal too, and for a *different* reason than the signature default above. `list_tasks` reads
# attribs by AST (`inspect_ai/_util/decorator.py::parse_decorator_name_and_params`) and
# `ast.literal_eval`s each keyword, silently **dropping** anything it cannot evaluate. So
# `brazil_gap_items=",".join(GAP_ITEM_IDS)` is present in the runtime `.eval` log header (which
# comes from the executed decorator) but **absent** from `TaskInfo.attribs` — the source
# `vigilai list --brazil` and the report's registry fallback both read. The two views of the same
# task would disagree, with no error anywhere. Write the literal; a test pins it against the data.
# Both traps apply to `prompt_mode` (Resolution 9): the signature default below is the literal
# `"unguided"` and NOT `PROMPT_MODE_UNGUIDED`, and if a later phase ever carries the mode as a
# decorator attrib it must be written as a literal there too, never as `"|".join(PROMPT_MODES)`.
@task(
    technical_requirement="Societal Alignment",
    brazil_article="Arts. 25-28",
    brazil_scope="high_risk",
    # The gap-flagging item ids, carried on the **decorator** so they land in the log header and
    # `vigilai report` can mark them without ever reading a sample (the aggregator is
    # deliberately header-only).
    brazil_gap_items=(
        "human_review_gap_lgpd20,pix_fraud_blocking_no_analogue,ai_interaction_disclosure_gap"
    ),
)
def aia_checklist(
    sector: str | None = None, split: str = "all", prompt_mode: str = "unguided"
) -> Task:
    """Brazil PL 2338/2023 Arts. 25-28 Algorithmic Impact Assessment awareness task.

    Prompts the model to lay out the AIA obligations a concrete Brazilian high-risk deployment
    must meet and scores the response by the fraction of the applicable checklist items it
    covers, using the deterministic (non-LLM-judge) :func:`aia_checklist_scorer`.

    **Run both prompt modes; the delta between them is a result, not a diagnostic.** The
    ``"guided"`` frame hands the model the list of obligations, so the rendered prompt scores
    0.9444 against its own scorer — a model that restates it is credited with 17 of 18 items.
    The ``"unguided"`` default states the legal basis and asks what it requires, which is the
    question the paper actually poses. Expect unguided scores to be far lower; a low score is a
    publishable finding, because it is evidence that Brazil-specific obligations are not covered
    by models trained on EU/US material.

    Args:
        sector: ``None`` (default) runs every sector that has deployer scenarios; pass a
            :data:`~vigilai.tasks.aia_checklist.checklist.SECTORS` key
            (``--task-arg aia_checklist:sector=finance_bacen``) to run one overlay on its own.
            Each sample is scored on the six cross-sector PL 2338 items **plus** its sector's
            overlay items. Note the CLI arg format is ``task_name:key=value``; a bare
            ``key=value`` is silently ignored.
        split: ``"all"`` (default) runs every variant; ``"held_out"`` runs the one reserved
            variant per sector that the Phase 6 LLM judge grades; ``"train"`` runs the rest.
        prompt_mode: ``"unguided"`` (default, the headline condition) or ``"guided"``
            (``--task-arg aia_checklist:prompt_mode=guided``). The scored item set is identical
            in both, so the two runs differ only in the frame. **Send the two runs to different
            ``--log-dir``s:** ``vigilai report`` keys task scores by task name and the later log
            silently overwrites the earlier one, so one dir would report a single, unlabelled
            ``aia_checklist`` row.
    """
    return Task(
        dataset=aia_checklist_dataset(sector, split, prompt_mode),
        solver=[generate()],
        scorer=aia_checklist_scorer(),
    )


__all__ = [
    "AIA_CHECKLIST",
    "AIA_SCENARIOS",
    "AIADeployerScenario",
    "DEPLOYER_PROVENANCE_PREFIX",
    "PILOT_PROVENANCE",
    "PROMPT_MODE_GUIDED",
    "PROMPT_MODE_UNGUIDED",
    "PROMPT_MODES",
    "SECTOR_REGIME_PT",
    "aia_checklist",
    "aia_checklist_dataset",
    "aia_scenarios",
    "resolve_prompt_mode",
]
