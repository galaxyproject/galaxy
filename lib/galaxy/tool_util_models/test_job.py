"""Pydantic model for the ``job:`` block of Planemo / ``*.gxwf-tests.yml`` tests.

Defines the canonical CWL-style workflow-test input syntax — the shape the
schema blesses, not every shape the helpers in ``galaxy_test.base.populators``
happen to tolerate. Legacy ``type: File | Directory | raw`` / ``value`` forms
are intentionally not modeled; those are left to helper-layer tolerances and
should not leak into test fixtures.

Follow-up to galaxyproject/galaxy#18884, which modeled ``TestJob.outputs`` but
left ``TestJob.job`` as ``Dict[str, Any]``.
"""

from typing import (
    Optional,
    Union,
)

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    RootModel,
    Tag,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from ._base import (
    CollectionType,
    StrictModel,
)

# Mirrored from galaxy.util.hash_util.HashFunctionNames — duplicated rather than
# imported so this package stays free of a galaxy-util runtime dep. Kept in sync
# by test/unit/tool_util_models/test_hash_function_names_sync.py, which runs in
# the monorepo where galaxy.util is available.
HashFunctionNames = Literal["MD5", "SHA-1", "SHA-256", "SHA-512"]


class _StrictJobModel(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        field_title_generator=lambda field_name, field_info: field_name.lower(),
    )


class HashEntry(_StrictJobModel):
    hash_function: HashFunctionNames
    hash_value: str


class BaseFile(_StrictJobModel):
    """Fields common to every ``class: File`` variant."""

    class_: Literal["File"] = Field(alias="class")
    filetype: Optional[str] = None
    dbkey: Optional[str] = None
    decompress: Optional[bool] = None
    to_posix_lines: Optional[bool] = None
    space_to_tab: Optional[bool] = None
    deferred: Optional[bool] = None
    name: Optional[str] = None
    info: Optional[str] = None
    tags: Optional[list[str]] = None
    hashes: Optional[list[HashEntry]] = None
    identifier: Optional[str] = None


class LocationFile(BaseFile):
    location: str
    path: Optional[str] = None
    contents: Optional[str] = None
    composite_data: Optional[list[str]] = None


class PathFile(BaseFile):
    path: str
    location: Optional[str] = None
    contents: Optional[str] = None
    composite_data: Optional[list[str]] = None


class ContentsFile(BaseFile):
    """CWL File literal — content inlined as a string."""

    contents: str
    path: Optional[str] = None
    location: Optional[str] = None
    composite_data: Optional[list[str]] = None


class CompositeDataFile(BaseFile):
    composite_data: list[str]
    path: Optional[str] = None
    location: Optional[str] = None
    contents: Optional[str] = None


def _discriminate_file(v):
    if isinstance(v, dict):
        if "location" in v:
            return "location"
        if "path" in v:
            return "path"
        if "contents" in v:
            return "contents"
        if "composite_data" in v:
            return "composite_data"
        return None
    if isinstance(v, LocationFile):
        return "location"
    if isinstance(v, PathFile):
        return "path"
    if isinstance(v, ContentsFile):
        return "contents"
    if isinstance(v, CompositeDataFile):
        return "composite_data"
    return None


File = Annotated[
    Union[
        Annotated[LocationFile, Tag("location")],
        Annotated[PathFile, Tag("path")],
        Annotated[ContentsFile, Tag("contents")],
        Annotated[CompositeDataFile, Tag("composite_data")],
    ],
    Discriminator(_discriminate_file),
]


class Collection(_StrictJobModel):
    class_: Literal["Collection"] = Field(alias="class")
    collection_type: CollectionType = None
    name: Optional[str] = None
    identifier: Optional[str] = None
    elements: Optional[list["CollectionElement"]] = None
    rows: Optional[dict[str, list]] = None


CollectionElement = Annotated[
    Union[File, Collection],
    Field(discriminator="class_"),
]

Collection.model_rebuild()


class Directory(_StrictJobModel):
    """CWL-style directory input. Supported by stage_inputs for directory-typed
    datasets (e.g. bwa_mem2_index test fixtures). Rare in workflow tests; IWC
    does not use it.
    """

    class_: Literal["Directory"] = Field(alias="class")
    path: Optional[str] = None
    location: Optional[str] = None
    filetype: Optional[str] = None
    name: Optional[str] = None


# JobParamValue is non-recursive at the list axis: a job-param list may contain
# files or scalars but not further nested lists. Collection nesting (lists of
# collections) is recursive via ``CollectionElement``. No observed workflow
# test value needs a list-of-lists at the job-input level; widen explicitly if
# that changes rather than defaulting to Any.
JobParamValue = Union[
    File,
    Collection,
    Directory,
    str,
    int,
    float,
    bool,
    None,
    list[Union[File, str, int, float, bool, None]],
]

Job = RootModel[dict[str, JobParamValue]]
