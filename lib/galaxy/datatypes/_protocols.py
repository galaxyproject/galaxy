"""
Location of protocols used in datatypes
"""
from typing import Any

from typing_extensions import Protocol


class HasExtraFilesPathProperty(Protocol):
    @property
    def extra_files_path(self):
        ...


class HasFileNameProperty(Protocol):
    @property
    def file_name(self):
        ...


class HasId(Protocol):
    id: int


class HasMetadata(Protocol):
    metadata: Any


class HasInfo(Protocol):
    info: str


class HasCreatingJobProperty(Protocol):
    @property
    def creating_job(self):
        ...


class HasClearAssociatedFiles(Protocol):
    def clear_associated_files(self, metadata_safe: bool = False, purge: bool = False) -> None:
        ...


class GeneratePrimaryFileDataset(HasExtraFilesPathProperty, HasMetadata, Protocol):
    ...


class Dataset_t1(HasExtraFilesPathProperty, HasFileNameProperty, Protocol):
    name: str
    extension: str  # TODO reconcile: ext vs. extension


class Dataset_t2(HasMetadata, HasFileNameProperty, Protocol):
    datatype: Any
    ext: str  # TODO reconcile: ext vs. extension


class Dataset_t3(Protocol):
    hid: str
    ext: str  # TODO reconcile: ext vs. extension


class Dataset_t4(Protocol):
    hid: str
    name: str
    extension: str  # TODO reconcile: ext vs. extension


class Dataset_t5(HasFileNameProperty, Dataset_t4, Protocol):
    ...
