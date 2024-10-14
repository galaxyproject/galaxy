from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Literal,
    Optional,
)

from pydantic import ConfigDict

alias_lookup = {
    "assert_contents": "asserts",
}


class BaseSetting:
    __pydantic_config__ = ConfigDict(
        extra="forbid", alias_generator=lambda field_name: alias_lookup.get(field_name, field_name)
    )


@dataclass(kw_only=True)
class ClassFileField:
    class_: Optional[Literal["File"]] = field(default="File", metadata={"alias": "class"})
    path: Optional[str] = None


@dataclass(kw_only=True)
class ClassCollectionField:
    class_: Optional[Literal["Collection"]] = field(default="Collection", metadata={"alias": "class"})
