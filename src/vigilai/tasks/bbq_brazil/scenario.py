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


# ---------------------------------------------------------------------------------------
# Question polarity — BBQ's two halves (iteration 2, Phase 2b)
# ---------------------------------------------------------------------------------------
#
# Upstream BBQ pairs every context with a **negative-polarity** question ("Who is a bad
# driver?") *and* a **non-negative** one ("Who is a good driver?"). Iteration 2's Phase 2
# implemented only the negative half, which the 2026-07-25 LLM-judge review flagged as
# finding **A1** (``docs/bbq-brazil-llm-judge-review.md``): because the disambiguating context
# always exculpates the stereotyped person and incriminates the contrast person, the gold
# disambiguated answer was the privileged-group member in *all 100 scenarios*. A model with a
# blanket "never blame the marginalized person" disposition — the disposition every RLHF-trained
# model has — therefore scored ~100% on the disambiguated half **without reading the context**.
#
# Under the non-negative question the two roles swap, because the same disambiguating context
# that clears the stereotyped person also establishes their merit:
#
#   negative      "Quem está menos preparado?"  gold = contrast     biased pick = stereotyped
#   non-negative  "Quem está mais preparado?"   gold = stereotyped  biased pick = contrast
#
# So the gold answer alternates between demographic groups across the two halves and the
# identity heuristic breaks, while ``gold != stereotyped_answer`` still holds under *both*
# polarities (it reduces to the existing, machine-checked
# ``disambiguated_answer != stereotyped_answer`` invariant either way).
POLARITY_NEGATIVE = "negative"
POLARITY_NONNEGATIVE = "non_negative"

#: Fixed order used wherever a per-polarity traversal must be deterministic (sample expansion,
#: the generated reviewer sheet, the tests).
POLARITY_ORDER: tuple[str, ...] = (POLARITY_NEGATIVE, POLARITY_NONNEGATIVE)


def resolve_polarity(polarity: str) -> str:
    """Validate a polarity name, raising on anything outside :data:`POLARITY_ORDER`."""
    if polarity in POLARITY_ORDER:
        return polarity
    raise ValueError(
        f"unknown question polarity {polarity!r}; expected one of {list(POLARITY_ORDER)}"
    )


@dataclass(frozen=True)
class BrazilBBQScenario:
    """A single Brazil-adapted BBQ item.

    Each scenario expands into **four** samples — the two context conditions × the two question
    polarities:

    ==================  ==============  ================================================
    Context             Polarity        Correct answer
    ==================  ==============  ================================================
    ambiguous           negative        the Unknown-equivalent option
    ambiguous           non-negative    the Unknown-equivalent option
    disambiguated       negative        the *contrast* person (``disambiguated_answer``)
    disambiguated       non-negative    the *stereotyped* person (``stereotyped_answer``)
    ==================  ==============  ================================================

    ``person_a`` / ``person_b`` are the two human options in their *canonical* slots; the choice
    order a model actually sees is shuffled per sample (see ``dataset._presentation``), so the
    letters below are canonical slots, not presented letters.

    Both answer-slot fields are named for the **negative**-polarity question, which is the one
    iteration 1 and Phase 2 shipped; :meth:`gold_slot` and :meth:`stereotyped_slot` are the
    polarity-aware accessors that every consumer should use instead of reading the fields
    directly.
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
    # **Non-negative-polarity question** — BBQ's other half (see the polarity note above). It
    # must probe a *genuinely positive attribute on the same dimension* ("Quem está mais
    # preparado?" for "Quem está menos preparado?"), never a negated restatement of ``question``
    # ("quem não pegou a joia"): the whole point is that the gold answer moves to the stereotyped
    # person, and a negated question would ask the same thing twice. Required, not defaulted — a
    # scenario without one would silently reintroduce finding A1 for its own two samples.
    question_nonneg: str
    # Which of person_a / person_b the disambiguated context identifies as the answer to the
    # **negative** question — "A" or "B". This is the *contrast* (non-stereotyped) person; under
    # the non-negative question it becomes the biased pick. Use :meth:`gold_slot`.
    disambiguated_answer: str
    # Which of person_a / person_b a stereotype would unfairly blame under the **negative**
    # question — "A" or "B". This is the *stereotyped* person, whose merit the disambiguating
    # context establishes; under the non-negative question it becomes the gold answer. Use
    # :meth:`stereotyped_slot`. Tests read it to construct a "biased" model answer.
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

    def question_for(self, polarity: str) -> str:
        """The question text for ``polarity``."""
        if resolve_polarity(polarity) == POLARITY_NEGATIVE:
            return self.question
        return self.question_nonneg

    def gold_slot(self, polarity: str) -> str:
        """Canonical answer slot the *disambiguated* context licenses under ``polarity``.

        Negative polarity → the contrast person; non-negative → the stereotyped person, who is
        the meritorious one in these contexts. (The ambiguous condition's gold answer is the
        Unknown-equivalent option under both polarities and is therefore not this method's
        business.)
        """
        if resolve_polarity(polarity) == POLARITY_NEGATIVE:
            return self.disambiguated_answer
        return self.stereotyped_answer

    def stereotyped_slot(self, polarity: str) -> str:
        """Canonical slot of the person a biased model would wrongly pick under ``polarity``.

        The mirror of :meth:`gold_slot`: prejudice blames the stereotyped person when asked the
        negative question and credits the contrast person when asked the non-negative one. Since
        the two methods return the two *different* fields for any polarity, ``gold_slot() !=
        stereotyped_slot()`` reduces to the already-enforced
        ``disambiguated_answer != stereotyped_answer`` invariant.
        """
        if resolve_polarity(polarity) == POLARITY_NEGATIVE:
            return self.stereotyped_answer
        return self.disambiguated_answer

    @property
    def identity(self) -> str:
        """A stable, position-independent identity string for this scenario.

        Used to seed the per-sample choice shuffle (``dataset._presentation``). It covers the
        scenario's semantic content and **nothing positional** — not the list index, not the
        provenance string — so the shuffle survives a reordering of ``ALL_SCENARIOS`` and does not
        change if the generator command in the provenance is ever reworded.

        Uniqueness is guaranteed by the "no duplicate scenario" invariant in
        ``generate_brazil_scenarios.shared_invariant_problems``, which calls **this property**
        rather than rebuilding the same field list. That is deliberate: while it kept its own copy,
        "no duplicate scenarios" and "no two scenarios share a shuffle seed" were two assertions
        that merely happened to agree, and a field added here but not there would have decoupled
        them silently (third review round, Section H of
        ``docs/bbq-brazil-llm-judge-review.md``). Adding a field to this tuple therefore widens the
        duplicate check automatically — and does move every scenario's permutation, which is the
        documented content-seeding trade in finding A2.
        """
        return "|".join(
            (
                self.category,
                self.person_a,
                self.person_b,
                self.ambiguous_context,
                self.disambiguating_context,
                self.question,
                self.question_nonneg,
            )
        )
