import logging
from typing import (
    Any,
    cast,
    Literal,
    TYPE_CHECKING,
)

from fsspec import AbstractFileSystem
from urllib3.exceptions import LocationParseError
from urllib3.util import parse_url

from galaxy.exceptions import (
    AuthenticationRequired,
    ConfigDoesNotAllowException,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
    RemoteDirectory,
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.files.uris import validate_non_local
from galaxy.util.config_templates import TemplateExpansion

try:
    from nomad_fsspec import NomadFileSystem
except ImportError:
    NomadFileSystem = None  # type: ignore[assignment, misc, unused-ignore]

if TYPE_CHECKING:
    from nomad_fsspec import NomadFileSystem as NomadFileSystemType

log = logging.getLogger(__name__)

DEFAULT_NOMAD_URL = "https://nomad-lab.eu/prod/v1"
# fsspec keeps every listing until it is read again; one instance serves a whole thread
MAX_LISTINGS = 100


class NomadFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    base_url: str | TemplateExpansion = DEFAULT_NOMAD_URL
    token: str | TemplateExpansion | None = None
    writable: Literal[False] = False
    max_paths: int | None = MAX_LISTINGS


class NomadFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str = DEFAULT_NOMAD_URL
    token: str | None = None
    writable: Literal[False] = False
    max_paths: int | None = MAX_LISTINGS


class NomadFilesSource(FsspecFilesSource[NomadFileSourceTemplateConfiguration, NomadFileSourceConfiguration]):
    """Browse NOMAD and import raw files.

    Without a token, the top level lists public datasets, and a dataset lists its uploads by id;
    their names are looked up for the page shown. With a token, the top level lists the user's
    own and shared uploads, published or not.
    """

    plugin_type = "nomad"
    required_module = NomadFileSystem
    required_package = "nomad-fsspec"

    template_config_class = NomadFileSourceTemplateConfiguration
    resolved_config_class = NomadFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[NomadFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if NomadFileSystem is None:
            raise self.required_package_exception
        config = context.config
        self._refuse_a_private_address(config.base_url)
        # the token is part of fsspec's instance key, so users never share listings
        return NomadFileSystem(base_url=config.base_url, token=config.token or None, **cache_options)

    def _refuse_a_private_address(self, base_url: str) -> None:
        # parsed as requests parses it; validate_non_local needs a lowercase scheme and a bare IPv6 host
        try:
            url = parse_url(base_url.strip())
        except LocationParseError:
            url = None
        if url is None or url.scheme not in ("http", "https") or not url.host:
            raise MessageException(f"{self.label} needs a base_url like {DEFAULT_NOMAD_URL}.")
        host = url.host.strip("[]")
        try:
            validate_non_local(f"{url.scheme}://{host}", self._file_sources_config.fetch_url_allowlist or [])
        except ConfigDoesNotAllowException as e:
            raise ConfigDoesNotAllowException(
                f"{self.label} points to {host}, an address on this server's own network. Galaxy only "
                "connects to those if an administrator adds them to fetch_url_allowlist."
            ) from e
        except RequestParameterInvalidException as e:
            raise MessageException(f"Could not find {host}, the address of {self.label}.") from e

    def _list(
        self,
        context: FilesSourceRuntimeContext[NomadFileSourceConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if recursive and not path.strip("/") and not context.config.token:
            raise RequestParameterInvalidException("Recursive listing of all NOMAD datasets is not supported.")
        return super()._list(context, path, recursive, write_intent, limit, offset, query, sort_by)

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[NomadFileSourceConfiguration],
    ) -> None:
        fs = cast("NomadFileSystemType", self._open_fs(context, self._get_cache_options(context.config)))
        folder = RequestParameterInvalidException(f"{source_path} is a folder in NOMAD; select a file inside it.")
        if len([part for part in source_path.split("/") if part]) <= fs.upload_depth:
            raise folder
        try:
            fs.get_file(source_path, native_path)
        except IsADirectoryError as e:
            raise folder from e
        except FileNotFoundError as e:
            raise ObjectNotFound(f"{source_path} was not found in NOMAD.") from e
        except PermissionError as e:
            raise AuthenticationRequired(
                f"NOMAD refused access to {source_path}. "
                f"Please check your credentials in your preferences for {self.label}."
            ) from e

    def _info_to_entry(self, info: dict[str, Any], config: NomadFileSourceConfiguration) -> AnyRemoteEntry:
        entry = super()._info_to_entry(info, config)
        if display_name := info.get("display_name"):
            entry.name = display_name
        return entry

    def _list_with_query(
        self, fs: AbstractFileSystem, path: str, query: str, config: NomadFileSourceConfiguration
    ) -> list[AnyRemoteEntry]:
        # paths are NOMAD ids, so search the names users see instead of globbing paths
        needle = query.strip().casefold()
        entries = self._list_directory(fs, path, config)
        self._name_uploads(fs, entries)
        return [entry for entry in entries if needle in entry.name.casefold()]

    def _enrich_entries(
        self, fs: AbstractFileSystem, entries: list[AnyRemoteEntry], config: NomadFileSourceConfiguration
    ) -> None:
        try:
            self._name_uploads(fs, entries)
        except Exception:
            log.warning("Could not look up the names of NOMAD uploads", exc_info=True)

    def _name_uploads(self, fs: AbstractFileSystem, entries: list[AnyRemoteEntry]) -> None:
        nomad = cast("NomadFileSystemType", fs)
        if nomad.upload_depth != 2:
            return
        uploads = {
            entry.path.rsplit("/", 1)[-1]: entry
            for entry in entries
            if isinstance(entry, RemoteDirectory) and entry.path.count("/") == 2
        }
        for upload_id, name in nomad.upload_names(uploads).items():
            uploads[upload_id].name = name

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[NomadFileSourceConfiguration],
    ) -> str | None:
        raise MessageException("NOMAD file sources are read-only.")


__all__ = ("NomadFilesSource",)
