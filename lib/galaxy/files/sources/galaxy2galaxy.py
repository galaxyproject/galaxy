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

Known limits: the API key is a whole-account credential, entries carry no dates or hashes, and
library files are listed with a size of 0.
"""

import ipaddress
from typing import Literal
from urllib.parse import (
    ParseResult,
    urlparse,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    ConfigDoesNotAllowException,
    MessageException,
    RequestParameterInvalidException,
)
from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.files.uris import validate_non_local
from galaxy.util.config_templates import TemplateExpansion
from . import PluginKind

try:
    from galaxy_fsspec.fs import GalaxyFileSystem
except ImportError:
    GalaxyFileSystem = None  # type: ignore[assignment, misc, unused-ignore]


class Galaxy2GalaxyFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    # Not ``url``: that is a common FilesSourceProperties field, excluded from template expansion
    # and from _serialize_config, so a field by that name would not reach the job.
    base_url: str | TemplateExpansion
    api_key: str | TemplateExpansion
    show_hid_in_names: bool | TemplateExpansion = False
    writable: Literal[False] = False


class Galaxy2GalaxyFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str
    api_key: str
    show_hid_in_names: bool = False
    writable: Literal[False] = False


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

    # galaxy-fsspec fetches a listing whole, so the client pages and filters it instead.
    supports_pagination = False
    supports_search = False

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[Galaxy2GalaxyFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> "GalaxyFileSystem":
        config = context.config
        url = (config.base_url or "").strip().rstrip("/")
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

        return GalaxyFileSystem(
            url=url,
            api_key=config.api_key,
            show_hid_in_names=config.show_hid_in_names,
            # Without this one request's filesystem is shared with every other using the same key.
            skip_instance_cache=True,
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

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[Galaxy2GalaxyFileSourceConfiguration],
    ) -> None:
        raise MessageException("Galaxy instance file sources are read-only and do not support exporting files.")

    def get_scheme(self) -> str:
        # A source a user creates from the template is given gxuserfiles, and its URIs use that.
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else "galaxy2galaxy"


__all__ = ("Galaxy2GalaxyFilesSource",)
