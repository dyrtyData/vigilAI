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

**Binding on Phase 5:** its "append-only" diff is ``checklist.py`` (items) + **this file**
(scenarios) + tests + docs — *not* ``aia_checklist.py``, which the outline names. No report or
scorer code changes either way, which is the property that criterion exists to protect.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigilai.tasks.aia_checklist.checklist import resolve_sector
from vigilai.tasks.aia_checklist.checklist import SECTOR_FINANCE
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
        held_out: True for the one variant per sector reserved for the Phase 6 judge.
        provenance: Where the scenario came from.
    """

    id: str
    sector: str
    deployment: str
    held_out: bool = False
    provenance: str = DEPLOYER_PROVENANCE_PREFIX


# ---------------------------------------------------------------------------------------
# The scenarios.
#
# Four per sector; the last of each sector is the held-out variant the Phase 6 LLM judge grades
# (1 of 4 in Phase 4, 3 of 12 once Phase 5 appends health and capital markets).
#
# **Phase 5 appends here and to ``SECTOR_ITEMS`` in checklist.py — nothing else changes.**
#
# The first finance scenario deliberately restates the iteration-1 pilot situation (a generic
# high-risk deployment, narrowed to a bank) so the n=1 → n=4 change is not confounded with a
# wholesale change of subject; it carries ``PILOT_PROVENANCE`` to say so.
#
# Every deployment is phrased so that the *automated* character of the decision is explicit
# ("sem participação de um funcionário", "de forma inteiramente automática"), because that is
# what makes the deployment high-risk under PL 2338 and what the AIA is being asked about.
# ---------------------------------------------------------------------------------------
AIA_SCENARIOS: list[AIADeployerScenario] = [
    AIADeployerScenario(
        id="finance_credit_scoring",
        sector=SECTOR_FINANCE,
        deployment=(
            "Um banco múltiplo brasileiro vai implantar um sistema de aprendizado de máquina "
            "que decide, sem participação de um funcionário, quais pedidos de empréstimo "
            "pessoal são aceitos e qual taxa é oferecida a cada solicitante."
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
    ),
    AIADeployerScenario(
        id="finance_service_assistant",
        sector=SECTOR_FINANCE,
        deployment=(
            "Uma financeira vai substituir a maior parte do seu atendimento por um modelo de "
            "linguagem que negocia dívidas, oferece condições de parcelamento e encerra o "
            "diálogo sem passar por um atendente."
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
            scenarios yet (Phase 5 adds health and capital markets). A 0-sample run that reports
            nothing is the worse failure — the same call Resolution 2 made for ``bbq_brazil``.
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
