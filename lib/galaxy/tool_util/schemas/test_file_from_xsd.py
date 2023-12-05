from __future__ import annotations

import json
from dataclasses import dataclass
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
from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
)

extra_forbidden = ConfigDict(extra="forbid")


@dataclass
class TestOutputElement(TestOutput):
    element_tests: dict[str, TestOutputElement | TestOutput]


@dataclass
class TestOutputCollection(TestOutputCollection_):
    element_tests: dict[str, TestOutputElement | TestOutput]


AnyOutput = Union[TestOutputElement, TestOutput, TestOutputCollection]  # noqa: F405


class Test(BaseModel):
    model_config = extra_forbidden

    doc: str
    job: str
    outputs: dict[str, AnyOutput]


class ListOfTests(RootModel):
    root: list[Test]


print(json.dumps(ListOfTests.model_json_schema(), indent=2))
