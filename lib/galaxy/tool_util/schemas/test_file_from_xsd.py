from __future__ import annotations

import json
from typing import (
    Union,
)

# bug with pydantic, need everything in namespace
from generated.galaxy import *  # noqa: F403
from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
)

extra_forbidden = ConfigDict(extra="forbid")


AnyOutput = Union[TestOutput, TestOutputCollection]  # noqa: F405


class Test(BaseModel):
    model_config = extra_forbidden

    doc: str
    job: str
    outputs: dict[str, AnyOutput]


class ListOfTests(RootModel):
    root: list[Test]


print(json.dumps(ListOfTests.model_json_schema(), indent=2))
# print(json.dumps(TypeAdapter(TestOutput).json_schema(), indent=2))
