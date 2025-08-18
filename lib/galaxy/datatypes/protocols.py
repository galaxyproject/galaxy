"""
Location of protocols used in datatypes
"""

from typing import Any

from typing_extensions import Protocol


class HasClearAssociatedFiles(Protocol):
    def clear_associated_files(self, metadata_safe: bool = False, purge: bool = False) -> None: ...


class HasCreatingJob(Protocol):
    @property
    def creating_job(self): ...


class HasDeleted(Protocol):
    deleted: bool


class HasExt(Protocol):
    @property
    def ext(self): ...


class HasExtraFilesPath(Protocol):
    @property
    def extra_files_path(self) -> str: ...


class HasFileName(Protocol):
    def get_file_name(self, sync_cache=True) -> str: ...


class HasHid(Protocol):
    hid: str


class HasId(Protocol):
    id: int


class HasInfo(Protocol):
    info: str


class HasMetadata(Protocol):
    metadata: Any


class HasName(Protocol):
    name: str


class HasExtraFilesAndMetadata(HasExtraFilesPath, HasMetadata, Protocol): ...


class DatasetProtocol(
    HasCreatingJob,
    HasDeleted,
    HasExt,
    HasExtraFilesPath,
    HasFileName,
    HasId,
    HasInfo,
    HasMetadata,
    HasName,
    Protocol,
):
    blurb: str
    dataset: Any
    dbkey: Any
    extension: str
    peek: Any
    state: Any
    states: Any

    @property
    def datatype(self): ...

    def get_converted_files_by_type(self, file_type): ...

    def get_mime(self) -> str: ...

    def get_size(self) -> int: ...

    def has_data(self) -> bool: ...

    def set_peek(self) -> None: ...

    def attach_implicitly_converted_dataset(self, session, new_dataset, target_ext: str) -> None: ...


class DatasetHasHidProtocol(DatasetProtocol, HasHid, Protocol): ...
