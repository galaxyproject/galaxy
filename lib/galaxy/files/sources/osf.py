"""Galaxy FileSource implementation for OSF."""

from typing import Union
from abc import ABC

from galaxy import exceptions as galaxy_exceptions
from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util.config_templates import TemplateExpansion

OSF_DEFAULT_URL = "https://api.osf.io/v2/"


class OSFFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    type: str = "osf"
    url: Union[str, TemplateExpansion] = OSF_DEFAULT_URL
    token: Union[str, TemplateExpansion]


class OSFFileSourceConfiguration(BaseFileSourceConfiguration):
    url: str = OSF_DEFAULT_URL
    token: str


class OSFFilesSourceException(ABC, Exception):
    """Abstract base for every exception raised by this plugin."""


class InvalidPath(galaxy_exceptions.MessageException, OSFFilesSourceException):
    """Path is malformed or not absolute."""


class ResourceNotFound(galaxy_exceptions.ObjectNotFound, OSFFilesSourceException):
    """A project, registration, or file does not exist in OSF."""


class DirectoryExpected(galaxy_exceptions.MessageException, OSFFilesSourceException, ValueError):
    """A file path was given where a directory was expected."""


class FileExpected(galaxy_exceptions.MessageException, OSFFilesSourceException, ValueError):
    """A directory path was given where a file was expected."""


class ValidationError(galaxy_exceptions.MessageException, OSFFilesSourceException):
    """OSF returned an unexpected or malformed response."""
