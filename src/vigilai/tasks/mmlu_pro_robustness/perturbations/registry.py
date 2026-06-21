from typing import Literal

from vigilai.tasks.mmlu_pro_robustness.perturbations.contraction_expansion_perturbation import (
    ContractionPerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.contraction_expansion_perturbation import (
    ExpansionPerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.dialect_perturbation import (
    DialectPerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.filler_words_perturbation import (
    FillerWordsPerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.gender_perturbation import (
    GenderPerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.lowercase_perturbation import (
    LowerCasePerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.misspelling_perturbation import (
    MisspellingPerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.perturbation import Perturbation
from vigilai.tasks.mmlu_pro_robustness.perturbations.space_perturbation import (
    SpacePerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.synonym_perturbation import (
    SynonymPerturbation,
)
from vigilai.tasks.mmlu_pro_robustness.perturbations.typos_perturbation import (
    TyposPerturbation,
)


PERTURBATIONS: list[type[Perturbation]] = [
    ContractionPerturbation,
    ExpansionPerturbation,
    DialectPerturbation,
    FillerWordsPerturbation,
    GenderPerturbation,
    LowerCasePerturbation,
    MisspellingPerturbation,
    # TODO: This one requires a big model, > 10 GB
    # "paraphrase": ParaphrasePerturbation,
    SpacePerturbation,
    SynonymPerturbation,
    TyposPerturbation,
]

# Create the Literal type for perturbation names
PerturbationName = Literal[
    "contraction",
    "expansion",
    "dialect",
    "filler-words",
    "gender",
    "lowercase",
    "misspelling",
    # "paraphrase",
    "space",
    "synonym",
    "typos",
]
