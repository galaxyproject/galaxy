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


class HasPeekProperty(Protocol):
    @property
    def peek(self):
        ...


class HasId(Protocol):
    id: int


class HasMetadata(Protocol):
    metadata: Any


class HasInfo(Protocol):
    info: str


class HasName(Protocol):
    name: str


class HasDataset(Protocol):
    dataset: Any  # TODO tighten


class HasCreatingJobProperty(Protocol):
    @property
    def creating_job(self):
        ...


class HasClearAssociatedFiles(Protocol):
    def clear_associated_files(self, metadata_safe: bool = False, purge: bool = False) -> None:
        ...


class HasDbKey(Protocol):
    dbkey: str


class HasExt(Protocol):
    ext: str  # TODO reconcile: ext vs. extension


class GeneratePrimaryFileDataset(HasExtraFilesPathProperty, HasMetadata, Protocol):
    ...


class Dataset_t1(HasName, HasExtraFilesPathProperty, HasFileNameProperty, Protocol):
    extension: str  # TODO reconcile: ext vs. extension


class Dataset_t2(HasMetadata, HasFileNameProperty, HasExt, Protocol):
    datatype: Any


class Dataset_t3(HasExt, Protocol):
    hid: str


class Dataset_t4(HasName, Protocol):
    hid: str
    extension: str  # TODO reconcile: ext vs. extension


class Dataset_t5(HasFileNameProperty, Dataset_t4, Protocol):
    ...


class Dataset_t6(HasMetadata, HasFileNameProperty, HasExtraFilesPathProperty, Protocol):
    datatype: Any
    extension: str  # TODO reconcile: ext vs. extension


class Dataset_t7(HasDataset, HasName, Protocol):
    ...


class Dataset_t8(HasMetadata, HasId, HasPeekProperty, Protocol):
    def set_peek(self) -> None:
        ...


class Dataset_t9(HasMetadata, HasId, Protocol):
    ...


class Dataset_t10(Dataset_t8, HasFileNameProperty, HasName, Protocol):
    ...


class Dataset_t11(HasFileNameProperty, Protocol):
    def get_size(self) -> str:
        ...


class Dataset_t12(HasDataset, HasMetadata, Protocol):
    state: Any  # TODO tighten (should be property)
    states: Any

    def has_data(self) -> bool:
        ...


class Dataset_t13(Dataset_t12, HasFileNameProperty, HasId, HasMetadata, Protocol):
    ...


class Dataset_t14(Dataset_t13, HasName, HasDbKey, Protocol):
    ...


class Dataset_t15(Dataset_t13, HasDbKey, Protocol):
    ...


class Dataset_t16(HasExt, Protocol):
    def get_converted_files_by_type(self, file_type):
        ...
