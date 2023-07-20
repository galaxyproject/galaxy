import logging
from typing import (
    cast,
    Optional,
)

from typing_extensions import Unpack

from galaxy.files import ProvidesUserFileSourcesUserContext
from galaxy.files.sources import (
    BaseFilesSource,
    FilesSourceProperties,
)

log = logging.getLogger(__name__)


class RDMFilesSourceProperties(FilesSourceProperties):
    url: str


class RDMFilesSource(BaseFilesSource):
    """Base class for Research Data Management (RDM) file sources.

    This class is not intended to be used directly, but rather to be subclassed
    by file sources that interact with RDM repositories.

    A RDM file source is similar to a regular file source, but instead of tree of
    files and directories, it provides a (one level) list of records (representing directories)
    that can contain only files (no subdirectories).

    In addition, RDM file sources might need to create a new record (directory) in advance in the
    repository, and then upload a file to it. This is done by calling the `create_entry`
    method.

    """

    # This allows to filter out the RDM file sources from the list of available
    # file sources.
    supports_rdm = True

    def __init__(self, **kwd: Unpack[FilesSourceProperties]):
        props = self._parse_common_config_opts(kwd)
        base_url = props.get("url", None)
        if not base_url:
            raise Exception("URL for RDM repository must be provided in configuration")
        self._repository_url = base_url
        self._props = props

    @property
    def repository_url(self) -> str:
        return self._repository_url

    def _serialization_props(
        self, user_context: Optional[ProvidesUserFileSourcesUserContext] = None
    ) -> RDMFilesSourceProperties:
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        effective_props["url"] = self.repository_url
        return cast(RDMFilesSourceProperties, effective_props)
