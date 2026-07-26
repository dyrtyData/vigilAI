"""Deployer scenarios for the ``aia_checklist`` benchmark — a leaf data module.

Why this is a separate module and not part of ``aia_checklist.py``
------------------------------------------------------------------

**A forced deviation from the structure outline, discovered by running the task.** Inspect loads
a ``@task``-bearing file *by path* (``inspect_ai/_util/module.py::load_module``) without
registering it in ``sys.modules``. A ``@dataclass`` declared in such a file, under
``from __future__ import annotations``, therefore blows up inside CPython's own
``dataclasses._is_type``, which does ``sys.modules.get(cls.__module__).__dict__`` and gets
``None``::

    AttributeError: 'NoneType' object has no attribute '__dict__'

The failure is at *task discovery* time — ``vigilai eval --tasks aia_checklist`` cannot even
load — and it is invisible to a plain ``import``, because a normal import does register the
module. It is the same shape as the import-cycle deviations Phases 2 and 3 hit, and it is fixed
the same way: the dataclass lives in a **leaf module** that is only ever imported normally, which
is why ``bbq_brazil``, ``explanation_quality`` and ``contestation_review`` each already have a
``scenario.py``. This module makes ``aia_checklist`` consistent with all three.

**What Phase 5 actually cost, recorded because the phase's success criterion is a diff shape.**
The eight new scenarios and the two new sectors' items are pure data, exactly as predicted, and
**nothing in ``src/vigilai/report/`` or in the scorer moved**. Two lines of ``aia_checklist.py``
did have to move, and both were forced rather than chosen: the ``brazil_gap_items`` decorator
attrib is a **literal** by an earlier cross-phase correction, so two new gap items had to be
written into it; and Resolution 10's per-scenario ``expected_items`` needed the dataset to call
:func:`items_for_scenario` for the scored set while the guided frame keeps rendering
``items_for_sector``. The outline's own Phase 5 checkbox names ``aia_checklist.py`` as in scope
for precisely this reason.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigilai.tasks.aia_checklist.checklist import AIA_CHECKLIST
from vigilai.tasks.aia_checklist.checklist import AIAItem
from vigilai.tasks.aia_checklist.checklist import items_by_id
from vigilai.tasks.aia_checklist.checklist import resolve_sector
from vigilai.tasks.aia_checklist.checklist import SECTOR_CAPITAL
from vigilai.tasks.aia_checklist.checklist import SECTOR_FINANCE
from vigilai.tasks.aia_checklist.checklist import SECTOR_HEALTH
from vigilai.tasks.aia_checklist.checklist import SECTORS
from vigilai.tasks.rubric_scenario import resolve_split
from vigilai.tasks.rubric_scenario import SPLIT_ALL
from vigilai.tasks.rubric_scenario import SPLIT_HELD_OUT


# ---------------------------------------------------------------------------------------
# Prompt-mode vocabulary (Resolution 9, 2026-07-25).
#
# The task ships **two prompt frames** and both are run, because the difference between them is
# itself the result:
#
# * ``"unguided"`` — the default and the headline number. Role + deployer scenario + the legal
#   basis (PL 2338/2023 Arts. 25-28 and the sector's regime) + "explain the applicable
#   obligations completely". **No enumerated item list.** This measures what the paper claims:
#   whether the model knows what a Brazilian AIA must contain.
# * ``"guided"`` — the iteration-1 / Phase-4 frame, kept verbatim and labelled. It enumerates
#   every applicable item's ``description``, which is why its **prompt-echo floor is 0.9444**:
#   the rendered prompt, scored as if it were the answer, covers 17 of 18 finance items. Keeping
#   it makes the floor measurable rather than asserted, and keeps a comparable to iteration 1.
#
# The delta between the two conditions is the reportable quantity — how much of a score is
# knowledge and how much is restatement — and it is the same question Phase 6's judge asks about
# the rubric tasks. Both floors are pinned by ``tests/test_aia_checklist.py::TestPromptEchoFloor``.
# ---------------------------------------------------------------------------------------

#: No item list: the model is given the legal basis and asked what it requires.
PROMPT_MODE_UNGUIDED = "unguided"

#: The enumerated-topics frame, preserved from iteration 1 / Phase 4.
PROMPT_MODE_GUIDED = "guided"

#: Every accepted ``prompt_mode``, in report order (headline condition first).
PROMPT_MODES: tuple[str, ...] = (PROMPT_MODE_UNGUIDED, PROMPT_MODE_GUIDED)


def resolve_prompt_mode(prompt_mode: str) -> str:
    """Validate a ``prompt_mode``, or raise naming the accepted values.

    Raises rather than falling back, for the reason Resolution 2 gives for ``bbq_brazil``'s
    ``split``: a run that silently degrades to the *other* condition would publish a number
    labelled with the mode it did not use, and the two conditions differ by ~0.9 of the score.
    """
    if prompt_mode in PROMPT_MODES:
        return prompt_mode
    raise ValueError(
        f"unknown prompt_mode {prompt_mode!r}; expected one of {list(PROMPT_MODES)}"
    )


#: Provenance carried by the iteration-1 single-sample prompt, so the pilot row stays
#: distinguishable from the iteration-2 deployer variants in the data itself and not only in
#: ``git blame`` — the same convention ``bbq_brazil`` and the two rubric tasks use.
PILOT_PROVENANCE = "hand-authored pilot (iteration 1)"

#: Prefix every iteration-2 deployer variant's provenance starts with.
DEPLOYER_PROVENANCE_PREFIX = "iteration-2 deployer variant"


# ---------------------------------------------------------------------------------------
# Per-scenario elicitation licences (Resolution 10, Phase 5).
#
# Phase 4 scored every sample against **all** of its sector's items regardless of what the
# deployment described, so five of the eighteen finance items were topical on exactly one of the
# four scenarios and the attainable ceiling was ~0.61-0.78 rather than 1.0. The guided frame hid
# that by naming every item in every prompt; the unguided frame exposed it. It is a **dataset**
# property — the scorer already resolves ``state.metadata["expected_items"]`` per sample — so the
# fix is data, and it lands here.
#
# Each scenario records, per **sector** item it is scored on, why that item is answerable from
# this deployment: either a **verbatim span** of its own ``deployment`` prose, or the marker
# :data:`FRAME_LICENCE` meaning the *task frame* raises it (an institution-wide duty that the
# unguided prompt's "quais obrigações essa organização precisa cumprir ... o que o regime setorial
# já exige dela hoje" reaches regardless of the deployment). This is the same span-or-frame shape
# the Phase 3 rubric licence audit uses, and it carries the same **parity rule**: the
# frame-licensed set must be identical across every scenario of a sector, so a dataset expansion
# cannot silently make one variant easier than its siblings.
#
# The six cross-sector PL 2338 items are **never** listed: the prompt cites Arts. 25-28 by number
# in both conditions, so they are frame-licensed for every scenario in every sector by
# construction, and :func:`items_for_scenario` prepends them.
# ---------------------------------------------------------------------------------------

#: Licence marker: the item is raised by the task frame rather than by this deployment's prose.
FRAME_LICENCE = "frame"


@dataclass(frozen=True)
class AIADeployerScenario:
    """One concrete high-risk deployment the model is asked to advise on.

    ``deployment`` is the only authored prose that reaches the prompt besides the checklist
    topic list. It is deliberately written **not** to contain any detection cue: a test scores
    ``deployment`` on its own with the real detector, against **every** item that exists rather
    than only its own sector's, and refuses a scenario that credits any of them. A scenario can
    therefore never hand the model a point the other variants make it earn. (The *topic list* is
    a different matter and is a known, measured property of this task — see the prompt-echo floor
    in ``checklist.py``.)

    Attributes:
        id: Stable machine key, also the Inspect ``Sample.id``.
        sector: One of :data:`~vigilai.tasks.aia_checklist.checklist.SECTORS`.
        deployment: The pt-BR description of what is being deployed and by whom.
        raises: The sector items this deployment can raise, as ``(item_id, licence)`` pairs, where
            the licence is either a **verbatim span** of ``deployment`` or :data:`FRAME_LICENCE`.
            This is the scored denominator (Resolution 10): the six cross-sector items plus
            exactly these. A pair list rather than a dict so the dataclass stays hashable and the
            authored order survives in the diff.
        held_out: True for the one variant per sector reserved for the Phase 6 judge.
        provenance: Where the scenario came from.
    """

    id: str
    sector: str
    deployment: str
    raises: tuple[tuple[str, str], ...] = ()
    held_out: bool = False
    provenance: str = DEPLOYER_PROVENANCE_PREFIX

    @property
    def raised_item_ids(self) -> tuple[str, ...]:
        """Just the sector item ids this deployment raises, in authored order."""
        return tuple(item_id for item_id, _ in self.raises)

    @property
    def frame_licensed_ids(self) -> frozenset[str]:
        """The sector items licensed by the task frame rather than by this deployment's prose."""
        return frozenset(
            item_id for item_id, licence in self.raises if licence == FRAME_LICENCE
        )


def items_for_scenario(scenario: AIADeployerScenario) -> list[AIAItem]:
    """The item set **one sample** is scored on: the cross-sector six plus what it raises.

    Resolution 10's denominator. Distinct from
    :func:`~vigilai.tasks.aia_checklist.checklist.items_for_sector`, which is the *whole* sector
    overlay and stays the guided frame's topic list — so the guided prompts are byte-identical to
    what Phase 4 shipped while the scored set narrows in **both** conditions together, as
    Resolution 9 constraint (d) requires.
    """
    return items_by_id(
        [item.id for item in AIA_CHECKLIST] + list(scenario.raised_item_ids)
    )


# ---------------------------------------------------------------------------------------
# The scenarios.
#
# Four per sector, twelve in all; the last of each sector is the held-out variant the Phase 6 LLM
# judge grades (3 of 12).
#
# The first finance scenario deliberately restates the iteration-1 pilot situation (a generic
# high-risk deployment, narrowed to a bank) so the n=1 → n=4 change is not confounded with a
# wholesale change of subject; it carries ``PILOT_PROVENANCE`` to say so.
#
# Every deployment is phrased so that the *automated* character of the decision is explicit
# ("sem participação de um funcionário", "de forma inteiramente automática"), because that is
# what makes the deployment high-risk under PL 2338 and what the AIA is being asked about.
#
# **Every deployment is also written to contain no detection cue at all** — the leakage guard
# scores each one alone against *every* item that exists, across all three sectors, and requires
# zero hits. That is why several obvious words are avoided on purpose: *prévia* (satisfies
# ``timing`` next to *operação*), *operador* and *fornecedor* (``who_conducts``), *ouvidoria*,
# *supervisão humana*, *revisão*, and *classe de risco*.
#
# ``raises`` is the Resolution 10 denominator; see the licence block above.
# ---------------------------------------------------------------------------------------

#: The finance items every finance deployment raises through the frame rather than through its own
#: prose: duties of the **institution** rather than of the particular system. The parity rule
#: requires this set to be identical across all four finance scenarios.
_FINANCE_FRAME_ITEMS: tuple[tuple[str, str], ...] = (
    ("ouvidoria_channel", FRAME_LICENCE),
    ("cybersecurity_cloud_vendor_accountability", FRAME_LICENCE),
    ("integrated_risk_management_framework", FRAME_LICENCE),
)

#: Capital markets: the information-security / cybersecurity duty attaches to any CVM-regulated
#: entity, intermediary or portfolio manager alike, so it is frame-licensed in all four.
_CAPITAL_FRAME_ITEMS: tuple[tuple[str, str], ...] = (
    ("intermediary_infosec_cyber_policy", FRAME_LICENCE),
)

#: Health has **no** frame-licensed item, and that is a finding rather than an omission. The
#: health overlay splits cleanly into medical-device duties (ANVISA), physician duties (CFM) and
#: health-plan duties (ANS), and no deployment raises all three: a prior-authorisation engine at a
#: plan operator is not a medical device and is not physician-mediated, so it shares no sector
#: item with the three clinical deployments. The parity rule therefore forces the empty set.
_HEALTH_FRAME_ITEMS: tuple[tuple[str, str], ...] = ()

AIA_SCENARIOS: list[AIADeployerScenario] = [
    # -- Finance / BACEN (Phase 4 scenarios; ``raises`` retrofitted in Phase 5) --------------
    AIADeployerScenario(
        id="finance_credit_scoring",
        sector=SECTOR_FINANCE,
        deployment=(
            "Um banco múltiplo brasileiro vai implantar um sistema de aprendizado de máquina "
            "que decide, sem participação de um funcionário, quais pedidos de empréstimo "
            "pessoal são aceitos e qual taxa é oferecida a cada solicitante."
        ),
        raises=_FINANCE_FRAME_ITEMS
        + (
            ("cadastro_positivo_criteria_disclosure", "qual taxa é oferecida a cada solicitante"),
            (
                "cadastro_positivo_contestation",
                "quais pedidos de empréstimo pessoal são aceitos",
            ),
            ("credit_model_governance", "um sistema de aprendizado de máquina que decide"),
            ("human_review_gap_lgpd20", "sem participação de um funcionário"),
        ),
        provenance=PILOT_PROVENANCE,
    ),
    AIADeployerScenario(
        id="finance_pix_fraud_blocking",
        sector=SECTOR_FINANCE,
        deployment=(
            "Uma instituição de pagamento vai implantar um modelo antifraude que interrompe "
            "transferências instantâneas em tempo real, de forma inteiramente automática, "
            "sempre que classifica a transferência como suspeita."
        ),
        raises=_FINANCE_FRAME_ITEMS
        + (
            ("pix_med_contestation", "transferências instantâneas em tempo real"),
            ("fraud_data_sharing_due_process", "um modelo antifraude"),
            ("human_review_gap_lgpd20", "de forma inteiramente automática"),
            ("pix_fraud_blocking_no_analogue", "classifica a transferência como suspeita"),
        ),
    ),
    AIADeployerScenario(
        id="finance_service_assistant",
        sector=SECTOR_FINANCE,
        deployment=(
            "Uma financeira vai substituir a maior parte do seu atendimento por um modelo de "
            "linguagem que negocia dívidas, oferece condições de parcelamento e encerra o "
            "diálogo sem passar por um atendente."
        ),
        raises=_FINANCE_FRAME_ITEMS
        + (
            ("human_review_gap_lgpd20", "encerra o diálogo sem passar por um atendente"),
            (
                "ai_interaction_disclosure_gap",
                "substituir a maior parte do seu atendimento por um modelo de linguagem",
            ),
        ),
    ),
    AIADeployerScenario(
        id="finance_open_finance_offers",
        sector=SECTOR_FINANCE,
        deployment=(
            "Uma fintech vai usar extratos e histórico de pagamentos recebidos de outras "
            "instituições para gerar automaticamente ofertas de empréstimo, calibrando limite e "
            "taxa a partir desses dados sem revisão de um funcionário."
        ),
        raises=_FINANCE_FRAME_ITEMS
        + (
            ("cadastro_positivo_criteria_disclosure", "calibrando limite e taxa"),
            ("cadastro_positivo_contestation", "extratos e histórico de pagamentos"),
            ("credit_model_governance", "gerar automaticamente ofertas de empréstimo"),
            (
                "open_finance_consent_automated_credit",
                "recebidos de outras instituições",
            ),
            ("human_review_gap_lgpd20", "sem revisão de um funcionário"),
        ),
        held_out=True,
    ),
    # -- Health / ANVISA + CFM + ANS (Phase 5) -------------------------------------------------
    AIADeployerScenario(
        id="health_diagnostic_imaging",
        sector=SECTOR_HEALTH,
        deployment=(
            "Um hospital privado brasileiro vai implantar em seu serviço de radiologia um "
            "programa de computador que analisa exames de imagem do tórax, emite o laudo "
            "preliminar e define a ordem em que os pacientes serão chamados, sem que alguém "
            "confira cada caso."
        ),
        raises=_HEALTH_FRAME_ITEMS
        + (
            (
                "samd_risk_classification_disclosed",
                "um programa de computador que analisa exames de imagem do tórax",
            ),
            ("clinical_validation_evidence", "emite o laudo preliminar"),
            (
                "tecnovigilancia_adverse_event_reporting",
                "vai implantar em seu serviço de radiologia",
            ),
            ("cybersecurity_lifecycle_management", "um programa de computador"),
            ("clinician_human_oversight_override", "sem que alguém confira cada caso"),
            ("patient_ai_disclosure", "define a ordem em que os pacientes serão chamados"),
            (
                "algorithmic_bias_monitoring_health",
                "define a ordem em que os pacientes serão chamados",
            ),
            ("contestability_second_opinion_health", "emite o laudo preliminar"),
            (
                "health_aia_public_conclusions_disclosure",
                "Um hospital privado brasileiro vai implantar em seu serviço de radiologia",
            ),
        ),
    ),
    AIADeployerScenario(
        id="health_adaptive_monitoring",
        sector=SECTOR_HEALTH,
        deployment=(
            "Uma fabricante de equipamentos hospitalares vai distribuir a unidades de terapia "
            "intensiva um sistema que prevê a piora do quadro do paciente e dispara alertas à "
            "equipe, e que passa a ser reajustado toda semana com os dados coletados em cada "
            "unidade."
        ),
        raises=_HEALTH_FRAME_ITEMS
        + (
            (
                "samd_risk_classification_disclosed",
                "um sistema que prevê a piora do quadro do paciente",
            ),
            (
                "clinical_validation_evidence",
                "prevê a piora do quadro do paciente e dispara alertas à equipe",
            ),
            (
                "tecnovigilancia_adverse_event_reporting",
                "vai distribuir a unidades de terapia intensiva",
            ),
            (
                "software_update_retraining_notification",
                "reajustado toda semana com os dados coletados em cada unidade",
            ),
            ("cybersecurity_lifecycle_management", "Uma fabricante de equipamentos hospitalares"),
            ("clinician_human_oversight_override", "dispara alertas à equipe"),
            ("algorithmic_bias_monitoring_health", "os dados coletados em cada unidade"),
            (
                "health_aia_public_conclusions_disclosure",
                "vai distribuir a unidades de terapia intensiva",
            ),
        ),
    ),
    AIADeployerScenario(
        id="health_plan_prior_authorization",
        sector=SECTOR_HEALTH,
        deployment=(
            "Uma operadora de plano de saúde vai passar a decidir por um modelo estatístico, "
            "sem que alguém analise o caso, quais pedidos de autorização de procedimento são "
            "aceitos e quais são recusados."
        ),
        # The thinnest overlay of the twelve, and deliberately so: a prior-authorisation engine at
        # a health-plan operator is **not** a medical device (so no ANVISA duty attaches) and is
        # **not** physician-mediated (so CFM Res. 2.454/2026, which binds *médicos*, does not reach
        # it either). What is left is the ANS pair. That thinness is the finding — the same
        # deployment in a hospital would carry nine sector items.
        raises=_HEALTH_FRAME_ITEMS
        + (
            (
                "coverage_denial_written_justification_ans",
                "quais pedidos de autorização de procedimento são aceitos e quais são recusados",
            ),
            ("coverage_denial_appeal_ombudsman_ans", "quais são recusados"),
        ),
    ),
    AIADeployerScenario(
        id="health_telemedicine_intake",
        sector=SECTOR_HEALTH,
        deployment=(
            "Uma plataforma de telemedicina vai usar um assistente de conversa para conduzir a "
            "anamnese, sugerir a hipótese diagnóstica e preencher a prescrição, que o "
            "profissional apenas assina ao final da consulta."
        ),
        raises=_HEALTH_FRAME_ITEMS
        + (
            ("samd_risk_classification_disclosed", "sugerir a hipótese diagnóstica"),
            (
                "clinical_validation_evidence",
                "sugerir a hipótese diagnóstica e preencher a prescrição",
            ),
            (
                "tecnovigilancia_adverse_event_reporting",
                "Uma plataforma de telemedicina vai usar um assistente de conversa",
            ),
            (
                "clinician_human_oversight_override",
                "que o profissional apenas assina ao final da consulta",
            ),
            ("patient_ai_disclosure", "um assistente de conversa para conduzir a anamnese"),
            ("algorithmic_bias_monitoring_health", "sugerir a hipótese diagnóstica"),
            ("contestability_second_opinion_health", "preencher a prescrição"),
            ("health_aia_public_conclusions_disclosure", "Uma plataforma de telemedicina"),
        ),
        held_out=True,
    ),
    # -- Capital markets / CVM (Phase 5) -------------------------------------------------------
    AIADeployerScenario(
        id="capital_robo_advisor",
        sector=SECTOR_CAPITAL,
        deployment=(
            "Uma administradora de carteiras vai passar a montar e rebalancear as carteiras dos "
            "seus clientes de varejo por um modelo proprietário, sem que uma pessoa aprove cada "
            "movimentação."
        ),
        raises=_CAPITAL_FRAME_ITEMS
        + (
            ("algo_source_code_disclosure_cvm", "por um modelo proprietário"),
            ("algo_accountability_retention", "sem que uma pessoa aprove cada movimentação"),
            ("suitability_profile_match", "as carteiras dos seus clientes de varejo"),
            (
                "sandbox_experimental_authorization",
                "por um modelo proprietário, sem que uma pessoa aprove cada movimentação",
            ),
            (
                "algo_impact_public_disclosure_gap_cvm",
                "Uma administradora de carteiras",
            ),
            ("ai_recommendation_disclosure_gap_cvm", "clientes de varejo"),
        ),
    ),
    AIADeployerScenario(
        id="capital_advisor_recommendation_engine",
        sector=SECTOR_CAPITAL,
        deployment=(
            "Uma plataforma ligada a uma corretora vai gerar por um modelo de linguagem as "
            "recomendações personalizadas enviadas a cada cliente e os resumos de mercado que as "
            "acompanham, sem que uma pessoa leia o texto enviado."
        ),
        raises=_CAPITAL_FRAME_ITEMS
        + (
            (
                "suitability_profile_match",
                "as recomendações personalizadas enviadas a cada cliente",
            ),
            ("ombudsman_redress_channel", "Uma plataforma ligada a uma corretora"),
            ("advisor_conflict_and_fee_disclosure", "Uma plataforma ligada a uma corretora"),
            (
                "analyst_report_conflict_disclosure",
                "os resumos de mercado que as acompanham",
            ),
            ("algo_impact_public_disclosure_gap_cvm", "por um modelo de linguagem"),
            (
                "ai_recommendation_disclosure_gap_cvm",
                "recomendações personalizadas enviadas a cada cliente",
            ),
        ),
    ),
    AIADeployerScenario(
        id="capital_broker_execution_model",
        sector=SECTOR_CAPITAL,
        deployment=(
            "Uma corretora vai passar a enviar as ordens dos seus clientes por um algoritmo que "
            "aprende sozinho quando e a que preço executar, sem que uma pessoa confira cada "
            "envio."
        ),
        # Res. CVM 21 Art. 19 is scoped to *administração de carteiras*, not to broker execution,
        # so neither source-code inspection nor the accountability clause is raised here — doc 12
        # records that no CVM instrument licenses or even defines algorithmic trading. Three
        # sector items plus the frame one is the honest set.
        raises=_CAPITAL_FRAME_ITEMS
        + (
            ("ombudsman_redress_channel", "as ordens dos seus clientes"),
            (
                "market_manipulation_tech_neutral",
                "um algoritmo que aprende sozinho quando e a que preço executar",
            ),
            ("algo_impact_public_disclosure_gap_cvm", "por um algoritmo que aprende sozinho"),
        ),
    ),
    AIADeployerScenario(
        id="capital_fund_vendor_model",
        sector=SECTOR_CAPITAL,
        deployment=(
            "Uma gestora de recursos com ações listadas em bolsa vai contratar de outra empresa "
            "o modelo que define a alocação dos fundos que administra, ficando apenas com o "
            "acompanhamento dos resultados."
        ),
        raises=_CAPITAL_FRAME_ITEMS
        + (
            (
                "algo_source_code_disclosure_cvm",
                "o modelo que define a alocação dos fundos que administra",
            ),
            ("algo_accountability_retention", "ficando apenas com o acompanhamento dos resultados"),
            (
                "fund_essential_provider_accountability",
                "contratar de outra empresa o modelo que define a alocação dos fundos",
            ),
            ("ai_vendor_procurement_diligence_selfreg", "vai contratar de outra empresa o modelo"),
            ("risk_factor_public_disclosure", "com ações listadas em bolsa"),
            (
                "algo_impact_public_disclosure_gap_cvm",
                "Uma gestora de recursos com ações listadas em bolsa",
            ),
            ("ai_recommendation_disclosure_gap_cvm", "a alocação dos fundos que administra"),
        ),
        held_out=True,
    ),
]


def aia_scenarios(sector: str | None = None, split: str = SPLIT_ALL) -> list[AIADeployerScenario]:
    """The deployer scenarios for ``sector`` (all sectors when ``None``), filtered by ``split``.

    Ordering is **interleaved by sector** — round-robin in :data:`SECTORS` order, preserving
    order inside each sector — for the same reason ``bbq_brazil`` interleaves by category and the
    rubric tasks by domain: ``--limit N`` takes the *first* N samples, so a sector-grouped order
    would make a truncated run silently single-sector while still reporting a "per-sector"
    picture. Interleaved, every prefix of 3k samples holds exactly k per sector, and because the
    held-out variant is the last of each sector the held-out slice is exactly the tail.

    Raises:
        ValueError: for an unknown sector or split, or for a **known** sector that has no
            scenarios. Every sector has had scenarios since Phase 5, so that branch is now
            unreachable from the shipped data — it is kept because a 0-sample run that reports
            nothing is the worse failure (the same call Resolution 2 made for ``bbq_brazil``),
            and a test drives it against a stubbed scenario list rather than deleting it.
    """
    resolve_sector(sector)
    resolve_split(split, task="aia_checklist")

    wanted = SECTORS if sector is None else (sector,)
    buckets = {key: [s for s in AIA_SCENARIOS if s.sector == key] for key in wanted}
    if sector is not None and not buckets[sector]:
        available = sorted({s.sector for s in AIA_SCENARIOS})
        raise ValueError(
            f"sector {sector!r} has no deployer scenarios yet; Phase 5 of the iteration-2 "
            f"structure outline adds the health and capital-markets variants. "
            f"Available now: {available}"
        )

    ordered: list[AIADeployerScenario] = []
    for position in range(max((len(bucket) for bucket in buckets.values()), default=0)):
        for key in wanted:
            bucket = buckets[key]
            if position < len(bucket):
                ordered.append(bucket[position])

    if split == SPLIT_ALL:
        return ordered
    want_held_out = split == SPLIT_HELD_OUT
    return [s for s in ordered if s.held_out == want_held_out]
