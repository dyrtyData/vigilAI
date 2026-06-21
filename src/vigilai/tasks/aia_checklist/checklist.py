"""Brazil PL 2338/2023 Arts. 25-28 — Algorithmic Impact Assessment (AIA) checklist + scorer.

This module is the heart of the ``aia_checklist`` benchmark. Brazil's PL 2338/2023 requires
operators of high-risk AI to conduct an **Avaliação de Impacto Algorítmico (AIA)** — a
*fundamental-rights* impact assessment (risks **and** benefits), distinct from the EU's
market-conformity certification (research §5). The benchmark tests whether a model, asked to
lay out the AIA obligations, demonstrates awareness of the items the law requires.

Design decision — **keep the AIA representation data-driven, not a hard-coded ANPD format**
(design discussion §10.3 / research §10.3). Arts. 25-28 delegate the detailed AIA methodology
to future ANPD *Instruções Normativas*. So instead of baking one fixed checklist into the
scorer, we externalize the requirement items into a single editable data structure
(:data:`AIA_CHECKLIST`). Each item is self-contained — it carries its own id, description, the
governing article, and the multilingual detection cues used to decide whether a response
covers it. **The scorer iterates over whatever items the checklist defines.** A future ANPD
item can therefore be added by appending one :class:`AIAItem` to :data:`AIA_CHECKLIST` — no
change to the scorer or the task code is required (this is exactly the flexibility the manual
verification checks).

The seed items reflect research §5 ("Algorithmic Impact Assessment (AIA) vs. EU Conformity
Assessment"):

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
:func:`_item_covered`. The score is the **fraction of checklist items covered** (0.0-1.0),
with per-item booleans recorded in ``Score.metadata`` for inspection.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from inspect_ai.scorer import mean
from inspect_ai.scorer import Score
from inspect_ai.scorer import Scorer
from inspect_ai.scorer import scorer
from inspect_ai.scorer import stderr
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState


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

    Attributes:
        id: Stable machine key for the item (used in ``Score.metadata`` and tests).
        article: The governing PL 2338/2023 article(s), for documentation / the report.
        description: Human-readable statement of the obligation. Surfaced to the model in the
            prompt so the checklist is the single source of truth for *what is asked* as well
            as *what is scored*.
        any_of: Cue groups; the item is covered when **at least one** group is fully matched.
            Each group is a tuple of substrings that must **all** appear (accent-folded,
            lower-cased) in the response for that group to match. This "OR of ANDs" shape lets
            an item be satisfied by a pt-BR phrasing *or* an English phrasing *or* a strong
            single keyword, while still requiring genuine topical coverage (e.g. the timing
            item needs an actual timing cue, not just the word "impacto").
    """

    id: str
    article: str
    description: str
    any_of: tuple[tuple[str, ...], ...] = field(default_factory=tuple)


# The seed AIA checklist (research §5). Editable data — add/extend items here only.
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
            ("desenvolvedor",),
            ("operador",),
            ("aplicador",),
            ("fornecedor",),
            ("agente", "cadeia"),
            ("developer",),
            ("applier",),
            ("deployer",),
            ("provider",),
            ("who", "conduct"),
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
            ("antes",),
            ("previamente",),
            ("previa",),
            ("ciclo de vida",),
            ("continua",),
            ("contínua",),
            ("periodica",),
            ("mudanca significativa",),
            ("alteracao significativa",),
            ("pre-market",),
            ("before",),
            ("lifecycle",),
            ("continuous",),
            ("ongoing",),
            ("significant change",),
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
            ("risco", "direitos"),
            ("riscos", "beneficios"),
            ("direitos fundamentais",),
            ("medidas de mitigacao",),
            ("mitigacao",),
            ("mitigar",),
            ("risk", "benefit"),
            ("fundamental rights",),
            ("mitigation",),
            ("mitigate",),
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
            ("conclusoes", "publicas"),
            ("conclusao", "publica"),
            ("publicar",),
            ("publicidade",),
            ("divulgacao",),
            ("transparencia",),
            ("segredo",),
            ("conclusions", "public"),
            ("publish",),
            ("publicly",),
            ("trade secret",),
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
            ("relatorio de impacto", "protecao de dados"),
            ("lgpd",),
            ("protecao de dados",),
            ("conjunto", "dados pessoais"),
            ("data protection impact",),
            ("dpia",),
            ("jointly", "data protection"),
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
            ("incidente", "notific"),
            ("comunicar", "incidente"),
            ("autoridade competente",),
            ("anpd", "incidente"),
            ("pessoas afetadas",),
            ("base de dados publica",),
            ("incident", "notif"),
            ("notify", "authority"),
            ("affected persons",),
            ("public database",),
        ),
    ),
]


def _normalize(text: str) -> str:
    """Lower-case and strip Portuguese diacritics so cue matching is accent-insensitive.

    Implemented without external deps (mirrors the ``explanation_quality`` rubric helper):
    map the accented vowels / ç to their ASCII bases, then lower-case. This lets a cue like
    ``"conclusoes"`` match a response written "conclusões".
    """
    table = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return text.translate(table).lower()


def _group_matches(normalized: str, group: tuple[str, ...]) -> bool:
    """True if **every** cue in a group appears in the normalized text (an AND group)."""
    return all(_normalize(cue) in normalized for cue in group)


def _item_covered(normalized: str, item: AIAItem) -> bool:
    """True if the normalized response covers ``item`` (any one of its cue groups matches)."""
    return any(_group_matches(normalized, group) for group in item.any_of)


def detect_items(text: str, checklist: list[AIAItem] | None = None) -> dict[str, bool]:
    """Pure, importable detector: which checklist items does ``text`` cover?

    Args:
        text: The model's response.
        checklist: The checklist to score against; defaults to :data:`AIA_CHECKLIST`. Passing
            an explicit checklist is what lets tests prove the scorer is data-driven (extend
            the list -> the extra item is scored, with no code change).

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


@scorer(metrics=[mean(), stderr()])
def aia_checklist_scorer(checklist: list[AIAItem] | None = None) -> Scorer:
    """Inspect AI scorer wrapping the deterministic AIA-checklist detector.

    Scores each sample by the **fraction of checklist items covered** in the model's
    completion (0.0-1.0), computed by the pure :func:`detect_items` / :func:`score_checklist`
    helpers — **no second model call**, so it is deterministic and runs under ``mockllm/model``
    with no API key (consistent with the Phase 5 rubric scorer). Per-item booleans, the count
    and the governing articles are recorded in ``Score.metadata`` for ``inspect view`` and the
    Phase 7 report.

    Args:
        checklist: The checklist to score against. Defaults to :data:`AIA_CHECKLIST`; accepted
            as a parameter purely so the item set is **data-driven** — extend
            :data:`AIA_CHECKLIST` (or pass a custom list) and the scorer iterates it with no
            other change.
    """
    items = AIA_CHECKLIST if checklist is None else checklist

    async def score(state: TaskState, target: Target) -> Score:
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
            },
        )

    return score
