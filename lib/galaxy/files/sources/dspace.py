import json
import posixpath
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import (
    Annotated,
    Any,
    Literal,
)
from urllib.parse import urljoin

from pydantic import Field
from urllib3.exceptions import LocationParseError
from urllib3.util import parse_url

from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
    RemoteFileHash,
)
from galaxy.files.uris import validate_non_local
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
    stream_to_path,
)
from galaxy.util.config_templates import TemplateExpansion
from . import BaseFilesSource

PAGE_SIZE = 100
CONTENT_BUNDLE = "ORIGINAL"
MAX_REDIRECTS = 5


class DSpaceFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    api_url: str | TemplateExpansion
    token: str | TemplateExpansion | None = None
    writable: Literal[False] = False


class DSpaceFileSourceConfiguration(BaseFileSourceConfiguration):
    api_url: Annotated[
        str,
        Field(
            title="DSpace REST API URL",
            description="The REST API of a DSpace 7 or newer server, e.g. https://demo.dspace.org/server/api.",
        ),
    ]
    token: Annotated[
        str | None,
        Field(
            title="DSpace token",
            description="Optional bearer token, sent only to the api_url server, for items that are not public.",
        ),
    ] = None
    writable: Literal[False] = False


class DSpaceFilesSource(BaseFilesSource[DSpaceFileSourceTemplateConfiguration, DSpaceFileSourceConfiguration]):
    plugin_type = "dspace"
    supports_pagination = True
    supports_search = True

    template_config_class = DSpaceFileSourceTemplateConfiguration
    resolved_config_class = DSpaceFileSourceConfiguration

    def _list(
        self,
        context: FilesSourceRuntimeContext[DSpaceFileSourceConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if recursive:
            raise MessageException("Recursive listing is not supported for DSpace file sources.")
        config = context.config
        query = query.strip() if query else None
        parts = self._split(path)
        if not parts:
            endpoint = "core/communities/search/top"
            if query:
                # this endpoint has no search, so filter all top communities by name
                communities = self._directories("communities", self._all(config, endpoint, {}, "communities"))
                return self._filter_and_page(communities, limit, offset, query)
            objects, total = self._objects(config, endpoint, {}, "communities", limit, offset)
            return self._directories("communities", objects), total
        if len(parts) == 2 and parts[0] == "communities":
            children = self._directories(
                "communities", self._all(config, f"core/communities/{parts[1]}/subcommunities", {}, "subcommunities")
            ) + self._directories(
                "collections", self._all(config, f"core/communities/{parts[1]}/collections", {}, "collections")
            )
            return self._filter_and_page(children, limit, offset, query)
        if len(parts) == 2 and parts[0] == "collections":
            params = {"dsoType": "ITEM", "scope": parts[1], "sort": "dc.title,ASC"}
            if query:
                # DSpace matches whole words only; a trailing * also finds partial ones, but breaks words like "a-b"
                params["query"] = " ".join(f"{word}*" if re.fullmatch(r"\w+", word) else word for word in query.split())
            items, total = self._objects(config, "discover/search/objects", params, "searchResult", limit, offset)
            return self._directories("items", items), total
        if len(parts) == 2 and parts[0] == "items":
            bitstreams = self._bitstreams(config, parts[1])
            files: list[AnyRemoteEntry] = [self._file(bitstream) for bitstream in bitstreams]
            return self._filter_and_page(files, limit, offset, query)
        raise ObjectNotFound(f"The specified DSpace path is not a directory [{path}].")

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[DSpaceFileSourceConfiguration],
    ) -> None:
        # the file name at the end only names the dataset; the bitstream uuid finds the file
        parts = self._split(source_path, maxsplit=2)
        if len(parts) != 3 or parts[0] != "bitstreams":
            raise ObjectNotFound(f"The specified DSpace path is not a file [{source_path}].")
        config = context.config
        with self._open_url(config, self._url(config.api_url, f"core/bitstreams/{parts[1]}/content")) as response:
            stream_to_path(response, native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[DSpaceFileSourceConfiguration],
    ) -> str | None:
        raise MessageException("DSpace file sources are read-only.")

    def _bitstreams(self, config: DSpaceFileSourceConfiguration, item_id: str) -> list[dict[str, Any]]:
        bundles = self._all(config, f"core/items/{item_id}/bundles", {}, "bundles")
        return [
            bitstream
            for bundle in bundles
            if bundle.get("name") == CONTENT_BUNDLE
            for bitstream in self._all(config, f"core/bundles/{bundle['uuid']}/bitstreams", {}, "bitstreams")
        ]

    def _file(self, bitstream: dict[str, Any]) -> RemoteFile:
        path = f"/bitstreams/{bitstream['uuid']}/{bitstream['name']}"
        checksum = bitstream.get("checkSum") or {}
        hashes = None
        if checksum.get("checkSumAlgorithm") == "MD5" and checksum.get("value"):
            hashes = [RemoteFileHash(hash_function="MD5", hash_value=checksum["value"].lower())]
        return RemoteFile(
            name=bitstream["name"],
            size=bitstream.get("sizeBytes") or 0,
            uri=self.uri_from_path(path),
            path=path,
            hashes=hashes,
        )

    def _directories(self, kind: str, objects: list[dict[str, Any]]) -> list[AnyRemoteEntry]:
        return [
            RemoteDirectory(name=obj.get("name") or obj["uuid"], uri=self.uri_from_path(path), path=path)
            for obj in objects
            for path in [f"/{kind}/{obj['uuid']}"]
        ]

    def _objects(
        self,
        config: DSpaceFileSourceConfiguration,
        endpoint: str,
        params: dict[str, str],
        key: str,
        limit: int | None,
        offset: int | None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List one page of objects from the server."""
        if limit is None:
            # shortcut: unpaged listings (the file set wizards) get the first PAGE_SIZE objects, not a whole
            # collection; page through here if users need more.
            limit = PAGE_SIZE
        # shortcut: DSpace pages by page number, so an offset that is not a multiple of limit is rounded down;
        # fetch two pages and slice if a client ever sends unaligned offsets.
        return self._page(config, endpoint, {**params, "size": str(limit), "page": str((offset or 0) // limit)}, key)

    def _all(
        self, config: DSpaceFileSourceConfiguration, endpoint: str, params: dict[str, str], key: str
    ) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        page = 0
        while True:
            batch, total = self._page(config, endpoint, {**params, "size": str(PAGE_SIZE), "page": str(page)}, key)
            objects.extend(batch)
            page += 1
            if not batch or len(objects) >= total:
                return objects

    def _page(
        self, config: DSpaceFileSourceConfiguration, endpoint: str, params: dict[str, str], key: str
    ) -> tuple[list[dict[str, Any]], int]:
        data = self._get_json(config, self._url(config.api_url, endpoint), params)
        if key == "searchResult":
            data = data.get("_embedded", {}).get("searchResult", {})
            objects = [obj["_embedded"]["indexableObject"] for obj in data.get("_embedded", {}).get("objects", [])]
        else:
            objects = data.get("_embedded", {}).get(key, [])
        return objects, data.get("page", {}).get("totalElements", len(objects))

    def _filter_and_page(
        self, entries: list[AnyRemoteEntry], limit: int | None, offset: int | None, query: str | None
    ) -> tuple[list[AnyRemoteEntry], int]:
        if query:
            entries = [entry for entry in entries if query.lower() in entry.name.lower()]
        start = offset or 0
        return entries[start : start + limit if limit is not None else None], len(entries)

    def _get_json(self, config: DSpaceFileSourceConfiguration, url: str, params: dict[str, str]) -> dict[str, Any]:
        with self._open_url(config, url, params, accept="application/json") as response:
            try:
                data: dict[str, Any] = json.load(response)
                return data
            except ValueError as e:
                raise MessageException(f"{url} did not answer like a DSpace 7 or newer REST API.") from e

    @contextmanager
    def _open_url(
        self,
        config: DSpaceFileSourceConfiguration,
        url: str,
        params: dict[str, str] | None = None,
        accept: str = "application/octet-stream",
    ) -> Iterator[Any]:
        token = (config.token or "").strip()
        try:
            # redirects are followed here, so every address is checked before it is requested
            for _ in range(MAX_REDIRECTS + 1):
                self._refuse_a_private_address(url)
                headers = {"Accept": accept, "User-Agent": "Galaxy DSpace file source"}
                if token and self._origin(url) == self._origin(config.api_url):
                    headers["Authorization"] = f"Bearer {token}"
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    stream=True,
                    timeout=DEFAULT_SOCKET_TIMEOUT,
                    allow_redirects=False,
                )
                if not response.is_redirect:
                    break
                response.close()
                url, params = urljoin(response.url, response.headers["Location"]), None
            else:
                raise MessageException(f"DSpace redirected more than {MAX_REDIRECTS} times [{url}].")
            with response:
                if response.status_code == 404:
                    raise ObjectNotFound(f"DSpace object not found [{response.url}].")
                if response.status_code in (401, 403):
                    hint = "Check the token of" if token else "It is not public, and there is no token in"
                    raise MessageException(f"DSpace refused access to {response.url}. {hint} {self.label}.")
                response.raise_for_status()
                response.raw.decode_content = True
                yield response.raw
        except requests.exceptions.RequestException as e:
            raise MessageException(f"Could not get {url} from DSpace. Reason: {e}") from e

    def _refuse_a_private_address(self, url: str) -> None:
        # parsed as requests parses it; validate_non_local needs a lowercase scheme and a bare IPv6 host
        try:
            parsed = parse_url(url.strip())
        except LocationParseError:
            parsed = None
        if parsed is None or parsed.scheme not in ("http", "https") or not parsed.host:
            raise MessageException(f"{self.label} needs an api_url like https://demo.dspace.org/server/api.")
        host = parsed.host.strip("[]")
        try:
            validate_non_local(f"{parsed.scheme}://{host}", self._file_sources_config.fetch_url_allowlist or [])
        except ConfigDoesNotAllowException as e:
            raise ConfigDoesNotAllowException(
                f"{self.label} points to {host}, an address on this server's own network. An administrator "
                "can allow it by adding its IP address to fetch_url_allowlist, which applies to every URL "
                "Galaxy fetches."
            ) from e
        except RequestParameterInvalidException as e:
            raise MessageException(f"Could not find {host}, the address of {self.label}.") from e

    def _origin(self, url: str) -> tuple[str | None, str | None, int | None]:
        parsed = parse_url(url.strip())
        return parsed.scheme, parsed.host, parsed.port

    def _url(self, api_url: str, endpoint: str) -> str:
        return f"{api_url.rstrip('/')}/{endpoint}"

    def _split(self, path: str, maxsplit: int = -1) -> list[str]:
        path = posixpath.normpath(f"/{path or ''}").strip("/")
        return path.split("/", maxsplit) if path else []


__all__ = ("DSpaceFilesSource",)
