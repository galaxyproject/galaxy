"""File source for the histories and data libraries of another Galaxy server.

Backed by ``galaxy-fsspec``, which exposes a Galaxy account as a read-only tree::

    /
    ├── histories/<history>/<dataset>            (file)
    │                      /<collection>/...     (directory; collections nest)
    └── libraries/<library>/<folder>/<dataset>

Path segments are display names, not ids. ``galaxy-fsspec`` replaces a slash inside a Galaxy name
with an underscore and breaks a collision within one listing by appending a short id.

Galaxy already fetches a single dataset from another Galaxy through ``drs://``. This browses, so a
user can find the dataset instead of pasting its id, and it reaches collections and data libraries.

Known limits: the API key is a whole-account credential, entries carry no hashes, and a listing is
fetched whole and paged in memory, so a large history costs one request per page.
"""

import functools
import ipaddress
from typing import cast
from urllib.parse import (
    ParseResult,
    urlparse,
)

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
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
    MAX_ITEMS_LIMIT,
)
from galaxy.files.uris import validate_non_local
from galaxy.util.config_templates import TemplateExpansion
from . import PluginKind

try:
    from galaxy_fsspec.fs import GalaxyFileSystem
except ImportError:
    GalaxyFileSystem = None  # type: ignore[assignment, misc, unused-ignore]

READ_ONLY_MESSAGE = "Galaxy instance file sources are read-only and do not support exporting files."


class Galaxy2GalaxyFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    # Not ``url``: that is a common FilesSourceProperties field, excluded from template expansion
    # and from _serialize_config, so a field by that name would not reach the job.
    base_url: str | TemplateExpansion
    api_key: str | TemplateExpansion
    show_hid_in_names: bool | TemplateExpansion = False


class Galaxy2GalaxyFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str
    api_key: str
    show_hid_in_names: bool = False


class Galaxy2GalaxyFilesSource(
    FsspecFilesSource[Galaxy2GalaxyFileSourceTemplateConfiguration, Galaxy2GalaxyFileSourceConfiguration]
):
    """Browse another Galaxy server's histories and data libraries."""

    plugin_type = "galaxy2galaxy"
    plugin_kind = PluginKind.rfs

    required_module = GalaxyFileSystem
    required_package = "galaxy-fsspec"

    template_config_class = Galaxy2GalaxyFileSourceTemplateConfiguration
    resolved_config_class = Galaxy2GalaxyFileSourceConfiguration

    def __init__(self, template_config: Galaxy2GalaxyFileSourceTemplateConfiguration):
        defaults = dict(
            id="galaxy2galaxy",
            label="Galaxy instance",
            doc="Browse the histories and data libraries of another Galaxy server",
            writable=False,
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        if template_config.writable:
            raise ValueError("Galaxy instance file sources are read-only and cannot be configured as writable.")
        super().__init__(template_config)

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[Galaxy2GalaxyFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> "GalaxyFileSystem":
        # Off the class, so a test redirects the backend by setting ``required_module`` alone.
        filesystem_class = self.required_module
        if filesystem_class is None:
            raise self.required_package_exception

        config = context.config
        url = (config.base_url or "").strip()
        parts = urlparse(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            # Without a protocol the address reaches bioblend as a relative URL, and the error
            # names only the URL, which says nothing about the field to fix.
            raise RequestParameterInvalidException(
                f"'{config.base_url}' is not a usable address for {self.label}. It needs a protocol "
                "and a host, as in 'https://usegalaxy.org'."
            )
        self._refuse_a_private_address(url, parts)

        if not (config.api_key or "").strip():
            raise AuthenticationRequired(
                f"{self.label} has no API key. Browsing another Galaxy always needs one: add the "
                "key from that server's user preferences."
            )

        return filesystem_class(
            url=url,
            api_key=config.api_key,
            show_hid_in_names=config.show_hid_in_names,
            # Without this one request's filesystem is shared with every other using the same key.
            skip_instance_cache=True,
            **cache_options,
        )

    def _refuse_a_private_address(self, url: str, parts: ParseResult) -> None:
        """Refuse an address on the network Galaxy itself sits on.

        ``base_url`` is a user-supplied template variable, so without this a personal file source
        aimed at a loopback or link-local address turns the server into a probe for its own network.

        ``validate_non_local`` cannot be handed the raw URL: it tests the scheme with a
        case-sensitive ``startswith``, so ``HTTP://127.0.0.1`` passes unchecked, and it resolves an
        IPv6 literal with its brackets still on. ``urlparse`` lowercases the host and strips them.
        """
        allowlist = self._file_sources_config.fetch_url_allowlist or []
        host = parts.hostname or ""
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None

        if literal is None:
            try:
                validate_non_local(f"{parts.scheme}://{host}", allowlist)
            except RequestParameterInvalidException:
                # A name that does not resolve. Galaxy cannot reach it either, so the connection
                # error that follows says more than this check would.
                pass
            except ConfigDoesNotAllowException as e:
                raise ConfigDoesNotAllowException(self._private_address_message(url)) from e
            return

        if not literal.is_private:
            return
        for allowlisted in allowlist:
            if isinstance(allowlisted, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                if literal in allowlisted:
                    return
            elif literal == allowlisted:
                return
        raise ConfigDoesNotAllowException(self._private_address_message(url))

    def _private_address_message(self, url: str) -> str:
        return (
            f"{self.label} is configured with '{url}', which is an address on this server's own "
            "network. Galaxy does not fetch from those unless an administrator lists them in "
            "fetch_url_allowlist. List the host itself rather than a whole private range, since "
            "the allowlist applies to every URL Galaxy fetches."
        )

    def _list_recursive(
        self,
        fs: "GalaxyFileSystem",
        path: str,
        config: Galaxy2GalaxyFileSourceConfiguration,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Recurse with failures raised rather than omitted.

        Its own stack rather than ``fs.walk``: walk swallows ``OSError``, and galaxy-fsspec's errors
        subclass it so that a missing entry is skipped. That also hid a real API failure below the
        top level, which returned the remaining folders empty with HTTP 200.
        """
        entries: list[AnyRemoteEntry] = []
        to_entry = functools.partial(self._info_to_entry, config=config)
        pending = [path]
        while pending:
            listing = cast(list[dict], fs.ls(pending.pop(), detail=True))
            entries.extend(map(to_entry, listing))
            if len(entries) >= MAX_ITEMS_LIMIT:
                self._on_listing_exceeded()
                break
            pending.extend(info["name"] for info in listing if info.get("type") == "directory")
        return entries, len(entries)

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[Galaxy2GalaxyFileSourceConfiguration],
    ):
        # The shared _realize_to wraps nothing, so a backend error reaches the API untranslated and
        # is reported as a bare 500 with a traceback. Importing a dataset that is still running is
        # an ordinary thing for a user to try, so it has to say so instead.
        try:
            return super()._realize_to(source_path, native_path, context)
        except MessageException:
            raise
        except FileNotFoundError as e:
            raise ObjectNotFound(f"The specified path does not exist in {self.label} [{source_path}].") from e
        except PermissionError as e:
            raise AuthenticationRequired(
                f"{self.label} refused access to [{source_path}]. Check the API key for this file source."
            ) from e
        except Exception as e:
            # Not OSError: bioblend raises its own ConnectionError for every HTTP failure, and unlike
            # the builtin it shares a name with, it is not an OSError. An expired key would otherwise
            # arrive as a bare 500. The shared _list catches Exception for the same reason.
            raise MessageException(f"Problem reading [{source_path}] from {self.label}. Reason: {e}") from e

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[Galaxy2GalaxyFileSourceConfiguration],
    ):
        raise MessageException(READ_ONLY_MESSAGE)

    def _create_entry(self, entry_data, context):
        raise MessageException(READ_ONLY_MESSAGE)

    def _list(
        self,
        context: FilesSourceRuntimeContext[Galaxy2GalaxyFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ):
        if write_intent:
            raise MessageException(READ_ONLY_MESSAGE)
        try:
            return super()._list(context, path, recursive, write_intent, limit, offset, query, sort_by)
        except MessageException as e:
            # The shared _list opens the filesystem inside its own try and wraps everything that is
            # not a PermissionError, so exceptions raised in _open_fs lose their status on the way
            # out: a refused private address came back as 400 rather than 403. It chains with
            # ``from``, so the original is still on __cause__.
            cause = e.__cause__
            if isinstance(cause, MessageException):
                raise cause
            if isinstance(cause, FileNotFoundError):
                raise ObjectNotFound(f"The specified path does not exist in {self.label} [{path}].") from e
            raise

    def get_url(self) -> str | None:
        """Surface the remote server in the UI, since base_url is not the common ``url`` field."""
        return self.template_config.base_url if isinstance(self.template_config.base_url, str) else None

    def get_scheme(self) -> str:
        return "galaxy2galaxy"


__all__ = ("Galaxy2GalaxyFilesSource",)
