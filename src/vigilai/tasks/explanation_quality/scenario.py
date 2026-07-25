"""The ``explanation_quality`` scenario class, its four domains, and its licence parity set.

Split out of :mod:`vigilai.tasks.explanation_quality.dataset` in iteration 2 Phase 3 so the
generated literals in :mod:`vigilai.tasks.explanation_quality.generated` can construct
``ExplanationScenario`` without importing ``dataset`` (which imports ``generated`` in turn). The
import graph is a straight line — ``rubric_scenario → scenario → generated → dataset`` — and
``dataset`` re-exports every public name here, so existing imports keep working.
"""

from __future__ import annotations

from dataclasses import dataclass

from vigilai.tasks.rubric_scenario import RubricScenario


@dataclass(frozen=True)
class ExplanationScenario(RubricScenario):
    """A high-stakes automated decision the model must *explain* (Art. 6, I; LGPD Art. 20).

    Adds no fields to :class:`~vigilai.tasks.rubric_scenario.RubricScenario`; the distinct type
    exists so a ``contestation_review`` scenario cannot be dropped into this dataset by accident.
    """


# ---------------------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------------------
#
# Credit / employment / social benefit are the iteration-1 domains — the canonical "affecting
# personal, professional, consumer, and credit profiles" decisions LGPD Art. 20 names.
#
# ``health_coverage`` is iteration 2's fourth domain (structure outline, Resolution 4). ANS
# RN 623/2024 gives it a statutory hook that maps almost one-to-one onto what this rubric scores:
# Art. 14 (**caput**) requires any coverage denial to be reduced to a **clear written
# justification citing the specific contractual clause or legal basis** — §1 extends the duty to
# every service channel and §2 is only the *format* rule (printable / downloadable); the "§2"
# pincite this comment used to carry was corrected in the Phase 3 review — and Art. 16 lets the
# beneficiary request an **ombudsman reanalysis answered within 7 business days**.
# It is *not* drafted as an AI rule —
# that is the point of a "de facto analogue" — and it bridges to the Phase 5 health overlay.
# ``content_moderation`` was rejected as the fourth domain because it already exists in
# ``contestation_review``, and duplicating it would confound the two tasks' domain sets when their
# scores are compared.
DOMAIN_CREDIT = "credit"
DOMAIN_EMPLOYMENT = "employment"
DOMAIN_SOCIAL_BENEFIT = "social_benefit"
DOMAIN_HEALTH_COVERAGE = "health_coverage"

#: Fixed order for every deterministic traversal (the round-robin interleave, the generator, the
#: reviewer sheet). Iteration-1 domains first, in their iteration-1 order.
DOMAIN_ORDER: tuple[str, ...] = (
    DOMAIN_CREDIT,
    DOMAIN_EMPLOYMENT,
    DOMAIN_SOCIAL_BENEFIT,
    DOMAIN_HEALTH_COVERAGE,
)

#: Variants per domain — 4 × 3 = 12 scenarios.
VARIANTS_PER_DOMAIN = 3

#: Held-out variants per domain — 4 × 1 = 4 held out of 12 (33 %, Resolution 1).
HELD_OUT_PER_DOMAIN = 1

#: Rubric elements every scenario licenses **only** through the task frame, never through its own
#: text. Inherited from the iteration-1 pilot rather than chosen, so the n=3 → n=12 expansion
#: cannot be confounded with an easier prompt.
#:
#: ``confidence_level`` is the whole set, and it is the honest reading of the pilot: none of the
#: three iteration-1 scenarios states a probability, a score band, or any other certainty figure.
#: What every scenario *does* supply is a documented, verifiable basis (a credit-bureau report,
#: a CadÚnico record, a medical report), which is what a compliant "alta certeza, com base em
#: documentos verificados" sentence is grounded in — and the few-shot exemplar demonstrates
#: exactly that sentence. Adding a canned certainty figure to the nine new scenarios would have
#: made them measurably easier than the three old ones on the one element models most often miss.
#: (Iteration 1 scored ``explanation_quality`` at 0.833 = 5/6; *which* element was missing is not
#: recorded anywhere in the repo, so "it was probably this one" is a hypothesis for Phase 8 to
#: settle from ``Score.metadata["missing_elements"]``, not a finding.)
FRAME_LICENSED_ELEMENTS = frozenset({"confidence_level"})
