import logging
from typing import (
    List,
    NamedTuple,
    Optional,
    Tuple,
)

from typing_extensions import Unpack

from galaxy.files import OptionalUserContext
from galaxy.files.sources import (
    BaseFilesSource,
    FilesSourceProperties,
    PluginKind,
    RemoteDirectory,
    RemoteFile,
)

log = logging.getLogger(__name__)


class RDMFilesSourceProperties(FilesSourceProperties):
    token: str
    public_name: str


class ContainerAndFileIdentifier(NamedTuple):
    """The file_identifier could be a filename or a file_id."""
    container_id: str
    file_identifier: str


class RDMRepositoryInteractor:
    """Base class for interacting with an external RDM repository.

    This class is not intended to be used directly, but rather to be subclassed
    by file sources that interact with RDM repositories.

    Different RDM repositories use different terminology. Also they use the same term for different things.
    To prevent confusion, we use the term "container" in the base repository.
    This is an abstract term for the entity that contains multiple files.
    """

    def __init__(self, repository_url: str, plugin: "RDMFilesSource"):
        self._repository_url = repository_url
        self._plugin = plugin

    @property
    def plugin(self) -> "RDMFilesSource":
        """Returns the plugin associated with this repository interactor."""
        return self._plugin

    @property
    def repository_url(self) -> str:
        """Returns the base URL of the repository.

        Example: https://zenodo.org
        """
        return self._repository_url

    def to_plugin_uri(self, container_id: str, filename: Optional[str] = None) -> str:
        """Creates a valid plugin URI to reference the given container_id.

        If a filename is provided, the URI will reference the specific file in the container."""
        raise NotImplementedError()

    def get_file_containers(
        self,
        writeable: bool,
        user_context: OptionalUserContext = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[RemoteDirectory], int]:
        """Returns the list of file containers in the repository and the total count containers.

        If writeable is True, only containers that the user can write to will be returned.
        The user_context might be required to authenticate the user in the repository.
        """
        raise NotImplementedError()

    def get_files_in_container(
        self, container_id: str, writeable: bool, user_context: OptionalUserContext = None
    ) -> List[RemoteFile]:
        """Returns the list of files of a file container.

        If writeable is True, we are signaling that the user intends to write to the container.
        """
        raise NotImplementedError()

    def create_draft_container(

        self, title: str, public_name: Optional[str] = None, user_context: OptionalUserContext = None
    ):
        """Creates a draft container (directory) in the repository with basic metadata.

        The metadata is usually just the title of the container and the user that created it.
        Some plugins might also provide additional metadata defaults in the user settings."""
        raise NotImplementedError()

    def upload_file_to_draft_container(
        self,
        container_id: str,
        filename: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ) -> None:
        """Uploads a file with the provided filename (from file_path) to a draft container with the given container_id.

        The draft container must have been created in advance with the `create_draft_container` method.

        The file must exist in the file system at the given file_path.
        The user_context might be required to authenticate the user in the repository.
        """
        raise NotImplementedError()

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ) -> None:
        """Downloads a file with the provided filename from the container with the given container_id.

        The file will be downloaded to the file system at the given file_path.
        The user_context might be required to authenticate the user in the repository if the
        file is not publicly available.
        """
        raise NotImplementedError()


class RDMFilesSource(BaseFilesSource):
    """Base class for Research Data Management (RDM) file sources.

    This class is not intended to be used directly, but rather to be subclassed
    by file sources that interact with RDM repositories.

    A RDM file source is similar to a regular file source, but instead of tree of
    files and directories, it provides a (one level) list of containers (representing directories)
    that can contain only files (no subdirectories).

    In addition, RDM file sources might need to create a new container (directory) in advance in the
    repository, and then upload a file to it. This is done by calling the `_create_entry` method.
    """

    plugin_kind = PluginKind.rdm

    def __init__(self, **kwd: Unpack[RDMFilesSourceProperties]):
        props = self._parse_common_config_opts(kwd)
        self.url = props.get("url")
        if not self.url:
            raise Exception("URL for RDM repository must be provided in configuration")
        self._props = props
        self._repository_interactor = self.get_repository_interactor(self.url)

    @property
    def repository(self) -> RDMRepositoryInteractor:
        return self._repository_interactor

    def get_url(self) -> Optional[str]:
        return self.url

    def get_repository_interactor(self, repository_url: str) -> RDMRepositoryInteractor:
        """Returns an interactor compatible with the given repository URL.

        This must be implemented by subclasses."""
        raise NotImplementedError()

    def parse_path(self, source_path: str, container_id_only: bool = False) -> ContainerAndFileIdentifier:
        """Parses the given source path and returns the container_id and filename.
        
        If container_id_only is True, an empty filename will be returned.

        This must be implemented by subclasses."""
        raise NotImplementedError()

    def get_container_id_from_path(self, source_path: str) -> str:
        raise NotImplementedError()

    def _serialization_props(self, user_context: OptionalUserContext = None):
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props

    def get_authorization_token(self, user_context: OptionalUserContext) -> Optional[str]:
        token = None
        if user_context:
            effective_props = self._serialization_props(user_context)
            token = effective_props.get("token")
        return token

    def get_public_name(self, user_context: OptionalUserContext) -> Optional[str]:
        effective_props = self._serialization_props(user_context)
        return effective_props.get("public_name")
