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
    Dict,
    List,
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
    )


class HashEntry(_StrictJobModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="HashEntry")
    hash_function: Annotated[HashFunctionNames, Field(title="Hash Function")]
    hash_value: Annotated[str, Field(title="Hash Value")]


class BaseFile(_StrictJobModel):
    """Fields common to every ``class: File`` variant."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="BaseFile")
    class_: Literal["File"] = Field(alias="class", title="Class")
    filetype: Annotated[Optional[str], Field(title="File Type")] = None
    dbkey: Annotated[Optional[str], Field(title="Dbkey")] = None
    decompress: Annotated[Optional[bool], Field(title="Decompress")] = None
    to_posix_lines: Annotated[Optional[bool], Field(title="To POSIX Lines")] = None
    space_to_tab: Annotated[Optional[bool], Field(title="Space To Tab")] = None
    deferred: Annotated[Optional[bool], Field(title="Deferred")] = None
    name: Annotated[Optional[str], Field(title="Name")] = None
    info: Annotated[Optional[str], Field(title="Info")] = None
    tags: Annotated[Optional[List[str]], Field(title="Tags")] = None
    hashes: Annotated[Optional[List[HashEntry]], Field(title="Hashes")] = None
    identifier: Annotated[Optional[str], Field(title="Identifier")] = None


class LocationFile(BaseFile):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="LocationFile")
    location: Annotated[str, Field(title="Location")]
    path: Annotated[Optional[str], Field(title="Path")] = None
    contents: Annotated[Optional[str], Field(title="Contents")] = None
    composite_data: Annotated[Optional[List[str]], Field(title="Composite Data")] = None


class PathFile(BaseFile):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="PathFile")
    path: Annotated[str, Field(title="Path")]
    location: Annotated[Optional[str], Field(title="Location")] = None
    contents: Annotated[Optional[str], Field(title="Contents")] = None
    composite_data: Annotated[Optional[List[str]], Field(title="Composite Data")] = None


class ContentsFile(BaseFile):
    """CWL File literal — content inlined as a string."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="ContentsFile")
    contents: Annotated[str, Field(title="Contents")]
    path: Annotated[Optional[str], Field(title="Path")] = None
    location: Annotated[Optional[str], Field(title="Location")] = None
    composite_data: Annotated[Optional[List[str]], Field(title="Composite Data")] = None


class CompositeDataFile(BaseFile):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="CompositeDataFile")
    composite_data: Annotated[List[str], Field(title="Composite Data")]
    path: Annotated[Optional[str], Field(title="Path")] = None
    location: Annotated[Optional[str], Field(title="Location")] = None
    contents: Annotated[Optional[str], Field(title="Contents")] = None


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
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="Collection")
    class_: Literal["Collection"] = Field(alias="class", title="Class")
    collection_type: Annotated[CollectionType, Field(title="Collection Type")] = None
    name: Annotated[Optional[str], Field(title="Name")] = None
    identifier: Annotated[Optional[str], Field(title="Identifier")] = None
    elements: Annotated[Optional[List["CollectionElement"]], Field(title="Elements")] = None
    rows: Annotated[Optional[Dict[str, list]], Field(title="Rows")] = None


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

    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="Directory")
    class_: Literal["Directory"] = Field(alias="class", title="Class")
    path: Annotated[Optional[str], Field(title="Path")] = None
    location: Annotated[Optional[str], Field(title="Location")] = None
    filetype: Annotated[Optional[str], Field(title="File Type")] = None
    name: Annotated[Optional[str], Field(title="Name")] = None


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
    List[Union[File, str, int, float, bool, None]],
]


class Job(RootModel[Dict[str, JobParamValue]]):
    model_config = ConfigDict(title="Job")
