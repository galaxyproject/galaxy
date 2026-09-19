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
    Annotated,
    Literal,
)

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    RootModel,
    Tag,
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
    filetype: Annotated[str | None, Field(title="File Type")] = None
    dbkey: Annotated[str | None, Field(title="Dbkey")] = None
    decompress: Annotated[bool | None, Field(title="Decompress")] = None
    to_posix_lines: Annotated[bool | None, Field(title="To POSIX Lines")] = None
    space_to_tab: Annotated[bool | None, Field(title="Space To Tab")] = None
    deferred: Annotated[bool | None, Field(title="Deferred")] = None
    name: Annotated[str | None, Field(title="Name")] = None
    info: Annotated[str | None, Field(title="Info")] = None
    tags: Annotated[list[str] | None, Field(title="Tags")] = None
    hashes: Annotated[list[HashEntry] | None, Field(title="Hashes")] = None
    identifier: Annotated[str | None, Field(title="Identifier")] = None


class LocationFile(BaseFile):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="LocationFile")
    location: Annotated[str, Field(title="Location")]
    path: Annotated[str | None, Field(title="Path")] = None
    contents: Annotated[str | None, Field(title="Contents")] = None
    composite_data: Annotated[list[str] | None, Field(title="Composite Data")] = None


class PathFile(BaseFile):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="PathFile")
    path: Annotated[str, Field(title="Path")]
    location: Annotated[str | None, Field(title="Location")] = None
    contents: Annotated[str | None, Field(title="Contents")] = None
    composite_data: Annotated[list[str] | None, Field(title="Composite Data")] = None


class ContentsFile(BaseFile):
    """CWL File literal — content inlined as a string."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="ContentsFile")
    contents: Annotated[str, Field(title="Contents")]
    path: Annotated[str | None, Field(title="Path")] = None
    location: Annotated[str | None, Field(title="Location")] = None
    composite_data: Annotated[list[str] | None, Field(title="Composite Data")] = None


class CompositeDataFile(BaseFile):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="CompositeDataFile")
    composite_data: Annotated[list[str], Field(title="Composite Data")]
    path: Annotated[str | None, Field(title="Path")] = None
    location: Annotated[str | None, Field(title="Location")] = None
    contents: Annotated[str | None, Field(title="Contents")] = None


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
    Annotated[LocationFile, Tag("location")]
    | Annotated[PathFile, Tag("path")]
    | Annotated[ContentsFile, Tag("contents")]
    | Annotated[CompositeDataFile, Tag("composite_data")],
    Discriminator(_discriminate_file),
]


class Collection(_StrictJobModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, title="Collection")
    class_: Literal["Collection"] = Field(alias="class", title="Class")
    collection_type: Annotated[CollectionType, Field(title="Collection Type")] = None
    name: Annotated[str | None, Field(title="Name")] = None
    identifier: Annotated[str | None, Field(title="Identifier")] = None
    elements: Annotated[list["CollectionElement"] | None, Field(title="Elements")] = None
    rows: Annotated[dict[str, list] | None, Field(title="Rows")] = None


CollectionElement = Annotated[
    File | Collection,
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
    path: Annotated[str | None, Field(title="Path")] = None
    location: Annotated[str | None, Field(title="Location")] = None
    filetype: Annotated[str | None, Field(title="File Type")] = None
    name: Annotated[str | None, Field(title="Name")] = None


# JobParamValue is non-recursive at the list axis: a job-param list may contain
# files or scalars but not further nested lists. Collection nesting (lists of
# collections) is recursive via ``CollectionElement``. No observed workflow
# test value needs a list-of-lists at the job-input level; widen explicitly if
# that changes rather than defaulting to Any.
JobParamValue = (
    File | Collection | Directory | str | int | float | bool | None | list[File | str | int | float | bool | None]
)


class Job(RootModel[dict[str, JobParamValue]]):
    model_config = ConfigDict(title="Job")
