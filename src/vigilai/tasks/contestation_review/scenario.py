"""The ``contestation_review`` scenario class, its four domains, and its licence parity set.

Split out of :mod:`vigilai.tasks.contestation_review.dataset` in iteration 2 Phase 3 for the same
reason as its ``explanation_quality`` sibling: the generated literals must construct the scenario
class without importing the module that imports them. Graph:
``rubric_scenario → scenario → generated → dataset``.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigilai.tasks.rubric_scenario import RubricScenario


@dataclass(frozen=True)
class ContestationScenario(RubricScenario):
    """A high-stakes automated decision the affected person wants to **contest**.

    Adds no fields to :class:`~vigilai.tasks.rubric_scenario.RubricScenario`; the distinct type
    keeps the two rubric datasets from being interchangeable by accident.
    """


# ---------------------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------------------
#
# All four already existed in iteration 1 — credit / employment / social benefit are LGPD Art. 20's
# canonical decisions, and content moderation was added so this dataset is not a verbatim copy of
# the explanation-quality set. Phase 3 adds two variants to each, not a fifth domain (structure
# outline: "contestation_review already has four domains and needs no new one").
DOMAIN_CREDIT = "credit"
DOMAIN_EMPLOYMENT = "employment"
DOMAIN_SOCIAL_BENEFIT = "social_benefit"
DOMAIN_CONTENT_MODERATION = "content_moderation"

#: Fixed order for every deterministic traversal, in the iteration-1 order.
DOMAIN_ORDER: tuple[str, ...] = (
    DOMAIN_CREDIT,
    DOMAIN_EMPLOYMENT,
    DOMAIN_SOCIAL_BENEFIT,
    DOMAIN_CONTENT_MODERATION,
)

#: Variants per domain — 4 × 3 = 12 scenarios.
VARIANTS_PER_DOMAIN = 3

#: Held-out variants per domain — 4 × 1 = 4 held out of 12 (33 %, Resolution 1).
HELD_OUT_PER_DOMAIN = 1

#: Rubric elements every scenario licenses **only** through the task frame.
#:
#: Four of the six, and that is a fact about this rubric rather than a weakness of the scenarios:
#: ``contestation_channel``, ``contestation_deadline``, ``reviewer_authority`` and
#: ``review_outcome_communicated`` are all things the **deploying institution must offer**, so a
#: scenario that stated them would be handing the model the answer. The parity rule is therefore
#: doing double duty here — anti-confound *and* anti-leakage. The two remaining elements are
#: genuinely licensed by the scenario: the affected person's own request establishes both that
#: they contest the outcome (``contestation_right``) and that they want a person to look at it
#: (``human_review``), exactly as in the four iteration-1 pilot scenarios.
FRAME_LICENSED_ELEMENTS = frozenset(
    {
        "contestation_channel",
        "contestation_deadline",
        "reviewer_authority",
        "review_outcome_communicated",
    }
)
