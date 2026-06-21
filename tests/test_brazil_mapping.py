"""Tests for the Brazil PL 2338/2023 article-mapping metadata layer (Phase 2).

Covers two things:

1. The mapping module (``vigilai.brazil.mapping``) is internally consistent.
2. The tasks tagged with ``brazil_article`` / ``brazil_scope`` decorator kwargs expose
   that metadata via Inspect AI's ``TaskInfo.attribs``, and the values agree with the
   canonical mapping.
"""

from inspect_ai import TaskInfo

from vigilai._cli.utils import get_vigilai_tasks
from vigilai.brazil.mapping import brazil_article_for
from vigilai.brazil.mapping import BRAZIL_SCOPES
from vigilai.brazil.mapping import TECH_REQ_TO_BRAZIL


# The exact tasks we tagged in Phase 2 -> their expected (article, scope), derived from
# the design discussion §2 / research §4 mapping. Hard-coded here (rather than imported
# from the mapping) so a mistake in the mapping is actually caught.
EXPECTED_TAGGED_TASKS: dict[str, tuple[str, str]] = {
    "human_deception": ("Art. 5, I", "all_ai"),
    "bbq": ("Art. 5, III", "all_ai"),
    "bold": ("Art. 5, III", "all_ai"),
    "cab": ("Art. 5, III", "all_ai"),
    "decoding_trust": ("Art. 5, III", "all_ai"),
    "fairllm": ("Art. 5, III", "all_ai"),
    "bigbench_calibration": ("Art. 6, I", "high_risk"),
    "triviaqa_calibration": ("Art. 6, I", "high_risk"),
}


def _tasks_by_name() -> dict[str, TaskInfo]:
    return {task.name: task for task in get_vigilai_tasks()}


class TestMappingConsistency:
    """Mapping module is internally consistent."""

    def test_mapping_is_non_empty(self) -> None:
        assert TECH_REQ_TO_BRAZIL

    def test_every_entry_is_article_scope_pair(self) -> None:
        for requirement, value in TECH_REQ_TO_BRAZIL.items():
            assert isinstance(requirement, str) and requirement
            assert isinstance(value, tuple) and len(value) == 2
            article, scope = value
            assert isinstance(article, str) and article.startswith("Art")
            assert scope in BRAZIL_SCOPES

    def test_art5_is_all_ai_and_art6_is_high_risk(self) -> None:
        """Brazil Chapter II: Art. 5 rights apply to all AI, Art. 6 to high-risk only."""
        for article, scope in TECH_REQ_TO_BRAZIL.values():
            if article.startswith("Art. 5"):
                assert scope == "all_ai"
            elif article.startswith("Art. 6"):
                assert scope == "high_risk"

    def test_brazil_article_for_known_requirement(self) -> None:
        assert brazil_article_for("Disclosure of AI") == ("Art. 5, I", "all_ai")
        assert brazil_article_for("Interpretability") == ("Art. 6, I", "high_risk")

    def test_brazil_article_for_unmapped_requirement_returns_none(self) -> None:
        # EU-only requirements have no Brazil counterpart yet.
        assert brazil_article_for("Capabilities, Performance, and Limitations") is None
        assert brazil_article_for("not a real requirement") is None


class TestTaskAttribs:
    """Tagged tasks expose Brazil metadata via TaskInfo.attribs."""

    def test_tagged_tasks_are_discoverable(self) -> None:
        discovered = set(_tasks_by_name())
        missing = set(EXPECTED_TAGGED_TASKS) - discovered
        assert not missing, f"tagged tasks not discovered: {sorted(missing)}"

    def test_tagged_tasks_expose_brazil_article_and_scope(self) -> None:
        tasks = _tasks_by_name()
        for name, (article, scope) in EXPECTED_TAGGED_TASKS.items():
            attribs = tasks[name].attribs
            assert attribs.get("brazil_article") == article, name
            assert attribs.get("brazil_scope") == scope, name

    def test_decorator_attribs_agree_with_mapping(self) -> None:
        """Each tagged task's decorator metadata matches what the mapping derives from
        its technical_requirement (the two sources of truth must not drift)."""
        tasks = _tasks_by_name()
        for name in EXPECTED_TAGGED_TASKS:
            attribs = tasks[name].attribs
            requirement = attribs["technical_requirement"]
            derived = brazil_article_for(requirement)
            assert derived is not None, name
            assert (attribs["brazil_article"], attribs["brazil_scope"]) == derived, name

    def test_decorator_mapping_agreement_holds_for_every_rights_mapped_task(self) -> None:
        """Stronger drift guard: for **every** discovered task whose technical_requirement is
        in the canonical Chapter II rights mapping, its decorator's (brazil_article,
        brazil_scope) must equal the mapping's value — not just the hand-listed
        ``EXPECTED_TAGGED_TASKS``.

        Carve-out for AIA (Phase 6): a task may carry a per-task ``brazil_article`` for an
        EU-only ``technical_requirement`` that is **deliberately not** in
        ``TECH_REQ_TO_BRAZIL``. The ``aia_checklist`` task is tagged
        ``technical_requirement="Societal Alignment"`` (an EU-only requirement, shared with
        ``mask`` / ``simpleqa_verified`` / ``truthfulqa``) but carries
        ``brazil_article="Arts. 25-28"`` because the AIA is a PL 2338/2023 **Chapter IV
        governance instrument**, not a Chapter II rights-requirement. Such a tag must NOT be
        added to the canonical requirement→article mapping (that would wrongly pull the other
        "Societal Alignment" tasks under Arts. 25-28). So agreement is enforced **only when the
        requirement is in the mapping**; an extra per-task article for an unmapped requirement
        is explicitly allowed. This does not weaken the check for the rights-mapped tasks
        above — those are still required to agree exactly.
        """
        for task in get_vigilai_tasks():
            attribs = task.attribs
            requirement = attribs.get("technical_requirement", "")
            decorator_article = attribs.get("brazil_article")
            derived = brazil_article_for(requirement)

            if derived is not None:
                # Rights-mapped requirement: decorator (if present) must agree exactly, and
                # rights-mapped tasks are expected to carry the tag.
                assert decorator_article is not None, task.name
                assert (
                    attribs.get("brazil_article"),
                    attribs.get("brazil_scope"),
                ) == derived, task.name
            elif decorator_article is not None:
                # EU-only requirement carrying an extra per-task article (the AIA carve-out):
                # allowed precisely because the requirement is absent from the canonical
                # mapping. Guard the invariant that makes the carve-out safe.
                assert brazil_article_for(requirement) is None, task.name

    def test_every_mapped_requirement_has_at_least_one_tagged_task(self) -> None:
        """Each requirement in the mapping is actually used by a discovered task with the
        matching brazil_article attrib."""
        tagged_articles = {
            task.attribs.get("brazil_article")
            for task in get_vigilai_tasks()
            if task.attribs.get("brazil_article") is not None
        }
        for article, _scope in TECH_REQ_TO_BRAZIL.values():
            assert article in tagged_articles, article
