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

ITEM_STATUSES: tuple[str, ...] = (
    ITEM_BINDING,
    ITEM_GAP,
    ITEM_NON_BINDING,
    ITEM_SELF_REGULATORY,
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


#: Sector key -> that sector's overlay items. **Phase 5 appends here** (health / capital
#: markets) and nothing else in this module or in the scorer changes — that is the data-driven
#: extensibility property, stated as a verifiable outcome.
SECTOR_ITEMS: dict[str, list[AIAItem]] = {
    SECTOR_FINANCE: FINANCE_ITEMS,
    SECTOR_HEALTH: [],
    SECTOR_CAPITAL: [],
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
}
