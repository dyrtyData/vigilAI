"""Deterministic generator for the Brazil benchmark scenarios.

    uv run python tools/generate_brazil_scenarios.py

Expands the templates and term banks in :mod:`brazil_term_banks` over a fixed, seedless,
network-free traversal and writes the committed Python literals in
``src/vigilai/tasks/bbq_brazil/generated.py`` plus the reviewer artifact
``docs/bbq-brazil-generated-spot-check.md``.

**Deterministic by construction, not by seeding.** There is no RNG: the traversal order, the
answer-slot alternation, and the emitted source formatting are all fixed functions of the banks,
so the same input produces byte-identical output. ``tests/test_bbq_brazil.py`` pins that
(re-render and compare), mirroring the ``make default-config`` convention the repo already uses.

Why a generator rather than more hand-authoring, and why not an LLM: iteration 2 needs
``bbq_brazil`` at 100 scenarios (400 samples after Phase 2b's polarity pair) for coverage and
per-axis balance, and LLM-drafted bias probes scored by LLMs would introduce a circularity a
reviewer would rightly flag (design discussion, Resolved Q3). Automation raises n and balance; it
is **not** community validation — that remains documented-as-pending (Phase 10 protocol). And note
that the four samples of one scenario are *not* independent observations, so the printed standard
error is a lower bound — see the ``dataset`` module docstring.

What this file guarantees (all enforced before it will write anything, and re-checked by tests):

* exactly ``CategoryPlan.target`` scenarios per category, so the finished dataset is balanced at
  20 scenarios / 80 samples per category across all five axes;
* no ``(pair, template)`` combination is used twice, and pairs/templates are cycled evenly;
* **no incompatible ``(pair, template)`` combination is emitted at all** — a pair that is not
  role-neutral names the templates it fits, and a situation that cannot perceive a marker names
  the pairs it rejects, so a socially absurd item is impossible by construction rather than
  avoided by luck (2026-07-25 LLM-judge review, finding A5);
* the stereotyped person alternates between answer slots A and B, so the disambiguated answer
  letter is not a positional giveaway;
* the disambiguating sentence establishes the stereotyped person's merit **and names the other
  person** — so it licenses the correct disambiguated answer under *both* question polarities (the
  contrast person under the negative question, the stereotyped person under the non-negative one);
* **both** questions ask about a **fact**, never about a third party's suspicion or perception,
  which would make the stereotype-consistent answer the truthful one (review finding A3);
* every template carries a non-negative question that differs from its negative one, so no
  scenario silently reintroduces review finding A1 for its own samples;
* every placeholder is substituted, pt-BR gender agreement matches the pair's declared gender,
  and no scenario or prompt is a duplicate of another.

The checks split two ways: :func:`shared_invariant_problems` holds for **every** scenario in the
benchmark (the hand-authored pilot included, and the test suite runs it over the union), while
:func:`validate_scenarios` adds the rules that only make sense for generated rows.
"""

from __future__ import annotations

import hashlib
import re
import sys
import types
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


# --- Bootstrap: never parse the file this generator writes -------------------------------
#
# The generator imports ``BrazilBBQScenario`` from ``vigilai.tasks.bbq_brazil.scenario``, and
# importing any submodule runs the package ``__init__``, which chains
# ``__init__ → bbq_brazil → dataset → generated``. So a plain import *does* load the committed
# ``generated.py`` — and if that file is stale in a way that no longer constructs (which is exactly
# what happens the moment ``BrazilBBQScenario`` gains a required field, as ``question_nonneg`` did
# in Phase 2b), the generator cannot even start, and the only way out is to hand-edit the generated
# file it exists to own.
#
# Pre-registering an empty stub under that module name makes the documented design property
# ("the generator imports only from ``scenario``, so it never depends on the file it writes")
# actually true: ``dataset`` binds ``GENERATED_SCENARIOS = []`` from the stub, the package
# ``__init__`` succeeds, and ``scenario.BrazilBBQScenario`` is the real class object — so the
# scenarios this module builds still compare equal to the ones the committed literals produce,
# which the drift guard relies on.
#
# **Scoped to ``__main__`` on purpose.** Only the script entry point needs the bootstrap. Doing it
# unconditionally would mean that a test process which happened to ``import
# generate_brazil_scenarios`` *before* ``vigilai.tasks.bbq_brazil.dataset`` would leave the whole
# suite looking at 22 scenarios instead of 100 — an order-dependent failure that would be
# miserable to diagnose. Imported as a module, this file loads the committed data normally.
#
# **Consequence when it does apply:** inside the generator *process*
# ``vigilai.tasks.bbq_brazil.dataset.ALL_SCENARIOS`` holds only the 22 hand-authored pilot rows.
# Nothing here imports ``dataset``, and nothing here may start to — read the committed data through
# the test suite instead.
# **Phase 3 adds two more.** The rubric tasks got the same generated-module pattern, and the same
# chain applies twice over: ``vigilai.tasks.explanation_quality.scenario`` runs that package's
# ``__init__ → explanation_quality → dataset → generated``. Without a stub the generator cannot run
# at all before the file it writes exists — which is every fresh checkout, not just a stale-file
# edge case.
_GENERATED_MODULES = (
    "vigilai.tasks.bbq_brazil.generated",
    "vigilai.tasks.explanation_quality.generated",
    "vigilai.tasks.contestation_review.generated",
)
if __name__ == "__main__":
    for _module_name in _GENERATED_MODULES:
        if _module_name not in sys.modules:
            _stub = types.ModuleType(_module_name)
            _stub.GENERATED_SCENARIOS = []  # type: ignore[attr-defined]
            sys.modules[_module_name] = _stub

from brazil_rubric_scenarios import CONDITIONAL_VOCABULARY_RULES  # noqa: E402
from brazil_rubric_scenarios import CONTENT_STOPWORDS  # noqa: E402
from brazil_rubric_scenarios import ENGLISH_SUFFIXES  # noqa: E402
from brazil_rubric_scenarios import ENGLISH_WORDS  # noqa: E402
from brazil_rubric_scenarios import GLOBAL_FORBIDDEN  # noqa: E402
from brazil_rubric_scenarios import LEAK_TERMS  # noqa: E402
from brazil_rubric_scenarios import MAX_INTRA_DOMAIN_OVERLAP  # noqa: E402
from brazil_rubric_scenarios import MIN_REFERENCE_GROUNDING_TOKENS  # noqa: E402
from brazil_rubric_scenarios import PT_BR_LOANWORDS  # noqa: E402
from brazil_rubric_scenarios import RESEARCH_ANCHORS  # noqa: E402
from brazil_rubric_scenarios import RUBRIC_TASK_PLANS  # noqa: E402
from brazil_rubric_scenarios import RubricTaskPlan  # noqa: E402
from brazil_rubric_scenarios import RubricVariant  # noqa: E402

from brazil_term_banks import AGREEMENT_STEMS  # noqa: E402
from brazil_term_banks import CATEGORY_PLANS  # noqa: E402
from brazil_term_banks import CategoryPlan  # noqa: E402
from brazil_term_banks import category_terms  # noqa: E402
from brazil_term_banks import ContrastPair  # noqa: E402
from brazil_term_banks import DEMOGRAPHIC_ADJECTIVES  # noqa: E402
from brazil_term_banks import FEMININE  # noqa: E402
from brazil_term_banks import FORBIDDEN_TERMS  # noqa: E402
from brazil_term_banks import incompatibility  # noqa: E402
from brazil_term_banks import KNOWN_PLACEHOLDERS  # noqa: E402
from brazil_term_banks import MASCULINE  # noqa: E402
from brazil_term_banks import OBLIGATORY_CONTRACTIONS  # noqa: E402
from brazil_term_banks import PHRASE_STOPWORDS  # noqa: E402
from brazil_term_banks import PersonTerm  # noqa: E402
from brazil_term_banks import SCENARIOS_PER_CATEGORY  # noqa: E402
from brazil_term_banks import ScenarioTemplate  # noqa: E402
from brazil_term_banks import VICTIM_FRAMING_PATTERNS  # noqa: E402

from vigilai.tasks.bbq_brazil.scenario import BrazilBBQScenario  # noqa: E402
from vigilai.tasks.bbq_brazil.scenario import CATEGORY_ORDER  # noqa: E402
from vigilai.tasks.bbq_brazil.scenario import GENERATED_PROVENANCE_PREFIX  # noqa: E402
from vigilai.tasks.contestation_review.rubric import (  # noqa: E402
    detect_elements as detect_contestation_elements,
)
from vigilai.tasks.contestation_review.rubric import score_contestation  # noqa: E402
from vigilai.tasks.contestation_review.scenario import ContestationScenario  # noqa: E402
from vigilai.tasks.explanation_quality.rubric import (  # noqa: E402
    detect_elements as detect_explanation_elements,
)
from vigilai.tasks.explanation_quality.rubric import score_explanation  # noqa: E402
from vigilai.tasks.explanation_quality.scenario import ExplanationScenario  # noqa: E402
from vigilai.tasks.rubric_scenario import FRAME_LICENCE  # noqa: E402
from vigilai.tasks.rubric_scenario import MIN_LICENCE_SPAN  # noqa: E402
from vigilai.tasks.rubric_scenario import RubricScenario  # noqa: E402
from vigilai.tasks.rubric_scenario import frame_licensed_elements  # noqa: E402


GENERATOR_COMMAND = "uv run python tools/generate_brazil_scenarios.py"

BBQ_GENERATED_PATH = _REPO_ROOT / "src" / "vigilai" / "tasks" / "bbq_brazil" / "generated.py"
BBQ_SPOT_CHECK_PATH = _REPO_ROOT / "docs" / "bbq-brazil-generated-spot-check.md"
RUBRIC_SPOT_CHECK_PATH = _REPO_ROOT / "docs" / "rubric-scenarios-generated-spot-check.md"


def rubric_generated_path(plan: RubricTaskPlan) -> Path:
    """Where a rubric task's generated literals are written."""
    return _REPO_ROOT.joinpath(*plan.module_path)


#: The deterministic rubric scorer for each task, used to *prove* every scenario can elicit all
#: six of its elements: the generator refuses to write a scenario whose ``reference_answer`` does
#: not score exactly 1.0. Importing these is safe under the bootstrap stub above.
RUBRIC_SCORERS = {
    "explanation_quality": score_explanation,
    "contestation_review": score_contestation,
}

#: The real per-element detector for each task. **New in the Phase 3 cue fix.** Until the cue
#: lists were word-bounded this could not be used as a leakage guard at all — ``"form"`` matched
#: *forma* / *informação* / *conforme* / *plataforma*, so every pilot scenario "leaked" a
#: contestation channel and so would almost any Portuguese sentence. With that class of defect
#: closed, running the scorer's own detector over scenario text is exactly the right check, and it
#: now runs **alongside** the hand-written :data:`LEAK_TERMS` list rather than instead of it: the
#: detector catches anything the *scorer* would credit, the term list catches phrasings that leak
#: an element semantically without being a cue (*canal de atendimento*, *daremos retorno*).
RUBRIC_DETECTORS = {
    "explanation_quality": detect_explanation_elements,
    "contestation_review": detect_contestation_elements,
}

#: The concrete scenario class each task's literals construct.
RUBRIC_SCENARIO_CLASSES: dict[str, type[RubricScenario]] = {
    "explanation_quality": ExplanationScenario,
    "contestation_review": ContestationScenario,
}

# Marker line whose *following* bytes the recorded digest covers, so a hand edit of the data is
# detectable from the file alone — no need to re-run the generator.
DIGEST_MARKER = "# content-sha256: "

# Emitted string chunks wrap at this many characters of content, keeping the generated literals
# inside a normal review width without any dependency on a formatter.
_WRAP_WIDTH = 76

# **Canonical** answer slots for the two person choices — the Unknown option is the third; see
# ``dataset._canonical_choices``. These are the slots ``disambiguated_answer`` /
# ``stereotyped_answer`` name, *not* the letters a model sees: since Phase 2b the presented order is
# shuffled per sample (``dataset._presentation``).
_SLOT_A = "A"
_SLOT_B = "B"


# ---------------------------------------------------------------------------------------
# Rendering one scenario
# ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Assignment:
    """One (pair, template) combination plus the slot the stereotyped person is placed in."""

    pair: ContrastPair
    template: ScenarioTemplate
    stereotyped_slot: str  # _SLOT_A or _SLOT_B

    @property
    def slot_a(self) -> PersonTerm:
        return (
            self.pair.stereotyped if self.stereotyped_slot == _SLOT_A else self.pair.contrast
        )

    @property
    def slot_b(self) -> PersonTerm:
        return (
            self.pair.contrast if self.stereotyped_slot == _SLOT_A else self.pair.stereotyped
        )

    @property
    def disambiguated_slot(self) -> str:
        """The non-stereotyped slot — the correct answer once the context disambiguates."""
        return _SLOT_B if self.stereotyped_slot == _SLOT_A else _SLOT_A


def _capitalize(phrase: str) -> str:
    """Upper-case the first character only ("a mulher negra" → "A mulher negra")."""
    return phrase[:1].upper() + phrase[1:]


def _fill(text: str, assignment: _Assignment) -> str:
    """Substitute every placeholder in a template string."""
    pair = assignment.pair
    gender = pair.gender
    substitutions = {
        "A": _capitalize(assignment.slot_a.indefinite),
        "a": assignment.slot_a.indefinite,
        "B": _capitalize(assignment.slot_b.indefinite),
        "b": assignment.slot_b.indefinite,
        "Target": _capitalize(pair.stereotyped.definite),
        "target": pair.stereotyped.definite,
        "Answer": _capitalize(pair.contrast.definite),
        "answer": pair.contrast.definite,
        "g": "a" if gender == FEMININE else "o",
        "gp": "as" if gender == FEMININE else "os",
    }
    return text.format(**substitutions)


def _provenance(assignment: _Assignment) -> str:
    """The per-scenario provenance string: everything needed to regenerate exactly this row."""
    return (
        f"{GENERATED_PROVENANCE_PREFIX} ({GENERATOR_COMMAND}): "
        f"template={assignment.template.key}; "
        f"pair={assignment.pair.key}; "
        f"stereotyped_slot={assignment.stereotyped_slot}; "
        f"bank={assignment.pair.bank}"
    )


def _scenario_for(assignment: _Assignment) -> BrazilBBQScenario:
    template = assignment.template
    return BrazilBBQScenario(
        category=template.category,
        person_a=assignment.slot_a.definite,
        person_b=assignment.slot_b.definite,
        ambiguous_context=_fill(template.situation, assignment),
        disambiguating_context=_fill(template.disambiguation, assignment),
        question=_fill(template.question, assignment),
        question_nonneg=_fill(template.question_nonneg, assignment),
        disambiguated_answer=assignment.disambiguated_slot,
        stereotyped_answer=assignment.stereotyped_slot,
        groups=assignment.pair.groups,
        bias_type=template.bias_type,
        held_out=False,  # bbq_brazil holds out nothing — structure outline, Resolution 2
        provenance=_provenance(assignment),
    )


# ---------------------------------------------------------------------------------------
# The traversal
# ---------------------------------------------------------------------------------------


def _assignments_for(plan: CategoryPlan) -> list[_Assignment]:
    """Enumerate ``plan.target`` unique, *compatible* (pair, template) combinations.

    Diagonal traversal: on pass ``d`` pair ``i`` is matched with template ``(i + d) % T``. Every
    pass uses each pair exactly once and each pair sees a different template, so combinations
    never repeat while both banks are cycled evenly. The stereotyped person alternates between
    answer slots on consecutive scenarios, which keeps the disambiguated answer letter close to
    50/50 per category rather than a constant a model could exploit without reading the context.

    **Incompatible combinations are skipped** (:func:`brazil_term_banks.incompatibility`), which
    is what turns "the committed rotation happens to avoid nonsense" into "nonsense is impossible
    by construction" — see the 2026-07-25 LLM-judge review, finding A5. Two consequences worth
    stating:

    * The alternation is driven by ``len(assignments)``, i.e. by how many scenarios have been
      *emitted*, not by the traversal index. A skip therefore cannot skew the answer-letter
      balance; it only shifts which slot the next emitted scenario uses.
    * The target must fit inside the *compatible* combination count, not the raw product, or the
      traversal would run out of passes. Checked here and again in :func:`validate_term_banks`.

    **Why ``target <= affordable`` is sufficient**, and not merely necessary: across its
    ``len(templates)`` passes the diagonal visits pair ``i`` against template ``(i + d) % T`` for
    every ``d``, so it enumerates **every** (pair, template) combination exactly once — the whole
    product, not a subset of it. Every compatible combination is therefore reachable, and the
    trailing ``raise`` below cannot fire once the affordability check passes. That is stated here
    because the pragma on it used to credit :func:`validate_term_banks`, which only checks the
    *count*; the reachability comes from the traversal's own coverage (third review round,
    Section H).
    """
    pairs = plan.pairs
    templates = plan.templates
    if not pairs or not templates:
        raise ValueError(f"{plan.category}: term banks must not be empty")
    affordable = len(plan.compatible_combinations())
    if plan.target > affordable:
        raise ValueError(
            f"{plan.category}: needs {plan.target} scenarios but the banks only afford "
            f"{affordable} unique *compatible* (pair, template) combinations "
            f"({len(pairs) * len(templates)} before pair-compatibility exclusions)"
        )

    assignments: list[_Assignment] = []
    for offset in range(len(templates)):
        for index, pair in enumerate(pairs):
            if len(assignments) == plan.target:
                return assignments
            template = templates[(index + offset) % len(templates)]
            if incompatibility(pair, template) is not None:
                continue
            stereotyped_slot = _SLOT_B if len(assignments) % 2 else _SLOT_A
            assignments.append(_Assignment(pair, template, stereotyped_slot))
    # Unreachable because the diagonal enumerates the *whole* pair × template product (see the
    # docstring), so `target <= affordable` guarantees `target` compatible combinations are visited.
    # Kept as a refusal rather than deleted: it is the one failure the affordability count alone
    # would not catch if the traversal were ever changed to visit a subset.
    if len(assignments) != plan.target:  # pragma: no cover - see the docstring's coverage note
        raise ValueError(
            f"{plan.category}: the diagonal traversal emitted {len(assignments)} of "
            f"{plan.target} scenarios — {affordable} compatible combinations exist, but not "
            "enough of them lie on the diagonal. Add a template or relax an exclusion."
        )
    return assignments


def generate_bbq_scenarios() -> list[BrazilBBQScenario]:
    """Build the generated ``bbq_brazil`` scenarios (78: 14/15/15/17/17 by category).

    Grouped by category in ``CATEGORY_ORDER``; ``dataset.ALL_SCENARIOS`` interleaves the
    hand-authored and generated populations afterwards so that any ``--limit`` prefix stays
    category-balanced.
    """
    plans = {plan.category: plan for plan in CATEGORY_PLANS}
    scenarios: list[BrazilBBQScenario] = []
    for category in CATEGORY_ORDER:
        plan = plans[category]
        scenarios.extend(_scenario_for(a) for a in _assignments_for(plan))
    return scenarios


# ---------------------------------------------------------------------------------------
# Validation — every mechanical property a reviewer should never have to check by eye
# ---------------------------------------------------------------------------------------


def _agreement_problems(text: str, gender: str, where: str) -> list[str]:
    """Flag pt-BR gender agreement that contradicts the scenario's declared gender.

    Only inspects the declared :data:`AGREEMENT_STEMS`, and only where the stem is followed by
    an ``o``/``a`` — so "também" (stem "amb" + "é") is not a false positive, while "ambos" in a
    feminine scenario is caught.
    """
    expected = "a" if gender == FEMININE else "o"
    wrong = "o" if gender == FEMININE else "a"
    problems: list[str] = []
    lowered = text.lower()
    for stem in AGREEMENT_STEMS:
        start = 0
        while (found := lowered.find(stem, start)) != -1:
            start = found + 1
            suffix_at = found + len(stem)
            if suffix_at >= len(lowered):
                continue
            if lowered[suffix_at] == wrong:
                problems.append(
                    f"{where}: '{text[found:suffix_at + 2]}' does not agree with the pair's "
                    f"declared gender {gender!r} (expected '{stem}{expected}…')"
                )
    return problems


def contraction_problems(text: str, where: str) -> list[str]:
    """Flag missing pt-BR preposition + article contractions ("de o rapaz" → "do rapaz").

    Exported (not private) because the test suite runs it over the hand-authored scenarios too:
    it is a general pt-BR correctness check, not a generator-specific one.
    """
    problems: list[str] = []
    words = [word.strip(",.;:?!()").lower() for word in text.split()]
    for first, second in zip(words, words[1:]):
        correct = OBLIGATORY_CONTRACTIONS.get((first, second))
        if correct is not None:
            problems.append(
                f"{where}: '{first} {second}' must contract to '{correct}' in pt-BR"
            )
    return problems


def repeated_word_problems(text: str, where: str) -> list[str]:
    """Flag an immediately repeated word — the usual signature of a substitution artifact."""
    problems: list[str] = []
    words = [word.strip(",.;:?!()").lower() for word in text.split()]
    for first, second in zip(words, words[1:]):
        if first and first == second:
            problems.append(f"{where}: word {first!r} is repeated back-to-back")
    return problems


def victim_framing_problems(question: str, where: str) -> list[str]:
    """Flag the **A3 victim-framing question shape**: a third party's perception, not a fact.

    A BBQ item asks who *did* the negative thing, and the disambiguating sentence then makes
    exactly one answer licensed. A question that instead asks whom some third party *suspected*,
    *mistook* or *believed something about* inverts the measurement, because the
    stereotype-consistent answer is also the truthful one — a Brazilian security guard really
    would suspect the Black shopper first, so either the coded gold answer is unlicensed by the
    text or ``stereotyped_answer == disambiguated_answer``. Seven items had this defect
    (LLM-judge review, finding A3), which is why it is worth a guard and not only seven fixes.

    Exported (not private) because the test suite runs it over **every** scenario, generated and
    hand-authored: the hand-authored pilot is where six of the seven lived. The patterns and the
    deliberate near-misses are documented on
    :data:`brazil_term_banks.VICTIM_FRAMING_PATTERNS`.

    Scoped to the ``question`` field on purpose. A *context* may legitimately narrate someone's
    suspicion (that is often the social fact the item is about); it is asking the model to
    reproduce that suspicion as its answer that breaks the item.
    """
    problems: list[str] = []
    lowered = question.lower()
    for pattern, why in VICTIM_FRAMING_PATTERNS:
        if pattern in lowered:
            problems.append(
                f"{where}: victim-framing question shape {pattern!r} — {why}. "
                f"Question was: {question!r}"
            )
    return problems


def _compatibility_problems(plan: CategoryPlan) -> list[str]:
    """Check the declared pair-compatibility exclusions for typos and for over-restriction."""
    problems: list[str] = []
    pair_keys = {pair.key for pair in plan.pairs}
    template_keys = {template.key for template in plan.templates}

    for pair in plan.pairs:
        unknown = sorted(pair.only_templates - template_keys)
        if unknown:
            problems.append(
                f"pair {pair.key}: only_templates names {unknown!r}, which are not "
                f"{plan.category} templates — a typo here would silently widen the restriction"
            )
    for template in plan.templates:
        unknown = sorted(template.excluded_pairs - pair_keys)
        if unknown:
            problems.append(
                f"template {template.key}: excluded_pairs names {unknown!r}, which are not "
                f"{plan.category} pairs — a typo here would silently drop the exclusion"
            )

    affordable = len(plan.compatible_combinations())
    if plan.target > affordable:
        problems.append(
            f"{plan.category}: needs {plan.target} scenarios but pair-compatibility leaves only "
            f"{affordable} usable (pair, template) combinations"
        )
    return problems


#: Characters that would break the ``key=value; key=value`` provenance format.
_PROVENANCE_SEPARATORS = ("=", ";")


def _key_shape_problems(kind: str, key: str) -> list[str]:
    """Check that a bank key can survive a round-trip through the provenance string.

    :func:`provenance_field` — and therefore :func:`_emitted_combination_problems`,
    :func:`_spot_check_picks` and three tests — recovers a pair/template key by splitting the
    provenance on ``"pair="`` / ``"template="`` and then on ``";"``. That only works while no key
    contains a separator, which was true because every key happens to be identifier-shaped. "Happens
    to be" is the inference the third review round swept for (Section H), so it is a declared
    invariant now: the precondition the parsing layer rests on is checked where the keys are
    defined, not assumed where they are read.
    """
    if not key:
        return [f"{kind}: empty key"]
    return [
        f"{kind} {key!r}: keys must not contain {separator!r} — it is a separator in the "
        "provenance string that provenance_field() parses back out"
        for separator in _PROVENANCE_SEPARATORS
        if separator in key
    ]


def bank_lookup() -> tuple[dict[str, ContrastPair], dict[str, ScenarioTemplate]]:
    """``(pairs_by_key, templates_by_key)`` across all five category plans."""
    pairs = {pair.key: pair for plan in CATEGORY_PLANS for pair in plan.pairs}
    templates = {t.key: t for plan in CATEGORY_PLANS for t in plan.templates}
    return pairs, templates


def _emitted_combination_problems(scenario: BrazilBBQScenario, where: str) -> list[str]:
    """Re-check one committed generated row against the declared compatibility rules.

    The traversal already skips incompatible combinations, so this can only fire if the two ever
    disagree — which is exactly the case worth catching, because the *committed* literals are what
    a model sees.
    """
    if not scenario.is_generated:
        return []
    pairs, templates = bank_lookup()
    pair_key = provenance_field(scenario, "pair")
    template_key = provenance_field(scenario, "template")
    pair = pairs.get(pair_key)
    template = templates.get(template_key)
    if pair is None or template is None:
        return [
            f"{where}: provenance names an unknown pair/template "
            f"({pair_key!r} / {template_key!r})"
        ]
    reason = incompatibility(pair, template)
    if reason is not None:
        return [f"{where}: incompatible combination was emitted — {reason}"]
    return []


def _person_term_problems(term: PersonTerm, where: str) -> list[str]:
    """Check a noun phrase's demographic adjectives against the gender its article declares."""
    problems: list[str] = []
    if term.gender not in (MASCULINE, FEMININE):
        problems.append(f"{where}: unknown gender {term.gender!r}")
        return problems
    expected_article = "uma" if term.gender == FEMININE else "um"
    if not term.indefinite.startswith(f"{expected_article} "):
        problems.append(
            f"{where}: indefinite form {term.indefinite!r} disagrees with gender {term.gender!r}"
        )
    tokens = term.definite.split(" ")
    for token in tokens[2:]:  # tokens[0] is the article, tokens[1] the head noun
        if token in PHRASE_STOPWORDS:
            break  # what follows modifies another noun, not the person
        for base, (masculine, feminine) in DEMOGRAPHIC_ADJECTIVES.items():
            if token not in (masculine, feminine):
                continue
            wanted = feminine if term.gender == FEMININE else masculine
            if token != wanted:
                problems.append(
                    f"{where}: {term.definite!r} uses {token!r} but its article declares "
                    f"{term.gender!r} (expected {wanted!r} for '{base}')"
                )
    return problems


def validate_term_banks() -> list[str]:
    """Check the banks' own invariants. Empty list means clean."""
    problems: list[str] = []

    seen_pairs: dict[str, str] = {}
    seen_templates: dict[str, str] = {}
    planned_categories = [plan.category for plan in CATEGORY_PLANS]

    if sorted(planned_categories) != sorted(CATEGORY_ORDER):
        problems.append(
            f"CATEGORY_PLANS covers {planned_categories!r}, expected {list(CATEGORY_ORDER)!r}"
        )

    for plan in CATEGORY_PLANS:
        if plan.hand_authored + plan.target != SCENARIOS_PER_CATEGORY:
            problems.append(
                f"{plan.category}: {plan.hand_authored} hand-authored + {plan.target} generated "
                f"!= {SCENARIOS_PER_CATEGORY} scenarios per category"
            )
        problems.extend(_compatibility_problems(plan))
        for pair in plan.pairs:
            where = f"pair {pair.key}"
            problems.extend(_key_shape_problems("pair", pair.key))
            if pair.key in seen_pairs:
                problems.append(f"{where}: duplicate pair key")
            seen_pairs[pair.key] = plan.category
            if pair.category != plan.category:
                problems.append(f"{where}: category {pair.category!r} != {plan.category!r}")
            if pair.stereotyped.gender != pair.contrast.gender:
                problems.append(
                    f"{where}: pair is not gender-matched "
                    f"({pair.stereotyped.definite!r} vs {pair.contrast.definite!r}) — the "
                    "agreement checks assume one gender per scenario"
                )
            if pair.stereotyped.definite == pair.contrast.definite:
                problems.append(f"{where}: both sides are the same phrase")
            problems.extend(_person_term_problems(pair.stereotyped, f"{where} (stereotyped)"))
            problems.extend(_person_term_problems(pair.contrast, f"{where} (contrast)"))

        for template in plan.templates:
            where = f"template {template.key}"
            problems.extend(_key_shape_problems("template", template.key))
            if template.key in seen_templates:
                problems.append(f"{where}: duplicate template key")
            seen_templates[template.key] = plan.category
            if template.category != plan.category:
                problems.append(f"{where}: category {template.category!r} != {plan.category!r}")
            problems.extend(template_problems(template))

    return problems


def template_problems(template: ScenarioTemplate) -> list[str]:
    """Lint one template's text fields. Empty list means clean.

    Extracted from :func:`validate_term_banks` so a single template can be checked in isolation —
    the tests build deliberately broken ones to prove each rule still bites.
    """
    problems: list[str] = []
    where = f"template {template.key}"
    if not template.bias_type:
        problems.append(f"{where}: empty bias_type")
    fields = {
        "situation": template.situation,
        "disambiguation": template.disambiguation,
        "question": template.question,
        "question_nonneg": template.question_nonneg,
    }
    for name, text in fields.items():
        for token in _placeholders(text):
            if token not in KNOWN_PLACEHOLDERS:
                problems.append(f"{where}.{name}: unknown placeholder {{{token}}}")
        # A literal gendered ending in a template means the author forgot {g}/{gp}.
        for stem in AGREEMENT_STEMS:
            for suffix in ("o", "a"):
                if f"{stem}{suffix}" in text.lower():
                    problems.append(
                        f"{where}.{name}: hardcoded gendered ending "
                        f"'{stem}{suffix}' — use '{stem}{{g}}' instead"
                    )
    for token in ("A", "b"):
        if f"{{{token}}}" not in template.situation:
            problems.append(
                f"{where}.situation: must introduce both people — {{{token}}} missing"
            )
    # Both people must be named, because each is the gold answer under one polarity.
    if "{answer}" not in template.disambiguation:
        problems.append(
            f"{where}.disambiguation: must name the non-stereotyped answer via {{answer}} "
            "(the gold answer under the negative question)"
        )
    if "{target}" not in template.disambiguation.replace("{Target}", "{target}"):
        problems.append(
            f"{where}.disambiguation: must establish the stereotyped person's merit via "
            "{target} (the gold answer under the non-negative question)"
        )
    for name in ("question", "question_nonneg"):
        text = fields[name]
        for token in ("{a}", "{A}", "{b}", "{B}", "{target}", "{answer}"):
            if token in text:
                problems.append(f"{where}.{name}: must not name a person ({token} found)")
        problems.extend(victim_framing_problems(text, f"{where}.{name}"))
        if not text.endswith("?"):
            problems.append(f"{where}.{name}: must end with a question mark")
    # The non-negative half is what makes the disambiguated gold answer alternate between
    # demographic groups (review finding A1). A template that left it empty — or that just
    # restated the negative question — would reinstate the defect for every scenario it
    # produces, so both are refusals rather than review notes.
    if not template.question_nonneg.strip():
        problems.append(
            f"{where}.question_nonneg: missing — every template needs BBQ's non-negative "
            "half, or its scenarios reinstate finding A1"
        )
    if template.question_nonneg == template.question:
        problems.append(
            f"{where}.question_nonneg: identical to the negative question, so the two "
            "polarities would ask the same thing and the gold answer would not alternate"
        )
    if not template.situation.endswith("."):
        problems.append(f"{where}.situation: must end with a period")
    if not template.disambiguation.endswith("."):
        problems.append(f"{where}.disambiguation: must end with a period")
    return problems


def _placeholders(text: str) -> list[str]:
    """The placeholder names used by a template string, in order of appearance."""
    tokens: list[str] = []
    rest = text
    while "{" in rest:
        _, _, rest = rest.partition("{")
        token, sep, rest = rest.partition("}")
        if not sep:
            tokens.append(token)  # unterminated — reported as unknown
            break
        tokens.append(token)
    return tokens


def _scenario_fields(scenario: BrazilBBQScenario) -> dict[str, str]:
    """Every rendered text field the checks run over, in a stable order.

    The single source of truth for "which fields are linted": adding a field here extends the
    contraction, repeated-word, whitespace, stray-punctuation, forbidden-term and gender-agreement
    checks to it in one edit. ``tests/test_bbq_brazil.py`` keeps its own tuple for parametrizing and
    asserts the two agree, rather than assuming it (third review round, Section H) — the count is
    deliberately not written down in either place.
    """
    return {
        "ambiguous_context": scenario.ambiguous_context,
        "disambiguating_context": scenario.disambiguating_context,
        "question": scenario.question,
        "question_nonneg": scenario.question_nonneg,
        "person_a": scenario.person_a,
        "person_b": scenario.person_b,
    }


def _where(scenario: BrazilBBQScenario) -> str:
    return f"{scenario.category}/{scenario.provenance.split('template=')[-1][:40]}"


def shared_invariant_problems(scenarios: Sequence[BrazilBBQScenario]) -> list[str]:
    """The checks that must hold for **every** scenario — hand-authored rows included.

    :func:`validate_scenarios` is generator-scoped: several of its rules (verbatim answer naming,
    term-bank membership, per-category target counts, gender agreement) legitimately do not apply
    to the hand-authored pilot, and the generator only ever calls it with ``GENERATED_SCENARIOS``.
    That scoping is what let finding **A4** through — a pilot row keyed the same letter as both
    the gold disambiguated answer and the biased pick, so any bias-rate metric over
    ``metadata["stereotyped_answer"]`` would have scored the correct answer as bias. Rule 3 below
    forbade it and the matching test asserted it, but **both only ever saw the generated set**.
    The coverage gap was the real defect; the item was only its first victim.

    This function is therefore the universal subset, callable over the union. The generator runs
    it on what it writes; ``tests/test_bbq_brazil.py`` runs it over ``ALL_SCENARIOS``. It cannot
    live in the generator's own ``main()`` over the union, because importing ``dataset`` here
    would make the generator depend on the file it writes.
    """
    problems: list[str] = []
    seen_scenarios: set[str] = set()
    seen_prompts: set[str] = set()

    for scenario in scenarios:
        where = _where(scenario)

        # 1. Nothing unsubstituted, nothing malformed.
        for name, text in _scenario_fields(scenario).items():
            if "{" in text or "}" in text:
                problems.append(f"{where}.{name}: unreplaced placeholder in {text!r}")
            if text != text.strip():
                problems.append(f"{where}.{name}: leading/trailing whitespace")
            if "  " in text:
                problems.append(f"{where}.{name}: doubled whitespace")
            for bad in (" ,", " .", " ?", " ;", "..", ",,", "??", ",.", " )", "( "):
                if bad in text:
                    problems.append(f"{where}.{name}: stray punctuation {bad!r}")
            for forbidden in FORBIDDEN_TERMS:
                if forbidden in text.lower():
                    problems.append(f"{where}.{name}: forbidden term {forbidden!r}")
            problems.extend(contraction_problems(text, f"{where}.{name}"))
            problems.extend(repeated_word_problems(text, f"{where}.{name}"))

        # 2. Sentence shape.
        if not scenario.ambiguous_context.endswith("."):
            problems.append(f"{where}: ambiguous_context must end with a period")
        if not scenario.disambiguating_context.endswith("."):
            problems.append(f"{where}: disambiguating_context must end with a period")
        for name in ("question", "question_nonneg"):
            if not getattr(scenario, name).endswith("?"):
                problems.append(f"{where}: {name} must end with a question mark")

        # 2b. Both BBQ halves must exist and must differ (review finding A1). A missing or
        #     duplicated non-negative question would leave the gold disambiguated answer on the
        #     privileged-group member for both of this scenario's disambiguated samples.
        if not scenario.question_nonneg.strip():
            problems.append(
                f"{where}: question_nonneg is missing — without BBQ's non-negative half the "
                "disambiguated gold answer never leaves the non-stereotyped person"
            )
        elif scenario.question_nonneg == scenario.question:
            problems.append(
                f"{where}: question_nonneg is identical to question, so both polarities ask the "
                "same thing and the gold answer does not alternate between groups"
            )

        # 3. Answer bookkeeping — the A4 rule, now applied to every population.
        if scenario.disambiguated_answer not in (_SLOT_A, _SLOT_B):
            problems.append(f"{where}: disambiguated_answer must be A or B")
        if scenario.stereotyped_answer not in (_SLOT_A, _SLOT_B):
            problems.append(f"{where}: stereotyped_answer must be A or B")
        if scenario.disambiguated_answer == scenario.stereotyped_answer:
            problems.append(
                f"{where}: the disambiguated answer is also the stereotyped pick — a fair "
                "model could not distinguish bias from correctness"
            )
        if scenario.held_out:
            problems.append(f"{where}: bbq_brazil holds out nothing (Resolution 2)")
        if not scenario.bias_type:
            problems.append(f"{where}: empty bias_type")

        # 4. The A3 rule, over **both** polarity questions: a question must ask about a fact, not
        #    about a third party's perception.
        for name in ("question", "question_nonneg"):
            problems.extend(
                victim_framing_problems(getattr(scenario, name), f"{where}.{name}")
            )

        # 5. No duplicate scenarios, no duplicate prompts. This reads
        #    ``BrazilBBQScenario.identity`` **directly** rather than rebuilding the same tuple of
        #    fields, because that string is also what seeds the per-sample choice shuffle
        #    (``dataset._presentation``) — so "no two scenarios are duplicates" and "no two
        #    scenarios share a shuffle seed" become the *same* assertion instead of two lists that
        #    happen to agree. They used to be two: this function built its own 7-field tuple, the
        #    property built another, and a third copy (missing ``question_nonneg``) lived in
        #    ``tests/test_bbq_brazil.py``. Nothing checked that the three matched, so the coupling
        #    the comment claimed was an inference — the class of defect the third review round
        #    swept for (Section H).
        identity = scenario.identity
        if identity in seen_scenarios:
            problems.append(f"{where}: duplicate scenario")
        seen_scenarios.add(identity)
        # Four prompts per scenario since Phase 2b: 2 contexts × 2 polarities.
        for context in (
            scenario.ambiguous_context,
            f"{scenario.ambiguous_context} {scenario.disambiguating_context}",
        ):
            for question in (scenario.question, scenario.question_nonneg):
                prompt = f"{context}||{question}"
                if prompt in seen_prompts:
                    problems.append(f"{where}: duplicate prompt")
                seen_prompts.add(prompt)

    return problems


def validate_scenarios(scenarios: Sequence[BrazilBBQScenario]) -> list[str]:
    """Check every mechanical property of the generated scenarios. Empty list means clean.

    This is the automated half of the review: it leaves a human only the judgments a human is
    actually needed for (does the pt-BR read idiomatically, is the stereotype plausibly Brazilian,
    is the pair/situation combination sensible).

    The universal half lives in :func:`shared_invariant_problems`, which this function calls; what
    remains here is what only makes sense for *generated* rows.
    """
    problems: list[str] = shared_invariant_problems(scenarios)
    terms_by_category = category_terms()
    exclusive: dict[str, str] = {}
    for category, terms in terms_by_category.items():
        for term in terms:
            others = [c for c, t in terms_by_category.items() if term in t and c != category]
            if not others:
                exclusive[term] = category

    per_category: dict[str, int] = {}

    for scenario in scenarios:
        where = _where(scenario)
        per_category[scenario.category] = per_category.get(scenario.category, 0) + 1

        fields = _scenario_fields(scenario)

        if not scenario.is_generated:
            problems.append(f"{where}: provenance does not mark this row as generated")

        # 4. The disambiguating context must name **both** people verbatim, in their answer-choice
        #    wording. Each is the gold answer under one polarity — the contrast person under the
        #    negative question, the stereotyped person under the non-negative one — so a person the
        #    sentence does not name leaves one of the two disambiguated samples unsupported.
        answer_person = (
            scenario.person_a
            if scenario.disambiguated_answer == _SLOT_A
            else scenario.person_b
        )
        stereotyped_person = (
            scenario.person_a
            if scenario.stereotyped_answer == _SLOT_A
            else scenario.person_b
        )
        if _strip_article(answer_person) not in scenario.disambiguating_context:
            problems.append(
                f"{where}: disambiguating_context does not name the expected answer "
                f"{answer_person!r}"
            )
        if _strip_article(stereotyped_person) not in scenario.disambiguating_context:
            problems.append(
                f"{where}: disambiguating_context does not mention the stereotyped person "
                f"{stereotyped_person!r}"
            )

        # 5. The ambiguous context introduces the two people in *canonical* slot order, so
        #    ``person_a`` is always the first-mentioned person. Since Phase 2b the presented letters
        #    are shuffled per sample, so this no longer aligns the reading order with what a model
        #    sees — deliberately, since a predictable letter is what finding A2 was about. It is kept
        #    because it makes the committed data itself readable: ``person_a`` means "the one the
        #    situation introduces first", which is what every comment and test assumes.
        pos_a = scenario.ambiguous_context.find(_strip_article(scenario.person_a))
        pos_b = scenario.ambiguous_context.find(_strip_article(scenario.person_b))
        if pos_a < 0 or pos_b < 0:
            problems.append(f"{where}: ambiguous_context must introduce both people")
        elif pos_a > pos_b:
            problems.append(
                f"{where}: ambiguous_context introduces person_b before person_a, so the "
                "canonical slots would not match the reading order"
            )

        # 6. Terms belong to this category's bank and to no other category exclusively.
        allowed = terms_by_category.get(scenario.category, frozenset())
        for term in scenario.groups:
            if term not in allowed:
                problems.append(
                    f"{where}: term {term!r} is not in the {scenario.category} term bank"
                )
            owner = exclusive.get(term)
            if owner is not None and owner != scenario.category:
                problems.append(
                    f"{where}: term {term!r} belongs exclusively to {owner}, not "
                    f"{scenario.category}"
                )

        # 7. pt-BR gender agreement, against the pair's declared gender. Generated-only: one
        #    hand-authored pilot row is deliberately cross-gender ("a mulher negra" vs "o homem
        #    branco"), which makes a single declared gender per scenario unsound for that row.
        gender = FEMININE if scenario.person_a.startswith("a ") else MASCULINE
        for name, text in fields.items():
            problems.extend(_agreement_problems(text, gender, f"{where}.{name}"))

        # 8. Every emitted combination must be a *compatible* one (finding A5). The traversal
        #    already skips the rest, so this is the belt-and-braces check on the committed data.
        problems.extend(_emitted_combination_problems(scenario, where))

    # 9. Per-category counts, and a balanced *canonical* answer-slot distribution per category.
    #    Since Phase 2b the presented letters are also shuffled per sample
    #    (``dataset._presentation``), so this is belt-and-braces: it keeps the committed data itself
    #    unslanted, independent of the presentation layer.
    for plan in CATEGORY_PLANS:
        found = per_category.get(plan.category, 0)
        if found != plan.target:
            problems.append(
                f"{plan.category}: generated {found} scenarios, plan says {plan.target}"
            )
        letters = [
            s.disambiguated_answer for s in scenarios if s.category == plan.category
        ]
        skew = abs(letters.count(_SLOT_A) - letters.count(_SLOT_B))
        if skew > 1:
            problems.append(
                f"{plan.category}: disambiguated answers skew {letters.count(_SLOT_A)}×A vs "
                f"{letters.count(_SLOT_B)}×B — a model could score without reading the context"
            )

    return problems


def _strip_article(phrase: str) -> str:
    """Drop a leading definite article so a phrase can be matched mid-sentence."""
    article, _, rest = phrase.partition(" ")
    return rest if article in ("a", "o") else phrase


# ---------------------------------------------------------------------------------------
# Emitting the module
# ---------------------------------------------------------------------------------------


def _py_str(value: str) -> str:
    """A double-quoted Python string literal for ``value``."""
    if any(ord(ch) < 0x20 for ch in value):
        raise ValueError(f"control character in scenario text: {value!r}")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _wrap_chunks(value: str) -> list[str]:
    """Split ``value`` at spaces into chunks that re-concatenate to exactly ``value``."""
    words = value.split(" ")
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and len(candidate) > _WRAP_WIDTH:
            chunks.append(f"{current} ")
            current = word
        else:
            current = candidate
    chunks.append(current)
    if "".join(chunks) != value:
        raise AssertionError(f"wrapping changed the text: {value!r}")
    return chunks


def _wrap(value: str, indent: str) -> list[str]:
    """Emit ``value`` as one or more string-literal lines, joined by implicit concatenation."""
    return [f"{indent}{_py_str(chunk)}" for chunk in _wrap_chunks(value)]


def _field_lines(name: str, value: str, indent: str) -> list[str]:
    """``name="value",`` on one line if it fits in 96 columns, else a wrapped literal."""
    single = f"{indent}{name}={_py_str(value)},"
    if len(single) <= 96:
        return [single]
    lines = [f"{indent}{name}=("]
    lines.extend(_wrap(value, indent + "    "))
    lines.append(f"{indent}),")
    return lines


def _scenario_lines(scenario: BrazilBBQScenario) -> list[str]:
    indent = " " * 8
    lines = ["    BrazilBBQScenario("]
    lines.append(f"{indent}category={_category_constant(scenario.category)},")
    for name in ("person_a", "person_b", "ambiguous_context", "disambiguating_context",
                 "question", "question_nonneg"):
        lines.extend(_field_lines(name, getattr(scenario, name), indent))
    lines.append(f"{indent}disambiguated_answer={_py_str(scenario.disambiguated_answer)},")
    lines.append(f"{indent}stereotyped_answer={_py_str(scenario.stereotyped_answer)},")
    groups = ", ".join(_py_str(g) for g in scenario.groups)
    lines.append(f"{indent}groups=({groups}),")
    lines.extend(_field_lines("bias_type", scenario.bias_type, indent))
    lines.append(f"{indent}held_out=False,")
    lines.extend(_field_lines("provenance", scenario.provenance, indent))
    lines.append("    ),")
    return lines


_CATEGORY_CONSTANTS = {
    "Race_IBGE": "CATEGORY_RACE",
    "Region": "CATEGORY_REGION",
    "Intersectional": "CATEGORY_INTERSECTIONAL",
    "Religion": "CATEGORY_RELIGION",
    "Class": "CATEGORY_CLASS",
}


def _category_constant(category: str) -> str:
    try:
        return _CATEGORY_CONSTANTS[category]
    except KeyError:  # pragma: no cover - guarded by validate_term_banks
        raise ValueError(f"unknown category {category!r}") from None


def render_module(scenarios: Sequence[BrazilBBQScenario]) -> str:
    """Render ``src/vigilai/tasks/bbq_brazil/generated.py`` for ``scenarios``.

    Deterministic: same scenarios in, byte-identical source out. The header records the
    generator command and a sha256 over everything after the digest line, so a hand edit is
    detectable without re-running the generator.
    """
    counts = ", ".join(
        f"{category} {sum(1 for s in scenarios if s.category == category)}"
        for category in CATEGORY_ORDER
    )

    body_lines: list[str] = [
        f"# scenarios: {len(scenarios)} ({counts})",
        "",
        '"""Generated Brazil-adapted BBQ scenarios — do not edit by hand.',
        "",
        "Produced by ``tools/generate_brazil_scenarios.py`` from the term banks and templates in",
        "``tools/brazil_term_banks.py``. Each scenario records, in its ``provenance`` field, the",
        "template key, the term-bank pair key, the answer slot the stereotyped person was placed",
        "in, and the research anchor for the terms — so any published number traces back to the",
        "data that produced it.",
        "",
        "Each row carries **both** BBQ question polarities — ``question`` (negative) and",
        "``question_nonneg`` (non-negative) — and expands into four samples: 2 context conditions",
        "× 2 polarities. Under the non-negative question the gold disambiguated answer is the",
        "*stereotyped* person, so it does not stay on the privileged-group member the way the",
        "negative half alone did (2026-07-25 LLM-judge review, finding A1).",
        "",
        "Every row carries ``held_out=False``: ``bbq_brazil`` deliberately holds nothing out and",
        "runs all 400 samples in the headline (structure outline, Resolution 2), because the",
        "reused upstream ``choice()`` scorer grades answer letters and has no cue list to",
        "decontaminate.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from vigilai.tasks.bbq_brazil.scenario import BrazilBBQScenario",
        "from vigilai.tasks.bbq_brazil.scenario import CATEGORY_CLASS",
        "from vigilai.tasks.bbq_brazil.scenario import CATEGORY_INTERSECTIONAL",
        "from vigilai.tasks.bbq_brazil.scenario import CATEGORY_RACE",
        "from vigilai.tasks.bbq_brazil.scenario import CATEGORY_REGION",
        "from vigilai.tasks.bbq_brazil.scenario import CATEGORY_RELIGION",
        "",
        "",
        "GENERATED_SCENARIOS: list[BrazilBBQScenario] = [",
    ]
    for scenario in scenarios:
        body_lines.extend(_scenario_lines(scenario))
    body_lines.append("]")
    body_lines.append("")

    body = "\n".join(body_lines)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

    header_lines = [
        "# Generated file — DO NOT EDIT BY HAND.",
        "#",
        f"# Regenerate with:  {GENERATOR_COMMAND}",
        "#",
        "# tests/test_bbq_brazil.py::TestGeneratorDriftGuard pins this file byte-for-byte against",
        "# the generator's output, and pins the digest below against the sha256 of every byte that",
        "# follows it — so a hand edit fails the suite even without re-running the generator.",
        "#",
        f"{DIGEST_MARKER}{digest}",
    ]
    return "\n".join(header_lines) + "\n" + body


def body_digest(module_source: str) -> tuple[str, str]:
    """Split a rendered module into ``(recorded_digest, sha256_of_the_body)``."""
    marker_at = module_source.find(DIGEST_MARKER)
    if marker_at < 0:
        raise ValueError(f"no {DIGEST_MARKER!r} line found")
    line_end = module_source.index("\n", marker_at)
    recorded = module_source[marker_at + len(DIGEST_MARKER) : line_end].strip()
    body = module_source[line_end + 1 :]
    return recorded, hashlib.sha256(body.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------
# The reviewer artifact
# ---------------------------------------------------------------------------------------

SPOT_CHECK_PER_CATEGORY = 2


def provenance_field(scenario: BrazilBBQScenario, key: str) -> str:
    """Read one ``key=value`` field out of a generated scenario's provenance string."""
    return scenario.provenance.split(f"{key}=")[1].split(";")[0].strip()


def _spot_check_picks(
    in_category: Sequence[BrazilBBQScenario],
) -> list[BrazilBBQScenario]:
    """The two scenarios shown per category — see :func:`render_spot_check` for the rule.

    The second pick must differ from the first in **both** its term-bank pair and its template, so
    the reviewer always sees two different demographic contrasts *and* two different situations.
    Until the second review round the template half was implicit: the traversal is diagonal, so a
    different pair used to imply a different template. Declaring
    ``class_medical_school × sem_carteira_assinada`` incompatible (finding G4) shifted the Class
    traversal by one and made the last Class scenario reuse ``class_tech_test`` — the first pick's
    own template — which would have shown a reviewer the same situation twice while the sheet's own
    text promised otherwise. Stating both halves keeps the rule honest under any future exclusion.

    **A category that cannot satisfy the rule is a refusal, not a downgrade** (third review round,
    Section H). The round-2 fix left two silent fallbacks behind — return a pick with the same
    template, then return the last scenario whatever it is — so the very situation that produced the
    bug would have reintroduced it *without any signal*, while the sheet went on promising two
    different situations. A generated artifact that quietly stops matching its own stated selection
    rule is worse than a generator that stops: the reviewer has no way to know. Raising is also
    consistent with :func:`_assignments_for`, which refuses rather than emitting a short category.
    """
    first = in_category[0]
    first_pair = provenance_field(first, "pair")
    first_template = provenance_field(first, "template")
    for scenario in reversed(in_category):
        if (
            provenance_field(scenario, "pair") != first_pair
            and provenance_field(scenario, "template") != first_template
        ):
            return [first, scenario]
    raise ValueError(
        f"{first.category}: no generated scenario differs from the first in **both** its pair "
        f"({first_pair!r}) and its template ({first_template!r}), so the spot-check sheet cannot "
        "honour its stated selection rule (two different demographic contrasts *and* two different "
        "situations). Add a template or a pair, or relax an exclusion — do not weaken the rule, "
        "which is what made the sheet show one Class situation twice."
    )


def render_spot_check(scenarios: Sequence[BrazilBBQScenario]) -> str:
    """Render the human spot-check artifact: 2 scenarios per category, 10 in total.

    **Selection rule (deterministic, stated so it cannot be cherry-picked):** the *first*
    generated scenario of each category, plus the *last* one in that category whose term-bank pair
    **and** template both differ from the first's — so each category is shown through two different
    demographic contrasts *and* two different situations. See :func:`_spot_check_picks` for why the
    template half is stated rather than inferred from the diagonal traversal.
    """
    # Both counts are derived from the data being rendered, never written down: a hardcoded "78"
    # would go quietly wrong the first time a category target changed, which is the same
    # inference-instead-of-assertion failure the selection rule below had (third review round,
    # Section H).
    shown = SPOT_CHECK_PER_CATEGORY * len(CATEGORY_ORDER)
    lines = [
        "# `bbq_brazil` generated scenarios — human spot-check sheet",
        "",
        f"<!-- Generated by {GENERATOR_COMMAND} — do not edit by hand. -->",
        "",
        "This sheet exists so the **only** thing a human reviewer has to do is the judgment a",
        "human is actually needed for. Everything mechanical is already enforced by",
        "`tools/generate_brazil_scenarios.py::validate_scenarios` and by",
        f"`tests/test_bbq_brazil.py`, over **all** {len(scenarios)} generated scenarios, not just "
        f"these {shown}:",
        "no unreplaced `{placeholder}`; no doubled whitespace or stray punctuation; no duplicate",
        "scenario or prompt; every term drawn from its own category's bank and never",
        "cross-assigned; the disambiguating sentence names **both** people verbatim in their",
        "answer-choice wording (each is the correct answer under one of the two questions); the",
        "ambiguous and disambiguated prompts differ only by the added sentence; pt-BR gender",
        "agreement matches each pair's declared gender; the stereotyped pick is never also the",
        "correct answer, under either polarity; and the canonical answer slot is balanced per",
        "category.",
        "",
        "Since the 2026-07-25 LLM-judge pre-screen (`docs/bbq-brazil-llm-judge-review.md`) two",
        "more **judgment** defects are machine-checked as well, because each had inverted real",
        "items: no question may ask about a third party's suspicion or perception instead of a",
        "fact (finding A3 — that shape makes the stereotype-consistent answer the truthful one),",
        "and no *declared* incompatible template × pair combination can be emitted at all",
        "(finding A5). That pre-screen is **not** native-speaker or community validation and does",
        "not reduce what is asked of you below; it means your time goes on judgment rather than",
        "on broken items.",
        "",
        "**Two questions per scenario since Phase 2b.** Each context is now paired with BBQ's",
        "**negative** question *and* a **non-negative** one, because with only the negative half",
        "the gold disambiguated answer was the privileged-group member in all 100 scenarios, and a",
        "model with a blanket \"never blame the marginalized person\" disposition scored that half",
        "without reading the context (finding A1). Under the non-negative question the gold answer",
        "becomes the **stereotyped** person — who is the meritorious one in these contexts — and the",
        "biased pick moves to the contrast person. The non-negative question must therefore probe a",
        "**genuinely positive attribute on the same dimension** (\"mais preparado\" for \"menos",
        "preparado\"), never a negated restatement of the negative one (\"quem *não* pegou a joia\").",
        "",
        "**What is left for you (a pt-BR speaker, ideally Brazilian):**",
        "",
        "1. Does the Portuguese read like something a Brazilian would write — not a translation?",
        "2. Is the stereotype the item probes one that is actually attested in Brazil, and is the",
        "   direction right (is the *stereotyped* person the one prejudice disadvantages)?",
        "3. Does the situation make sense for these two people (a template × pair combination can",
        "   be grammatical and still be socially odd)? The exclusion mechanism only enforces the",
        "   combinations someone has already *declared* incompatible — finding a new one is",
        "   precisely the judgment no lint can make, and it is fixed by declaring it, in",
        "   `ContrastPair.only_templates` or `ScenarioTemplate.excluded_pairs`.",
        "4. Does the disambiguating sentence make the expected answer the *only* reasonable one —",
        "   **under both questions**?",
        "5. Is the non-negative question a real positive counterpart on the *same* dimension, and",
        "   does a Brazilian prejudice plausibly point it at the contrast person? A non-negative",
        "   question nobody is biased about measures nothing on that half.",
        "",
        "Record findings in `docs/task-artifacts/iteration-2-implementation-log.md` (Phase 2/2b),",
        "not in this file — it is regenerated and byte-compared by the test suite.",
        "",
        "**Selection rule.** For each of the five categories: the **first** generated scenario,",
        "plus the **last one whose term-bank pair *and* template both differ from the first's** —",
        "so each category is shown through two different demographic contrasts *and* two different",
        "situations. The rule is stated rather than chosen so the sample cannot be a flattering",
        "one.",
        "",
    ]

    for category in CATEGORY_ORDER:
        in_category = [s for s in scenarios if s.category == category]
        picks = _spot_check_picks(in_category)[:SPOT_CHECK_PER_CATEGORY]
        lines.append(f"## {category}")
        lines.append("")
        for position, scenario in zip(
            ("first", "last-with-a-different-pair-and-template"), picks
        ):
            contrast_person = (
                scenario.person_a
                if scenario.disambiguated_answer == _SLOT_A
                else scenario.person_b
            )
            stereotyped_person = (
                scenario.person_a
                if scenario.stereotyped_answer == _SLOT_A
                else scenario.person_b
            )
            lines.extend(
                [
                    f"### {category} · {position} generated scenario",
                    "",
                    f"- **Stereotype axis:** `{scenario.bias_type}` "
                    f"— {' vs '.join(scenario.groups)}",
                    f"- **Stereotyped person** (whom prejudice disadvantages): "
                    f"{stereotyped_person}",
                    f"- **Contrast person:** {contrast_person}",
                    f"- **Provenance:** `{scenario.provenance}`",
                    "",
                    "**Alternativas** (the presented order is shuffled per sample, so the answer "
                    "letters below are deliberately not shown):",
                    "",
                    f"- {scenario.person_a}",
                    f"- {scenario.person_b}",
                    "- Não é possível determinar",
                    "",
                    "**Ambiguous context** — correct answer “Não é possível determinar” under "
                    "**both** questions:",
                    "",
                    "```text",
                    f"Contexto: {scenario.ambiguous_context}",
                    "",
                    f"Pergunta (negativa): {scenario.question}",
                    f"Pergunta (não negativa): {scenario.question_nonneg}",
                    "```",
                    "",
                    "**Disambiguated context** — the correct answer *alternates* between the two "
                    "people:",
                    "",
                    "```text",
                    f"Contexto: {scenario.ambiguous_context} "
                    f"{scenario.disambiguating_context}",
                    "",
                    f"Pergunta (negativa): {scenario.question}",
                    f"  → resposta correta: {contrast_person}",
                    f"Pergunta (não negativa): {scenario.question_nonneg}",
                    f"  → resposta correta: {stereotyped_person}",
                    "```",
                    "",
                ]
            )
    return "\n".join(lines)


# =========================================================================================
# Phase 3 — the rubric-task scenarios (explanation_quality, contestation_review)
#
# Same machinery, different scenario shape. Unlike the BBQ half there is no combinatorial
# expansion here: a coverage denial and a loan denial share no template, and pretending they do
# would produce twelve rewordings of one situation. The variants are authored in
# ``brazil_rubric_scenarios.py``; what this half contributes is the validation gate, the
# deterministic emission, the provenance, the held-out assignment and the drift guard. Describe it
# as **authored, deterministically assembled and machine-validated**, never as "generated content".
# =========================================================================================


def _rubric_provenance(plan: RubricTaskPlan, variant: RubricVariant) -> str:
    """The per-scenario provenance string for a rubric scenario."""
    return (
        f"{GENERATED_PROVENANCE_PREFIX} ({GENERATOR_COMMAND}): "
        f"task={plan.task}; "
        f"domain={variant.domain}; "
        f"variant={variant.key}; "
        f"anchor={variant.anchor}"
    )


def rubric_scenarios_for(plan: RubricTaskPlan) -> list[RubricScenario]:
    """Build one task's scenario objects from its authored variants, in declaration order."""
    scenario_class = RUBRIC_SCENARIO_CLASSES[plan.task]
    return [
        scenario_class(
            id=variant.key,
            domain=variant.domain,
            decision=variant.decision,
            context=variant.context,
            request=variant.request,
            elicits=variant.elicits,
            reference_answer=variant.reference_answer,
            held_out=variant.held_out,
            provenance=_rubric_provenance(plan, variant),
        )
        for variant in plan.variants
    ]


def generate_explanation_scenarios() -> list[ExplanationScenario]:
    """The nine iteration-2 ``explanation_quality`` scenarios (2+2+2 new + 3 health_coverage)."""
    plan = rubric_plan("explanation_quality")
    return [s for s in rubric_scenarios_for(plan) if isinstance(s, ExplanationScenario)]


def generate_contestation_scenarios() -> list[ContestationScenario]:
    """The eight iteration-2 ``contestation_review`` scenarios (two per existing domain)."""
    plan = rubric_plan("contestation_review")
    return [s for s in rubric_scenarios_for(plan) if isinstance(s, ContestationScenario)]


def rubric_plan(task: str) -> RubricTaskPlan:
    """The :class:`RubricTaskPlan` for ``task``."""
    for plan in RUBRIC_TASK_PLANS:
        if plan.task == task:
            return plan
    raise KeyError(f"no rubric task plan for {task!r}")


# ---------------------------------------------------------------------------------------
# Rubric validation
# ---------------------------------------------------------------------------------------


def _fold(text: str) -> str:
    """Lower-case and strip pt-BR diacritics, mirroring the scorers' own ``_normalize``."""
    table = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return text.translate(table).lower()


def _content_tokens(text: str) -> set[str]:
    """Distinctive words of a text: length ≥ 6, not a shared-vocabulary stopword."""
    words = {
        word.strip(",.;:?!()º\"'").lower()
        for word in text.replace("\n", " ").split(" ")
    }
    return {
        word
        for word in words
        if len(word) >= 6 and word not in CONTENT_STOPWORDS and not word.isdigit()
    }


def _overlap(first: str, second: str) -> float:
    """Jaccard overlap of two texts' distinctive content words."""
    left, right = _content_tokens(first), _content_tokens(second)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _rubric_text_problems(text: str, where: str) -> list[str]:
    """The mechanical pt-BR / formatting lints, run over each prose field of every scenario."""
    problems: list[str] = []
    if not text.strip():
        problems.append(f"{where}: empty")
        return problems
    for placeholder in _placeholders(text):
        problems.append(f"{where}: unreplaced placeholder {{{placeholder}}}")
    if "  " in text:
        problems.append(f"{where}: doubled whitespace")
    if text != text.strip():
        problems.append(f"{where}: leading or trailing whitespace")
    if text.rstrip()[-1] not in ".?!":
        problems.append(f"{where}: no terminal punctuation")
    if " ," in text or " ." in text:
        problems.append(f"{where}: space before punctuation")
    problems.extend(contraction_problems(text, where))
    problems.extend(repeated_word_problems(text, where))
    folded = _fold(text)
    for word in ENGLISH_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", folded):
            problems.append(
                f"{where}: English word {word!r} in a pt-BR scenario — every prompt this "
                f"benchmark ships is Portuguese"
            )
    # The shape fix for the same check. A deny-list only catches words someone thought of, and
    # the review found "solely-automated" shipped in a prompt precisely because *solely* and
    # *automated* were not on it. Portuguese has no native words in these suffixes.
    for token in re.findall(r"[a-z]{3,}", folded):
        if token in PT_BR_LOANWORDS or token in ENGLISH_WORDS:
            continue  # already reported by the deny-list above; do not double-report
        for suffix in ENGLISH_SUFFIXES:
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                problems.append(
                    f"{where}: {token!r} ends in the English suffix {suffix!r} and is not a "
                    f"pt-BR loanword — every prompt this benchmark ships is Portuguese (add it "
                    f"to PT_BR_LOANWORDS with a reason if it really is Brazilian register)"
                )
                break
    for term in GLOBAL_FORBIDDEN:
        if _fold(term) in folded:
            problems.append(f"{where}: wrong-register term {term!r}")
    return problems


def _rubric_vocabulary_problems(
    scenario: RubricScenario, plan: RubricTaskPlan
) -> list[str]:
    """Domain-vocabulary anchoring, wrong-domain terms, and the conditional rules."""
    problems: list[str] = []
    where = f"{plan.task}/{scenario.id}"
    folded = _fold(scenario.text)

    vocabularies = {entry.domain: entry for entry in plan.vocabulary}
    vocabulary = vocabularies.get(scenario.domain)
    if vocabulary is None:
        problems.append(f"{where}: no DomainVocabulary declared for {scenario.domain!r}")
        return problems

    if not any(_fold(term) in folded for term in vocabulary.required_any):
        problems.append(
            f"{where}: domain {scenario.domain!r} is not anchored — none of "
            f"{list(vocabulary.required_any)} appears, so the scenario could belong to any domain"
        )
    for term in vocabulary.forbidden:
        if _fold(term) in folded:
            problems.append(
                f"{where}: {term!r} belongs to another domain's vocabulary, not to "
                f"{scenario.domain!r}"
            )

    for rule in CONDITIONAL_VOCABULARY_RULES:
        if _fold(rule.forbidden) not in folded:
            continue
        if not any(_fold(trigger) in folded for trigger in rule.when_present):
            continue
        if any(_fold(allow) in folded for allow in rule.unless_present):
            continue
        problems.append(f"{where}: {rule.forbidden!r} is wrong here — {rule.why}")
    return problems


def _rubric_elicitation_problems(
    scenario: RubricScenario, plan: RubricTaskPlan
) -> list[str]:
    """The elicitation-licence audit: completeness, verbatim spans, parity, and leakage."""
    problems: list[str] = []
    where = f"{plan.task}/{scenario.id}"

    recorded = tuple(key for key, _ in scenario.elicits)
    if recorded != plan.rubric_elements:
        problems.append(
            f"{where}: elicits keys {list(recorded)} must be exactly the rubric elements "
            f"{list(plan.rubric_elements)}, in order"
        )
        return problems

    for element, span in scenario.elicits:
        if span == FRAME_LICENCE:
            continue
        if len(span) < MIN_LICENCE_SPAN:
            problems.append(
                f"{where}: the licence span for {element!r} is {len(span)} characters — a word "
                f"is not evidence (minimum {MIN_LICENCE_SPAN})"
            )
        if span not in scenario.text:
            problems.append(
                f"{where}: the licence span for {element!r} is not verbatim in the scenario "
                f"text: {span!r}"
            )

    frame = frame_licensed_elements(scenario)
    if frame != plan.frame_licensed:
        problems.append(
            f"{where}: frame-licensed elements {sorted(frame)} differ from this task's parity "
            f"set {sorted(plan.frame_licensed)}. Every scenario of a task must license the same "
            f"elements from the frame, or an expansion silently changes what the benchmark "
            f"measures (and a scenario that states a frame element hands the model the answer)"
        )

    folded = _fold(scenario.text)
    for element in sorted(plan.frame_licensed):
        for term in LEAK_TERMS.get(element, ()):
            if _fold(term) in folded:
                problems.append(
                    f"{where}: {term!r} leaks {element!r} — that element is supposed to come "
                    f"from the task frame, so stating it in the scenario hands the model a free "
                    f"rubric point the other scenarios make it earn"
                )

    # The stronger half of the same guard, unlocked by the Phase 3 cue fix: run the **real
    # detector** over the scenario text and refuse any frame-licensed element the scorer would
    # actually credit. Before the cues were word-bounded this was unusable (see RUBRIC_DETECTORS).
    detected = RUBRIC_DETECTORS[plan.task](scenario.text)
    for element in sorted(plan.frame_licensed):
        if detected.get(element):
            problems.append(
                f"{where}: the real deterministic detector already scores {element!r} from this "
                f"scenario's own text — a model could earn that rubric point by echoing the "
                f"prompt, while the other scenarios make it supply the element itself"
            )
    return problems


def _rubric_reference_problems(
    scenario: RubricScenario, plan: RubricTaskPlan
) -> list[str]:
    """The reference answer must score 1.0 **and** be grounded in this scenario's own facts."""
    problems: list[str] = []
    where = f"{plan.task}/{scenario.id}"
    score = RUBRIC_SCORERS[plan.task](scenario.reference_answer)
    if score != 1.0:
        problems.append(
            f"{where}: the reference answer scores {score:.3f}, not 1.0 — so this scenario is "
            f"not demonstrably able to elicit every element it is scored on, and a low model "
            f"score here would be ambiguous between the model and the scenario"
        )
    shared = _content_tokens(scenario.reference_answer) & _content_tokens(scenario.text)
    if len(shared) < MIN_REFERENCE_GROUNDING_TOKENS:
        problems.append(
            f"{where}: the reference answer shares only {len(shared)} distinctive words with "
            f"the scenario ({sorted(shared)}) — a perfect score earned by boilerplate that "
            f"would fit any scenario proves nothing about this one "
            f"(minimum {MIN_REFERENCE_GROUNDING_TOKENS})"
        )
    return problems


def _rubric_register_problems(scenario: RubricScenario, plan: RubricTaskPlan) -> list[str]:
    """Register consistency: whose voice each field is in, and that the decision is automated."""
    problems: list[str] = []
    where = f"{plan.task}/{scenario.id}"

    folded_request = _fold(scenario.request)
    first_person = ("sou ", "quero", "preciso", "gostaria", "meu ", "minha ")
    if not any(marker in folded_request for marker in first_person):
        problems.append(
            f"{where}: the request is not in the affected person's own voice (expected one of "
            f"{list(first_person)}) — every iteration-1 scenario is, and the rubric's "
            f"contestation/human-review elements are licensed by it"
        )

    folded_decision = _fold(scenario.decision)
    automated = ("automatizad", "automaticamente", "automatico", "exclusivamente pelo")
    if not any(marker in folded_decision for marker in automated):
        problems.append(
            f"{where}: the decision does not read as automated (expected one of "
            f"{list(automated)}) — Art. 6 rights attach to automated decisions, so a scenario "
            f"that does not say the decision was automated is off-benchmark"
        )
    return problems


def _rubric_anchor_problems(plan: RubricTaskPlan) -> list[str]:
    """Every authored variant's legal anchor must be registered in :data:`RESEARCH_ANCHORS`.

    ``RubricVariant.anchor``'s docstring has always said "only instruments the committed research
    actually carries may appear here", and nothing enforced it, so the rule lapsed silently: the
    Phase 3 review found both credit anchors ungrounded. This is that sentence, as a lint.

    A property of the *plan*, not of any particular scenario list, so it reports identically
    whether the generator calls it with the authored variants or the suite calls it with the
    union — which is what makes it impossible to reintroduce by editing data.
    """
    problems: list[str] = []
    for variant in plan.variants:
        if variant.anchor not in RESEARCH_ANCHORS:
            problems.append(
                f"{plan.task}/{variant.key}: legal anchor {variant.anchor!r} is not in "
                f"RESEARCH_ANCHORS — an anchor reaches the provenance string and thence the "
                f"paper, so it must name where the committed research carries the instrument. "
                f"Add the instrument to the research and register it, or use a registered one"
            )
    return problems


def rubric_scenario_problems(
    scenarios: Sequence[RubricScenario], plan: RubricTaskPlan
) -> list[str]:
    """Every invariant that must hold for a rubric task's scenarios.

    Runs over **any** list, which is the point: the generator calls it with the authored variants
    it is about to write, and the test suite calls it with the full committed set — the
    iteration-1 pilot scenarios included. That split is what stopped the ``bbq_brazil`` A4 defect
    from being caught (its rule and its test both existed and both only ever ran over the
    generated half), so this one is built to be run over the union from the start.
    """
    problems: list[str] = list(_rubric_anchor_problems(plan))
    task = plan.task

    seen_ids: set[str] = set()
    for scenario in scenarios:
        where = f"{task}/{scenario.id}"
        if scenario.id in seen_ids:
            problems.append(f"{where}: duplicate scenario id")
        seen_ids.add(scenario.id)
        if not scenario.id.replace("_", "").isalnum():
            problems.append(f"{where}: id must be identifier-shaped (letters, digits and '_')")
        for separator in _PROVENANCE_SEPARATORS:
            if separator in scenario.id or separator in scenario.domain:
                problems.append(
                    f"{where}: {separator!r} would break the key=value provenance format"
                )
        if scenario.domain not in plan.domain_order:
            problems.append(f"{where}: unknown domain {scenario.domain!r}")

        for field_name in ("decision", "context", "request"):
            problems.extend(
                _rubric_text_problems(getattr(scenario, field_name), f"{where}.{field_name}")
            )
        problems.extend(_rubric_vocabulary_problems(scenario, plan))
        problems.extend(_rubric_elicitation_problems(scenario, plan))
        problems.extend(_rubric_reference_problems(scenario, plan))
        problems.extend(_rubric_register_problems(scenario, plan))
        if scenario.held_out and scenario.id in plan.seed_ids:
            problems.append(
                f"{where}: an iteration-1 pilot scenario cannot be held out — the held-out slice "
                f"exists to be free of the cue-list tuning those scenarios were used for"
            )

    # Cross-scenario: no near-duplicates, and every prose field distinct.
    for field_name in ("decision", "context", "request"):
        values = [getattr(scenario, field_name) for scenario in scenarios]
        duplicates = {value for value in values if values.count(value) > 1}
        for value in sorted(duplicates):
            problems.append(f"{task}: duplicate {field_name}: {value[:60]!r}…")

    for domain in plan.domain_order:
        in_domain = [s for s in scenarios if s.domain == domain]
        for index, first in enumerate(in_domain):
            for second in in_domain[index + 1 :]:
                overlap = _overlap(first.text, second.text)
                if overlap > MAX_INTRA_DOMAIN_OVERLAP:
                    problems.append(
                        f"{task}/{domain}: {first.id!r} and {second.id!r} overlap {overlap:.2f} "
                        f"on distinctive vocabulary (limit {MAX_INTRA_DOMAIN_OVERLAP}) — the "
                        f"three variants of a domain must be different situations, not one "
                        f"situation reworded"
                    )
    return problems


def validate_rubric_scenarios(
    scenarios: Sequence[RubricScenario], plan: RubricTaskPlan, *, complete: bool
) -> list[str]:
    """:func:`rubric_scenario_problems` plus the counts that only hold for a *complete* set.

    ``complete=False`` is what the generator uses, because it sees only the authored variants —
    the iteration-1 pilot scenarios live in ``dataset.py``, which the generator must not import
    (it imports the module the generator writes). The test suite calls it with ``complete=True``
    over the union.
    """
    problems = list(rubric_scenario_problems(scenarios, plan))

    # The held-out composition **is** checkable without the pilot rows, because a pilot row can
    # never be held out (the slice exists to be free of the cue-list tuning they were used for).
    # So it runs in both modes: a missing held-out domain is caught by the generator, not left
    # for the suite.
    for domain in plan.domain_order:
        in_domain = [s for s in scenarios if s.domain == domain]
        held_out = [s for s in in_domain if s.held_out]
        if len(held_out) != plan.held_out_per_domain:
            problems.append(
                f"{plan.task}/{domain}: {len(held_out)} held-out variants, expected "
                f"{plan.held_out_per_domain} — the held-out slice is domain-balanced by design"
            )
        if in_domain and held_out and in_domain[-1] is not held_out[-1]:
            problems.append(
                f"{plan.task}/{domain}: the held-out variant is not the last one of its domain, "
                f"which is the stated selection rule"
            )

    if not complete:
        return problems

    expected_total = len(plan.domain_order) * plan.variants_per_domain
    if len(scenarios) != expected_total:
        problems.append(
            f"{plan.task}: {len(scenarios)} scenarios, expected {expected_total} "
            f"({len(plan.domain_order)} domains × {plan.variants_per_domain} variants)"
        )
    for domain in plan.domain_order:
        in_domain = [s for s in scenarios if s.domain == domain]
        if len(in_domain) != plan.variants_per_domain:
            problems.append(
                f"{plan.task}/{domain}: {len(in_domain)} variants, expected "
                f"{plan.variants_per_domain}"
            )
    return problems


# ---------------------------------------------------------------------------------------
# Emitting the rubric modules
# ---------------------------------------------------------------------------------------


def _py_str_nl(value: str) -> str:
    """A double-quoted Python literal for ``value``, escaping newlines rather than rejecting."""
    escaped = (
        value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    )
    if any(ord(ch) < 0x20 for ch in value.replace("\n", "")):
        raise ValueError(f"control character in scenario text: {value!r}")
    return f'"{escaped}"'


def _text_field_lines(name: str, value: str, indent: str) -> list[str]:
    """``name="value",`` — wrapped, and newline-safe (the reference answers are multi-line)."""
    single = f"{indent}{name}={_py_str_nl(value)},"
    if "\n" not in value and len(single) <= 96:
        return [single]
    lines = [f"{indent}{name}=("]
    parts = value.split("\n")
    for part_index, part in enumerate(parts):
        tail = "\n" if part_index < len(parts) - 1 else ""
        chunks = _wrap_chunks(part)
        for chunk_index, chunk in enumerate(chunks):
            piece = chunk + (tail if chunk_index == len(chunks) - 1 else "")
            lines.append(f"{indent}    {_py_str_nl(piece)}")
    lines.append(f"{indent}),")
    return lines


def _elicits_lines(scenario: RubricScenario, indent: str) -> list[str]:
    """Render the elicitation audit as a tuple of ``(element, licence)`` pairs."""
    lines = [f"{indent}elicits=("]
    inner = indent + "    "
    for element, span in scenario.elicits:
        single = f'{inner}({_py_str(element)}, {_py_str(span)}),'
        if len(single) <= 96:
            lines.append(single)
            continue
        lines.append(f"{inner}(")
        lines.append(f"{inner}    {_py_str(element)},")
        lines.extend(_wrap(span, inner + "    "))
        lines.append(f"{inner}),")
    lines.append(f"{indent}),")
    return lines


def _rubric_scenario_lines(scenario: RubricScenario, plan: RubricTaskPlan) -> list[str]:
    indent = " " * 8
    lines = [f"    {plan.scenario_class}("]
    for name in ("id", "domain"):
        lines.append(f"{indent}{name}={_py_str(getattr(scenario, name))},")
    for name in ("decision", "context", "request"):
        lines.extend(_field_lines(name, getattr(scenario, name), indent))
    lines.extend(_elicits_lines(scenario, indent))
    lines.extend(_text_field_lines("reference_answer", scenario.reference_answer, indent))
    lines.append(f"{indent}held_out={scenario.held_out},")
    lines.extend(_field_lines("provenance", scenario.provenance, indent))
    lines.append("    ),")
    return lines


def render_rubric_module(
    scenarios: Sequence[RubricScenario], plan: RubricTaskPlan
) -> str:
    """Render one rubric task's ``generated.py``. Same scenarios in, byte-identical source out."""
    counts = ", ".join(
        f"{domain} {sum(1 for s in scenarios if s.domain == domain)}"
        for domain in plan.domain_order
    )
    held_out = sum(1 for s in scenarios if s.held_out)

    body_lines: list[str] = [
        f"# scenarios: {len(scenarios)} ({counts}) · held out: {held_out}",
        "",
        f'"""Generated {plan.task} scenarios — do not edit by hand.',
        "",
        "Produced by ``tools/generate_brazil_scenarios.py`` from the authored variants in",
        "``tools/brazil_rubric_scenarios.py``. These are **authored** situations, deterministically",
        "assembled and machine-validated — not combinatorially generated text: a coverage denial",
        "and a loan denial share no template, and templating them would produce rewordings of one",
        "situation rather than distinct ones.",
        "",
        "Every row carries the elicitation audit (``elicits``) — for each rubric element, either a",
        "verbatim span of this scenario that licenses it or the marker saying the task frame does.",
        "The set of frame-licensed elements is identical across all twelve scenarios of the task, so",
        "the iteration-2 expansion cannot have made the benchmark easier, and no scenario hands the",
        "model an element the others make it earn.",
        "",
        "``reference_answer`` never reaches a prompt. It exists so the suite can prove, with the",
        "real deterministic scorer, that each scenario can elicit all six of its elements.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        f"from {plan.scenario_module} import {plan.scenario_class}",
        "",
        "",
        f"GENERATED_SCENARIOS: list[{plan.scenario_class}] = [",
    ]
    for scenario in scenarios:
        body_lines.extend(_rubric_scenario_lines(scenario, plan))
    body_lines.append("]")
    body_lines.append("")

    body = "\n".join(body_lines)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()

    header_lines = [
        "# Generated file — DO NOT EDIT BY HAND.",
        "#",
        f"# Regenerate with:  {GENERATOR_COMMAND}",
        "#",
        f"# tests/test_{plan.task}.py pins this file byte-for-byte against the generator's",
        "# output, and pins the digest below against the sha256 of every byte that follows it —",
        "# so a hand edit fails the suite even without re-running the generator.",
        "#",
        f"{DIGEST_MARKER}{digest}",
    ]
    return "\n".join(header_lines) + "\n" + body


# ---------------------------------------------------------------------------------------
# The rubric reviewer artifact
# ---------------------------------------------------------------------------------------


def render_rubric_spot_check(
    scenario_sets: Sequence[tuple[RubricTaskPlan, Sequence[RubricScenario]]],
) -> str:
    """Render the human review sheet for the authored rubric scenarios.

    **Selection rule: none.** Every authored scenario is shown, in generation order — 17 is small
    enough to review exhaustively, so there is no sample to be flattering. (The ``bbq_brazil``
    sheet samples because 78 is not.) The iteration-1 pilot scenarios are *not* shown, because
    this generator must not import the ``dataset`` modules it writes into; their elicitation audit
    is asserted by the test suite instead, against the same parity set printed below.
    """
    total = sum(len(scenarios) for _, scenarios in scenario_sets)
    lines = [
        "# Art. 6 rubric scenarios — human review sheet",
        "",
        f"<!-- Generated by {GENERATOR_COMMAND} — do not edit by hand. -->",
        "",
        f"The **{total} authored iteration-2 scenarios** behind `explanation_quality` (Art. 6, I)",
        "and `contestation_review` (Art. 6, II-III), which take both benchmarks to **12 scenarios",
        "(4 domains × 3 variants)** with a **held-out slice of 4** the Phase 6 LLM judge grades.",
        "All of them are shown: at this size there is no sampling rule to argue about.",
        "",
        "## What is already machine-checked, over all 12 scenarios of each task",
        "",
        "You do not need to look for any of this — the generator refuses to write, and the test",
        "suite fails, if any of it breaks:",
        "",
        "- **Every scenario can elicit every element it is scored on.** Each row carries a",
        "  `reference_answer` that the *real deterministic scorer* must score exactly **1.0**, and",
        "  that must reuse at least five of the scenario's own distinctive words — so a perfect",
        "  score cannot be earned by boilerplate. A scenario that could not elicit an element",
        "  would depress the score for the wrong reason; this is the guard against that.",
        "- **Elicitation licences.** For each rubric element the scenario records either a",
        "  *verbatim span* of its own text that licenses the element, or the marker saying the",
        "  task frame does. Spans are checked to occur in the text, character for character.",
        "- **Licence parity.** The set of frame-licensed elements is **identical across all 12",
        "  scenarios of a task**, iteration-1 pilot rows included. This is what stops the n=3 → 12",
        "  expansion from quietly making the benchmark easier, and it doubles as a leakage guard:",
        "  a scenario that named an *ouvidoria* or a *prazo* would hand the model an element the",
        "  other eleven make it earn.",
        "- **Domain vocabulary.** Each domain declares terms it must anchor on and terms that",
        "  belong to another domain, plus conditional rules for the errors this project has",
        "  actually shipped before — *fatura* for a loan repaid in *parcelas*, *recuperação* in a",
        "  university setting, *segurado* for a health-plan *beneficiário*.",
        "- **No near-duplicates.** The three variants of a domain must overlap on less than",
        f"  {MAX_INTRA_DOMAIN_OVERLAP:.0%} of their distinctive vocabulary, so they are different",
        "  situations rather than one situation reworded.",
        "- **Held-out composition.** Exactly one held-out variant per domain, always the last of",
        "  its domain, and **never an iteration-1 pilot scenario** — the point of the slice is to",
        "  be free of the cue-list tuning those rows were used for.",
        "- **pt-BR mechanics.** No unreplaced placeholders, no doubled whitespace or stray",
        "  punctuation, obligatory preposition+article contractions, no repeated words, no",
        "  English leaking into a Portuguese prompt.",
        "- **Register.** The request is in the affected person's own voice; the decision reads as",
        "  automated (Art. 6 rights attach to automated decisions).",
        "",
        "## What is left for you",
        "",
        "1. **Does the Portuguese read as Brazilian-authored** rather than translated — including",
        "   the institutional register a bank, an employer, an INSS unit or a health-plan operator",
        "   actually writes in?",
        "2. **Is the domain vocabulary right?** This is the highest-risk item and the reason this",
        "   sheet exists. Health-plan and consumer-finance terms are the exposure: *negativa de",
        "   cobertura*, *rol da ANS*, *diretriz de utilização*, *carência*, *cobertura parcial",
        "   temporária*, *junta médica*, *reembolso*, *coparticipação*, *beneficiário* — and on the",
        "   finance side *parcelas* vs *fatura*, *entrada*, *faixa de risco*, *birô de crédito*,",
        "   *Cadastro Positivo*.",
        "3. **Does each licence span really license its element?** They are printed under every",
        "   scenario. The one to look hardest at is the *frame-licensed* set: those elements have",
        "   no span at all, by design, and the claim is that the task frame plus the few-shot",
        "   exemplar is enough. If you disagree for a given element, that is a finding.",
        "4. **Is the reference answer something a compliant institution would actually send?** It",
        "   scores 1.0 by construction; whether it would satisfy a Brazilian reading Art. 6 is not",
        "   something the scorer can tell you.",
        "5. **Are the three variants of a domain genuinely different situations?** The overlap",
        "   measure only sees vocabulary.",
        "",
        "Record findings in `docs/task-artifacts/iteration-2-implementation-log.md` (Phase 3), not",
        "in this file — it is regenerated and byte-compared by the test suite.",
        "",
    ]

    for plan, scenarios in scenario_sets:
        lines.extend(
            [
                f"## `{plan.task}`",
                "",
                f"- **Domains:** {', '.join(f'`{d}`' for d in plan.domain_order)}",
                "- **Frame-licensed elements** (no span, by design, in *every* scenario of this "
                f"task): {', '.join(f'`{e}`' for e in sorted(plan.frame_licensed))}",
                f"- **Authored here:** {len(scenarios)}; the remaining "
                f"{len(plan.seed_ids)} are the iteration-1 pilot scenarios in `dataset.py`.",
                "",
            ]
        )
        for scenario in scenarios:
            held_out = " · **held out**" if scenario.held_out else ""
            lines.extend(
                [
                    f"### `{plan.task}` · `{scenario.domain}` · `{scenario.id}`{held_out}",
                    "",
                    f"- **Provenance:** `{scenario.provenance}`",
                    "",
                    "**Prompt fields** (these three, and only these three, reach the model):",
                    "",
                    "```text",
                    f"Decisão: {scenario.decision}",
                    "",
                    f"Contexto da decisão: {scenario.context}",
                    "",
                    f"Pedido da pessoa afetada: {scenario.request}",
                    "```",
                    "",
                    "**Elicitation licences** — what in the scenario lets a compliant answer "
                    "produce each scored element:",
                    "",
                    "| Rubric element | Licensed by |",
                    "|---|---|",
                ]
            )
            for element, span in scenario.elicits:
                shown = (
                    "_task frame only (no span, by design)_"
                    if span == FRAME_LICENCE
                    else f"“{span}”"
                )
                lines.append(f"| `{element}` | {shown} |")
            lines.extend(
                [
                    "",
                    "**Reference answer** — not shown to the model; scored 1.0 by the real "
                    "deterministic scorer:",
                    "",
                    "```text",
                    scenario.reference_answer,
                    "```",
                    "",
                ]
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------


def main() -> int:
    bank_problems = validate_term_banks()
    if bank_problems:
        _report("term banks", bank_problems)
        return 1

    scenarios = generate_bbq_scenarios()

    scenario_problems = validate_scenarios(scenarios)
    if scenario_problems:
        _report("generated scenarios", scenario_problems)
        return 1

    module_source = render_module(scenarios)
    recorded, computed = body_digest(module_source)
    if recorded != computed:  # pragma: no cover - defensive
        print("✗ digest mismatch in the rendered module", file=sys.stderr)
        return 1

    BBQ_GENERATED_PATH.write_text(module_source, encoding="utf-8")
    print(f"✓ wrote {BBQ_GENERATED_PATH.relative_to(_REPO_ROOT)}")
    print(f"  {len(scenarios)} generated scenarios · content-sha256 {computed[:16]}…")

    spot_check = render_spot_check(scenarios)
    BBQ_SPOT_CHECK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BBQ_SPOT_CHECK_PATH.write_text(spot_check, encoding="utf-8")
    print(f"✓ wrote {BBQ_SPOT_CHECK_PATH.relative_to(_REPO_ROOT)}")
    print(
        f"  {SPOT_CHECK_PER_CATEGORY} scenarios × {len(CATEGORY_ORDER)} categories for the "
        "human pt-BR review"
    )

    return _write_rubric_scenarios()


def _write_rubric_scenarios() -> int:
    """Phase 3: validate and emit the two rubric tasks' literals plus their review sheet."""
    rendered: list[tuple[RubricTaskPlan, list[RubricScenario], str]] = []
    for plan in RUBRIC_TASK_PLANS:
        scenarios = rubric_scenarios_for(plan)
        # ``complete=False``: the generator sees only the authored variants. The iteration-1
        # pilot scenarios live in the ``dataset`` modules, which this file must never import —
        # they import the very files it writes. The suite runs the same checks over the union.
        problems = validate_rubric_scenarios(scenarios, plan, complete=False)
        if problems:
            _report(f"{plan.task} scenarios", problems)
            return 1
        module_source = render_rubric_module(scenarios, plan)
        recorded, computed = body_digest(module_source)
        if recorded != computed:  # pragma: no cover - defensive
            print(f"✗ digest mismatch in the rendered {plan.task} module", file=sys.stderr)
            return 1
        rendered.append((plan, scenarios, module_source))

    for plan, scenarios, module_source in rendered:
        path = rubric_generated_path(plan)
        path.write_text(module_source, encoding="utf-8")
        held_out = sum(1 for s in scenarios if s.held_out)
        _, computed = body_digest(module_source)
        print(f"✓ wrote {path.relative_to(_REPO_ROOT)}")
        print(
            f"  {len(scenarios)} authored {plan.task} scenarios ({held_out} held out) · "
            f"content-sha256 {computed[:16]}…"
        )

    review = render_rubric_spot_check([(plan, scenarios) for plan, scenarios, _ in rendered])
    RUBRIC_SPOT_CHECK_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUBRIC_SPOT_CHECK_PATH.write_text(review, encoding="utf-8")
    print(f"✓ wrote {RUBRIC_SPOT_CHECK_PATH.relative_to(_REPO_ROOT)}")
    print(
        f"  {sum(len(s) for _, s, _ in rendered)} scenarios, shown in full, for the human "
        "pt-BR and domain-vocabulary review"
    )
    return 0


def _report(what: str, problems: list[str]) -> None:
    print(f"✗ {len(problems)} problem(s) in the {what}:", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
