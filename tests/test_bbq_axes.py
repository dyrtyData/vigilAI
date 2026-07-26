"""Tests for the axis-stratified EU ``bbq`` baseline (``vigilai.tasks.bbq.stratify``).

The defect these pin — the **sixth** broken measurement instrument of iteration 2, and the one that
outranks the other five because no error bar could ever have caught it:

``--limit`` is global per invocation and ``inspect_evals.bbq.combine_subsets`` concatenates its
eleven subsets with ``Age`` **first**, so ``--limit 100`` took ``Age_00000``–``Age_00099`` and
**every EU ``bbq`` baseline in this project, in both iterations, was 100 ``Age`` samples**. The
EU↔Brazil "bias delta" therefore compared five Brazilian prejudices asked in Portuguese against
*ageism asked in English* — it varied the prejudice as well as the jurisdiction. Raising the limit
would not have helped: ``Age`` alone has 3,680 rows.

Four things are pinned here, and the ordering is deliberate — each one is a way the fix could
silently stop working:

1. **The defaults still mean what they meant.** ``bbq()`` with no kwargs hands upstream's dataset
   through untouched, so every pre-2026-07-26 run stays reproducible and the change is additive.
2. **The stratified sample is what it claims to be** — 4 axes × 48 rows, interleaved, with the
   four (context × polarity) cells balanced.
3. **Drift fails loudly.** Selection is by *id*, so a change in upstream's revision, row order or
   id scheme makes the task unloadable rather than silently sampling something else.
4. **The committed census artifact agrees with the code's own rule.** ``docs/bbq-matched-axes-
   census.md`` is generated from the *real* logs, which are gitignored — so the artifact is checked
   against :func:`~vigilai.tasks.bbq.stratify.expected_sample_ids` here, offline, closing the loop
   between "what the run actually sampled" and "what the code says it samples".

Everything runs **offline**: upstream's Hugging Face loader is stubbed with a synthetic dataset that
reproduces BBQ's *shape* (eleven subsets, ``f"{subset}_{example_id:05d}"`` ids, four consecutive
rows per scenario), the same convention Phase 7 used for the un-downloadable ``human_deception``
dataset.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest
import yaml
from inspect_ai import Task
from inspect_ai.dataset import MemoryDataset
from inspect_ai.dataset import Sample
from inspect_ai.solver import multiple_choice

from vigilai.tasks.bbq.stratify import AXES_MATCHED
from vigilai.tasks.bbq.stratify import AXES_UPSTREAM
from vigilai.tasks.bbq.stratify import MATCHED_AXES
from vigilai.tasks.bbq.stratify import MATCHED_PER_AXIS
from vigilai.tasks.bbq.stratify import SAMPLES_PER_SCENARIO
from vigilai.tasks.bbq.stratify import axes_for_mode
from vigilai.tasks.bbq.stratify import expected_sample_ids
from vigilai.tasks.bbq.stratify import resolve_axes_mode
from vigilai.tasks.bbq.stratify import resolve_per_axis_limit
from vigilai.tasks.bbq.stratify import stratified_samples
from vigilai.tasks.choice_parse import CHOICE_SCORER_NAME


_REPO_ROOT = Path(__file__).resolve().parents[1]
_CENSUS = _REPO_ROOT / "docs" / "bbq-matched-axes-census.md"

# The eleven upstream subsets, in upstream's own order — ``Age`` first, which is the whole defect.
_UPSTREAM_ORDER = (
    "Age",
    "Disability_status",
    "Gender_identity",
    "Nationality",
    "Physical_appearance",
    "Race_ethnicity",
    "Race_x_SES",
    "Race_x_gender",
    "Religion",
    "SES",
    "Sexual_orientation",
)

# Rows per synthetic subset. Comfortably above ``MATCHED_PER_AXIS`` and a multiple of 4 so the
# scenario blocks are whole.
_ROWS_PER_SUBSET = 60

# BBQ's per-scenario row order, verified against the real dataset: two context conditions ×
# two question polarities, in this sequence, repeating every four rows.
_CELL_CYCLE = (
    ("ambig", "neg"),
    ("disambig", "neg"),
    ("ambig", "nonneg"),
    ("disambig", "nonneg"),
)


def _fake_sample(subset: str, index: int) -> Sample:
    context, polarity = _CELL_CYCLE[index % SAMPLES_PER_SCENARIO]
    return Sample(
        input=f"Context: {subset} {index}\n\nQuestion: who?",
        choices=["first", "second", "Cannot answer"],
        target="C",
        id=f"{subset}_{index:05d}",
        metadata={
            "category": subset,
            "context_condition": context,
            "question_polarity": polarity,
            "question_index": str(index // SAMPLES_PER_SCENARIO),
        },
    )


def _fake_dataset(subsets: list[str] | None) -> MemoryDataset:
    names = list(_UPSTREAM_ORDER) if subsets is None else list(subsets)
    return MemoryDataset(
        samples=[
            _fake_sample(subset, index)
            for subset in names
            for index in range(_ROWS_PER_SUBSET)
        ],
        name="bbq-fake",
        location="memory://bbq-fake",
    )


@pytest.fixture
def bbq_module(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """``vigilai.tasks.bbq.bbq`` with upstream's HF loader replaced by a synthetic dataset.

    Fetched from ``sys.modules`` rather than via ``import vigilai.tasks.bbq.bbq``, because the
    package ``__init__`` re-exports the *function* ``bbq``, which shadows the submodule attribute of
    the same name — the same footgun ``tests/test_choice_parse.py`` documents.
    """
    import vigilai.tasks.bbq.bbq  # noqa: F401  (ensure the submodule is imported)

    module = sys.modules["vigilai.tasks.bbq.bbq"]

    calls: list[tuple[object, bool]] = []

    def fake_upstream(subsets: object = None, shuffle: bool = False) -> Task:
        calls.append((subsets, shuffle))
        return Task(
            dataset=_fake_dataset(subsets if subsets is None else list(subsets)),  # type: ignore[arg-type]
            solver=[multiple_choice()],
            scorer=None,
            version=11,
            metadata={"upstream": True},
        )

    monkeypatch.setattr(module, "inspect_bbq", fake_upstream)
    module.upstream_calls = calls  # type: ignore[attr-defined]
    return module


def _ids(task: Task) -> list[str]:
    assert task.dataset is not None
    return [str(sample.id) for sample in task.dataset]


def _axis_of(sample_id: str) -> str:
    return sample_id.rsplit("_", 1)[0]


def _cell_of(sample: Sample) -> tuple[str, str]:
    metadata = sample.metadata or {}
    return str(metadata["context_condition"]), str(metadata["question_polarity"])


# ---------------------------------------------------------------------------
# 1. The defaults still mean exactly what they meant
# ---------------------------------------------------------------------------


class TestDefaultsPreserveUpstreamBehaviour:
    """The change is additive or it is not safe. ``bbq()`` must be the task it always was.

    Iteration 1 and iteration 2 both ran ``uv run vigilai eval … --tasks bbq --limit 100``. Those
    runs are the *before* half of the correction, and the paper differences against them, so the
    default path has to stay byte-for-byte the same command.
    """

    def test_no_kwargs_hands_upstreams_dataset_through_untouched(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """Not "an equal dataset" — the **same object**, so nothing can have been re-derived."""
        upstream = bbq_module.inspect_bbq(None, False)
        task = bbq_module.bbq()
        assert _ids(task) == _ids(upstream)
        assert len(_ids(task)) == len(_UPSTREAM_ORDER) * _ROWS_PER_SUBSET

    def test_the_default_prefix_is_still_age_only(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """The defect itself, pinned. Not a regression to fix — the record of what was measured.

        If this ever stops holding, the *default* sampling changed and every earlier EU number
        stopped being reproducible from the committed code.
        """
        ids = _ids(bbq_module.bbq())
        assert {_axis_of(sample_id) for sample_id in ids[:40]} == {"Age"}

    def test_defaults_do_not_touch_the_scorer_substitution(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        from inspect_ai._util.registry import registry_unqualified_name

        task = bbq_module.bbq()
        assert task.scorer is not None
        assert [registry_unqualified_name(s) for s in task.scorer] == [CHOICE_SCORER_NAME]

    def test_upstream_metadata_and_version_survive_stratification(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """``task_with`` replaces two fields; everything else upstream set must be preserved."""
        task = bbq_module.bbq(axes=AXES_MATCHED)
        assert task.version == 11
        assert task.metadata == {"upstream": True}

    def test_the_stratified_path_also_uses_the_wrapper_scorer(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """Both sides of the delta must be read by one parser, whichever sampling is used."""
        from inspect_ai._util.registry import registry_unqualified_name

        task = bbq_module.bbq(axes=AXES_MATCHED)
        assert task.scorer is not None
        assert [registry_unqualified_name(s) for s in task.scorer] == [CHOICE_SCORER_NAME]

    def test_matched_mode_asks_upstream_for_only_the_matched_subsets(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """58k rows are loaded to keep 192 otherwise; also proves the axis list reaches upstream."""
        bbq_module.upstream_calls.clear()
        bbq_module.bbq(axes=AXES_MATCHED)
        assert bbq_module.upstream_calls == [(list(MATCHED_AXES), False)]


# ---------------------------------------------------------------------------
# 2. The stratified sample is what it claims to be
# ---------------------------------------------------------------------------


class TestMatchedAxisSampling:
    """192 samples, 48 per axis, 48 per cell — measured, not asserted in a docstring."""

    def test_counts(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        ids = _ids(bbq_module.bbq(axes=AXES_MATCHED))
        assert len(ids) == len(MATCHED_AXES) * MATCHED_PER_AXIS == 192

    def test_axis_breakdown_is_exactly_balanced(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        ids = _ids(bbq_module.bbq(axes=AXES_MATCHED))
        counts = {axis: sum(_axis_of(i) == axis for i in ids) for axis in MATCHED_AXES}
        assert counts == {axis: MATCHED_PER_AXIS for axis in MATCHED_AXES}

    def test_the_four_context_by_polarity_cells_are_exactly_balanced(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """The reason ``MATCHED_PER_AXIS`` is 48 and not the 50 originally specified.

        ``bbq_brazil`` is exactly 100 samples in each of its four cells. 50 rows per axis yields 52
        ``neg`` against 48 ``nonneg`` — a composition difference on the very comparison the matched
        axes exist to make like-for-like.
        """
        task = bbq_module.bbq(axes=AXES_MATCHED)
        assert task.dataset is not None
        cells: dict[tuple[str, str], int] = {}
        for sample in task.dataset:
            cells[_cell_of(sample)] = cells.get(_cell_of(sample), 0) + 1
        assert cells == {cell: MATCHED_PER_AXIS for cell in _CELL_CYCLE}

    def test_matched_per_axis_is_a_multiple_of_the_scenario_size(self) -> None:
        assert MATCHED_PER_AXIS % SAMPLES_PER_SCENARIO == 0

    @pytest.mark.parametrize("limit", [4, 8, 16, 40, 100, 192])
    def test_any_multiple_of_four_limit_keeps_the_axes_balanced(self, bbq_module, limit: int) -> None:  # type: ignore[no-untyped-def]
        """``--limit`` takes the *first* N samples, so the interleave is what makes it safe.

        Without it, ``--limit 100`` on the matched set would be 48 ``Race_ethnicity`` + 48
        ``Religion`` + 4 ``SES`` and no ``Nationality`` at all — a smaller replay of the very
        defect being fixed.
        """
        ids = _ids(bbq_module.bbq(axes=AXES_MATCHED))[:limit]
        counts = {axis: sum(_axis_of(i) == axis for i in ids) for axis in MATCHED_AXES}
        assert set(counts.values()) == {limit // len(MATCHED_AXES)}

    @pytest.mark.parametrize("limit", [16, 32, 64, 192])
    def test_any_multiple_of_sixteen_limit_also_keeps_the_cells_balanced(self, bbq_module, limit: int) -> None:  # type: ignore[no-untyped-def]
        """4 axes × 4 cells = 16. Documented as the stricter rule, and pinned as one."""
        task = bbq_module.bbq(axes=AXES_MATCHED)
        assert task.dataset is not None
        cells: dict[tuple[str, str], int] = {}
        for sample in list(task.dataset)[:limit]:
            cells[_cell_of(sample)] = cells.get(_cell_of(sample), 0) + 1
        assert cells == {cell: limit // len(_CELL_CYCLE) for cell in _CELL_CYCLE}

    def test_the_interleave_is_round_robin_in_declared_axis_order(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        ids = _ids(bbq_module.bbq(axes=AXES_MATCHED))
        assert ids[: len(MATCHED_AXES)] == [f"{axis}_00000" for axis in MATCHED_AXES]
        assert ids[len(MATCHED_AXES) : 2 * len(MATCHED_AXES)] == [
            f"{axis}_00001" for axis in MATCHED_AXES
        ]

    def test_the_sample_set_is_identical_across_repeated_construction(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """Determinism: no RNG, no seed, so two constructions cannot differ."""
        assert _ids(bbq_module.bbq(axes=AXES_MATCHED)) == _ids(bbq_module.bbq(axes=AXES_MATCHED))

    def test_selection_survives_a_reordered_upstream_dataset(self, bbq_module, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Selection is by **id**, so upstream row order cannot change the sample set.

        The property that makes the drift guard meaningful: a reshuffled Hugging Face split yields
        the same 192 items in the same order rather than 192 different ones.
        """
        baseline = _ids(bbq_module.bbq(axes=AXES_MATCHED))

        def reversed_upstream(subsets: object = None, shuffle: bool = False) -> Task:
            dataset = _fake_dataset(None if subsets is None else list(subsets))  # type: ignore[arg-type]
            return Task(
                dataset=MemoryDataset(samples=list(reversed(list(dataset)))),
                solver=[multiple_choice()],
                scorer=None,
            )

        monkeypatch.setattr(bbq_module, "inspect_bbq", reversed_upstream)
        assert _ids(bbq_module.bbq(axes=AXES_MATCHED)) == baseline

    def test_an_explicit_per_axis_limit_overrides_the_default(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """The lever the budget needs: fewer samples per axis without a new task or a new mode."""
        ids = _ids(bbq_module.bbq(axes=AXES_MATCHED, per_axis_limit=8))
        assert len(ids) == 8 * len(MATCHED_AXES)
        assert {_axis_of(i) for i in ids} == set(MATCHED_AXES)

    def test_a_per_axis_limit_alone_stratifies_the_eleven_upstream_axes(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """``per_axis_limit`` is meaningful without ``axes``: an all-eleven *balanced* sample.

        Not what the paper reports — an all-eleven sample puts Brazil's five axes against axes it
        does not cover — but the kwarg has to behave, and this is the shape someone will reach for.
        """
        ids = _ids(bbq_module.bbq(per_axis_limit=4))
        assert len(ids) == 4 * len(_UPSTREAM_ORDER)
        counts = {axis: sum(_axis_of(i) == axis for i in ids) for axis in _UPSTREAM_ORDER}
        assert set(counts.values()) == {4}


# ---------------------------------------------------------------------------
# 3. The axis mapping, and what it deliberately leaves out
# ---------------------------------------------------------------------------


class TestAxisMapping:
    """The four matched axes are a documented judgment call; pin the call, not a vibe."""

    def test_the_matched_axes_are_the_four_declared_ones(self) -> None:
        assert MATCHED_AXES == ("Race_ethnicity", "Religion", "SES", "Nationality")

    def test_every_matched_axis_is_a_real_upstream_subset(self) -> None:
        assert set(MATCHED_AXES) <= set(_UPSTREAM_ORDER)

    def test_age_is_excluded(self) -> None:
        """``bbq_brazil`` has no age axis, and ``Age`` is the whole of the retracted baseline."""
        assert "Age" not in MATCHED_AXES

    def test_race_x_ses_is_excluded_so_race_and_ses_are_not_double_counted(self) -> None:
        """The obvious candidate for the Intersectional axis, deliberately not used.

        Its rows are race × SES, both of which the sample already covers separately, so including
        it would weight those two axes twice and leave the sample no longer balanced across axes.
        """
        assert "Race_x_SES" not in MATCHED_AXES

    def test_axes_for_mode_upstream_is_all_eleven_in_upstream_order(self) -> None:
        assert axes_for_mode(AXES_UPSTREAM) == _UPSTREAM_ORDER

    def test_axes_for_mode_matched_is_the_matched_four(self) -> None:
        assert axes_for_mode(AXES_MATCHED) == MATCHED_AXES


# ---------------------------------------------------------------------------
# 4. Bad input fails loudly, and drift fails loudly
# ---------------------------------------------------------------------------


class TestRefusals:
    """Every one of these degrades to "silently sampled something else" if it does not raise."""

    def test_an_unknown_axes_mode_raises_and_names_the_modes(self) -> None:
        with pytest.raises(ValueError, match="unknown axes mode"):
            resolve_axes_mode("matched_axes")

    def test_a_typo_does_not_degrade_to_the_upstream_default(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """The failure mode that would let the age-only baseline survive a third iteration."""
        with pytest.raises(ValueError):
            bbq_module.bbq(axes="Matched")

    def test_a_negative_per_axis_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="per_axis_limit must be >= 0"):
            resolve_per_axis_limit(AXES_MATCHED, -1)

    def test_subsets_combined_with_a_stratified_mode_raises(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """Two ways of choosing subsets; a silent precedence rule between them is a trap."""
        with pytest.raises(ValueError, match="cannot be combined"):
            bbq_module.bbq(subsets=["Religion"], axes=AXES_MATCHED)

    def test_subsets_combined_with_a_bare_per_axis_limit_raises(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError, match="cannot be combined"):
            bbq_module.bbq(subsets=["Religion"], per_axis_limit=4)

    def test_subsets_alone_still_works(self, bbq_module) -> None:  # type: ignore[no-untyped-def]
        """Upstream's own kwarg is untouched — this is an additive change."""
        ids = _ids(bbq_module.bbq(subsets=["Religion"]))
        assert {_axis_of(i) for i in ids} == {"Religion"}

    def test_a_missing_pinned_id_raises_the_drift_guard(self) -> None:
        """**The drift guard.** Selection by id means a moved dataset is unloadable, not silent.

        This is the whole reason the sample set is pinned by id rather than by position: an upstream
        revision bump, a renumbering, or an id-format change must stop the run, because "sampled
        something else without telling anyone" is precisely how the age-only baseline happened.
        """
        short = [_fake_sample("Religion", index) for index in range(10)]
        with pytest.raises(ValueError, match="pinned bbq sample ids are absent"):
            stratified_samples(short, ["Religion"], MATCHED_PER_AXIS)

    def test_the_drift_message_points_at_the_dataset_revision(self) -> None:
        with pytest.raises(ValueError, match="BBQ_DATASET_REVISION"):
            stratified_samples([], ["Religion"], 1)


# ---------------------------------------------------------------------------
# 5. The pinned id rule
# ---------------------------------------------------------------------------


class TestPinnedIdRule:
    """``expected_sample_ids`` *is* the sampling design; it needs its own tests."""

    def test_shape(self) -> None:
        ids = expected_sample_ids(MATCHED_AXES, MATCHED_PER_AXIS)
        assert len(ids) == 192
        assert len(set(ids)) == 192

    def test_the_ids_are_the_first_n_of_each_axis(self) -> None:
        ids = expected_sample_ids(MATCHED_AXES, MATCHED_PER_AXIS)
        for axis in MATCHED_AXES:
            assert [i for i in ids if _axis_of(i) == axis] == [
                f"{axis}_{index:05d}" for index in range(MATCHED_PER_AXIS)
            ]

    def test_a_zero_limit_selects_nothing(self) -> None:
        assert expected_sample_ids(MATCHED_AXES, 0) == ()

    def test_an_unset_limit_resolves_to_the_pinned_design_under_matched(self) -> None:
        assert resolve_per_axis_limit(AXES_MATCHED, 0) == MATCHED_PER_AXIS

    def test_an_unset_limit_stays_uncapped_under_upstream(self) -> None:
        assert resolve_per_axis_limit(AXES_UPSTREAM, 0) == 0


# ---------------------------------------------------------------------------
# 6. Task-signature defaults are literals (the Phase 2 trap, third instance)
# ---------------------------------------------------------------------------


class TestTaskSignatureLiterals:
    """``make default-config`` serialises a default's **source text**, not its value.

    ``tools/generate_default_config.py`` AST-parses each ``@task`` signature with
    ``ast.literal_eval`` and falls back to ``ast.unparse``, so ``axes: str = AXES_UPSTREAM`` would
    write the *identifier* ``axes: AXES_UPSTREAM`` into ``config/default_config.yaml`` and a
    ``--task-config`` run would then pass the string ``"AXES_UPSTREAM"`` into the validator. Hit
    twice already (Phase 2's ``split``, Phase 4's decorator attrib); pinned a third time here.
    """

    @staticmethod
    def _defaults() -> dict[str, object]:
        source = (_REPO_ROOT / "src/vigilai/tasks/bbq/bbq.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        func = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "bbq"
        )
        names = [arg.arg for arg in func.args.args][-len(func.args.defaults) :]
        return {
            name: ast.literal_eval(default)
            for name, default in zip(names, func.args.defaults, strict=True)
        }

    def test_every_default_is_a_literal(self) -> None:
        """``ast.literal_eval`` raising *is* the failure — a named constant cannot be evaluated."""
        assert self._defaults() == {
            "subsets": None,
            "shuffle": False,
            "axes": "upstream",
            "per_axis_limit": 0,
        }

    def test_the_axes_literal_equals_the_module_constant(self) -> None:
        assert self._defaults()["axes"] == AXES_UPSTREAM

    def test_the_generated_config_carries_both_new_entries(self) -> None:
        config = yaml.safe_load(
            (_REPO_ROOT / "config/default_config.yaml").read_text(encoding="utf-8")
        )
        assert config["bbq"] == {
            "subsets": None,
            "shuffle": False,
            "axes": AXES_UPSTREAM,
            "per_axis_limit": 0,
        }


# ---------------------------------------------------------------------------
# 7. Cluster keys and the equal-cluster-size assertion
# ---------------------------------------------------------------------------


class TestScenarioClustering:
    """The cluster-robust error bar is only honest if the cluster key is right.

    It was not, on the first attempt: ``"_".join(parts[:2])`` collapsed all twenty ``Race_IBGE``
    scenarios into one 80-member cluster, because that one category key contains an underscore.
    It moved Haiku's ``bbq_brazil`` bar from 0.0181 to 0.0174 and **nothing else showed it** — the
    equal-cluster-size assertion is what caught it, which is why it is not optional.
    """

    @staticmethod
    def _tool():  # type: ignore[no-untyped-def]
        sys.path.insert(0, str(_REPO_ROOT))
        import tools.bbq_axis_census as census

        return census

    def test_brazil_key_strips_the_context_and_polarity_suffix(self) -> None:
        census = self._tool()
        assert census.scenario_key("bbq_brazil", "Class_004_ambig_neg") == "Class_004"
        assert census.scenario_key("bbq_brazil", "Class_004_disambig_nonneg") == "Class_004"

    def test_brazil_key_handles_the_category_whose_name_contains_an_underscore(self) -> None:
        """``Race_IBGE`` — the bug. Two different scenarios must not share a key."""
        census = self._tool()
        assert census.scenario_key("bbq_brazil", "Race_IBGE_000_ambig_neg") == "Race_IBGE_000"
        assert census.scenario_key("bbq_brazil", "Race_IBGE_005_ambig_neg") == "Race_IBGE_005"

    def test_eu_key_groups_four_consecutive_rows(self) -> None:
        census = self._tool()
        keys = {census.scenario_key("bbq", f"Religion_{i:05d}") for i in range(4)}
        assert keys == {"Religion_0"}
        assert census.scenario_key("bbq", "Religion_00004") == "Religion_1"

    def test_eu_key_does_not_merge_axes(self) -> None:
        census = self._tool()
        assert census.scenario_key("bbq", "SES_00000") != census.scenario_key("bbq", "Religion_00000")

    def test_an_unknown_task_raises_rather_than_guessing_a_cluster(self) -> None:
        census = self._tool()
        with pytest.raises(ValueError, match="not a BBQ-family task"):
            census.scenario_key("mmlu_pro", "x_00000")

    def test_unequal_clusters_are_refused(self) -> None:
        census = self._tool()
        with pytest.raises(ValueError, match="do not hold exactly 4 samples"):
            census.check_cluster_sizes({"a": [1.0, 0.0, 1.0]}, "synthetic")

    def test_equal_clusters_pass(self) -> None:
        census = self._tool()
        census.check_cluster_sizes({"a": [1.0, 0.0, 1.0, 1.0]}, "synthetic")

    def test_partial_clusters_can_be_allowed_explicitly(self) -> None:
        census = self._tool()
        census.check_cluster_sizes({"a": [1.0]}, "synthetic", allow_partial=True)

    def test_cluster_scores_groups_the_reduced_per_sample_means(self) -> None:
        census = self._tool()
        clusters = census.cluster_scores(
            "bbq", {f"Religion_{i:05d}": float(i % 2) for i in range(8)}
        )
        assert {key: sorted(values) for key, values in clusters.items()} == {
            "Religion_0": [0.0, 0.0, 1.0, 1.0],
            "Religion_1": [0.0, 0.0, 1.0, 1.0],
        }


# ---------------------------------------------------------------------------
# 8. The committed census artifact agrees with the code's own rule
# ---------------------------------------------------------------------------


class TestCommittedCensusArtifact:
    """The loop-closing test the brief asked for, made runnable on a fresh checkout.

    ``.eval`` logs are gitignored, so a test that reads them cannot run in CI. What *is* committed
    is ``docs/bbq-matched-axes-census.md``, generated by ``tools/bbq_axis_census.py`` from the real
    logs — so the check here is that the axis breakdown, cell breakdown and full id list *the run
    actually produced* match what
    :func:`~vigilai.tasks.bbq.stratify.expected_sample_ids` says they should be. A hand edit to
    either side fails.
    """

    @staticmethod
    def _text() -> str:
        return _CENSUS.read_text(encoding="utf-8")

    def test_the_artifact_exists_and_is_marked_generated(self) -> None:
        text = self._text()
        assert "GENERATED by" in text
        assert "tools/bbq_axis_census.py" in text

    def test_the_id_block_is_exactly_the_expected_sample_ids(self) -> None:
        """The load-bearing assertion: what ran == what the code says runs."""
        blocks = re.findall(r"```\n(.*?)```", self._text(), flags=re.DOTALL)
        assert blocks, "no fenced id block in the census artifact"
        found = sorted(blocks[-1].split())
        assert found == sorted(expected_sample_ids(MATCHED_AXES, MATCHED_PER_AXIS))

    def test_the_recorded_axis_breakdown_is_forty_eight_each(self) -> None:
        text = self._text()
        for axis in MATCHED_AXES:
            assert f"{axis} {MATCHED_PER_AXIS}" in text, axis

    def test_the_recorded_cell_breakdown_is_forty_eight_each(self) -> None:
        text = self._text()
        for context, polarity in _CELL_CYCLE:
            assert f"{context}/{polarity} {MATCHED_PER_AXIS}" in text, (context, polarity)

    def test_the_recorded_sample_count_is_192(self) -> None:
        assert f"| {len(MATCHED_AXES) * MATCHED_PER_AXIS} | " in self._text()

    def test_the_artifact_states_the_region_mismatch_rather_than_hiding_it(self) -> None:
        """The one axis with no true counterpart. Binding on the paper; pinned here.

        ``Nationality`` is prejudice against foreigners; Brazil's regional prejudice is internal
        (nordestino/sudestino). If this sentence ever disappears, a reader of the census would take
        the four axes as four clean matches.
        """
        # Whitespace-normalised, so reflowing the prose cannot break the check while deleting the
        # claim still does.
        flat = " ".join(self._text().split())
        assert "closest available analogue only" in flat
        assert "Intersectional axis has no counterpart" in flat

    def test_the_recorded_run_is_the_matched_condition_not_the_default(self) -> None:
        """The condition has to be legible off the artifact, as it is off the log header.

        The `aia_checklist` lesson (Resolution 9): two conditions of one task differ by most of the
        score, so a mislabelled record is worse than a missing one.
        """
        assert "axes='matched'" in self._text()
        assert "axes='upstream'" not in self._text()

    def test_no_run_in_the_artifact_reported_an_unparsable_answer(self) -> None:
        """Resolution 13(h)(v)'s doctrine pre-flight, read back off the committed record.

        A non-zero empty-``Score.answer`` count means the scorer could not read some completions and
        every number in the artifact is arithmetic rather than measurement.
        """
        text = self._text()
        table = text.split("## Empty-`Score.answer` census")[1].split("## Scores")[0]
        counts = [
            row.rsplit("|", 2)[1].strip()
            for row in table.splitlines()
            if row.startswith("| `iter2")
        ]
        assert counts, "no empty-answer rows in the census artifact"
        assert set(counts) == {"0"}, counts


# ---------------------------------------------------------------------------
# 9. The same assertion, made against a real .eval log when one is present
# ---------------------------------------------------------------------------


_MATCHED_RUN_DIRS = tuple(
    sorted(_REPO_ROOT.glob("logs/iter2-matched-axes-*"))
)


@pytest.mark.skipif(
    not _MATCHED_RUN_DIRS,
    reason="no logs/iter2-matched-axes-* run present (.eval logs are gitignored)",
)
class TestRealLogSampleIds:
    """The literal shape of the check: read the sample ids **out of the run** and assert on them.

    :class:`TestCommittedCensusArtifact` is the version that survives a fresh checkout, because the
    ``.eval`` logs are gitignored and the committed census stands in for them. This class is the
    version that has no intermediary at all — it opens the log, lists the ids the model was actually
    asked, and checks the axis and cell proportions directly. It runs on the machine that produced
    the run and skips everywhere else, which is exactly the trade the gitignore forces; the two
    together mean the claim is checked against the run *here* and against the code *everywhere*.
    """

    @staticmethod
    def _eu_logs():  # type: ignore[no-untyped-def]
        from inspect_ai.log import list_eval_logs
        from inspect_ai.log import read_eval_log

        found = []
        for run_dir in _MATCHED_RUN_DIRS:
            for info in list_eval_logs(str(run_dir)):
                header = read_eval_log(info.name, header_only=True)
                if header.eval.task.split("/")[-1] == "bbq":
                    found.append((run_dir.name, info.name, header))
        return found

    def test_each_run_dir_holds_exactly_one_eu_bbq_log(self) -> None:
        """Otherwise "which log did the report read?" is a question, not a fact.

        Resolution 12(b): two logs for one task in one directory means the aggregator silently picks
        one. The recency fix makes the pick *correct*; it does not make it *visible*.
        """
        by_dir: dict[str, int] = {}
        for run_dir, _path, _header in self._eu_logs():
            by_dir[run_dir] = by_dir.get(run_dir, 0) + 1
        assert by_dir, "no bbq log under logs/iter2-matched-axes-*"
        assert set(by_dir.values()) == {1}, by_dir

    def test_the_log_header_records_the_matched_condition(self) -> None:
        for run_dir, _path, header in self._eu_logs():
            args = dict(header.eval.task_args or {})
            assert args.get("axes") == AXES_MATCHED, (run_dir, args)

    def test_the_run_sampled_exactly_the_pinned_ids(self) -> None:
        """The load-bearing one: what the model was asked == what the sampler says it asks."""
        from inspect_ai.log import read_eval_log

        expected = sorted(expected_sample_ids(MATCHED_AXES, MATCHED_PER_AXIS))
        for run_dir, path, _header in self._eu_logs():
            log = read_eval_log(path)
            ids = sorted({str(sample.id) for sample in (log.samples or [])})
            assert ids == expected, run_dir

    def test_the_axis_proportions_are_equal_in_the_real_run(self) -> None:
        from collections import Counter

        from inspect_ai.log import read_eval_log

        for run_dir, path, _header in self._eu_logs():
            log = read_eval_log(path)
            ids = {str(sample.id) for sample in (log.samples or [])}
            counts = Counter(_axis_of(sample_id) for sample_id in ids)
            assert dict(counts) == {axis: MATCHED_PER_AXIS for axis in MATCHED_AXES}, run_dir

    def test_the_context_by_polarity_cells_are_equal_in_the_real_run(self) -> None:
        """Why ``MATCHED_PER_AXIS`` is 48: 50 would give 52 ``neg`` against 48 ``nonneg``."""
        from collections import Counter

        from inspect_ai.log import read_eval_log

        for run_dir, path, _header in self._eu_logs():
            log = read_eval_log(path)
            seen: set[str] = set()
            cells: Counter[tuple[str, str]] = Counter()
            for sample in log.samples or []:
                sample_id = str(sample.id)
                if sample_id in seen:
                    continue
                seen.add(sample_id)
                metadata = sample.metadata or {}
                cells[(str(metadata["context_condition"]), str(metadata["question_polarity"]))] += 1
            assert dict(cells) == {cell: MATCHED_PER_AXIS for cell in _CELL_CYCLE}, run_dir

    def test_no_sample_in_the_real_run_carries_an_unreadable_answer(self) -> None:
        """Resolution 13(h)(v)'s doctrine pre-flight, run against the log rather than the artifact."""
        from inspect_ai.log import read_eval_log

        for run_dir, path, _header in self._eu_logs():
            log = read_eval_log(path)
            empty = [
                str(sample.id)
                for sample in (log.samples or [])
                for score in (sample.scores or {}).values()
                if not (score.answer or "").strip()
            ]
            assert not empty, (run_dir, len(empty), empty[:5])
