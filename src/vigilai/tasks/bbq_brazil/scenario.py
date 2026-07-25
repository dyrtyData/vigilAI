"""The ``bbq_brazil`` scenario dataclass and category constants.

Split out of :mod:`vigilai.tasks.bbq_brazil.dataset` in iteration 2 so the *generated* scenario
literals in :mod:`vigilai.tasks.bbq_brazil.generated` can construct ``BrazilBBQScenario``
without importing ``dataset`` — which imports ``generated`` in turn. Keeping the dataclass here
makes the import graph a straight line::

    scenario  →  generated  →  dataset

instead of a cycle that would break ``import vigilai.tasks.bbq_brazil.generated`` depending on
which module happened to be imported first. Every public name in this module is re-exported from
``dataset``, so ``from vigilai.tasks.bbq_brazil.dataset import BrazilBBQScenario`` (and the
``CATEGORY_*`` constants) keeps working exactly as before.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


# The category groups stored on each sample's ``metadata["category"]`` so the dataset can be
# filtered/inspected per axis. The first three are required by the iteration-1 structure
# outline; the Religion and Class groups were added in iteration-1 Phase 11 (stretch) to broaden
# coverage of the research §9 term bank (§9.4 Afro-Brazilian religious discrimination; §9.3
# socioeconomic markers). Iteration 2 balances all five at 20 scenarios each.
CATEGORY_RACE = "Race_IBGE"
CATEGORY_REGION = "Region"
CATEGORY_INTERSECTIONAL = "Intersectional"
CATEGORY_RELIGION = "Religion"
CATEGORY_CLASS = "Class"

# Fixed order used everywhere a per-category traversal must be deterministic (the round-robin
# that interleaves ``ALL_SCENARIOS``, the generator, and the spot-check artifact).
CATEGORY_ORDER: tuple[str, ...] = (
    CATEGORY_RACE,
    CATEGORY_REGION,
    CATEGORY_INTERSECTIONAL,
    CATEGORY_RELIGION,
    CATEGORY_CLASS,
)

# Provenance recorded on the 22 hand-authored pilot scenarios. Generated scenarios overwrite it
# with their template + term-bank keys, so the two populations stay distinguishable in the data
# itself — not only in ``git blame``.
HAND_AUTHORED_PROVENANCE = "hand-authored pilot (research §9)"

# Prefix every generated scenario's provenance starts with, so "is this row generated?" is a
# string test rather than a set-membership lookup.
GENERATED_PROVENANCE_PREFIX = "generated"


@dataclass(frozen=True)
class BrazilBBQScenario:
    """A single Brazil-adapted BBQ item.

    Each scenario expands into **two** samples: one with the ambiguous context (correct
    answer = Unknown) and one with the disambiguated context (correct answer = the named
    individual). ``person_a`` / ``person_b`` are the two human options; ``stereotyped_answer``
    indicates which of them a biased model would wrongly pick in the ambiguous case.
    """

    category: str
    # Two demographic descriptions contrasted in the scenario, e.g. "homem branco" vs
    # "homem pardo". These become the first two answer choices, in this order.
    person_a: str
    person_b: str
    # Shared lead-in that introduces both people (ambiguous on its own).
    ambiguous_context: str
    # Extra sentence that resolves the ambiguity by naming the individual described by the
    # question. The combination must make exactly one of person_a / person_b correct.
    disambiguating_context: str
    # Negative-polarity question (the "who is the bad actor / less competent / etc." framing
    # that BBQ uses to surface stereotypes).
    question: str
    # Which of person_a / person_b the disambiguated context actually identifies as the
    # answer to ``question`` — "A" or "B".
    disambiguated_answer: str
    # Which of person_a / person_b a stereotype would unfairly blame — "A" or "B". Used by
    # tests to construct a "biased" model answer.
    stereotyped_answer: str
    # The Brazilian demographic terms exercised (for introspection/tests).
    groups: tuple[str, ...] = field(default_factory=tuple)
    # Short tag describing the social-harm framing (employment, criminality, etc.).
    bias_type: str = ""
    # Reserved-validation flag. **Always ``False`` for ``bbq_brazil``** — see the module
    # docstring of ``dataset`` and the structure outline's Resolution 2: this benchmark holds
    # out nothing, because the reused upstream ``choice()`` scorer has no cue list to
    # decontaminate. The field exists so the four Brazil datasets share one dataclass shape.
    held_out: bool = False
    # Where this scenario came from. Hand-authored rows keep the default; generated rows carry
    # their template + term-bank keys so any published number is traceable to its source data.
    provenance: str = HAND_AUTHORED_PROVENANCE

    @property
    def is_generated(self) -> bool:
        """True when this scenario came out of ``tools/generate_brazil_scenarios.py``."""
        return self.provenance.startswith(GENERATED_PROVENANCE_PREFIX)
