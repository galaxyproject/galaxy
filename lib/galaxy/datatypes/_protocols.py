"""
Location of protocols used in datatypes
"""
from typing import Any

from typing_extensions import Protocol


class HasBlurb(Protocol):
    blurb: str


class HasClearAssociatedFiles(Protocol):
    def clear_associated_files(self, metadata_safe: bool = False, purge: bool = False) -> None:
        ...


class HasCreatingJob(Protocol):
    @property
    def creating_job(self):
        ...


class HasDataset(Protocol):
    dataset: Any


class HasDatatype(Protocol):
    datatype: Any


class HasDbKey(Protocol):
    dbkey: str


class HasExt(Protocol):
    ext: str


class HasExtension(Protocol):
    extension: str


class HasExtraFilesPath(Protocol):
    @property
    def extra_files_path(self):
        ...


class HasFileName(Protocol):
    file_name: Any


class HasGetConvertedFilesByType(Protocol):
    def get_converted_files_by_type(self, file_type):
        ...


class HasGetMime(Protocol):
    def get_mime(self) -> str:
        ...


class HasGetSize(Protocol):
    def get_size(self) -> str:
        ...


class HasHasData(Protocol):
    def has_data(self) -> bool:
        ...


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


class HasPeek(Protocol):
    peek: Any


class HasSetPeek(Protocol):
    def set_peek(self) -> None:
        ...


class HasState(Protocol):
    state: Any


class HasStates(Protocol):
    states: Any


class DatasetProtocol0(Protocol):
    ...


class DatasetProtocol5(HasExt, HasGetConvertedFilesByType, Protocol):
    ...


class GeneratesPrimaryFile(HasExtraFilesPath, HasMetadata, Protocol):
    ...


class Displayable(
    HasCreatingJob,
    HasDataset,
    HasDatatype,
    HasExtension,
    HasExtraFilesPath,
    HasFileName,
    HasGetMime,
    HasHid,
    HasId,
    HasMetadata,
    HasName,
    Protocol,
):
    ...


class SetsMetadata(
    HasBlurb,
    HasDataset,
    HasExtraFilesPath,
    HasFileName,
    HasGetSize,
    HasHasData,
    HasId,
    HasInfo,
    HasMetadata,
    HasName,
    HasPeek,
    Protocol,
):
    ...


class Peekable(
    HasBlurb,
    HasDataset,
    HasExtension,
    HasExtraFilesPath,
    HasFileName,
    HasGetSize,
    HasId,
    HasInfo,
    HasMetadata,
    HasName,
    HasPeek,
    HasSetPeek,
    Protocol,
):
    ...


class ProvidesDataSource(HasDatatype, HasExt, HasFileName, HasMetadata, Protocol):
    # passed to the DatasetDataProvider constructor
    ...


class ProvidesDisplayLinks(
    HasDataset, HasDbKey, HasFileName, HasHasData, HasId, HasMetadata, HasName, HasState, HasStates, Protocol
):
    ...


class Convertable(HasExt, HasHid, Protocol):
    # TODO: this is passed to convert_dataset, from where it is passed on to
    # tools.execute(); so this Protocol is only complete in the context of the
    # datatypes package.
    ...


class Validatable(HasDatatype, HasFileName, HasMetadata, Protocol):
    ...


class Archivable(HasDatatype, HasExtension, HasExtraFilesPath, HasFileName, HasMetadata, Protocol):
    ...
