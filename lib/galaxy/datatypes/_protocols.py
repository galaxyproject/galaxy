"""
Location of protocols used in datatypes
"""
from typing import Any

from typing_extensions import Protocol


class HasExtraFilesPathProperty(Protocol):
    @property
    def extra_files_path(self):
        ...


class HasFilesNameProperty(Protocol):
    @property
    def file_name(self):
        ...


class HasId(Protocol):
    id: int


class HasMetadata(Protocol):
    metadata: Any


class HasCreatingJobProperty(Protocol):
    @property
    def creating_job(self):
        ...


class Dataset_t1(HasExtraFilesPathProperty, HasFilesNameProperty, Protocol):
    name: str
    extension: str


class GeneratePrimaryFileDataset(HasExtraFilesPathProperty, HasMetadata, Protocol):
    ...
