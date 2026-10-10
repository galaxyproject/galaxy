"""Separate tutor variants authored before the candidate run, using the baseline rubric."""

import json
from pathlib import Path

from pydantic_ai.models import Model
from pydantic_evals import (
    Case,
    Dataset,
)

from ..tutor_evaluators import (
    tutor_metadata,
    TutorEvidence,
    TutorQuality,
)


def tutor_variants_dataset(judge_model: Model | None = None, only: list[str] | None = None) -> Dataset:
    examples = json.loads(Path(__file__).with_name("tutor-variants.json").read_text())
    return Dataset(
        name="tutor_variants",
        cases=[
            Case(
                name=example["name"],
                inputs={"query": example["query"], "scenario": example["scenario"]},
                metadata=tutor_metadata(example),
            )
            for example in examples
            if not only or example["name"] in only
        ],
        evaluators=[TutorEvidence(), TutorQuality(judge_model)],
    )
