"""Single source of truth for the EU technical-requirement → Brazil PL 2338/2023 mapping.

COMPL-AI tags every benchmark with a ``technical_requirement`` string (one of nine
EU-AI-Act-derived categories). vigilAI preserves those strings unchanged and layers
Brazil PL 2338/2023 (Chapter II rights) metadata on top so the same model can be scored
against both regimes side-by-side.

This module is the authoritative mapping. It is consumed by:

* the task decorators (``brazil_article=`` / ``brazil_scope=`` kwargs are kept in sync
  with this table — see ``tests/test_brazil_mapping.py``);
* ``vigilai list --brazil`` (grouping tasks by Brazil article);
* the Phase 7 compliance report (aggregating scores per Brazil article).

Mapping rationale (design discussion §2, research §4):

* PL 2338/2023 splits its rights across **Chapter II ("Dos Direitos")**:
  - **Art. 5** — rights applicable to *all* AI systems (information, privacy,
    non-discrimination).
  - **Arts. 6-11** — additional rights for *high-risk* systems only (explanation,
    contestation, human review).
* Hence ``brazil_scope`` is ``"all_ai"`` for Art. 5 rights and ``"high_risk"`` for Art. 6
  rights.
"""

from __future__ import annotations

from typing import Final


# Valid Brazil scope tags. "all_ai" = Art. 5 rights (every AI system);
# "high_risk" = Art. 6 rights (high-risk systems only).
BRAZIL_SCOPES: Final[tuple[str, ...]] = ("all_ai", "high_risk")


# EU COMPL-AI technical_requirement  ->  (Brazil PL 2338/2023 article, scope)
#
# NOTE: the requirement strings must match the @task(technical_requirement=...) strings
# in the task source files *exactly*, including the em dash (U+2014) in the two bias /
# fairness requirements. ``brazil_article_for`` returns None for any unmapped requirement
# (e.g. "Capabilities, Performance, and Limitations") so the original EU-only tasks remain
# valid and untagged.
TECH_REQ_TO_BRAZIL: Final[dict[str, tuple[str, str]]] = {
    # Art. 5, I — Right to prior information about interactions with AI (all systems).
    "Disclosure of AI": ("Art. 5, I", "all_ai"),
    # Art. 5, III — Right to non-discrimination (all systems). COMPL-AI splits fairness
    # into two technical requirements; both map to Brazil's single non-discrimination
    # right.
    "Representation — Absence of Bias": ("Art. 5, III", "all_ai"),
    "Fairness — Absence of Discrimination": ("Art. 5, III", "all_ai"),
    # Art. 6, I — Right to explanation of automated decisions (high-risk systems;
    # cf. LGPD Art. 20).
    "Interpretability": ("Art. 6, I", "high_risk"),
}


def brazil_article_for(requirement: str) -> tuple[str, str] | None:
    """Return the ``(brazil_article, brazil_scope)`` pair for an EU technical requirement.

    Args:
        requirement: A COMPL-AI ``technical_requirement`` string.

    Returns:
        ``(article, scope)`` if the requirement is mapped to a Brazil PL 2338/2023
        article, otherwise ``None`` (EU-only requirements have no Brazil counterpart yet).
    """
    return TECH_REQ_TO_BRAZIL.get(requirement)
