from __future__ import annotations

import json
from typing import Union

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
    RootModel,
)
from pydantic.dataclasses import dataclass

extra_forbidden = ConfigDict(extra="forbid")


@dataclass
class TestOutputElement(TestOutput):
    element_tests: dict[str, TestOutputElement | TestOutput]


@dataclass
class TestOutputCollection(TestOutputCollection_):
    element_tests: dict[str, TestOutputElement | TestOutput]
    collection_type: str | None = None


AnyOutput = Union[TestOutputElement, TestOutput, TestOutputCollection, str, int, float, bool]  # noqa: F405


class Test(BaseModel):
    model_config = extra_forbidden

    doc: str
    job: Job
    outputs: dict[str, AnyOutput]


class ListOfTests(RootModel):
    root: list[Test]


print(json.dumps(ListOfTests.model_json_schema(), indent=2))
