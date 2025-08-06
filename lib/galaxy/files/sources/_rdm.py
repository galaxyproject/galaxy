import logging
from typing import (
    Any,
    NamedTuple,
    Optional,
    Union,
)

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources import (
    BaseFilesSource,
    PluginKind,
)
from galaxy.util.config_templates import TemplateExpansion

log = logging.getLogger(__name__)


class RDMFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    token: Union[str, TemplateExpansion]
    public_name: Union[str, TemplateExpansion]


class RDMFileSourceConfiguration(BaseFileSourceConfiguration):
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
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[RemoteDirectory], int]:
        """Returns the list of file containers in the repository and the total count containers.

        If writeable is True, only containers that the user can write to will be returned.
        """
        raise NotImplementedError()

    def get_files_in_container(
        self, container_id: str, writeable: bool, query: Optional[str] = None
    ) -> list[RemoteFile]:
        """Returns the list of files of a file container.

        If writeable is True, we are signaling that the user intends to write to the container.
        """
        raise NotImplementedError()

    def create_draft_file_container(self, title: str, public_name: str) -> dict[str, Any]:
        """Creates a draft file container in the repository with basic metadata.

        The metadata is usually just the title of the container and the user that created it.
        Some plugins might also provide additional metadata defaults in the user settings."""
        raise NotImplementedError()

    def upload_file_to_draft_container(
        self,
        container_id: str,
        filename: str,
        file_path: str,
    ) -> None:
        """Uploads a file with the provided filename (from file_path) to a draft container with the given container_id.

        The draft container must have been created in advance with the `create_draft_file_container` method.

        The file must exist in the file system at the given file_path.
        """
        raise NotImplementedError()

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
    ) -> None:
        """Downloads a file with the provided filename from the container with the given container_id.

        The file will be downloaded to the file system at the given file_path.
        """
        raise NotImplementedError()


class RDMFilesSource(BaseFilesSource[RDMFileSourceTemplateConfiguration, RDMFileSourceConfiguration]):
    """Base class for Research Data Management (RDM) file sources.

    This class is not intended to be used directly, but rather to be subclassed
    by file sources that interact with RDM repositories.

    A RDM file source is similar to a regular file source, but instead of tree of
    files and directories, it provides a (one level) list of containers
    that can contain only files (no subdirectories).

    In addition, RDM file sources might need to create a new container in advance in the
    repository, and then upload a file to it. This is done by calling the `_create_entry` method.
    """

    plugin_kind = PluginKind.rdm

    template_config_class = RDMFileSourceTemplateConfiguration
    resolved_config_class = RDMFileSourceConfiguration

    def __init__(self, template_config: RDMFileSourceTemplateConfiguration):
        super().__init__(template_config)
        if not self.config.url:
            raise Exception("URL for RDM repository must be provided in configuration")
        self._repository_interactor = self.get_repository_interactor(self.config.url)

    @property
    def repository(self) -> RDMRepositoryInteractor:
        return self._repository_interactor

    def get_url(self) -> Optional[str]:
        return self.config.url

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

    def get_authorization_token(self) -> Optional[str]:
        return self.config.token

    def get_public_name(self) -> str:
        return self.config.public_name or "Anonymous Galaxy User"
