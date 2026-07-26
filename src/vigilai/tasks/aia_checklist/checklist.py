"""Brazil PL 2338/2023 Arts. 25-28 — Algorithmic Impact Assessment (AIA) checklist + scorer.

This module is the heart of the ``aia_checklist`` benchmark. Brazil's PL 2338/2023 requires
operators of high-risk AI to conduct an **Avaliação de Impacto Algorítmico (AIA)** — a
*fundamental-rights* impact assessment (risks **and** benefits), distinct from the EU's
market-conformity certification (research §5). The benchmark tests whether a model, asked to
lay out the AIA obligations, demonstrates awareness of the items the law requires.

Design decision — **keep the AIA representation data-driven, not a hard-coded ANPD format**
(design discussion §10.3 / research §10.3). Arts. 25-28 delegate the detailed AIA methodology
to future ANPD *Instruções Normativas*. So instead of baking one fixed checklist into the
scorer, we externalize the requirement items into editable data structures
(:data:`AIA_CHECKLIST` for the cross-sector obligations, :data:`SECTOR_ITEMS` for the sector
overlays). Each item is self-contained — it carries its own id, description, the governing
article, the instrument it is drawn from, and the multilingual detection cues used to decide
whether a response covers it. **The scorer iterates over whatever items the sample asks for.**
A future ANPD item can therefore be added by appending one :class:`AIAItem` — no change to the
scorer or the task code is required (this is exactly the flexibility the manual verification
checks, and :class:`~tests.test_aia_checklist.TestDataDrivenExtensibility` pins it).

The cross-sector seed items reflect research §5 ("Algorithmic Impact Assessment (AIA) vs. EU
Conformity Assessment"):

* **who conducts** it — developer or applier by chain role (Art. 25);
* **timing** — pre-market + continuous over the lifecycle + after significant change
  (Art. 26);
* **required documentation** — fundamental-rights risks/benefits and mitigation measures
  with their effectiveness (Art. 25 §1);
* **public conclusions** — the AIA conclusions are public, trade/industrial secrets aside
  (Art. 28);
* **RIPD joint preparation** — the AIA may be prepared jointly with the LGPD Data Protection
  Impact Report / RIPD (Art. 27);
* **post-incident notification & public database** — notify the authority, chain actors and
  potentially affected persons (Art. 25 §7), feeding the public high-risk AI database
  (Art. 44).

Detection is deterministic (**no LLM judge**, consistent with the Phase 5 rubric scorer) and
**multilingual (pt-BR + English)** because the benchmark prompts in a Brazilian context but a
model may answer in either language. An item counts as covered when the (accent-folded,
lower-cased) response contains a sufficiently strong combination of its cues — see
:func:`_item_covered`. The score is the **fraction of applicable checklist items covered**
(0.0-1.0), with per-item booleans recorded in ``Score.metadata`` for inspection.

The sector dimension (Phase 4)
------------------------------

An :class:`AIAItem` carries an optional ``sector``. ``None`` means **cross-sector** (the six
seed items above, which every sample is scored on); a value from :data:`SECTORS` means the item
belongs to one regulator's overlay and is scored **only in that sector's samples**.
:func:`items_for_sector` assembles the applicable set, and the scorer resolves it **per sample**
from ``state.metadata["expected_items"]``, falling back to :data:`AIA_CHECKLIST` when the
metadata is absent.

**Every sector item is a *de facto* analogue, never an AI-specific rule.** No Brazilian sector
regulator has issued a binding AI rule (doc 12, Part 1 Summary): what exists is a lattice of
adjacent, binding obligations — ombudsman duties, credit-model governance, Cadastro Positivo
rights — that function as sectoral stand-ins for PL 2338's rights. Three finance items are
**gap-flagging** (:data:`ITEM_GAP`): they test whether a deployer *voluntarily exceeds* a duty
that no instrument imposes, so a low score there is a **regulatory** finding about the sector,
not only a finding about the model. Every item records its instrument, a primary-source URL and
a sourcing tier; the full verification record — with operative quotes — is
``docs/sector-overlay-legal-verification.md``. **None of this is legal advice.**

Cue matching is **word-bounded** (Phase 4 fix, 2026-07-25)
----------------------------------------------------------

``_group_matches`` folded accents and matched by plain substring, exactly as the two rubric
scorers did before the Phase 3 sweep. A group is an **AND** of its cues, which is structurally
safer than the rubric scorers' flat OR — but **48 of this module's 80 cue groups held a single
cue**, so for those there was no conjunction to protect anything. The same structural fix is
applied here: :func:`_contains_any` matches a **single-token** cue only on word boundaries.
Instances closed by the boundary rule alone:

===================  ==========================  ==============================================
Cue                  Item                        Was matched inside
===================  ==========================  ==============================================
``"antes"``          ``timing``                  *constantes*, *importantes*, *instantes* —
                                                 "as informações **constantes** do relatório"
``"previa"``         ``timing``                  *previamente* (kept as its own cue)
``"continua"``       ``timing``                  *continuar* — "continuar o atendimento"
``"periodica"``      ``timing``                  *periodicamente* (now listed explicitly)
``"publica"``        ``public_conclusions``      *publicar*
``"public"``         ``public_conclusions``      *publicidade*, *publicar*, *publicly*
``"notific"``        ``incident_notification``   any *notificação de multa* (now enumerated)
===================  ==========================  ==============================================

A word boundary is **not** sufficient on its own, and the audit found a second class the Phase 3
sweep did not have to face: cues that are whole words but too *general* for the obligation they
stand for. Those are fixed by conjunction or removal, each with the reason recorded at the site:

=========================  ==========================  =========================================
Cue                        Item                        Why it was wrong / what replaced it
=========================  ==========================  =========================================
``("provider",)``          ``who_conducts``            *cloud provider* — and Phase 4 adds a
                                                       cloud-vendor item, so it was a
                                                       cross-item free score. Now needs a
                                                       chain/role conjunct.
``("operador",)``          ``who_conducts``            *o operador de telefonia*. Now needs a
                                                       chain/role/conducting conjunct.
``("segredo",)``           ``public_conclusions``      *segredo industrial* alone **refuses**
                                                       publication; naming the carve-out is not
                                                       coverage of the duty. Dropped as a
                                                       standalone group.
``("trade secret",)``      ``public_conclusions``      Same, in English. Dropped as standalone.
``("publicidade",)``       ``public_conclusions``      In pt-BR this reads as *advertising*
                                                       first — the ``"data"`` homograph problem
                                                       Phase 3 hit. **Removed outright.**
``("transparencia",)``     ``public_conclusions``      Every AIA answer says it, about anything.
                                                       Now needs a publication conjunct.
``("lgpd",)``              ``ripd_joint_preparation``  A bare LGPD mention is near-free in this
                                                       benchmark. Now needs a joint-report
                                                       conjunct.
``("protecao de dados",)`` ``ripd_joint_preparation``  Same.
``("antes",)``             ``timing``                  Whole-word *antes de tudo*. Now needs a
                                                       pre-deployment conjunct.
``("before",)``            ``timing``                  Whole-word *before you go*. Same.
``("mitigar",)``           ``risk_benefit_docum…``     *mitigar custos*. Now needs a
                                                       risk/impact/harm conjunct.
=========================  ==========================  =========================================

Word-bounded matching does not follow inflection, so forms previously caught by substring
accident are now listed **explicitly** (``continuamente``, ``periodicamente``, ``notificacao``,
…). Because several of this module's groups are genuine conjunctions, a conjunct often needs to
accept any of several surface forms; a cue may therefore hold ``|``-separated alternatives
(``"notificar|notificacao|notificada"``). :func:`_cue_alternatives` splits them and
:func:`_contains_any` applies the same word-boundary rule to each — the three helpers lifted
from ``explanation_quality.rubric`` are otherwise **verbatim**, so the two Art. 6 detectors and
this one behave consistently.

The prompt-echo floor, and the two prompt conditions (Resolution 9, 2026-07-25)
------------------------------------------------------------------------------

Unlike the rubric scorers, this task's prompt genuinely *was* built from ``item.description``, and
a description cannot state its obligation without using the obligation's own vocabulary — so the
rendered prompt, scored as if it were the answer, covered **17 of 18** finance items (**0.9444**).
The task was measuring whether a model can restate a list it was just handed, and iteration 1's
0.983 is essentially that floor.

Phase 4 recorded the figure and escalated the decision; the decision came back **fix it**. The task
now takes a ``prompt_mode`` and **both conditions are run**:

* ``"unguided"`` (default, headline) — role + deployer scenario + the legal basis (PL 2338/2023
  Arts. 25-28 and :data:`SECTOR_REGIME_PT`), **no item list**. Measured echo floor **0.0000**.
* ``"guided"`` — the old frame, byte-identical, floor **0.9444**, so the floor stays *measurable*
  and one condition stays comparable to iteration 1.

The guided↔unguided delta is a **reported result** — how much of a score is knowledge and how much
is restatement — the same question Phase 6's judge asks about the rubric tasks. Both floors are
pinned by ``tests/test_aia_checklist.py::TestPromptEchoFloor``, so a prompt edit that reintroduces
the leak fails the suite. **Every published ``aia_checklist`` figure remains superseded**, for three
independent reasons: n=1, this floor, and the 1.000 hostile-probe cue floor above.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field
from functools import lru_cache

from inspect_ai.scorer import grouped
from inspect_ai.scorer import mean
from inspect_ai.scorer import Score
from inspect_ai.scorer import Scorer
from inspect_ai.scorer import scorer
from inspect_ai.scorer import stderr
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState

from vigilai.tasks.judge import render_judge_instructions


# ---------------------------------------------------------------------------------------
# Sector vocabulary.
#
# One key per regulator whose adjacent, binding rules act as a *de facto* PL 2338 analogue.
# Phase 4 ships the finance/BACEN slice; Phase 5 appends health and capital markets as pure
# data (append to SECTOR_ITEMS below and to AIA_SCENARIOS in aia_checklist.py — no code change).
# ---------------------------------------------------------------------------------------
SECTOR_FINANCE = "finance_bacen"
SECTOR_HEALTH = "health_anvisa"
SECTOR_CAPITAL = "capital_cvm"

#: Every sector key the task and the report understand, in report order.
SECTORS: tuple[str, ...] = (SECTOR_FINANCE, SECTOR_HEALTH, SECTOR_CAPITAL)

#: Human-readable regulator label per sector (used by the report's overlay section header and
#: by the README table, so the two never drift).
SECTOR_LABELS: dict[str, str] = {
    SECTOR_FINANCE: "Finance — BACEN / CMN",
    SECTOR_HEALTH: "Health — ANVISA / CFM / ANS",
    SECTOR_CAPITAL: "Capital markets — CVM",
}

#: pt-BR naming of each sector's **regime** — the regulators and the body of rules whose
#: obligations the overlay items are drawn from. Used by the ``prompt_mode="unguided"`` frame
#: (``aia_checklist.py::_build_unguided_prompt``), which states the *legal basis* a compliance
#: consultant would work from and then asks for the obligations, instead of enumerating them.
#:
#: **The wording rule is load-bearing and a test enforces it: name the regulator and the field,
#: never an instrument or an obligation.** "as normas do Banco Central" is a legal basis; "a
#: resolução sobre ouvidoria" is a topic list with one entry. The whole point of the unguided
#: condition is that the enumeration is gone, so anything that smuggles an item back in
#: reintroduces the echo floor this mode exists to remove.
#:
#: **Phase 5 appends here** when it adds health and capital-markets scenarios — a test refuses a
#: sector that has scenarios but no regime phrase, so it cannot be forgotten.
SECTOR_REGIME_PT: dict[str, str] = {
    SECTOR_FINANCE: (
        "a regulação brasileira já vigente do sistema financeiro — as normas do Banco Central "
        "do Brasil e do Conselho Monetário Nacional aplicáveis a instituições financeiras e de "
        "pagamento, e a legislação de crédito e de defesa do consumidor que incide sobre elas"
    ),
    SECTOR_HEALTH: (
        "a regulação brasileira já vigente da saúde — as normas da ANVISA, do Conselho Federal "
        "de Medicina e da ANS aplicáveis a produtos e serviços de saúde"
    ),
    SECTOR_CAPITAL: (
        "a regulação brasileira já vigente do mercado de capitais — as normas da Comissão de "
        "Valores Mobiliários aplicáveis a intermediários, gestores e consultores"
    ),
}


def resolve_sector(sector: str | None) -> str | None:
    """Validate a sector key (``None`` = cross-sector only), or raise naming the accepted set."""
    if sector is None or sector in SECTORS:
        return sector
    raise ValueError(f"unknown sector {sector!r}; expected one of {list(SECTORS)} or None")


# ---------------------------------------------------------------------------------------
# Item status — the *regulatory character* of the obligation an item stands for.
#
# This is what lets a reader tell "the model failed" from "the law is silent". It reaches the
# report through the task decorator (``brazil_gap_items``), not through the sample metadata,
# because ``build_brazil_report`` is deliberately header-only.
# ---------------------------------------------------------------------------------------
#: A binding instrument imposes the duty.
ITEM_BINDING = "binding"
#: **No** instrument imposes the duty. Presence in a response means the deployer *voluntarily
#: exceeds* the baseline; absence is a finding about Brazilian law, not about the model.
ITEM_GAP = "gap"
#: An instrument states the expectation but declares itself non-binding (e.g. ANVISA Guia
#: 38/2020, *"caráter recomendatório e não vinculante"*). Phase 5 uses this.
ITEM_NON_BINDING = "non_binding"
#: Industry self-regulation, not a regulator's rule (e.g. the ANBIMA AI-procurement guide).
#: Phase 5 uses this.
ITEM_SELF_REGULATORY = "self_regulatory"
#: **Adopted, dated, and not yet effective.** Added in Phase 5 for CFM Res. 2.454/2026, whose own
#: Art. 23 puts it in force 180 days after publication — **26 August 2026**. It is neither
#: ``ITEM_BINDING`` (nothing is enforceable yet) nor ``ITEM_GAP`` (the duty exists and its
#: commencement date is fixed), and collapsing it into either would misstate Brazilian law in
#: opposite directions. A test requires every CFM-sourced item to carry it.
ITEM_NOT_YET_IN_FORCE = "not_yet_in_force"

ITEM_STATUSES: tuple[str, ...] = (
    ITEM_BINDING,
    ITEM_GAP,
    ITEM_NON_BINDING,
    ITEM_SELF_REGULATORY,
    ITEM_NOT_YET_IN_FORCE,
)


# ---------------------------------------------------------------------------------------
# Sourcing tier — how strong the verification behind an item's citation is.
#
# The Q8 verification gate (structure outline, Phase 4) requires every item's legal citation to
# be checked against a primary source before the item ships. Where that was not achievable the
# tier says so *in the data*, so the paper cannot silently promote a secondary source. The full
# record, with operative quotes, is docs/sector-overlay-legal-verification.md.
# ---------------------------------------------------------------------------------------
#: The operative text was read in an official primary source.
SOURCING_PRIMARY = "primary"
#: Independent professional sources converge, but the issuing body's own text was not reached.
SOURCING_CORROBORATED = "corroborated_secondary"
#: A material question about the instrument could not be resolved either way, and is stated as
#: an open question rather than answered.
SOURCING_OPEN = "open"

SOURCING_TIERS: tuple[str, ...] = (SOURCING_PRIMARY, SOURCING_CORROBORATED, SOURCING_OPEN)

#: The bill the six cross-sector items come from.
PL2338_URL = "https://www25.senado.leg.br/web/atividade/materias/-/materia/157233"


# ---------------------------------------------------------------------------------------
# The externalized checklist data structure.
#
# Each AIA requirement is one ``AIAItem``. To extend the checklist for a future ANPD
# Instrução Normativa, append a new ``AIAItem`` to ``AIA_CHECKLIST`` below — that is the
# *only* edit needed; the scorer and task iterate whatever this list contains.
# ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class AIAItem:
    """A single AIA requirement item the checklist tests for.

    The first four fields are the original, editable core: an item can still be written with
    ``AIAItem(id=…, article=…, description=…, any_of=…)`` and nothing else, which is what keeps
    the checklist a data structure an editor can extend. Everything added for the Phase 4 sector
    dimension is defaulted.

    Attributes:
        id: Stable machine key for the item (used in ``Score.metadata`` and tests).
        article: The governing PL 2338/2023 article(s), for documentation / the report.
        description: Human-readable statement of the obligation. Surfaced to the model **only in
            the ``"guided"`` prompt condition**, where the checklist is the single source of truth
            for *what is asked* as well as *what is scored* — and where it creates the 0.9444
            prompt-echo floor documented above. The default ``"unguided"`` condition never renders
            it, which is what takes that floor to 0.0000; a test asserts the negative.
        any_of: Cue groups; the item is covered when **at least one** group is fully matched.
            Each group is a tuple of cues that must **all** appear (accent-folded, lower-cased)
            in the response for that group to match. A cue may hold ``|``-separated surface
            forms, any one of which satisfies it. This "OR of ANDs" shape lets an item be
            satisfied by a pt-BR phrasing *or* an English phrasing *or* a strong single keyword,
            while still requiring genuine topical coverage (e.g. the timing item needs an actual
            timing cue, not just the word "impacto").
        sector: ``None`` for a cross-sector obligation drawn from PL 2338 itself; otherwise one
            of :data:`SECTORS`, meaning the item is scored **only** in that sector's samples.
        status: One of :data:`ITEM_STATUSES` — whether a binding instrument imposes the duty
            (:data:`ITEM_BINDING`), no instrument does (:data:`ITEM_GAP`), the instrument
            declares itself non-binding, or it is industry self-regulation.
        instrument: The naming instrument, e.g. ``"Res. CMN 4.860/2020"``. For a gap item this
            is the **nearest** instrument and what it stops short of, because a negative claim
            is only checkable if it names what it is negating.
        source_url: A primary-source URL for ``instrument``. The Q8 verification gate; a test
            refuses a sector item without one.
        sourcing: One of :data:`SOURCING_TIERS`.
    """

    id: str
    article: str
    description: str
    any_of: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    sector: str | None = None
    status: str = ITEM_BINDING
    instrument: str = "PL 2338/2023 (Senate-approved text, 10 Dec 2024)"
    source_url: str = PL2338_URL
    sourcing: str = SOURCING_PRIMARY

    @property
    def is_gap(self) -> bool:
        """True for a gap-flagging item — the ones whose low score is a regulatory finding."""
        return self.status == ITEM_GAP


# The seed AIA checklist (research §5) — the **cross-sector** obligations, drawn from PL
# 2338/2023 itself and therefore scored in every sample regardless of sector. Editable data;
# add/extend cross-sector items here only. Sector overlays live in ``SECTOR_ITEMS``.
AIA_CHECKLIST: list[AIAItem] = [
    AIAItem(
        id="who_conducts",
        article="Art. 25",
        description=(
            "Quem conduz a avaliação de impacto algorítmico — o desenvolvedor ou o "
            "operador/aplicador conforme o seu papel na cadeia de IA (who conducts the "
            "assessment: developer or applier, by their role in the AI chain)."
        ),
        any_of=(
            # Statutory PL 2338 chain roles: unambiguous on their own in this context.
            ("desenvolvedor|desenvolvedora|desenvolvedores",),
            ("aplicador|aplicadora|aplicadores",),
            ("agente|agentes", "cadeia"),
            # "operador" is also a telephony/machine operator in pt-BR, and "fornecedor" is any
            # vendor — both need a chain/role/conducting conjunct so an answer about a *supplier*
            # does not score "who conducts the AIA".
            (
                "operador|operadora|operadores",
                "cadeia|papel|conduz|conduzir|conduzida|realizar|elaborar|responsavel",
            ),
            ("fornecedor|fornecedora|fornecedores", "cadeia|papel|inteligencia artificial"),
            ("developer|developers",),
            ("applier|appliers",),
            ("deployer|deployers",),
            ("agent|agents", "chain"),
            # Bare "provider" matched *cloud provider*, and this phase adds a cloud-vendor item
            # to the finance overlay — so it was a free cross-item score. Needs a chain/role.
            ("provider|providers", "chain|role|ai system"),
            ("who|responsible", "conduct|conducts|conducted|conducting"),
        ),
    ),
    AIAItem(
        id="timing",
        article="Art. 26",
        description=(
            "Quando a avaliação deve ser realizada — antes da colocação no mercado, de forma "
            "contínua ao longo do ciclo de vida e após mudança significativa (timing: "
            "pre-market, continuously over the lifecycle, and after significant change)."
        ),
        any_of=(
            # "antes" / "before" are whole words in *antes de tudo* / *before you go*, so a bare
            # cue was not timing evidence; both now need a pre-deployment conjunct.
            (
                "antes|previamente|previa|previas|previo|previos",
                "mercado|implantacao|implementacao|disponibilizacao|colocacao|uso|lancamento"
                "|operacao",
            ),
            ("ciclo de vida",),
            # Boundary matching does not follow inflection: *continuamente* / *periodicamente*
            # used to be caught inside "continua" / "periodica" and are now listed explicitly.
            ("continua|continuas|continuo|continuos|continuamente",),
            ("periodica|periodicas|periodico|periodicos|periodicamente",),
            (
                "mudanca significativa|mudancas significativas|alteracao significativa"
                "|alteracoes significativas|modificacao significativa",
            ),
            ("pre-market",),
            (
                "before|prior",
                "market|deploy|deployment|release|launch|placed|placing|use|production",
            ),
            ("lifecycle|life cycle",),
            ("continuous|continuously|continual|continually",),
            ("ongoing",),
            ("significant change|significant changes|material change",),
        ),
    ),
    AIAItem(
        id="risk_benefit_documentation",
        article="Art. 25 §1",
        description=(
            "O que deve ser documentado — os riscos e benefícios aos direitos fundamentais e "
            "as medidas de mitigação e sua eficácia (required documentation: fundamental-"
            "rights risks and benefits, plus mitigation measures and their effectiveness)."
        ),
        any_of=(
            ("direitos fundamentais",),
            ("risco|riscos", "beneficio|beneficios"),
            (
                "risco|riscos",
                "direitos fundamentais|direitos humanos|direitos das pessoas"
                "|direitos dos titulares",
            ),
            ("medidas de mitigacao|medida de mitigacao|medidas mitigadoras",),
            # "mitigar custos" is not risk mitigation; the verb now needs a risk/impact/harm
            # object.
            (
                "mitigacao|mitigacoes|mitigar|mitigadoras",
                "risco|riscos|impacto|impactos|dano|danos|direitos",
            ),
            ("eficacia", "medida|medidas|mitigacao|controle|controles"),
            ("fundamental rights",),
            ("risk|risks", "benefit|benefits"),
            ("mitigation|mitigating|mitigate", "risk|risks|impact|impacts|harm|harms"),
            ("mitigation measures|mitigating measures",),
        ),
    ),
    AIAItem(
        id="public_conclusions",
        article="Art. 28",
        description=(
            "As conclusões da avaliação devem ser públicas, resguardados os segredos "
            "industrial e comercial (the assessment's conclusions must be made public, trade "
            "and industrial secrets aside)."
        ),
        any_of=(
            ("conclusoes|conclusao", "publica|publicas|publico|publicos|publicadas|divulgadas"),
            (
                "publicar|publicacao|publicada|publicadas|publicado|publicados",
                "conclusoes|conclusao|avaliacao|aia|resultados|relatorio",
            ),
            (
                "divulgacao|divulgar|divulgadas|divulgados",
                "conclusoes|conclusao|publica|publicas|publico|sociedade|resultados",
            ),
            # "transparência" is said by every AIA answer, about anything; it is only evidence of
            # the Art. 28 *publication* duty when it is attached to one.
            ("transparencia", "conclusoes|publica|publicas|publico|sociedade|divulgacao"),
            # Naming the trade-secret carve-out is not coverage of the duty it carves out of —
            # "não divulgamos por segredo industrial" used to score this item while refusing
            # publication. It counts only alongside the duty.
            (
                "segredo|segredos",
                "publica|publicas|publicar|publicacao|divulgacao|divulgar|conclusoes",
            ),
            ("conclusions", "public|publicly|published|disclose|disclosed|disclosure"),
            ("publish|published|publishing", "conclusion|conclusions|assessment|findings|results"),
            ("publicly", "available|disclosed|published|accessible|released"),
            ("trade secret|trade secrets", "public|publish|published|disclose|disclosure"),
        ),
    ),
    AIAItem(
        id="ripd_joint_preparation",
        article="Art. 27",
        description=(
            "A avaliação pode ser elaborada em conjunto com o relatório de impacto à "
            "proteção de dados pessoais (RIPD) da LGPD (the AIA may be prepared jointly with "
            "the LGPD Data Protection Impact Report / RIPD)."
        ),
        any_of=(
            ("ripd",),
            ("dpia",),
            ("relatorio de impacto", "protecao de dados"),
            # A bare "LGPD" or "proteção de dados" mention is near-free in a Brazilian AI
            # compliance answer; the item is about *joint preparation with the RIPD*, so the
            # jointness has to be present too.
            (
                "lgpd",
                "relatorio de impacto|ripd|conjunto|conjuntamente|unico documento|integrado",
            ),
            (
                "protecao de dados",
                "conjunto|conjuntamente|relatorio de impacto|ripd|unico documento",
            ),
            ("data protection impact assessment|data protection impact report",),
            ("data protection impact", "joint|jointly|together|combined|single"),
            ("jointly|together|combined", "data protection"),
        ),
    ),
    AIAItem(
        id="incident_notification",
        article="Art. 25 §7 / Art. 44",
        description=(
            "Após incidente, deve-se notificar a autoridade competente, os agentes da cadeia "
            "e as pessoas potencialmente afetadas, alimentando a base de dados pública de IA "
            "de alto risco (post-incident: notify the authority, chain actors and "
            "potentially affected persons; feeds the public high-risk AI database)."
        ),
        any_of=(
            # The old cue was the stem "notific", which a word boundary would never match; the
            # inflected forms are now enumerated.
            (
                "incidente|incidentes",
                "notificar|notificacao|notificacoes|notificada|notificadas|notificado"
                "|notificados|notifica|notificamos|comunicar|comunicacao|comunicado"
                "|comunicamos|comunica",
            ),
            ("anpd", "incidente|incidentes"),
            (
                "autoridade competente",
                "notificar|notificacao|notificamos|comunicar|comunicacao|comunicamos"
                "|informar|informamos|incidente|incidentes",
            ),
            ("pessoas afetadas|pessoas potencialmente afetadas|titulares afetados",),
            ("base de dados publica",),
            (
                "incident|incidents",
                "notify|notification|notifications|notified|notifying|report|reported",
            ),
            ("notify|notification|notified|notifying", "authority|authorities|regulator"),
            ("affected persons|affected individuals|affected people",),
            ("public database",),
        ),
    ),
]


# ---------------------------------------------------------------------------------------
# Sector overlay — finance / BACEN (Phase 4).
#
# Source: doc 12 "Research: Sector Overlays and Human-Rights Framing", Part 1, as corrected by
# the 2026-07-25 verification pass. **No BACEN rule regulates AI**; BACEN has said publicly it
# will not act before PL 2338 is enacted, and PL 2338 does not name BACEN. Every item below is a
# *de facto* analogue drawn from an adjacent, binding rule — a structural analogy for benchmark
# design, **not legal advice**.
#
# Each item records its instrument, a primary-source URL and a sourcing tier. The full record —
# operative quotes, what was checked, what remains open — is
# ``docs/sector-overlay-legal-verification.md``, and a test refuses an item that is not in it.
#
# bcb.gov.br is unreachable from this environment (connection timeout, reproducing the access
# problem doc 12 reports), so BACEN/CMN items carry the canonical `exibenormativo` URL, whose
# resolution was confirmed through a 200-status Internet Archive snapshot recorded in the
# verification doc alongside it.
# ---------------------------------------------------------------------------------------
_BCB_NORMATIVO = "https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo"

FINANCE_ITEMS: list[AIAItem] = [
    AIAItem(
        id="ouvidoria_channel",
        article="Art. 6, II (de facto analogue)",
        description=(
            "O canal de ouvidoria da instituição — última instância de atendimento, com prazo "
            "de resposta de 10 dias úteis (the institution's ombudsman channel as the final "
            "internal instance, answering within 10 business days)."
        ),
        # Res. CMN 4.860/2020 (23 Oct 2020). Art. 6 §2: 10 business days to respond, extendable
        # once, with extensions capped at 10% of the monthly volume of demands. Art. 22 revokes
        # Res. CMN 4.433/2015 **and** Res. CMN 4.629/2018.
        # NOT claimed: a minimum ombudsman term. Art. 8, III requires only that the term be
        # *stated in months*; doc 12's "≥1-yr mandate" is wrong and is corrected in the
        # verification doc.
        # Source: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #         ?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4860
        any_of=(
            ("ouvidoria|ouvidorias|ouvidor",),
            ("ombudsman",),
            ("10 dias uteis|dez dias uteis|prazo de 10 dias",),
            ("ultima instancia|instancia final",),
            ("10 business days|ten business days",),
            ("escalate|escalation", "complaint|complaints|grievance"),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument="Res. CMN 4.860/2020, Art. 6 §2 (ouvidoria; 10 business days)",
        source_url=(
            f"{_BCB_NORMATIVO}?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4860"
        ),
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="cadastro_positivo_criteria_disclosure",
        article="Art. 6, I (de facto analogue)",
        description=(
            "Divulgação dos principais elementos e critérios considerados na análise de risco "
            "de crédito, resguardado o segredo empresarial (disclosure of the main elements "
            "and criteria used in the credit risk analysis, trade secrecy aside)."
        ),
        # Lei 12.414/2011 Art. 5, IV (Cadastro Positivo), verbatim: "conhecer os principais
        # elementos e critérios considerados para a análise de risco, resguardado o segredo
        # empresarial". Inciso II (as amended by LC 166/2019) adds free access to one's own
        # score; §3 sets a 10-day disclosure deadline for incisos II and IV.
        # Implementing regulation: Decreto 9.936/2019.
        # Source: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12414.htm
        any_of=(
            ("cadastro positivo",),
            ("score de credito|escore de credito|nota de credito|pontuacao de credito",),
            (
                "criterio|criterios",
                "analise de risco|risco de credito|pontuacao|score|concessao",
            ),
            ("principais elementos|elementos considerados|elementos e criterios",),
            ("credit score|credit scoring",),
            ("risk analysis criteria|risk-analysis criteria|scoring factors|scoring criteria",),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument="Lei 12.414/2011, Art. 5, IV (as amended by LC 166/2019)",
        source_url="https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12414.htm",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="cadastro_positivo_contestation",
        article="Art. 6, II (de facto analogue)",
        description=(
            "Direito de impugnar informação erroneamente anotada e obter a sua correção ou "
            "cancelamento em até 10 dias, em todos os bancos de dados que a compartilharam "
            "(right to dispute a wrongly recorded entry and have it corrected or cancelled "
            "within 10 days across every database it was shared with)."
        ),
        # Lei 12.414/2011 Art. 5, III (redação da LC 166/2019), verbatim: "solicitar a
        # impugnação de qualquer informação sobre ele erroneamente anotada em banco de dados e
        # ter, em até 10 (dez) dias, sua correção ou seu cancelamento em todos os bancos de
        # dados que compartilharam a informação".
        # Source: https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12414.htm
        any_of=(
            ("impugnacao|impugnar|impugnado",),
            ("informacao incorreta|informacoes incorretas|dado incorreto|dados incorretos",),
            (
                "correcao|corrigir|corrigida|retificacao|cancelamento",
                "informacao|informacoes|dado|dados|cadastro|registro",
            ),
            ("dispute|disputing|challenge", "incorrect|inaccurate|erroneous|information|data"),
            ("correction|correct|rectification", "10 days|ten days|record|records|database"),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument="Lei 12.414/2011, Art. 5, III (as amended by LC 166/2019)",
        source_url="https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12414.htm",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="credit_model_governance",
        article="Arts. 25-28 (de facto analogue)",
        description=(
            "Governança do modelo de crédito — autorização prévia do supervisor para uso de "
            "sistemas internos de classificação de risco, validação independente do modelo e "
            "equipe qualificada para desenvolvê-lo, validá-lo e avaliá-lo (credit-model "
            "governance: prior supervisory authorisation for internal ratings systems, "
            "independent model validation, and qualified staff)."
        ),
        # Res. BCB 303/2023 (in force 1 Jul 2023). Art. 2 requires prior BCB authorisation to
        # use internal credit-risk rating systems (IRB) for capital purposes; the resolution
        # requires staffing qualified for the development, validation, evaluation, updating and
        # use of those systems. Art. 128 **revokes Circular BACEN 3.648/2013** — doc 12's "no
        # revocation clause found" is falsified; 3.648/2013 is cited here only as a superseded
        # predecessor and carries no duty.
        # Pillar-3 public disclosure is **not** in 303/2023; it lives in the companion
        # Res. BCB 306/2023, which is why the cue below names either.
        # Source: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #         ?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=303
        any_of=(
            ("modelo interno|modelos internos|sistema interno de classificacao",),
            ("irb",),
            ("validacao|validado|revalidacao", "modelo|modelos"),
            ("governanca", "modelo|modelos"),
            ("autorizacao previa", "banco central|bacen|bcb|supervisor|regulador"),
            ("pilar 3|pilar iii",),
            ("internal ratings-based|internal ratings based|internal rating system",),
            ("model validation|model governance|model risk",),
            ("pillar 3|pillar iii",),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument=(
            "Res. BCB 303/2023, Art. 2 (prior authorisation; model governance) "
            "— Pillar 3 disclosure: companion Res. BCB 306/2023"
        ),
        source_url=f"{_BCB_NORMATIVO}?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=303",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="pix_med_contestation",
        article="Art. 6, II (de facto analogue)",
        description=(
            "Contestação de um Pix fraudulento pelo Mecanismo Especial de Devolução — o "
            "pagador aciona a sua própria instituição, e o bloqueio cautelar retém os recursos "
            "na conta que os recebeu (contesting a fraudulent Pix through the Special Return "
            "Mechanism: the payer files with their own institution, and the precautionary "
            "block holds the funds in the receiving account)."
        ),
        # Res. BCB 103/2021 (MED) as replaced by Res. BCB 493/2025 ("MED 2.0", mandatory
        # 2 Feb 2026). Direction matters and is easy to get backwards: the **payer** initiates
        # through their own PSP; the *bloqueio cautelar* (up to 72 h) freezes funds in the
        # **receiving** account and is executed by the receiver's PSP.
        # Source: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #         ?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=103  (and &numero=493)
        any_of=(
            ("mecanismo especial de devolucao",),
            ("med", "pix|devolucao|bloqueio|fraude"),
            ("bloqueio cautelar",),
            ("pix", "devolucao|contestacao|contestar|reembolso|estorno|ressarcimento"),
            ("special return mechanism",),
            ("pix", "refund|reversal|return|contest|dispute|chargeback"),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument="Res. BCB 103/2021 → Res. BCB 493/2025 (MED 2.0, mandatory 2 Feb 2026)",
        source_url=f"{_BCB_NORMATIVO}?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=103",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="cybersecurity_cloud_vendor_accountability",
        article="Arts. 25-28 (de facto analogue)",
        description=(
            "Política de segurança cibernética e responsabilidade da instituição contratante "
            "pela infraestrutura de IA terceirizada ou em nuvem (cybersecurity policy, and the "
            "contracting institution remaining accountable for outsourced or cloud-hosted AI "
            "infrastructure)."
        ),
        # Res. CMN 4.893/2021 (26 Feb 2021), as amended by Res. CMN 5.274/2025 (18 Dec 2025,
        # compliance from 1 Mar 2026; companion Res. BCB 538/2025). The 2021 resolution revoked
        # Res. 4.658/2018 and 4.752/2019.
        # SOURCING: the 2025 amendment is **corroborated-secondary** — independent professional
        # sources converge on its date and compliance deadline, but bcb.gov.br's own text was
        # not reached. The 2021 base resolution is the binding anchor for this item.
        # Source: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #         ?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4893
        any_of=(
            ("politica de seguranca cibernetica",),
            (
                "seguranca cibernetica|seguranca da informacao",
                "nuvem|terceirizacao|terceirizados|terceiros|fornecedor|contratacao",
            ),
            ("computacao em nuvem|servicos em nuvem",),
            (
                "responsabilidade|responsavel",
                "instituicao contratante|terceirizacao|terceiros|nuvem|subcontratado",
            ),
            ("cloud computing|cloud services|cloud provider",),
            (
                "third-party|third party|outsourcing|outsourced|vendor",
                "accountable|accountability|responsible|responsibility|risk",
            ),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument="Res. CMN 4.893/2021 (am. Res. CMN 5.274/2025 + Res. BCB 538/2025)",
        source_url=f"{_BCB_NORMATIVO}?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4893",
        sourcing=SOURCING_CORROBORATED,
    ),
    AIAItem(
        id="integrated_risk_management_framework",
        article="Arts. 25-28 (de facto analogue)",
        description=(
            "Estrutura integrada de gerenciamento de riscos com declaração de apetite por "
            "riscos e um diretor de risco único, na qual a avaliação de um modelo não é feita "
            "pela unidade que o desenvolveu (integrated risk-management framework with a risk "
            "appetite statement and a single CRO, where a model is not evaluated by the unit "
            "that built it)."
        ),
        # Res. CMN 4.557/2017 (23 Feb 2017), as amended by Res. CMN 5.076/2023 and 5.077/2023.
        # Art. 64: a single CRO. Model evaluation may not be performed by the unit that
        # developed the model nor by a risk-taking unit. Chapter II is the RAS (declaração de
        # apetite por riscos).
        # Source (amending acts, since 4557 itself has no archived normativo page):
        #   https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #   ?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=5076
        any_of=(
            ("gerenciamento|gestao", "risco|riscos"),
            ("apetite por risco|apetite por riscos|apetite de risco|ras",),
            ("diretor de risco|diretor responsavel|cro",),
            ("unidade", "desenvolveu|desenvolvimento|independente|segregacao"),
            ("risk appetite|risk-appetite",),
            ("risk management", "framework|structure|integrated|policy|function"),
            ("chief risk officer",),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument="Res. CMN 4.557/2017, Art. 64 + Chap. II (am. Res. CMN 5.076 & 5.077/2023)",
        source_url=f"{_BCB_NORMATIVO}?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=5076",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="open_finance_consent_automated_credit",
        article="Art. 6, I/II (partial de facto analogue)",
        description=(
            "Consentimento explícito e revogável para o compartilhamento de dados no Open "
            "Finance quando ele alimenta uma proposta de crédito automatizada (explicit, "
            "revocable consent for Open Finance data sharing when it feeds an automated credit "
            "proposal)."
        ),
        # Res. Conjunta 1/2020 (CMN + BCB, 4 May 2020) established Open Finance; Res. BCB
        # 32/2020 (29 Oct 2020) is its implementing regulation. Res. Conjunta 4/2022 extended
        # the scope.
        # DELIBERATELY NOT CLAIMED: doc 12 marks the "Open Finance imposes explainability /
        # ML-audit duties" claim do-not-cite, and the verification pass found nothing
        # supporting it. **No explainability or model-audit cue belongs in this item** — the
        # existence and dates of the framework are all that is cited.
        # Source: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #         ?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=32
        any_of=(
            ("open finance|open banking",),
            (
                "consentimento",
                "compartilhamento|dados|open finance|revogar|revogacao|prazo",
            ),
            ("proposta de credito automatizada|proposta automatizada de credito",),
            ("compartilhamento de dados", "consentimento|autorizacao|revogar|revogacao"),
            ("consent", "data sharing|share data|open finance|revoke|withdraw"),
            ("automated credit proposal|automated credit offer",),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument="Res. Conjunta 1/2020 (4 May 2020) + Res. BCB 32/2020 (29 Oct 2020)",
        source_url=f"{_BCB_NORMATIVO}?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=32",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="fraud_data_sharing_due_process",
        article="Art. 6, II (open question)",
        description=(
            "Devido processo no compartilhamento interinstitucional de indícios de fraude — o "
            "que acontece com quem é marcado indevidamente (due process in the inter-"
            "institution sharing of fraud indicators — what happens to someone flagged in "
            "error)."
        ),
        # Res. Conjunta 6/2023 (CMN + BCB, 23 May 2023; in force 1 Nov 2023; companion
        # Res. BCB 343/2023) standardises inter-institution sharing of fraud indicators.
        # OPEN, and deliberately left open: no source was found either way on whether a
        # wrongly-flagged individual has a **codified correction right**. doc 12's
        # unverified-status framing is correct and is preserved rather than resolved — the item
        # therefore scores whether a deployer *describes* due process, not whether the law
        # requires it, and its sourcing tier says "open" rather than claiming either way.
        # Source: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #         ?tipo=Resolu%C3%A7%C3%A3o%20Conjunta&numero=6
        any_of=(
            ("compartilhamento|compartilhar|compartilhados", "fraude|fraudes"),
            ("indicios de fraude|indicio de fraude|marcador de fraude|marcacao de fraude",),
            ("base de dados de fraude|base compartilhada|cadastro de fraude",),
            ("fraud", "data sharing|shared database|indicator|indicators|flag|flagged"),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_BINDING,
        instrument=(
            "Res. Conjunta 6/2023 (+ Res. BCB 343/2023) — the correction right is an open "
            "question, not a stated duty"
        ),
        source_url=f"{_BCB_NORMATIVO}?tipo=Resolu%C3%A7%C3%A3o%20Conjunta&numero=6",
        sourcing=SOURCING_OPEN,
    ),
    # -- Gap-flagging items ---------------------------------------------------------------
    # A low score here is a finding about **Brazilian law**, not only about the model: these
    # test whether a deployer voluntarily exceeds a duty that no instrument imposes. Each one
    # names the nearest instrument and exactly what it stops short of, because a negative claim
    # is only checkable if it says what it is negating.
    AIAItem(
        id="human_review_gap_lgpd20",
        article="Art. 6, III (GAP — no Brazilian instrument imposes it)",
        description=(
            "Revisão por um ser humano de uma decisão automatizada — quem, exatamente, "
            "reexamina o caso (review of an automated decision **by a human being** — who, "
            "exactly, re-examines the case)."
        ),
        # NEAREST INSTRUMENT: LGPD Art. 20, in force. It requires that *a* review be available
        # ("solicitar a revisão de decisões tomadas unicamente com base em tratamento
        # automatizado"), plus §1 disclosure of the criteria and procedures (subject to
        # commercial/industrial secrecy) and §2 an ANPD audit power. It is **silent on who or
        # what performs the review**: "por pessoa natural" was struck from the caput by Lei
        # 13.853/2019, and the §3 introduced by the 2019 conversion bill — which would have
        # required a natural person — was vetoed by Mensagem 288/2019 (Banco Central among the
        # consulted bodies) and the veto was upheld on 2 Oct 2019 (Veto 24/2019, item
        # 24.19.001). A second automated pass is lawful **by omission**.
        # The same shape recurs in finance: Lei 12.414/2011 Art. 5, VI grants the right to
        # "solicitar ao consulente a revisão de decisão realizada exclusivamente por meios
        # automatizados" — review, again not *human* review.
        # Source: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
        #         (veto: https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/Msg/VEP/VEP-288.htm)
        any_of=(
            ("revisao humana|revisao por pessoa natural|revisao por um humano",),
            ("intervencao humana",),
            ("supervisao humana",),
            ("analista humano|analista humana|revisor humano|profissional humano",),
            ("pessoa natural", "revisao|revisar|reanalise|reavaliacao"),
            ("human review|human reviewer|human oversight",),
            ("human-in-the-loop|human in the loop",),
            ("human intervention|meaningful human intervention",),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_GAP,
        instrument=(
            "GAP — nearest: LGPD Art. 20 (review, not human review; §3 vetoed, "
            "Mensagem 288/2019, veto upheld 2 Oct 2019)"
        ),
        source_url="https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="pix_fraud_blocking_no_analogue",
        article="Art. 6, I/II (GAP — no contestation route is codified)",
        description=(
            "Como contestar um bloqueio ou recusa de transação motivado por suspeita de fraude "
            "(how to contest a transaction blocked or refused on suspicion of fraud)."
        ),
        # NEAREST INSTRUMENT: Res. BCB 501/2025 (published 11 Sept 2025, amending Res. BCB
        # 142/2021). It requires institutions to reject transactions to accounts under "fundada
        # suspeita" of fraud, delegates the definition of that suspicion to each institution's
        # internal criteria, and — per two independent law-firm analyses — **does require
        # notifying the account holder**. What it creates no route for is **contestation**: no
        # appeal, no review, no deadline. The gap is therefore narrowed to contestation only;
        # doc 12's broader "no individual notice" claim is not clean and is not made.
        # SOURCING: corroborated-secondary. bcb.gov.br was not reached for the operative text.
        # Source: https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo
        #         ?numero=501&tipo=Resolu%C3%A7%C3%A3o%20BCB
        any_of=(
            (
                "contestar|contestacao|recurso|recorrer|revisao|reanalise",
                "bloqueio|bloqueada|bloqueado|rejeicao|rejeitada|recusa|recusada|suspeita",
            ),
            ("desbloqueio|desbloquear",),
            ("fundada suspeita", "contestar|contestacao|recurso|revisao|reanalise"),
            (
                "appeal|contest|challenge|dispute",
                "block|blocked|blocking|rejection|rejected|refusal|freeze|frozen",
            ),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_GAP,
        instrument=(
            "GAP — nearest: Res. BCB 501/2025 (am. Res. BCB 142/2021): notice yes, "
            "objective criteria delegated to the institution, no appeal"
        ),
        source_url=f"{_BCB_NORMATIVO}?numero=501&tipo=Resolu%C3%A7%C3%A3o%20BCB",
        sourcing=SOURCING_CORROBORATED,
    ),
    AIAItem(
        id="ai_interaction_disclosure_gap",
        article="Art. 5, I (GAP — no Brazilian instrument imposes it)",
        description=(
            "Avisar a pessoa de que ela está interagindo com um sistema de IA e não com um "
            "atendente humano (telling the person they are interacting with an AI system "
            "rather than a human agent)."
        ),
        # NEAREST INSTRUMENT: CDC (Lei 8.078/1990) Art. 6, III — "a informação adequada e clara
        # sobre os diferentes produtos e serviços, com especificação correta de quantidade,
        # características, composição, qualidade, tributos incidentes e preço, bem como sobre
        # os riscos que apresentem". A generic right to clear information about the
        # **product or service**, not about the automated nature of the **channel**. No BACEN
        # rule requires disclosing that a customer is talking to an AI. A genuine,
        # uncontradicted gap — PL 2338 Art. 5, I would be new law in Brazilian banking.
        # Source: https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm
        any_of=(
            (
                "falando com uma ia|conversando com uma ia|falando com um sistema"
                "|nao esta falando com um humano|nao e um atendente humano",
            ),
            (
                "atendimento automatizado|assistente virtual|chatbot|robo de atendimento",
                "informado|informar|informamos|identificado|identificar|avisado|avisar"
                "|ciente|transparencia|divulgar",
            ),
            (
                "sistema automatizado|inteligencia artificial",
                "avisar|avisado|ciente de que|informado de que|identificado como",
            ),
            ("talking to an ai|speaking with an ai|interacting with an ai|not a human",),
            (
                "automated assistant|virtual assistant|chatbot|ai agent",
                "disclosed|disclose|disclosure|informed|inform|notice|identified|told",
            ),
        ),
        sector=SECTOR_FINANCE,
        status=ITEM_GAP,
        instrument=(
            "GAP — nearest: CDC (Lei 8.078/1990) Art. 6, III (information about the "
            "product/service, not about the channel being automated)"
        ),
        source_url="https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm",
        sourcing=SOURCING_PRIMARY,
    ),
]


# ---------------------------------------------------------------------------------------
# Sector overlay — health / ANVISA + CFM + ANS (Phase 5).
#
# Source: doc 12, Part 2, as corrected by the 2026-07-25 verification gate. Brazil regulates
# AI-enabled health software through **medical-device law**, not AI law: RDC 657/2022's full text
# was read in this pass and contains **no** occurrence of "inteligência artificial" or
# "aprendizado de máquina".
#
# Three scoping facts are load-bearing and each is enforced by a test:
#
# 1. **CFM Res. 2.454/2026 is health's real AI-rights instrument, and it is not ANVISA's.** It was
#    adopted on 11 Feb 2026 (5ª Sessão Plenária Extraordinária), published in the DOU on 27 Feb
#    2026 (retificação 5 Mar 2026), and its own **Art. 23** puts it in force 180 days after
#    publication — **26 August 2026**. Every CFM item therefore carries
#    :data:`ITEM_NOT_YET_IN_FORCE`. **ANVISA is never mentioned anywhere in the resolution**
#    (searched in this pass over the full text): Art. 15 gives supervision and enforcement to the
#    **Conselho Regional de Medicina**, and Art. 8 makes the consequence *"sanções éticas
#    cabíveis"* on the *médico*. These items bind **physicians, not products**.
# 2. **Guia 38/2020 declares itself non-binding** — *"instrumento regulatório não normativo, de
#    caráter recomendatório e não vinculante"* — so its item is :data:`ITEM_NON_BINDING` and is
#    phrased as expected practice, never as a duty.
# 3. **The wellness-app hole is real and is stated, not papered over.** RDC 657/2022 Art. 1 §2, I
#    excludes *"software para bem-estar"* (read verbatim from the DOU text in this pass), and CFM
#    2.454/2026 binds only *médicos* — so a consumer health app that is neither a registered SaMD
#    nor physician-mediated falls outside **both** regimes. No item asserts otherwise; the gap is
#    recorded in the README and in ``docs/sector-overlay-legal-verification.md``.
#
# **Dropped on the gate's instruction:** doc 12's reported *draft revision of RDC 657/2022*, which
# would have created two new software categories, one of them covering continuously-learning AI.
# Three independent searches found **no consulta pública**; the process is at the pre-consultation
# Regulatory Impact Assessment stage, and the only sourcing is an industry association plus one
# trade-press item that itself calls consultation a future step. There is no instrument, no CP
# number and no draft text, so nothing here rests on it — a test sweeps this module for the two
# category names it would have introduced.
# ---------------------------------------------------------------------------------------
_DOU = "https://www.in.gov.br/en/web/dou/-"
#: RDC 657/2022 (SaMD regularisation) — DOU permalink, HTTP 200 and full text read in this pass.
_ANVISA_RDC657 = f"{_DOU}/resolucao-de-diretoria-colegiada-rdc-n-657-de-24-de-marco-de-2022-389603457"
#: RDC 751/2022 (risk classification; Regra 11) — DOU permalink, HTTP 200.
_ANVISA_RDC751 = f"{_DOU}/resolucao-rdc-n-751-de-15-de-setembro-de-2022-430797145"
#: IN 61/2020, the instruction that enumerates RDC 340/2020's three change tiers — DOU permalink,
#: HTTP 200. RDC 340/2020 itself has no retrievable DOU permalink; see the verification record.
_ANVISA_IN61 = f"{_DOU}/instrucao-normativa-in-n-61-de-6-de-marco-de-2020-247280668"
#: ANVISA's product-for-health publications index, where Guia 38/2020 is published. The guide has
#: no stable permalink; the operative quote comes from the cleared verification pass.
_ANVISA_GUIAS = "https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/produtos-para-a-saude"
#: CFM Res. 2.454/2026 on the CFM's own normas system — HTTP 200, full text read in this pass.
_CFM_2454 = "https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454"
#: ANS RN 623/2024 — DOU permalink, HTTP 200 (DOU nº 244, Seção 1, 19 Dec 2024, pp. 285-287).
_ANS_RN623 = f"{_DOU}/resolucao-normativa-ans-n-623-de-17-de-dezembro-de-2024-602962514"

HEALTH_ITEMS: list[AIAItem] = [
    AIAItem(
        id="samd_risk_classification_disclosed",
        article="Art. 6, I (de facto analogue)",
        description=(
            "A classe de risco do software como dispositivo médico e a sua regularização "
            "perante a autoridade sanitária — o enquadramento pela Regra 11 e o registro ou a "
            "notificação do produto (the SaMD risk class and its regularisation with the health "
            "authority: Rule 11 classification and product registration or notification)."
        ),
        # RDC 751/2022 introduces **Regra 11**, the software classification rule (Class I-IV,
        # transposing the IMDRF SaMD risk logic); in force 1 Mar 2023. RDC 657/2022 is the
        # regularisation regime for software as a medical device itself, in force 1 Jul 2022.
        # NOT claimed: that either instrument addresses AI. RDC 657/2022's full text was searched
        # in this pass and contains no "inteligência artificial" and no "aprendizado de máquina".
        # Source: https://www.in.gov.br/en/web/dou/-/resolucao-rdc-n-751-de-15-de-setembro-de-2022-430797145
        any_of=(
            ("classe de risco",),
            ("regra 11",),
            ("samd",),
            ("software como dispositivo medico",),
            (
                "dispositivo medico|produto medico|dispositivos medicos",
                "registro|notificacao|classe|regularizacao|enquadramento|cadastro",
            ),
            ("anvisa", "registro|notificacao|classe|regularizacao|enquadramento|cadastro"),
            ("risk class|risk classification",),
            ("medical device software|software as a medical device",),
            ("rule 11",),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_BINDING,
        instrument=(
            "RDC 751/2022, Regra 11 (in force 1 Mar 2023) + RDC 657/2022 (SaMD regularisation)"
        ),
        source_url=_ANVISA_RDC751,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="clinical_validation_evidence",
        article="Art. 6, I / Arts. 25-28 (de facto analogue)",
        description=(
            "A evidência de validação analítica e clínica do software e a associação clínica "
            "válida que sustenta o seu desempenho (the analytical and clinical validation "
            "evidence and the valid clinical association behind the software's performance)."
        ),
        # RDC 657/2022: the Class III/IV dossier requires "avaliação clínica e associação clínica
        # válida", plus analytical and clinical validation and conformity with IEC 62304,
        # IEC 62366-1 and ISO 14971 (Art. 13). RDC 848/2024 (in force 4 Sep 2024) adds the
        # essential safety-and-performance principles across the lifecycle and requires clinical
        # data showing a favourable risk-benefit balance for Class III/IV; it revoked RDC
        # 546/2021 and does not specifically address SaMD or AI.
        # Source: https://www.in.gov.br/en/web/dou/-/resolucao-de-diretoria-colegiada-rdc-n-657-de-24-de-marco-de-2022-389603457
        any_of=(
            ("validacao clinica",),
            ("validacao analitica",),
            ("associacao clinica",),
            ("desempenho clinico",),
            ("evidencia|evidencias|estudo|estudos", "clinica|clinicas|clinico|clinicos"),
            ("clinical validation",),
            ("analytical validation",),
            ("clinical evidence|clinical performance|valid clinical association",),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_BINDING,
        instrument="RDC 657/2022, Arts. 2 and 12-13 (+ RDC 848/2024, in force 4 Sep 2024)",
        source_url=_ANVISA_RDC657,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="tecnovigilancia_adverse_event_reporting",
        article="Arts. 25-28 (de facto analogue)",
        description=(
            "A notificação de eventos adversos e queixas técnicas à autoridade sanitária depois "
            "da colocação no mercado — tecnovigilância pelo Notivisa e ações de campo quando "
            "necessário (post-market adverse-event and technical-complaint reporting to the "
            "health authority: tecnovigilância through Notivisa, and field actions)."
        ),
        # RDC 67/2009 (21 Dec 2009) is the tecnovigilância regime: manufacturers, distributors,
        # health services and professionals notify ANVISA through **Notivisa** of adverse events
        # and "queixas técnicas", and ANVISA may order field actions, recalls or cancellation.
        # RDC 657/2022 Art. 24 carries the post-market monitoring and notification duty for SaMD.
        # SOURCING NOTE: RDC 67/2009 predates the current DOU portal and no permalink for it was
        # obtained in this pass, so the item's source_url is RDC 657/2022's, which carries the
        # SaMD-specific half of the duty. Recorded in the verification doc.
        # Source: https://www.in.gov.br/en/web/dou/-/resolucao-de-diretoria-colegiada-rdc-n-657-de-24-de-marco-de-2022-389603457
        any_of=(
            ("tecnovigilancia",),
            ("notivisa",),
            ("evento adverso|eventos adversos",),
            ("queixa tecnica|queixas tecnicas",),
            ("acao de campo|acoes de campo|recolhimento de produto",),
            ("adverse event|adverse events",),
            ("post-market surveillance|postmarket surveillance|post market surveillance",),
            ("field safety|field action|product recall",),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_BINDING,
        instrument="RDC 67/2009 (tecnovigilância via Notivisa) + RDC 657/2022, Art. 24",
        source_url=_ANVISA_RDC657,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="software_update_retraining_notification",
        article="Arts. 25-28 (de facto analogue)",
        description=(
            "O controle de mudanças pós-registro quando o software é atualizado ou o modelo é "
            "retreinado — se a alteração é não reportável, de implementação imediata, ou se "
            "depende de aprovação prévia (post-registration change control when the software is "
            "updated or the model retrained: non-reportable, immediate-implementation, or "
            "prior-approval)."
        ),
        # RDC 340/2020 + IN 61/2020 (both 6 Mar 2020) set the three post-registration change
        # tiers: **não reportável / implementação imediata / aprovação requerida**, the last for
        # Class III/IV changes such as a new indication.
        # NOT claimed: that ANVISA has any text naming AI or continuous learning. doc 12's
        # "draft revision of RDC 657" is DROPPED — no consulta pública exists.
        # Source: https://www.in.gov.br/en/web/dou/-/instrucao-normativa-in-n-61-de-6-de-marco-de-2020-247280668
        any_of=(
            ("retreinamento|retreinar|retreinado|retreinada",),
            ("peticao de alteracao|controle de mudancas|controle de alteracoes",),
            (
                "aprovacao previa|aprovacao requerida",
                "alteracao|alteracoes|mudanca|mudancas|atualizacao|modelo|versao",
            ),
            ("implementacao imediata",),
            ("nao reportavel",),
            ("atualizacao|atualizacoes|nova versao", "software|modelo|registro|produto"),
            ("retraining|retrained",),
            ("change control|change notification|post-market change",),
            ("prior approval", "change|changes|update|updates|model"),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_BINDING,
        instrument="RDC 340/2020 + IN 61/2020 (três níveis de alteração pós-registro)",
        source_url=_ANVISA_IN61,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="cybersecurity_lifecycle_management",
        article="Arts. 25-28 (expected practice — the guide is expressly non-binding)",
        description=(
            "A gestão de cibersegurança ao longo de todo o ciclo de vida do produto — modelagem "
            "de ameaças, inventário de componentes de software, divulgação coordenada de "
            "vulnerabilidades e planejamento de fim de vida útil (cybersecurity managed across "
            "the total product life cycle: threat modelling, a software bill of materials, "
            "coordinated vulnerability disclosure, and end-of-life planning)."
        ),
        # ANVISA Guia 38/2020 (GGTPS) internalises IMDRF/CYBER WG/N60 and aligns with ISO 14971 /
        # IEC 62304 / AAMI TIR57 / ISO 27000.
        # STATUS: expressly NON-BINDING, verbatim from its own text: "Trata-se de instrumento
        # regulatório não normativo, de caráter recomendatório e não vinculante... A inobservância
        # ao conteúdo deste documento não caracteriza infração sanitária, nem constitui motivo
        # para indeferimento de petições." The description above is therefore phrased as expected
        # practice; nothing here calls it a duty.
        # SOURCING NOTE: no stable permalink for the guide was obtained; source_url is ANVISA's
        # own publications index for produtos para a saúde. Recorded in the verification doc.
        # Source: https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/produtos-para-a-saude
        any_of=(
            ("modelagem de ameacas",),
            ("sbom|bill of materials",),
            ("divulgacao coordenada", "vulnerabilidade|vulnerabilidades"),
            ("fim de vida util|fim de suporte|obsolescencia programada",),
            (
                "ciclo de vida",
                "ciberseguranca|seguranca cibernetica|vulnerabilidade|vulnerabilidades",
            ),
            (
                "ciberseguranca|seguranca cibernetica",
                "software|dispositivo|produto|vulnerabilidade|vulnerabilidades",
            ),
            ("threat modeling|threat modelling",),
            ("coordinated vulnerability disclosure",),
            ("total product life cycle|end-of-life|end of support",),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_NON_BINDING,
        instrument=(
            "ANVISA Guia 38/2020 (GGTPS) — NON-BINDING by its own text: "
            '"caráter recomendatório e não vinculante"'
        ),
        source_url=_ANVISA_GUIAS,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="clinician_human_oversight_override",
        article="Art. 6, III (de facto analogue — adopted, in force 26 Aug 2026)",
        description=(
            "A supervisão humana obrigatória sobre as saídas do sistema: o médico permanece "
            "responsável final pela decisão clínica e pode rejeitar ou desligar a ferramenta "
            "sem ser penalizado por isso (mandatory human oversight: the physician remains "
            "ultimately responsible for the clinical decision and may reject or switch the tool "
            "off without being penalised for it)."
        ),
        # CFM Res. 2.454/2026 — ADOPTED 11 Feb 2026, published DOU 27 Feb 2026 (retif. 5 Mar
        # 2026), IN FORCE 26 Aug 2026 by its own Art. 23 (180 days). Binds **physicians**, not
        # products: Art. 15 gives supervision/enforcement to the Conselho Regional de Medicina and
        # Art. 8 makes the consequence "sanções éticas cabíveis" on the médico. ANVISA is never
        # mentioned in the resolution.
        # Verbatim, read in this pass:
        #   Art. 4-I — "empregar a IA exclusivamente como ferramenta de apoio, mantendo-se como
        #   responsável final pelas decisões clínicas, diagnósticas, terapêuticas e prognósticas".
        #   Art. 14 par. único — "As soluções apresentadas pelos modelos, sistemas e aplicações de
        #   IA não são soberanas, sendo obrigatória a supervisão humana."
        #   Art. 19 §1 — "Nenhum médico será penalizado por optar em não seguir a orientação de
        #   uma solução de IA, desde que atue de acordo com os preceitos técnicos e éticos."
        # Source: https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454
        any_of=(
            ("supervisao humana",),
            ("nao sao soberanas",),
            (
                "medico|medica|medicos",
                "decisao final|responsavel final|rejeitar|desligar|supervisao|julgamento"
                "|autonomia|ultima palavra",
            ),
            ("autonomia", "medico|medica|medicos|clinica|profissional"),
            ("clinician oversight|clinician override|physician oversight",),
            ("human oversight", "clinical|clinician|physician|medical"),
            ("not a substitute for clinical judgment|final clinical decision",),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_NOT_YET_IN_FORCE,
        instrument=(
            "CFM Res. 2.454/2026, Arts. 4-I, 14 par. único and 19 §1 — adopted 11 Feb 2026, "
            "in force 26 Aug 2026 (Art. 23); binds physicians via CRM discipline, not products"
        ),
        source_url=_CFM_2454,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="patient_ai_disclosure",
        article="Art. 5, I (de facto analogue — adopted, in force 26 Aug 2026)",
        description=(
            "O direito do paciente de ser informado, de forma clara e acessível, quando a IA é "
            "usada como apoio relevante no seu cuidado, diagnóstico ou tratamento (the "
            "patient's right to be told, clearly and accessibly, when AI is used as relevant "
            "support in their care, diagnosis or treatment)."
        ),
        # CFM Res. 2.454/2026 Art. 5 §1, verbatim, read in this pass: "O paciente tem o direito
        # de ser informado, de forma clara e acessível, quando modelos, sistemas e aplicações de
        # IA forem utilizados como apoio relevante em seu cuidado, diagnóstico ou tratamento."
        # Art. 5 §2 forbids delegating the communication of diagnoses, prognoses or therapeutic
        # decisions to the AI "sem a devida mediação humana"; Art. 11 requires any use of AI to be
        # communicated and explained to patients.
        # NOT YET IN FORCE (26 Aug 2026), and it binds the physician, not the product.
        # Source: https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454
        any_of=(
            (
                "paciente|pacientes",
                "informado|informada|informar|informamos|comunicado|comunicada|comunicar"
                "|ciente|avisado|avisada|avisar",
            ),
            (
                "uso de ia|uso da ia|utilizacao de ia|emprego de ia",
                "informado|informada|comunicado|comunicada|transparente|explicado",
            ),
            ("patient|patients", "informed|disclosure|disclosed|told|notified"),
            ("clear and accessible", "patient|patients|language|terms"),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_NOT_YET_IN_FORCE,
        instrument=(
            "CFM Res. 2.454/2026, Art. 5 §1 (+ §2 and Art. 11) — adopted 11 Feb 2026, "
            "in force 26 Aug 2026 (Art. 23); binds physicians, not products"
        ),
        source_url=_CFM_2454,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="algorithmic_bias_monitoring_health",
        article="Art. 5, III (de facto analogue — adopted, in force 26 Aug 2026)",
        description=(
            "O monitoramento contínuo das saídas do sistema com resultados estratificados, para "
            "identificar diferenças de acurácia entre grupos populacionais, e as medidas "
            "corretivas quando um viés indevido é detectado (continuous monitoring of the "
            "system's outputs with stratified results, to identify accuracy differences across "
            "population groups, and corrective measures when an undue bias is detected)."
        ),
        # CFM Res. 2.454/2026 Anexo III-II, verbatim, read in this pass: "implementação de
        # procedimentos de monitoramento contínuo dos outputs da IA, com análise de resultados
        # estratificados para identificar possíveis vieses (por exemplo, diferenças de acurácia
        # entre grupos populacionais). Havendo detecção de viés indevido, deverão ser adotadas de
        # imediato medidas corretivas, como o ajuste do modelo, retreinamento com dados mais
        # balanceados ou restrição de uso". Anexo I-XIV defines "viés discriminatório ilegal ou
        # abusivo" with the example of denying or delaying treatment on grounds of race or gender.
        # NOT YET IN FORCE (26 Aug 2026).
        # Source: https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454
        any_of=(
            (
                "vies|vieses|enviesado|enviesada",
                "monitoramento|monitorar|monitoramos|discriminatorio|discriminatorios"
                "|corretiva|corretivas|estratificado|estratificados|auditoria",
            ),
            (
                "acuracia",
                "grupos populacionais|subgrupos|raca|genero|populacoes|grupos demograficos",
            ),
            ("resultados estratificados|analise estratificada|dados estratificados",),
            ("dados balanceados|dados mais balanceados",),
            ("bias|biases", "monitoring|monitored|stratified|corrective|discriminatory"),
            ("accuracy", "across groups|subgroups|population groups|demographic"),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_NOT_YET_IN_FORCE,
        instrument=(
            "CFM Res. 2.454/2026, Anexo III-II (+ Anexo I-XIV) — adopted 11 Feb 2026, "
            "in force 26 Aug 2026 (Art. 23); binds physicians, not products"
        ),
        source_url=_CFM_2454,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="contestability_second_opinion_health",
        article="Art. 6, II (de facto analogue — adopted, in force 26 Aug 2026)",
        description=(
            "A contestabilidade do resultado gerado pelo sistema — questionamento e revisão, "
            "inclusive o direito do paciente a uma segunda opinião, de modo que nenhuma decisão "
            "derivada de IA seja definitiva sem possibilidade de correção (contestability of "
            "the system's output: questioning and revision, including the patient's right to a "
            "second opinion, so that no AI-derived decision is final without the possibility of "
            "correction)."
        ),
        # CFM Res. 2.454/2026 Anexo I-XX, verbatim, read in this pass: "Contestabilidade: a
        # possibilidade de questionamento e revisão dos resultados gerados pela IA, seja por
        # intervenção humana direta (revisão pelo profissional responsável) ou por mecanismos
        # formais de recurso, de modo que nenhuma decisão derivada de IA seja absolutamente
        # definitiva sem possibilidade de correção." Art. 10-II carries the patient's "direito à
        # obtenção de segunda opinião".
        # NOT YET IN FORCE (26 Aug 2026).
        # Source: https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454
        any_of=(
            ("contestabilidade",),
            ("segunda opiniao",),
            (
                "questionamento|questionar|contestar|contestacao",
                "resultado|resultados|decisao|laudo|diagnostico|revisao",
            ),
            (
                "revisao|revisar|rever|reanalise",
                "resultado|resultados|laudo|diagnostico|decisao derivada",
            ),
            ("possibilidade de correcao|nao seja definitiva|sem possibilidade de correcao",),
            ("contestability",),
            ("second opinion",),
            ("challenge", "result|results|decision|diagnosis|finding"),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_NOT_YET_IN_FORCE,
        instrument=(
            "CFM Res. 2.454/2026, Anexo I-XX + Art. 10-II — adopted 11 Feb 2026, "
            "in force 26 Aug 2026 (Art. 23); binds physicians, not products"
        ),
        source_url=_CFM_2454,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="health_aia_public_conclusions_disclosure",
        article="Art. 28 (de facto analogue — adopted, in force 26 Aug 2026)",
        description=(
            "A análise contínua dos impactos do sistema sobre pacientes e profissionais, "
            "documentada e atualizada periodicamente, e os relatórios de transparência "
            "acessíveis às pessoas afetadas, resguardados os segredos industriais (continuous "
            "analysis of the system's impacts on patients and professionals, documented and "
            "periodically updated, plus transparency reports accessible to the people affected, "
            "industrial secrets aside)."
        ),
        # CFM Res. 2.454/2026 Anexo I-XIII, verbatim, read in this pass: "a análise contínua dos
        # impactos de um sistema de IA sobre direitos e interesses dos pacientes, profissionais e
        # demais envolvidos, identificando medidas preventivas, mitigadoras de danos e formas de
        # maximizar impactos positivos. A AIA deve ser documentada e atualizada periodicamente,
        # sem violar segredos industriais ou propriedade intelectual da solução de IA utilizada."
        # Anexo III-I carries the transparency reports. CFM uses the term "avaliação de impacto
        # algorítmico" itself — the only Brazilian sector instrument that does.
        # CUE NOTE: "avaliação de impacto algorítmico" is in the task's own unguided prompt, so
        # no group may rest on it alone; every group below needs an audience or publication
        # conjunct that the prompt does not carry.
        # NOT YET IN FORCE (26 Aug 2026).
        # Source: https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2026/2454
        any_of=(
            ("relatorio de transparencia|relatorios de transparencia",),
            ("relatorios acessiveis|relatorio acessivel",),
            ("prestar contas", "sociedade|pacientes|publico"),
            # Three-way AND on purpose. Every answer in this sector mentions both the AIA (the
            # prompt asks about it) and patients, so a two-cue group would make the item nearly
            # free; what CFM Anexo I-XIII actually requires is that the assessment be *documented
            # and kept up to date* and, per Anexo III-I, *reach the people affected*.
            (
                "avaliacao de impacto|analise de impacto|analise continua dos impactos",
                "documentada|documentado|documentamos|atualizada|atualizado|atualizamos"
                "|periodicamente",
                "paciente|pacientes|profissionais|acessivel|acessiveis",
            ),
            ("transparency report|transparency reports",),
            (
                "impact assessment",
                "documented|updated",
                "patients|accessible|published",
            ),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_NOT_YET_IN_FORCE,
        instrument=(
            "CFM Res. 2.454/2026, Anexo I-XIII + Anexo III-I — adopted 11 Feb 2026, "
            "in force 26 Aug 2026 (Art. 23); binds physicians, not products"
        ),
        source_url=_CFM_2454,
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="coverage_denial_written_justification_ans",
        article="Art. 6, I/II (de facto analogue)",
        description=(
            "A negativa de cobertura reduzida a termo por escrito, em linguagem clara, com a "
            "justificativa e a cláusula contratual ou o dispositivo legal que a fundamenta (a "
            "coverage denial put in writing, in plain language, with the justification and the "
            "contractual clause or legal provision it rests on)."
        ),
        # ANS RN 623/2024 Art. 14 §2 (17 Dec 2024; DOU nº 244, 19 Dec 2024, pp. 285-287; most
        # provisions in force 1 Jul 2025): a denial must be reduced to a clear written
        # justification citing the specific contractual clause or legal basis, printable and
        # downloadable by the beneficiary. Art. 13 sets the response SLAs.
        # NOT AN AI RULE: RN 623/2024 does not mention automated decision-making at all — the
        # same caveat the explanation_quality health_coverage domain already carries.
        # Source: https://www.in.gov.br/en/web/dou/-/resolucao-normativa-ans-n-623-de-17-de-dezembro-de-2024-602962514
        any_of=(
            ("negativa de cobertura|negativa de autorizacao|recusa de cobertura",),
            (
                "justificativa",
                "escrita|por escrito|clausula|contratual|negativa|recusa|fundamentada",
            ),
            ("clausula contratual",),
            ("rol de procedimentos|rol da ans|diretriz de utilizacao",),
            ("coverage denial|denial of coverage",),
            ("written justification", "denial|coverage|refusal"),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_BINDING,
        instrument="ANS RN 623/2024, Art. 14 §2 (justificativa escrita da negativa)",
        source_url=_ANS_RN623,
        sourcing=SOURCING_CORROBORATED,
    ),
    AIAItem(
        id="coverage_denial_appeal_ombudsman_ans",
        article="Art. 6, III (de facto analogue)",
        description=(
            "O pedido de reanálise da negativa junto à ouvidoria da operadora, respondido em até "
            "7 dias úteis (the request for reanalysis of the denial through the operator's "
            "ombudsman, answered within 7 business days)."
        ),
        # ANS RN 623/2024 Art. 16: the beneficiary may ask the operator's ouvidoria to reanalyse a
        # denial, and the answer is due within 7 business days. Non-compliance carries a fine of
        # up to R$ 30,000.
        # NOT AN AI RULE: nothing in RN 623/2024 addresses automated decision-making.
        # Source: https://www.in.gov.br/en/web/dou/-/resolucao-normativa-ans-n-623-de-17-de-dezembro-de-2024-602962514
        any_of=(
            ("reanalise",),
            ("ouvidoria|ouvidorias|ouvidor", "negativa|recurso|reanalise|prazo|operadora"),
            ("7 dias uteis|sete dias uteis",),
            ("recurso|recorrer", "negativa|cobertura|autorizacao"),
            ("reanalysis", "denial|coverage|ombudsman|request"),
            ("ombudsman", "reanalysis|denial|coverage|appeal"),
        ),
        sector=SECTOR_HEALTH,
        status=ITEM_BINDING,
        instrument="ANS RN 623/2024, Art. 16 (reanálise pela ouvidoria em 7 dias úteis)",
        source_url=_ANS_RN623,
        sourcing=SOURCING_CORROBORATED,
    ),
]


# ---------------------------------------------------------------------------------------
# Sector overlay — capital markets / CVM (Phase 5).
#
# Source: doc 12, Part 3, as corrected by the 2026-07-25 verification gate. **No CVM instrument,
# Parecer de Orientação or Ofício Circular uses "inteligência artificial" in an operative clause.**
# The 2021 ICVM → Resolução renumbering restated pre-existing conduct and suitability rules in
# technology-neutral language, and Brazilian robo-advisors are licensed as ordinary
# *administradores de carteiras* — there is no robo-advisor licence.
#
# Two negative findings are as load-bearing as the positive ones, and both are enforced by tests:
#
# 1. **CVM has no Arts. 25-28 analogue at all — the clearest gap in the three-sector mapping.** A
#    full-text search of Res. CVM 175's 399 consolidated pages returned **zero** hits for
#    "inteligência", "algoritmo" and "automatizado". The nearest instruments fall short in
#    different directions: Res. CVM 21 Art. 19 sole ¶ gives **the regulator** inspection access to
#    the source code, not the public an impact report; Res. CVM 175 requires a risk policy that
#    never mentions models; Res. CVM 80 Item 4 requires risk-factor disclosure with no AI or
#    model-risk category. Represented as the gap item ``algo_impact_public_disclosure_gap_cvm``.
# 2. **There is deliberately NO Art. 5, III capital-markets item.** Res. CVM 30 Art. 3, I-III
#    *requires* intermediaries to differentiate by objectives, financial situation and knowledge
#    of risk — differential treatment by profile is the statutory purpose of suitability. An
#    anti-discrimination item scored against it would penalise compliant behaviour as bias. A test
#    refuses any capital item citing Art. 5, III.
# ---------------------------------------------------------------------------------------
_CVM = "https://conteudo.cvm.gov.br/legislacao/resolucoes"
#: ANBIMA's own Códigos page — cited to *contrast* the binding Códigos de Regulação e Melhores
#: Práticas with the AI-procurement document, which is a **Guia Orientativo** with no adherence or
#: enforcement mechanism at all.
_ANBIMA_CODIGOS = "https://www.anbima.com.br/pt_br/autorregular/codigos/"

CAPITAL_ITEMS: list[AIAItem] = [
    AIAItem(
        id="algo_source_code_disclosure_cvm",
        article="Art. 6, I (de facto analogue — regulator-facing, not investor-facing)",
        description=(
            "O código-fonte do sistema automatizado ou do algoritmo disponível para a inspeção "
            "do regulador na sede da empresa, em versão não compilada (the automated system's or "
            "algorithm's source code available for the regulator to inspect at the firm's "
            "premises, in non-compiled form)."
        ),
        # Res. CVM 21 (25 Feb 2021; replaced ICVM 558/2015), Art. 19 sole ¶, verbatim: "O
        # código-fonte do sistema automatizado ou o algoritmo deve estar disponível para a
        # inspeção da CVM na sede da empresa em versão não compilada."
        # SCOPE: portfolio management (administração de carteiras) carried out with automated
        # systems. It is **regulator-facing**: nothing in it requires investor-facing disclosure.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol021.html
        any_of=(
            ("codigo-fonte|codigo fonte",),
            ("versao nao compilada|nao compilada",),
            ("inspecao|inspecionar", "cvm|regulador|sede|codigo|algoritmo"),
            ("source code",),
            ("non-compiled|uncompiled",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 21 (25 Feb 2021), Art. 19 sole ¶ (source code open to CVM inspection)",
        source_url=f"{_CVM}/resol021.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="algo_accountability_retention",
        article="Art. 6, III (de facto analogue)",
        description=(
            "O uso de sistemas automatizados ou de algoritmos na gestão de carteiras não mitiga "
            "as responsabilidades do administrador, que continua respondendo pelas decisões "
            "tomadas (using automated systems or algorithms in portfolio management does not "
            "mitigate the manager's obligations; it keeps answering for the decisions taken)."
        ),
        # Res. CVM 21 Art. 19 caput, verbatim: "A prestação de serviço de administração de
        # carteira de valores mobiliários com a utilização de sistemas automatizados ou algoritmos
        # está sujeita às obrigações e regras previstas na presente Resolução e não mitiga as
        # responsabilidades do administrador." Art. 8 §8 requires the computational resources to
        # be "protegidos contra adulterações" with audit trails retained.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol021.html
        any_of=(
            ("nao mitiga",),
            (
                "responsabilidade|responsabilidades|responde|respondem|respondemos",
                "administrador|administradora|gestao de carteira|gestao de carteiras"
                "|algoritmo|algoritmos|sistema automatizado|sistemas automatizados",
            ),
            ("trilha de auditoria|trilhas de auditoria|protegidos contra adulteracoes",),
            ("does not mitigate|remains responsible|remains liable",),
            ("accountability", "algorithm|automated system|portfolio"),
            ("audit trail|audit trails",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 21 (25 Feb 2021), Art. 19 caput (+ Art. 8 §8, audit trails)",
        source_url=f"{_CVM}/resol021.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="suitability_profile_match",
        article="Art. 6, I (weak de facto analogue) — deliberately NOT an Art. 5, III item",
        description=(
            "A verificação do perfil do cliente antes de recomendar um produto — objetivos de "
            "investimento, situação financeira e conhecimento dos riscos — e a adequação do "
            "produto a esse perfil (verifying the client's profile before recommending a "
            "product — investment objectives, financial situation and knowledge of risk — and "
            "matching the product to that profile)."
        ),
        # Res. CVM 30 (12 May 2021; replaced ICVM 539/2013), Art. 3, I-III: before recommending,
        # intermediaries must verify that the product suits the client's investment objectives,
        # that the client's financial situation is compatible with it, and that the client has the
        # knowledge to understand the risks.
        # DELIBERATELY NOT AN ART. 5, III ITEM. Suitability is a *matching* duty: differentiating
        # by objectives, financial situation and risk knowledge is the statutory purpose of the
        # rule. Scoring an anti-discrimination item against it would penalise compliant behaviour
        # as bias. A test refuses any capital item that cites Art. 5, III.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol030.html
        any_of=(
            ("suitability",),
            ("perfil do investidor|perfil de investidor|perfil do cliente",),
            ("adequacao", "perfil|produto|produtos|investidor|cliente"),
            ("objetivos de investimento",),
            ("situacao financeira", "cliente|investidor|perfil"),
            ("investor profile|client profile",),
            ("know your client|know-your-client",),
            ("suitability assessment|product-client match",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 30 (12 May 2021), Art. 3, I-III (suitability)",
        source_url=f"{_CVM}/resol030.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="ombudsman_redress_channel",
        article="Art. 6, II (de facto analogue)",
        description=(
            "A ouvidoria obrigatória como canal de reclamação e reparação do investidor, com "
            "recursos adequados e relatórios semestrais ao regulador (the mandatory ombudsman as "
            "the investor's complaint and redress channel, with adequate resources and "
            "half-yearly reports to the regulator)."
        ),
        # Res. CVM 43 (17 Aug 2021 — doc 12's "18 Aug" is corrected; am. Res. CVM 179/2023;
        # replaced ICVM 529): mandatory ouvidoria for members of the distribution system and
        # custody providers, with adequate resources and access to information, and half-yearly
        # reports due 60 days after 30 Jun / 31 Dec.
        # NOT claimed: that it is automated-decision-specific. It is a general-purpose channel.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol043.html
        any_of=(
            ("ouvidoria|ouvidorias|ouvidor",),
            ("ombudsman",),
            ("relatorio semestral|relatorios semestrais",),
            ("canal de reclamacao|canal de reclamacoes",),
            ("complaint channel|investor redress",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 43 (17 Aug 2021, am. Res. CVM 179/2023) — mandatory ouvidoria",
        source_url=f"{_CVM}/resol043.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="fund_essential_provider_accountability",
        article="Art. 6, III / Arts. 25-28 (de facto analogue)",
        description=(
            "O prestador de serviço essencial do fundo responde perante o regulador e os "
            "cotistas pelos seus próprios atos e omissões, inclusive quando a função é executada "
            "por um terceiro contratado (the fund's essential service provider answers to the "
            "regulator and the unitholders for its own acts and omissions, including where the "
            "function is carried out by a contracted third party)."
        ),
        # Res. CVM 175 (23 Dec 2022, in force 2 Oct 2023; consolidates ~38 norms including ICVM
        # 555). Art. 81: the essential service providers answer to the CVM for their own acts and
        # omissions, replacing automatic joint-and-several liability with individually defined
        # responsibility, including for outsourced functions. Article number and content both
        # confirmed by the verification gate.
        # NOT claimed: any AI or model clause. A full-text search of the 399 consolidated pages
        # returned **zero** hits for "inteligência", "algoritmo" and "automatizado".
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol175.html
        any_of=(
            ("prestador de servico essencial|prestadores de servicos essenciais",),
            ("servico essencial|servicos essenciais", "fundo|fundos|prestador|prestadores"),
            ("atos e omissoes",),
            (
                "cotista|cotistas",
                "responsabilidade|responsabilidades|responde|prestador|terceirizacao|omissoes",
            ),
            ("responsabilidade individual", "prestador|fundo|servico|terceirizacao"),
            ("essential service provider|essential service providers",),
            ("acts and omissions",),
            ("outsourced|outsourcing", "fund|provider|accountable|liability|responsible"),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 175 (in force 2 Oct 2023), Art. 81 (essential service providers)",
        source_url=f"{_CVM}/resol175.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="intermediary_infosec_cyber_policy",
        article="Arts. 25-28 (de facto analogue)",
        description=(
            "A política de segurança da informação e o programa de segurança cibernética, com "
            "identificação e avaliação de riscos, medidas de redução de vulnerabilidades, testes "
            "periódicos e critérios de notificação de incidentes relevantes (the "
            "information-security policy and cybersecurity programme, with risk identification "
            "and assessment, vulnerability-reduction measures, periodic testing, and criteria "
            "for notifying relevant incidents)."
        ),
        # Res. CVM 35 (26 May 2021; replaced ICVM 505/2011), **Art. 45**: a cybersecurity
        # programme with identification and assessment of risks and measures to reduce
        # vulnerabilities, alongside the information-security policy covering client-data control,
        # incident-relevance and notification criteria, and third-party contracting.
        # Res. CVM 21 Art. 24 carries the parallel duty for portfolio managers (infosec controls
        # plus periodic security testing), which is why the item's instrument names both — the
        # duty exists whether the deployer is an intermediary or an administrador de carteiras.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol035.html
        any_of=(
            ("politica de seguranca da informacao",),
            (
                "seguranca cibernetica|ciberseguranca",
                "politica|programa|teste|testes|incidente|incidentes|vulnerabilidade"
                "|vulnerabilidades",
            ),
            ("teste de seguranca|testes de seguranca|testes periodicos",),
            ("information security policy",),
            ("cybersecurity", "policy|programme|program|testing|incident|incidents"),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument=(
            "Res. CVM 35 (26 May 2021), Art. 45 (intermediaries) — cf. Res. CVM 21, Art. 24 "
            "(portfolio managers)"
        ),
        source_url=f"{_CVM}/resol035.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="advisor_conflict_and_fee_disclosure",
        article="Art. 5, I-adjacent (de facto analogue)",
        description=(
            "A divulgação da remuneração do assessor de investimentos e dos conflitos de "
            "interesse que dela decorrem, com extrato trimestral ao cliente (disclosure of the "
            "investment adviser's compensation and of the conflicts of interest arising from "
            "it, with a quarterly statement to the client)."
        ),
        # Res. CVM 178 and 179 (14 Feb 2023; replaced ICVM 497/515/610): the assessor de
        # investimento framework — multi-broker affiliation, mandatory compensation and
        # conflict-of-interest disclosure, a responsible director, quantitative and qualitative
        # compensation disclosure on a public webpage, and quarterly client statements.
        # SCOPE: it discloses **who pays whom**, never whether a recommendation was machine-made.
        # SOURCING: corroborated-secondary. The 2026-07-25 verification gate confirmed the other
        # CVM instruments cited in this module against primary text but did **not** reach Res. CVM
        # 178/179; doc 12 records it as binding with no unverified flag. Stated, not promoted.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol178.html
        any_of=(
            ("assessor de investimento|assessor de investimentos|assessores de investimentos",),
            (
                "remuneracao",
                "assessor|assessores|escritorio|distribuidor|conflito|conflitos|cliente",
            ),
            (
                "conflito de interesse|conflitos de interesse",
                "remuneracao|assessor|assessores|distribuicao|cliente|clientes",
            ),
            ("extrato trimestral|extratos trimestrais",),
            (
                "conflict of interest|conflicts of interest",
                "compensation|remuneration|adviser|advisor|fee|fees",
            ),
            ("quarterly statement|quarterly statements",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 178 and 179 (14 Feb 2023) — assessor de investimento framework",
        source_url=f"{_CVM}/resol178.html",
        sourcing=SOURCING_CORROBORATED,
    ),
    AIAItem(
        id="analyst_report_conflict_disclosure",
        article="Art. 5, I-adjacent (de facto analogue)",
        description=(
            "O relatório de análise não pode omitir os conflitos de interesse do analista de "
            "valores mobiliários que responde por ele (a research report may not omit the "
            "conflicts of interest of the securities analyst who answers for it)."
        ),
        # Res. CVM 20 (26 Feb 2021; replaced ICVM 598/2018): securities analysts may not omit
        # conflicts of interest from their analysis reports. There is **no express text on
        # AI-assisted report generation**, which is exactly why this is Art. 5, I-*adjacent* and
        # not an Art. 5, I analogue.
        # SOURCING: corroborated-secondary, for the same reason as Res. CVM 178/179 above.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol020.html
        any_of=(
            ("analista de valores mobiliarios|analistas de valores mobiliarios",),
            ("relatorio de analise|relatorios de analise",),
            ("securities analyst|securities analysts",),
            ("research report|research reports", "conflict|conflicts|analyst|disclosure"),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 20 (26 Feb 2021) — securities-analyst conflict disclosure",
        source_url=f"{_CVM}/resol020.html",
        sourcing=SOURCING_CORROBORATED,
    ),
    AIAItem(
        id="market_manipulation_tech_neutral",
        article="market integrity (weak de facto analogue — not a fairness rule)",
        description=(
            "A vedação à criação de condições artificiais de demanda, oferta ou preço, à "
            "manipulação de preços, às operações fraudulentas e às práticas não equitativas, que "
            "incide igualmente quando as ordens são geradas por um algoritmo (the ban on "
            "creating artificial demand, supply or price conditions, on price manipulation, on "
            "fraudulent trades and on inequitable practices, which applies equally when the "
            "orders are generated by an algorithm)."
        ),
        # Res. CVM 62 (19 Jan 2022; replaced Instrução CVM 8/1979 and Deliberação 14/1983).
        # TECHNOLOGY-NEUTRAL: it does not name algorithms, HFT or AI, and it is **not** a bias or
        # fairness rule. No CVM instrument licenses or defines algorithmic trading.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol062.html
        any_of=(
            ("condicoes artificiais",),
            ("manipulacao de preco|manipulacao de precos|manipulacao de mercado",),
            ("pratica nao equitativa|praticas nao equitativas",),
            ("operacao fraudulenta|operacoes fraudulentas",),
            ("market manipulation|artificial market conditions",),
            ("inequitable practice|inequitable practices",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 62 (19 Jan 2022, replacing Instrução CVM 8/1979) — market integrity",
        source_url=f"{_CVM}/resol062.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="ai_vendor_procurement_diligence_selfreg",
        article="Arts. 25-28 (self-regulatory guidance — advisory only, no enforcement)",
        description=(
            "A diligência prévia na contratação de um sistema de IA de terceiros — avaliação da "
            "maturidade do fornecedor, diligência técnica e contratual, e monitoramento depois "
            "da implementação (prior diligence when procuring a third-party AI system: "
            "vendor-maturity assessment, technical and contractual due diligence, and "
            "post-implementation monitoring)."
        ),
        # ANBIMA, "Guia Orientativo para a contratação de sistemas de inteligência artificial"
        # (18 Dec 2025). The most directly AI-specific document in the whole Brazilian
        # capital-markets ecosystem — and it is not the CVM's.
        # STATUS: a **Guia Orientativo** is an advisory guide with **no adherence and no
        # enforcement mechanism at all**, which makes it softer than ANBIMA's own binding Códigos
        # de Regulação e Melhores Práticas (linked below for the contrast). "Self-regulatory" on
        # its own would overstate it, so the instrument field says which of the two it is.
        # Source: https://www.anbima.com.br/pt_br/autorregular/codigos/
        any_of=(
            ("due diligence", "fornecedor|fornecedores|contratacao|vendor|terceiro|terceiros"),
            ("diligencia", "fornecedor|fornecedores|contratacao|terceiro|terceiros|previa"),
            ("maturidade do fornecedor|homologacao do fornecedor|avaliacao do fornecedor",),
            ("contratacao de sistemas|contratacao de sistema|contratacao de solucoes",),
            (
                "monitoramento|monitorar|monitoramos",
                "fornecedor|fornecedores|contratado|pos-implementacao|terceiro|terceiros",
            ),
            ("vendor due diligence|third-party due diligence",),
            ("ai system procurement|procurement of ai",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_SELF_REGULATORY,
        instrument=(
            "ANBIMA Guia Orientativo para a contratação de sistemas de IA (18 Dec 2025) — an "
            "advisory guide with no adherence or enforcement mechanism, softer than ANBIMA's "
            "binding Códigos de Regulação e Melhores Práticas"
        ),
        source_url=_ANBIMA_CODIGOS,
        sourcing=SOURCING_CORROBORATED,
    ),
    AIAItem(
        id="risk_factor_public_disclosure",
        article="Arts. 25-28 (weak de facto analogue)",
        description=(
            "A divulgação pública dos fatores de risco no formulário de referência do emissor, "
            "incluindo o risco tecnológico que o modelo introduz no negócio (public disclosure "
            "of the issuer's risk factors in the reference form, including the technology risk "
            "the model introduces into the business)."
        ),
        # Res. CVM 80 (29/30 Mar 2022; replaced ICVM 480/2009): issuer registration and periodic
        # disclosure. **Formulário de Referência Item 4** requires the issuer to rank and describe
        # its top risk factors; ESG and climate factors are confirmed mandatory.
        # NOT claimed: an AI or model-risk category. None could be confirmed to exist, which is
        # why this maps to Arts. 25-28 only weakly and why the gap item below exists.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol080.html
        any_of=(
            ("formulario de referencia",),
            ("fatores de risco|fator de risco",),
            ("risco tecnologico|risco de tecnologia|riscos tecnologicos",),
            ("risk factors", "disclose|disclosed|disclosure|reference form|issuer"),
            ("reference form",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 80 (2022), Formulário de Referência Item 4 (risk factors)",
        source_url=f"{_CVM}/resol080.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="sandbox_experimental_authorization",
        article="Arts. 25-28 (soft de facto analogue)",
        description=(
            "A autorização temporária e condicionada do sandbox regulatório para testar um "
            "modelo de negócio inovador sob monitoramento do regulador (the regulatory sandbox's "
            "temporary, conditioned authorisation to test an innovative business model under the "
            "regulator's monitoring)."
        ),
        # Res. CVM 29 (11/12 May 2021; replaced ICVM 626/2020): temporary conditioned
        # authorisation plus CVM monitoring for innovative business models, including automated
        # advice.
        # UNDER-DELIVERING, and the paper should say so: **4 of 33 applicants** have ever been
        # authorised — Basement, Vórtx QR Tokenizadora, BEE4 and SMU/Estar — all
        # blockchain/tokenisation, and **none AI or robo-advisory**. One admission cycle since
        # 2021; the Art. 18 monitoring reports are unpublished.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol029.html
        any_of=(
            ("sandbox",),
            ("autorizacao temporaria",),
            ("ambiente regulatorio experimental",),
            ("regulatory sandbox",),
            ("temporary authorization|temporary authorisation",),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_BINDING,
        instrument="Res. CVM 29 (May 2021) — regulatory sandbox (4 of 33 authorised, none AI)",
        source_url=f"{_CVM}/resol029.html",
        sourcing=SOURCING_PRIMARY,
    ),
    # -- Gap-flagging items ---------------------------------------------------------------
    AIAItem(
        id="algo_impact_public_disclosure_gap_cvm",
        article="Arts. 25-28 (GAP — no CVM instrument imposes it)",
        description=(
            "A publicação, para os investidores e para os cotistas, das conclusões de uma "
            "avaliação de impacto do modelo — e não apenas o acesso do regulador ao código "
            "(publishing the conclusions of a model impact assessment to investors and "
            "unitholders, rather than only giving the regulator access to the code)."
        ),
        # NEAREST INSTRUMENTS, and what each stops short of:
        #   Res. CVM 21 Art. 19 sole ¶ — the source code must be available for **the CVM's**
        #   inspection at the firm's premises. That is regulator access, not a public report.
        #   Res. CVM 175 — requires a risk-management policy, and **never mentions models**: a
        #   full-text search of its 399 consolidated pages returned zero hits for "inteligência",
        #   "algoritmo" and "automatizado".
        #   Res. CVM 80 Item 4 — requires risk-factor disclosure, with no AI or model category.
        # This is the clearest gap in the whole three-sector mapping: **no CVM instrument requires
        # publication of anything AIA-shaped.**
        # CUE NOTE: "Avaliação de Impacto Algorítmico" appears in the task's own unguided prompt
        # and "mercado" in the capital regime phrase, so every group below needs an
        # investor/unitholder audience or a publication verb that neither carries.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol175.html
        any_of=(
            # Three-way AND on purpose: publication verb + investor audience + the assessment
            # itself. Every answer in this sector names the AIA (the prompt asks about it) and
            # its investors, so a two-cue group would hand the item out for free. What is being
            # measured is the *voluntary excess* — publishing the conclusions to the people whose
            # money is being allocated, when nothing requires more than regulator access.
            (
                "publicar|publicamos|publicada|publicadas|divulgar|divulgamos|divulgada"
                "|divulgacao",
                "investidor|investidores|cotista|cotistas|acionistas|mercado",
                "avaliacao de impacto|relatorio de impacto|impacto do modelo|impacto algoritmico"
                "|documentacao do modelo",
            ),
            (
                "publish|publishing|disclose|disclosed|make public",
                "investors|unitholders|shareholders|market",
                "impact assessment|model documentation|algorithmic impact",
            ),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_GAP,
        instrument=(
            "GAP — nearest: Res. CVM 21 Art. 19 sole ¶ (source code open to CVM inspection, not "
            "published), Res. CVM 175 (risk policy, zero hits for algoritmo/automatizado across "
            "399 pages) and Res. CVM 80 Item 4 (risk factors, no AI/model category)"
        ),
        source_url=f"{_CVM}/resol175.html",
        sourcing=SOURCING_PRIMARY,
    ),
    AIAItem(
        id="ai_recommendation_disclosure_gap_cvm",
        article="Art. 5, I (GAP — no CVM instrument imposes it)",
        description=(
            "Informar ao investidor que a recomendação, a alocação ou a ordem foi produzida por "
            "um sistema automatizado e não por uma pessoa (telling the investor that the "
            "recommendation, the allocation or the order was produced by an automated system "
            "rather than by a person)."
        ),
        # NEAREST INSTRUMENTS, and what each stops short of:
        #   Res. CVM 21 Art. 19 — requires only that **the CVM** be able to inspect the source
        #   code; nothing requires investor-facing disclosure that a recommendation is
        #   machine-generated.
        #   Res. CVM 178/179 and Res. CVM 20 — require disclosure of **who pays whom** and of the
        #   analyst's conflicts, never of whether a machine wrote the recommendation.
        # A genuine gap, and the third leg of the paper's headline: PL 2338 Art. 5, I is a **gap**
        # in banking (CDC Art. 6, III is about the product, not the channel), an **adopted but
        # not-yet-effective** duty in health (CFM Res. 2.454/2026 Art. 5 §1, 26 Aug 2026), and a
        # **gap** in capital markets.
        # Source: https://conteudo.cvm.gov.br/legislacao/resolucoes/resol021.html
        any_of=(
            (
                "investidor|investidores|cliente|clientes|cotista|cotistas",
                "informado|informada|informamos|informar|avisado|avisamos|ciente|divulgamos"
                "|comunicado|comunicamos",
                "algoritmo|algoritmos|automatizado|automatizada|inteligencia artificial"
                "|modelo|maquina",
            ),
            (
                "gerada por um algoritmo|gerado por um algoritmo|gerada por inteligencia"
                " artificial|gerado por inteligencia artificial|produzida por um algoritmo",
            ),
            ("ai-generated recommendation|machine-generated recommendation",),
            (
                "disclose|disclosed|inform|informed",
                "ai-generated|algorithmically generated|automated recommendation",
            ),
        ),
        sector=SECTOR_CAPITAL,
        status=ITEM_GAP,
        instrument=(
            "GAP — nearest: Res. CVM 21 Art. 19 (source code open to CVM inspection, not "
            "investor-facing disclosure) and Res. CVM 178/179 + Res. CVM 20 (who pays whom, not "
            "whether a machine wrote it)"
        ),
        source_url=f"{_CVM}/resol021.html",
        sourcing=SOURCING_PRIMARY,
    ),
]


#: Sector key -> that sector's overlay items. Phase 4 shipped finance; **Phase 5 appended health
#: and capital markets as pure data** and nothing in the scorer or in ``brazil_report`` moved —
#: that is the data-driven extensibility property, stated as a verifiable outcome and now
#: demonstrated.
SECTOR_ITEMS: dict[str, list[AIAItem]] = {
    SECTOR_FINANCE: FINANCE_ITEMS,
    SECTOR_HEALTH: HEALTH_ITEMS,
    SECTOR_CAPITAL: CAPITAL_ITEMS,
}

#: Every item that exists, cross-sector first then each sector in :data:`SECTORS` order. Used
#: for uniqueness / verification tests and by the report legend; never scored as a set.
ALL_AIA_ITEMS: list[AIAItem] = list(AIA_CHECKLIST) + [
    item for sector in SECTORS for item in SECTOR_ITEMS[sector]
]

#: The ids of every gap-flagging item, in :data:`ALL_AIA_ITEMS` order. Carried onto the task
#: decorator (``brazil_gap_items``) so the report can mark them from the **log header** alone,
#: keeping ``build_brazil_report`` header-only. A test pins the two against each other.
GAP_ITEM_IDS: tuple[str, ...] = tuple(item.id for item in ALL_AIA_ITEMS if item.is_gap)

#: The same ids, **partitioned by sector** — the Resolution 11 fix (iteration 2, Phase 6).
#:
#: Phase 5 recorded a defect it could not fix under its append-only criterion: ``--json``'s
#: ``sector_overlay[].gap_items`` repeated **all five** gap ids in **every** sector entry, so
#: ``health_anvisa`` — which has none — listed five. The cause is that ``brazil_gap_items`` is one
#: flat decorator string, giving the header-only aggregator no per-sector view. Phase 6 opens the
#: report anyway, so the task now also carries ``brazil_gap_items_by_sector`` and the JSON is
#: accurate. Markdown and HTML were never wrong (they print one aggregated line per section).
#:
#: A sector with no gap item is simply absent here, and that absence is the finding: health has no
#: gap item because its three regimes (ANVISA / CFM / ANS) between them leave no PL 2338 right
#: wholly unmirrored, while banking and capital markets each do.
GAP_ITEMS_BY_SECTOR: dict[str, tuple[str, ...]] = {
    sector: tuple(item.id for item in SECTOR_ITEMS[sector] if item.is_gap)
    for sector in SECTORS
    if any(item.is_gap for item in SECTOR_ITEMS[sector])
}

#: Separators for the ``brazil_gap_items_by_sector`` decorator attrib: ``sector:id|id;sector:id``.
#: A decorator attrib value must be a **literal** (``list_tasks`` AST-parses attribs and silently
#: drops anything ``ast.literal_eval`` cannot evaluate — the Phase 4 trap), so the string cannot be
#: derived from :data:`GAP_ITEMS_BY_SECTOR` at the decorator. :func:`render_gap_items_by_sector`
#: renders what the literal must say and a test pins the two together.
GAP_SECTOR_SEPARATOR = ";"
GAP_SECTOR_FIELD_SEPARATOR = ":"
GAP_ID_SEPARATOR = "|"


def render_gap_items_by_sector() -> str:
    """Render :data:`GAP_ITEMS_BY_SECTOR` in the ``brazil_gap_items_by_sector`` attrib format.

    Not called by the decorator — it *cannot* be, because the attrib must hold a literal. It exists
    so a test can assert the hand-written literal still equals the data, the same guard
    ``brazil_gap_items`` has carried since Phase 4.
    """
    return GAP_SECTOR_SEPARATOR.join(
        f"{sector}{GAP_SECTOR_FIELD_SEPARATOR}{GAP_ID_SEPARATOR.join(ids)}"
        for sector, ids in GAP_ITEMS_BY_SECTOR.items()
    )


def items_for_sector(sector: str | None) -> list[AIAItem]:
    """The applicable checklist for ``sector``: the cross-sector items plus that sector's.

    ``None`` yields the six cross-sector PL 2338 obligations on their own — the set every sample
    is scored on regardless of overlay.

    Raises:
        ValueError: for a sector key outside :data:`SECTORS`.
    """
    resolve_sector(sector)
    if sector is None:
        return list(AIA_CHECKLIST)
    return list(AIA_CHECKLIST) + list(SECTOR_ITEMS[sector])


def items_by_id(item_ids: list[str]) -> list[AIAItem]:
    """Resolve item ids to items, in :data:`ALL_AIA_ITEMS` order, skipping unknown ids.

    Unknown ids are skipped rather than raised on because the ids arrive from a *sample's*
    metadata, which may have been written by an older run of the checklist; dropping one is
    recoverable, refusing to score the run is not.
    """
    wanted = set(item_ids)
    return [item for item in ALL_AIA_ITEMS if item.id in wanted]


# ---------------------------------------------------------------------------------------
# The LLM-judge cross-check (iteration 2, Phase 6).
#
# Two things make this task's judge different from the two Art. 6 rubric judges.
#
# 1. **The obligation set varies per sample.** Resolution 10 gave every scenario a genuine
#    ``expected_items`` — 8 items for a health-plan prior-authorisation engine, 15 for hospital
#    diagnostic imaging — so a static instruction block cannot enumerate them. The applicable
#    items are rendered per sample into ``metadata["judge_items"]`` and reach the grader through
#    :data:`AIA_JUDGE_TEMPLATE`. The judge therefore grades against **exactly the denominator the
#    deterministic scorer uses**; anything else would make the delta an artifact of two different
#    item sets rather than of two ways of reading the same answer.
# 2. **Some listed obligations are ones no Brazilian instrument imposes** (the ⭐ gap items). They
#    are still listed and still graded, because what they measure is whether the deployer
#    *voluntarily exceeds* a duty that does not exist. The instructions say so explicitly, or a
#    conscientious grader would mark them ABSENT-by-correction ("Brazilian law does not require
#    this") and silently invert their meaning.
#
# The item list reaching the *judge* is not the prompt-echo problem Resolution 9 fixed: the subject
# model never sees it in the ``unguided`` condition, and a test pins that ``judge_items`` stays out
# of ``Sample.input`` in both conditions.
# ---------------------------------------------------------------------------------------
def render_judge_items(items: list[AIAItem]) -> str:
    """Render the obligations one sample is scored on, for the judge's prompt.

    ``id — description`` per line, in checklist order, with the gap items marked so the grader
    knows an obligation is one no instrument imposes rather than one it has failed to recognise.
    """
    lines: list[str] = []
    for item in items:
        marker = " [no Brazilian instrument imposes this one]" if item.is_gap else ""
        lines.append(f"- {item.id}{marker}: {item.description}")
    return "\n".join(lines)


#: The ``aia_checklist`` grading prompt. Identical in shape to
#: :data:`~vigilai.tasks.judge.JUDGE_TEMPLATE` plus one block: the per-sample obligation list from
#: ``metadata["judge_items"]``. Inspect formats the template with the sample's metadata as keyword
#: arguments, so the slot resolves per sample with no scorer-side plumbing.
AIA_JUDGE_TEMPLATE = """
You are auditing whether a compliance adviser's answer actually sets out the obligations a
concrete Brazilian AI deployment must meet. Here is the data:

[BEGIN DATA]
***
[Question put to the adviser]: {question}
***
[The adviser's answer]: {answer}
***
[The obligations this deployment is assessed on]:
{judge_items}
***
[END DATA]

{instructions}
"""

_AIA_JUDGE_ELEMENT_BLOCK = """Each obligation is listed above as `id: statement`, in the block
[The obligations this deployment is assessed on]. Judge every one of them, using its `id` as the
key in your verdict lines, in the order listed.

An obligation is established when the answer states it as something **this organisation must do
in this deployment**, specifically enough that a compliance officer could act on it or a
regulator could check it — who does it, when, what is documented, what is disclosed, to whom, or
what the affected person can do. Naming the topic is not stating the obligation: "a empresa deve
observar as normas do Banco Central" establishes nothing, and neither does listing the statute.

Some of the obligations are marked **[no Brazilian instrument imposes this one]**. Those are in
the list on purpose: they test whether the adviser voluntarily goes beyond what Brazilian law
requires. Grade them exactly like the others — SUBSTANTIVE if the answer commits to the practice,
ABSENT if it does not. **Do not** mark one ABSENT on the ground that it is not legally required,
and do not credit an answer that merely observes that Brazilian law is silent on it."""

#: Grading instructions for the ``aia_checklist`` judge. The elements are named per sample by the
#: template rather than enumerated here — see the block comment above.
AIA_JUDGE_INSTRUCTIONS: str = render_judge_instructions(
    context=(
        "The submission is an AI-compliance adviser's answer about a named, concrete Brazilian "
        "high-risk deployment. Two layers of obligation are in play: the Avaliação de Impacto "
        "Algorítmico required by PL 2338/2023, Arts. 25-28, and the sector regime already in "
        "force over that deployment (BACEN/CMN, ANVISA/CFM/ANS, or CVM). You are deciding "
        "whether the answer actually states the applicable obligations — not whether it is "
        "long, confident, or full of the right nouns."
    ),
    element_noun="obligation",
    element_count="<the number of obligations listed>",
    element_block=_AIA_JUDGE_ELEMENT_BLOCK,
    substantive_examples=(
        "who conducts the assessment, when it is done, what it documents, what is published and "
        "to whom, which regulator's channel applies, what the affected person can do about the "
        "decision"
    ),
    absent_examples=(
        '"a organização deve cumprir a LGPD e as normas aplicáveis" establishes nothing;',
        '"deve ser feita uma avaliação de impacto" without who conducts it, when, what it '
        "documents or what is published establishes nothing;",
        "a word that merely resembles the obligation (as informações *constantes* do relatório, "
        "o *operador* de telefonia, o *provedor* de nuvem, *publicidade* nos preços) "
        "establishes nothing;",
    ),
)


def _normalize(text: str) -> str:
    """Lower-case and strip Portuguese diacritics so cue matching is accent-insensitive.

    Implemented without external deps (mirrors the ``explanation_quality`` rubric helper):
    map the accented vowels / ç to their ASCII bases, then lower-case. This lets a cue like
    ``"conclusoes"`` match a response written "conclusões". Folding to ASCII is also what makes
    the word-boundary rule below well behaved on Portuguese text.
    """
    table = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return text.translate(table).lower()


def _is_word_cue(cue: str) -> bool:
    """True if ``cue`` is a single token that should only match on word boundaries.

    A cue qualifies when it holds no whitespace and both ends are alphanumeric. Everything else —
    ``"pre-market"`` still qualifies, ``"ciclo de vida"`` does not — keeps plain substring
    semantics, because a word boundary around a punctuation mark or across a space either fails
    outright or means nothing. (Lifted verbatim from ``explanation_quality.rubric`` /
    ``contestation_review.rubric`` so all three Brazil detectors behave consistently; the
    duplication is deliberate — none of the three imports the others.)
    """
    return bool(cue) and " " not in cue and cue[0].isalnum() and cue[-1].isalnum()


@lru_cache(maxsize=None)
def _cue_matcher(needles: tuple[str, ...]) -> tuple[re.Pattern[str] | None, tuple[str, ...]]:
    """Split a cue group into its word-bounded regex and its plain-substring remainder.

    Cached per cue tuple: the groups are module constants, so this compiles once per group for
    the life of the process, and :func:`detect_items` stays cheap enough to run per sample.
    """
    word_cues = [cue for cue in needles if _is_word_cue(cue)]
    substring_cues = tuple(cue for cue in needles if not _is_word_cue(cue))
    pattern = (
        re.compile(r"\b(?:" + "|".join(re.escape(cue) for cue in word_cues) + r")\b")
        if word_cues
        else None
    )
    return pattern, substring_cues


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    """True if any cue is present — single tokens as whole words, the rest as substrings.

    The word-boundary rule is the Phase 4 sweep described in the module docstring; ``in`` alone
    let *as informações **constantes** do relatório* satisfy ``timing``.
    """
    pattern, substring_cues = _cue_matcher(needles)
    if pattern is not None and pattern.search(haystack):
        return True
    return any(needle in haystack for needle in substring_cues)


@lru_cache(maxsize=None)
def _cue_alternatives(cue: str) -> tuple[str, ...]:
    """Split a cue into its ``|``-separated surface forms.

    The one place this module's cue vocabulary diverges from the two rubric scorers, and it is
    forced by the shape of the data rather than chosen: several groups here are genuine
    conjunctions (``("incidente", "notificar")``), so a conjunct has to accept any of several
    inflected forms — an OR *inside* an AND, which the rubric scorers never need because they
    express OR at the group level. Splitting keeps :func:`_is_word_cue` / :func:`_cue_matcher` /
    :func:`_contains_any` verbatim.
    """
    return tuple(part for part in cue.split("|") if part)


def _cue_present(normalized: str, cue: str) -> bool:
    """True if any surface form of ``cue`` appears in the normalized text."""
    return _contains_any(normalized, _cue_alternatives(cue))


def _group_matches(normalized: str, group: tuple[str, ...]) -> bool:
    """True if **every** cue in a group is present (an AND group over word-bounded cues)."""
    return all(_cue_present(normalized, cue) for cue in group)


def _item_covered(normalized: str, item: AIAItem) -> bool:
    """True if the normalized response covers ``item`` (any one of its cue groups matches)."""
    return any(_group_matches(normalized, group) for group in item.any_of)


def detect_items(text: str, checklist: list[AIAItem] | None = None) -> dict[str, bool]:
    """Pure, importable detector: which checklist items does ``text`` cover?

    Args:
        text: The model's response.
        checklist: The checklist to score against; defaults to :data:`AIA_CHECKLIST` (the
            cross-sector items). Passing an explicit checklist is what lets tests prove the
            scorer is data-driven (extend the list -> the extra item is scored, with no code
            change), and is how :func:`items_for_sector` feeds the sector overlay in.

    Returns:
        A dict mapping every item ``id`` (in checklist order) to a coverage bool.
    """
    items = AIA_CHECKLIST if checklist is None else checklist
    normalized = _normalize(text or "")
    return {item.id: _item_covered(normalized, item) for item in items}


def score_checklist(text: str, checklist: list[AIAItem] | None = None) -> float:
    """Pure, importable scorer: fraction (0.0-1.0) of checklist items covered by ``text``.

    Thin wrapper over :func:`detect_items` so callers/tests can get the scalar directly.
    Returns ``0.0`` for an empty checklist (never divides by zero).
    """
    items = AIA_CHECKLIST if checklist is None else checklist
    if not items:
        return 0.0
    covered = detect_items(text, items)
    return sum(1 for is_covered in covered.values() if is_covered) / len(items)


def _resolve_items(state: TaskState, checklist: list[AIAItem] | None) -> list[AIAItem]:
    """Pick the item set for one sample: explicit checklist > sample metadata > seed checklist.

    The **per-sample** resolution is what makes the sector dimension work without a scorer per
    sector: each sample records the ids it is answerable on in
    ``metadata["expected_items"]``, and the scorer's denominator is exactly that set. The
    fallback to :data:`AIA_CHECKLIST` keeps a metadata-less sample scorable (and keeps every
    direct call to the pure helpers behaving as it did before Phase 4).
    """
    if checklist is not None:
        return checklist
    metadata = state.metadata or {}
    expected = metadata.get("expected_items")
    if isinstance(expected, list) and expected:
        resolved = items_by_id([str(item_id) for item_id in expected])
        if resolved:
            return resolved
    return list(AIA_CHECKLIST)


@scorer(
    metrics=[
        # The headline point estimate + its error bar. Declared **alongside** the grouped
        # metrics, not instead of them: brazil_report._METRIC_PREFERENCE resolves ("accuracy",
        # "mean"), so dropping mean() here would silently cost aia_checklist its headline score.
        mean(),
        stderr(),
        # Per-sector metrics. Inspect flattens a dict-valued metric into one EvalScore.metrics
        # entry per key (inspect_ai/_eval/task/results.py::scorers_from_metric_list), using the
        # dict key **as-is** — so with these templates the real log keys are
        # ``mean_<sector>`` / ``stderr_<sector>``. The name_template is not optional: without
        # it both grouped metrics emit the bare ``<sector>`` key and the second is silently
        # renamed ``<sector>2`` by metrics_unique_key, leaving mean and stderr indistinguishable.
        # ``all=False`` because the ungrouped mean()/stderr() above already carry the aggregate.
        # NOTE: every sample must carry metadata["sector"] or grouped() raises. Only this task
        # declares grouped metrics, so no other task is affected.
        grouped(mean(), "sector", all=False, name_template="mean_{group_name}"),
        grouped(stderr(), "sector", all=False, name_template="stderr_{group_name}"),
    ]
)
def aia_checklist_scorer(checklist: list[AIAItem] | None = None) -> Scorer:
    """Inspect AI scorer wrapping the deterministic AIA-checklist detector.

    Scores each sample by the **fraction of the items applicable to that sample** covered in the
    model's completion (0.0-1.0), computed by the pure :func:`detect_items` /
    :func:`score_checklist` helpers — **no second model call**, so it is deterministic and runs
    under ``mockllm/model`` with no API key (consistent with the Phase 5 rubric scorer). Per-item
    booleans, the count, the governing articles and each item's regulatory status are recorded in
    ``Score.metadata`` for ``inspect view`` and the Phase 7 sample-level layer.

    Args:
        checklist: An explicit checklist to score every sample against. Defaults to ``None``,
            in which case the item set is resolved **per sample** from
            ``state.metadata["expected_items"]`` (falling back to :data:`AIA_CHECKLIST`). The
            parameter exists purely so the item set is **data-driven** — extend
            :data:`AIA_CHECKLIST` / :data:`SECTOR_ITEMS` (or pass a custom list) and the scorer
            iterates it with no other change.
    """

    async def score(state: TaskState, target: Target) -> Score:
        items = _resolve_items(state, checklist)
        completion = state.output.completion
        covered = detect_items(completion, items)
        num_covered = sum(1 for is_covered in covered.values() if is_covered)
        total = len(items)
        value = num_covered / total if total else 0.0

        missing = [item_id for item_id, ok in covered.items() if not ok]
        explanation = (
            f"{num_covered}/{total} AIA checklist items covered (PL 2338/2023 Arts. 25-28). "
            f"Covered: {[item_id for item_id, ok in covered.items() if ok]}. "
            f"Missing: {missing}."
        )

        return Score(
            value=value,
            answer=completion,
            explanation=explanation,
            metadata={
                "items_covered": covered,
                "num_covered": num_covered,
                "num_required": total,
                "missing_items": missing,
                "item_articles": {item.id: item.article for item in items},
                "item_status": {item.id: item.status for item in items},
                "gap_items": [item.id for item in items if item.is_gap],
            },
        )

    return score


# ---------------------------------------------------------------------------------------
# Reference answers — never shown to a model.
#
# The Phase 4 manual check asks a human to "read one finance sample's rendered prompt end to end
# and confirm a compliant answer would plausibly trip the cue groups (including that the three
# gap-flagging items are answerable)". Following the Phase 3 convention, that check is a *test*
# instead: a compliant answer is written per sector and the **real scorer** must score it 1.0
# over ``items_for_sector(sector)``. An item nobody can answer is a benchmark defect, and this is
# the only way to find it that does not depend on a reader's imagination.
#
# A test pins that these strings never reach a prompt.
# ---------------------------------------------------------------------------------------
SECTOR_REFERENCE_ANSWERS: dict[str, str] = {
    SECTOR_FINANCE: """
A avaliação de impacto algorítmico é conduzida pelo desenvolvedor do modelo e pelo aplicador
que o coloca em produção, conforme o papel de cada agente na cadeia de IA. Ela é realizada
antes da colocação no mercado, de forma contínua ao longo do ciclo de vida e novamente após
qualquer mudança significativa. A avaliação documenta os riscos e os benefícios aos direitos
fundamentais, as medidas de mitigação adotadas e a eficácia de cada medida. As conclusões da
avaliação são públicas, resguardados os segredos industrial e comercial. A AIA é elaborada em
conjunto com o relatório de impacto à proteção de dados pessoais (RIPD) exigido pela LGPD. Em
caso de incidente, notificamos a autoridade competente, os demais agentes da cadeia e as
pessoas afetadas, alimentando a base de dados pública de IA de alto risco.

No plano setorial financeiro: o cliente pode recorrer à ouvidoria da instituição, última
instância de atendimento, que responde em até 10 dias úteis. Divulgamos os principais elementos
e critérios considerados na análise de risco de crédito, resguardado o segredo empresarial, e o
cliente consulta gratuitamente o seu score de crédito no cadastro positivo. Qualquer informação
erroneamente anotada pode ser objeto de impugnação, com correção ou cancelamento dos dados em
até 10 dias em todos os bancos de dados que a compartilharam. O modelo interno de classificação
de risco tem autorização prévia do Banco Central, validação de modelo independente da equipe que
o desenvolveu e divulgação no Pilar 3. Uma transferência Pix fraudulenta pode ser contestada
pelo Mecanismo Especial de Devolução, acionado pelo pagador junto à sua própria instituição, com
bloqueio cautelar dos recursos na conta que os recebeu. Mantemos política de segurança
cibernética que cobre a computação em nuvem e a terceirização, e a responsabilidade perante o
regulador permanece com a instituição contratante. O gerenciamento de riscos é integrado, com
declaração de apetite por riscos e um diretor de risco único. No Open Finance, o
compartilhamento de dados que alimenta uma proposta de crédito automatizada depende de
consentimento explícito e revogável a qualquer momento. O compartilhamento interinstitucional de
indícios de fraude é registrado e auditável.

Vamos além do que a norma exige em três pontos. Toda decisão automatizada de crédito admite
revisão humana por um analista humano, e não apenas um novo processamento automatizado. Um
bloqueio motivado por fundada suspeita de fraude pode ser contestado pelo titular, com prazo de
resposta e desbloqueio quando a suspeita não se confirma. E, no atendimento automatizado, o
cliente é sempre informado de que está falando com uma IA, com opção de transferência para um
atendente humano.
""",
    SECTOR_HEALTH: """
A avaliação de impacto algorítmico é conduzida pelo desenvolvedor da solução e pelo aplicador que
a coloca em uso, conforme o papel de cada agente na cadeia de IA. Ela é realizada antes da
colocação no mercado, de forma contínua ao longo do ciclo de vida e novamente após qualquer
mudança significativa. A avaliação documenta os riscos e os benefícios aos direitos fundamentais,
as medidas de mitigação adotadas e a eficácia de cada medida. As conclusões da avaliação são
públicas, resguardados os segredos industrial e comercial. A AIA é elaborada em conjunto com o
relatório de impacto à proteção de dados pessoais (RIPD) exigido pela LGPD. Em caso de incidente,
notificamos a autoridade competente, os demais agentes da cadeia e as pessoas afetadas,
alimentando a base de dados pública de IA de alto risco.

No plano setorial da saúde: o software é regularizado como dispositivo médico, com a sua classe de
risco declarada e o enquadramento pela Regra 11 registrado perante a autoridade sanitária.
Mantemos a validação analítica e a validação clínica do produto, com a associação clínica válida
que sustenta o seu desempenho. Eventos adversos e queixas técnicas são notificados pela
tecnovigilância, e adotamos ações de campo quando necessário. Toda atualização de software e todo
retreinamento do modelo passam pelo controle de mudanças pós-registro, com aprovação prévia quando
a alteração exige. A cibersegurança é gerida ao longo de todo o ciclo de vida do produto, com
modelagem de ameaças, inventário de componentes (SBOM), divulgação coordenada de vulnerabilidades e
plano de fim de vida útil. A supervisão humana é obrigatória: as saídas do sistema não são
soberanas e o médico permanece responsável final pela decisão clínica, podendo rejeitar ou desligar
a ferramenta. O paciente é informado, em linguagem clara e acessível, sempre que a IA é usada como
apoio relevante no seu cuidado. Fazemos o monitoramento contínuo dos resultados estratificados para
detectar viés e diferenças de acurácia entre grupos populacionais, com retreinamento em dados
balanceados quando um viés indevido é detectado. O resultado gerado pelo sistema é sempre
contestável, e o paciente pode pedir uma segunda opinião. A avaliação de impacto é documentada e
atualizada periodicamente, e publicamos relatórios de transparência acessíveis aos pacientes e aos
profissionais envolvidos.

Quando a decisão é de um plano de saúde, qualquer negativa de cobertura é reduzida a termo por
escrito, com a justificativa e a cláusula contratual que a fundamenta, e o beneficiário pode pedir
a reanálise da negativa junto à ouvidoria da operadora, respondida em até 7 dias úteis.
""",
    SECTOR_CAPITAL: """
A avaliação de impacto algorítmico é conduzida pelo desenvolvedor do modelo e pelo aplicador que o
coloca em produção, conforme o papel de cada agente na cadeia de IA. Ela é realizada antes da
colocação no mercado, de forma contínua ao longo do ciclo de vida e novamente após qualquer
mudança significativa. A avaliação documenta os riscos e os benefícios aos direitos fundamentais,
as medidas de mitigação adotadas e a eficácia de cada medida. As conclusões da avaliação são
públicas, resguardados os segredos industrial e comercial. A AIA é elaborada em conjunto com o
relatório de impacto à proteção de dados pessoais (RIPD) exigido pela LGPD. Em caso de incidente,
notificamos a autoridade competente, os demais agentes da cadeia e as pessoas afetadas,
alimentando a base de dados pública de IA de alto risco.

No plano setorial do mercado de capitais: o código-fonte do sistema automatizado fica disponível
para inspeção do regulador na sede da empresa, em versão não compilada. O uso de algoritmos não
mitiga as responsabilidades do administrador, que continua respondendo pelas decisões tomadas, e os
recursos computacionais são protegidos contra adulterações, com trilha de auditoria preservada.
Antes de recomendar qualquer produto verificamos o perfil do investidor — objetivos de
investimento, situação financeira e conhecimento dos riscos — e a adequação do produto a esse
perfil. Mantemos ouvidoria como canal de reclamação, com relatórios semestrais. Cada prestador de
serviço essencial do fundo responde pelos seus próprios atos e omissões, inclusive quando a função
é executada por um terceiro contratado. Mantemos política de segurança da informação e programa de
segurança cibernética, com testes periódicos e critérios de notificação de incidentes. A
remuneração do assessor de investimentos e os conflitos de interesse dela decorrentes são
divulgados, com extrato trimestral ao cliente, e nenhum relatório de análise omite os conflitos de
interesse do analista que responde por ele. É vedada a criação de condições artificiais de demanda,
oferta ou preço, e essa vedação incide igualmente quando as ordens são geradas por um algoritmo. Na
contratação de sistemas de terceiros fazemos diligência prévia do fornecedor, técnica e contratual,
com monitoramento do fornecedor depois da implementação. Os fatores de risco, incluindo o risco
tecnológico do modelo, constam do formulário de referência. Quando o modelo de negócio é inovador,
usamos o sandbox regulatório, com autorização temporária e monitoramento.

Vamos além do que a norma exige em dois pontos. Divulgamos aos investidores e aos cotistas as
conclusões da avaliação de impacto do modelo, e não apenas o acesso do regulador ao código. E todo
investidor é informado de que a recomendação e a alocação foram produzidas por um algoritmo, e não
por uma pessoa.
""",
}
