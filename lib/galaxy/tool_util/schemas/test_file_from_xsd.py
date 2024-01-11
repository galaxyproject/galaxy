from __future__ import annotations

import json
from typing import (
    Union,
)

# bug with pydantic, need everything in namespace, otherwise fails with
# `pydantic.errors.PydanticUserError: `ListOfTests` is not fully defined; you should define `TestDiscoveredDataset`, then call `ListOfTests.model_rebuild()`.`
from generated.galaxy import *  # noqa: F401,F403
from generated.galaxy import (
    TestOutput,
    TestOutputCollection as TestOutputCollection_,
)
from job import Job
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)
from pydantic.dataclasses import dataclass

extra_forbidden = ConfigDict(extra="forbid")


@dataclass
class TestOutputElement(TestOutput):
    elements: dict[str, TestOutputElement | TestOutput]


class TestOutputCollection(TestOutputCollection_):
    elements: dict[str, TestOutputElement | TestOutput]
    collection_type: str | None | None = None


@dataclass
class TestOutputCollectionDeprecated(TestOutputCollection_):
    element_tests: dict[str, TestOutputElement | TestOutput] = Field(
        ...,
        description="Deprecated field, please use elements to describe expectations about collection elements.",
        metadata={"deprecated": True},
    )
    collection_type: str | None | None = None


AnyOutput = Union[
    TestOutputElement, TestOutput, TestOutputCollection, TestOutputCollectionDeprecated, str, int, float, bool
]  # noqa: F405


class Test(BaseModel):
    model_config = extra_forbidden

    doc: str | None = Field(None, description="Describes the purpose of the test.")
    job: Job = Field(
        ...,
        description="Defines job to execute. Can be a path to a file or an line dictionary describing the job inputs.",
    )

    outputs: dict[str, AnyOutput] = Field(
        ...,
        description="Defines assertions about outputs (datasets, collections or parameters). Each key corresponds to a labeled output, values are dictionaries describing the expected output.",
    )


class ListOfTests(RootModel):
    root: list[Test]


print(json.dumps(ListOfTests.model_json_schema(), indent=2))
