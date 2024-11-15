"""
Galaxy FilesSource implementation for eLabFTW.

This module implements a FilesSource that interacts with an eLabFTW [1] instance. eLabFTW revolves around the concepts
of *experiment* [2] and *resource* [3]. Experiments and resources can have files attached to them. To get a quick
overview, try out the live demo [4]. The scope of this implementation is exporting data from and importing data to
eLabFTW as file attachments of *already existing* experiments and resources. Each user can configure their preferred
eLabFTW instance entering its URL and an API Key.

File sources reference files via a URI, while eLabFTW uses auto-incrementing positive integers. For more details read
galaxyproject/galaxy#18665 [5]. This leads to the need to declare a mapping between said identifiers and Galaxy URIs.

Those take the form ``elabftw://demo.elabftw.net/entity_type/entity_id/attachment_id``, where:
- ``entity_type`` is either 'experiments' or 'resources'
- ``entity_id`` is the id (an integer in string form) of an experiment or resource
- ``attachment_id`` is the id (an integer in string form) of an attachment

This implementation uses both ``aiohttp`` and the ``requests`` libraries as underlying mechanisms to communicate with
eLabFTW via its REST API [6]. A significant limitation of the implementation is that, due to the fact that the API does
not have an endpoint that can list attachments for several experiments and/or resources with a single request, when
listing the root directory or an entity type *recursively*, a list of entities has to be fetched first, then to fetch
the information on their attachments, a separate request has to be sent *for each one* of them. The ``aiohttp`` library
makes it bearable to recursively browse instances with up to ~500 experiments or resources with attachments by sending
them concurrently, but ultimately solving the problem would require changes to the API from the eLabFTW side.

References:
- [1] https://www.elabftw.net/
- [2] https://doc.elabftw.net/user-guide.html#experiments
- [3] https://doc.elabftw.net/user-guide.html#resources
- [4] https://demo.elabftw.net
- [5] https://github.com/galaxyproject/galaxy/issues/18665
- [6] https://doc.elabftw.net/api/v2
"""

import asyncio
import logging
import re
from abc import ABC
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from textwrap import dedent
from time import time
from typing import (
    AsyncIterator,
    cast,
    Dict,
    Generic,
    get_type_hints,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
)
from urllib.parse import (
    ParseResult,
    urljoin,
    urlparse,
)

import aiohttp
from requests import Session as RequestsSession
from typing_extensions import (
    NotRequired,
    TypedDict,
    Unpack,
)

from galaxy import exceptions as galaxy_exceptions
from galaxy.files import OptionalUserContext
from galaxy.files.sources import (
    AnyRemoteEntry,
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
    PluginKind,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.util import requests

__all__ = ("eLabFTWFilesSource",)

MAX_CONCURRENT_REQUESTS: int = 75  # max concurrent requests to eLabFTW (e.g. recursively listing a directory)
MAX_ITEMS_PER_PAGE: int = 1000  # max items per page when requesting experiments or resources
CONNECT_TIMEOUT: int = 10  # time out connections to eLabFTW after this number of seconds
READ_TIMEOUT: int = 10  # time out waiting for responses from eLabFTW after this number of seconds
PAGINATION_TIMEOUT: int = 30  # stop processing paginated responses after this number of seconds


eLabFTWRemoteEntryWrapperType = TypeVar("eLabFTWRemoteEntryWrapperType", bound=AnyRemoteEntry)


class eLabFTWRemoteEntryWrapper(Generic[eLabFTWRemoteEntryWrapperType]):  # noqa
    """
    Wrap a remote entry produced by this module to easily access its entity type, entity id, and attachment id.
    """

    def __init__(self, entry: eLabFTWRemoteEntryWrapperType, source: Optional[dict] = None):
        """
        Initialize the remote entry wrapper.

        :param entry: Remote entry to be wrapped.
        :type entry: eLabFTWRemoteEntryWrapperType
        :param source: Information used to construct the remote entry.
        :type source: Optional[dict]
        """
        self.entry = entry
        self.source = source

    @property
    def entity_type(self) -> Optional[str]:
        """
        Get the entity type for the wrapped entry.
        """
        return self._get_part("entity_type")

    @property
    def entity_id(self) -> Optional[str]:
        """
        Get the entity id for the wrapped entry.
        """
        return self._get_part("entity_id")

    @property
    def attachment_id(self) -> Optional[str]:
        """
        Get the attachment id for the wrapped entry.
        """
        return self._get_part("attachment_id")

    def _get_part(self, part: Literal["entity_type", "entity_id", "attachment_id"]) -> Optional[str]:
        """
        Get the entity type, entity id or attachment id for the wrapped entry.
        """
        path = self.entry["path"]
        entity_type, entity_id, attachment_id = split_path(path)
        return locals()[part]


class eLabFTWFilesSourceProperties(FilesSourceProperties, total=False):  # noqa
    endpoint: str
    api_key: str


class eLabFTWFilesSource(BaseFilesSource):  # noqa

    plugin_type = "elabftw"
    plugin_kind = PluginKind.rfs
    supports_pagination = True
    supports_search = True
    supports_sorting = True

    def __init__(self, *args, **kwargs: Unpack[eLabFTWFilesSourceProperties]):
        """Initialize the eLabFTW files source with an API key and an endpoint URL."""
        super().__init__()
        props = self._parse_common_config_opts(kwargs)
        self._props = props

        self._endpoint = kwargs["endpoint"]  # meant to be accessed only from `_get_endpoint()`
        self._api_key = kwargs["api_key"]  # meant to be accessed only from `_create_session()`

    def get_prefix(self) -> Optional[str]:
        return None

    def get_scheme(self) -> str:
        return "elabftw"

    def get_uri_root(self) -> str:
        return super().get_uri_root()

    def to_relative_path(self, url: str) -> str:
        parsed_url = urlparse(url)
        path = parsed_url.path
        if not path.startswith("/"):
            path = f"/{path}"
        return path

    def _create_session(
        self,
        options: Optional[FilesSourceOptions] = None,
        user_context: OptionalUserContext = None,
    ) -> RequestsSession:
        """
        Create a Galaxy ``requests`` session, overriding initial settings via a :class:`FileSourceOptions` object.
        """
        return requests.Session(
            headers=self._get_session_headers(options=options, user_context=user_context),  # type: ignore[call-arg]
        )

    def _create_session_async(
        self,
        options: Optional[FilesSourceOptions] = None,
        user_context: OptionalUserContext = None,
    ) -> aiohttp.ClientSession:
        """
        Create an ``aiohttp`` session, overriding initial settings via a :class:`FileSourceOptions` object.
        """
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
        return aiohttp.ClientSession(
            connector=connector,
            raise_for_status=True,
            headers=self._get_session_headers(options=options, user_context=user_context),
        )

    def _get_session_headers(
        self,
        options: Optional[FilesSourceOptions] = None,
        user_context: OptionalUserContext = None,
    ) -> dict:
        """
        Construct a dictionary of HTTP client session headers.

        Optionally, override initial settings via a :class:`FileSourceOptions` object and/or a
        :class:`FileSourcesUserContext` object.

        Meant to be used only by `_create_session()` and `_create_session_async()`.
        """
        props = dict(
            **(options.extra_props if options and options.extra_props else {}),
            **self._serialization_props(user_context),
        )
        headers = {
            "Authorization": props.get("api_key", self._api_key),
            "Accept": "application/json",
        }
        return headers

    def _get_endpoint(
        self,
        options: Optional[FilesSourceOptions] = None,
        user_context: OptionalUserContext = None,
    ) -> ParseResult:
        """
        Retrieve the endpoint from the constructor, or override it via a :class:`FileSourceOptions` object.
        """
        props = dict(
            **(options.extra_props if options and options.extra_props else {}),
            **self._serialization_props(user_context),
        )
        endpoint = props.get("endpoint", self._endpoint)
        # given that `options.extra_props` is of `eLabFTWFilesSourceProperties` type, it should be a string
        endpoint = cast(str, endpoint)

        return urlparse(endpoint)

    def _serialization_props(self, user_context: OptionalUserContext = None) -> eLabFTWFilesSourceProperties:
        effective_props = {}

        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)

        return cast(eLabFTWFilesSourceProperties, effective_props)

    async def _list(
        self,
        path="/",
        recursive=False,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
        # in particular, expecting
        # `sort_by: Optional[Literal["name", "uri", "path", "class", "size", "ctime"]] = None,`
        # from Python 3.9 on, the following would be possible, although barely readable
        # `sort_by: Optional[Literal[*(get_type_hints(RemoteDirectory) | get_type_hints(RemoteFile)).keys()]] = None,`
    ) -> Tuple[List[AnyRemoteEntry], int]:
        """
        List remote entries in a remote directory.

        List entity types ("experiment" and "resource"), entity ids of a specific type, or the ids of files attached to
        an entity.

        :param path: Path referring to the root, an entity type, or an entity id.
        :type path: str
        :param recursive: List recursively, including all entity types for the root, all entities for each entity type
                          and all attachments for each entity.
        :type recursive: bool
        :param user_context: Alter behavior using information from a user context (e.g. override the API key).
        :type user_context: OptionalUserContext
        :param opts: Alter behavior using information from a file source options object (e.g. ignore locked resources).
        :type opts: Optional[FilesSourceOptions]
        :param limit: Show at most this amount of results, defaults to unlimited.
        :type limit: Optional[int]
        :param offset: Filter out this amount of results from the beginning of the sequence, defaults to zero.
        :type offset: Optional[int]
        :param query: Show only results that contain this string.
        :type query: Optional[int]
        :param sort_by: Sort results by name, URI, path, class (directory or file), size (files only) or creation time
                        (files only).
        :type sort_by: Optional[str]

        :raises aiohttp.ClientError: When there is a connection error.
        :raises ValidationError: If any HTTP response from the eLabFTW server is invalid.
        :raises DirectoryExpected: If the path refers to an attachment id.
        :raises InvalidPath: Path constraints described in the docstring of :class:`InvalidPath` are not satisfied.
        :raises ResourceNotFound: If the path refers to a non-existing experiment, resource, or attachment.
        """
        session = self._create_session_async(options=opts, user_context=user_context)
        endpoint = self._get_endpoint(options=opts, user_context=user_context)

        entity_type, entity_id, attachment_id = split_path(path)

        async with session:
            retrieve_entity_types: bool = not entity_type
            retrieve_entities: bool = bool((entity_type and not entity_id) or (not entity_id and recursive))
            retrieve_entities_server_side_offset = offset if retrieve_entities and not recursive else None
            retrieve_attachments: bool = bool((entity_type and entity_id) or (not attachment_id and recursive))

            async def regular_iterable_to_async_iterator(regular_iter: Iterable) -> AsyncIterator:
                """
                Convert a regular iterable to an async iterator.
                """
                for item in regular_iter:
                    yield item

            async def collect_async_iterator(async_iter: AsyncIterator) -> list:
                """
                Collect values of an async iterator into a list.
                """
                return [value async for value in async_iter]

            fetch_entity_types_tasks: List[asyncio.Task] = (
                # fmt: off
                [
                    asyncio.create_task(
                        collect_async_iterator(
                            self._yield_entity_types(
                                endpoint,
                                session,
                            )
                        )
                    )
                ]
                # fmt: on
                if retrieve_entity_types
                else []
            )
            fetch_entities_tasks: List[asyncio.Task] = (
                [
                    asyncio.create_task(
                        collect_async_iterator(
                            self._yield_entities(
                                (
                                    # both `wrapped_entity_type.entity_type` and `entity_type` should not be `None` if
                                    # they are used
                                    cast(str, wrapped_entity_type.entity_type)
                                    if retrieve_entity_types
                                    else cast(str, entity_type)
                                ),
                                endpoint,
                                session,
                                limit=(
                                    limit
                                    if not (recursive and (sort_by in {"name", "class", "size", "ctime"} or query))
                                    else None
                                ),
                                offset=retrieve_entities_server_side_offset,
                                query=query if not recursive else None,
                                order=(
                                    # map Galaxy `sort_by` parameter to an eLabFTW API query param
                                    {
                                        "name": "title",
                                        "uri": "id",
                                        "path": "id",
                                    }.get(sort_by)
                                    if isinstance(sort_by, str)
                                    else None
                                ),
                                writable=self.writable,
                            )
                        )
                    )
                    async for wrapped_entity_type in (
                        (
                            wrapped_entity_type
                            for coroutine in asyncio.as_completed(fetch_entity_types_tasks)
                            for wrapped_entity_type in (await coroutine)
                        )
                        if retrieve_entity_types
                        else regular_iterable_to_async_iterator([None])
                    )
                ]
                if retrieve_entities
                else []
            )
            fetch_attachments_tasks: List[asyncio.Task] = (
                # fetching attachments is "bearable" for the user up to ~500 experiments + resources with attachments;
                # if eLabFTW allowed listing attachments without having to send individual requests for each experiment
                # or resource, this would not be a concern
                [
                    asyncio.create_task(
                        collect_async_iterator(
                            self._yield_attachments(
                                # all of `wrapped_entity_type.entity_type`, `wrapped_entity_type.entity_id`,
                                # `entity_type` and `entity_id` should not be `None` if they are used
                                cast(str, wrapped_entity.entity_type) if retrieve_entities else cast(str, entity_type),
                                cast(str, wrapped_entity.entity_id) if retrieve_entities else cast(str, entity_id),
                                endpoint,
                                session,
                            )
                        )
                    )
                    async for wrapped_entity in (
                        (
                            wrapped_entity
                            for coroutine in asyncio.as_completed(fetch_entities_tasks)
                            for wrapped_entity in (await coroutine)
                            if wrapped_entity.source["has_attachment"]
                        )
                        if retrieve_entities
                        else regular_iterable_to_async_iterator([None])
                    )
                ]
                if retrieve_attachments
                else []
            )

            wrapped_entity_types: List[eLabFTWRemoteEntryWrapper[RemoteDirectory]] = [
                wrapped_entity_type
                for wrapped_entity_types in await asyncio.gather(*fetch_entity_types_tasks)
                for wrapped_entity_type in wrapped_entity_types
            ]
            wrapped_entities: List[eLabFTWRemoteEntryWrapper[RemoteDirectory]] = [
                wrapped_entity
                for wrapped_entities in await asyncio.gather(*fetch_entities_tasks)
                for wrapped_entity in wrapped_entities
            ]
            wrapped_attachments: List[eLabFTWRemoteEntryWrapper[RemoteFile]] = [
                wrapped_attachment
                for wrapped_attachments in await asyncio.gather(*fetch_attachments_tasks)
                for wrapped_attachment in wrapped_attachments
            ]

        if attachment_id:
            attachment_ids = {
                wrapped_attachment.source["id"]
                for wrapped_attachment in wrapped_attachments
                if not isinstance(wrapped_attachment.source, type(None))
            }
            if attachment_id in attachment_ids:
                raise DirectoryExpected(err_msg=f"'{path}' is a file, it cannot be listed")
            else:
                raise ResourceNotFound(err_msg=f"'{path} does not exist")

        wrapped_entries = wrapped_entity_types + wrapped_entities + wrapped_attachments

        # results arrive from the server in nondeterministic order; even if `sort_by` is `None`, calling `_list` twice
        # with the same arguments should return the same results in the same order (otherwise the option `offset` makes
        # no sense).
        constructors = {**get_type_hints(RemoteDirectory), **get_type_hints(RemoteFile)}
        wrapped_entries = sorted(
            wrapped_entries,
            key=lambda x: (
                (
                    x.entry.get(sort_by, constructors[sort_by]())  # fall back to the default object for this key type
                    if sort_by is not None else None  # fmt: skip
                ),
                x.entry["uri"],  # ensure deterministic ordering (URIs are unique)
            ),
        )

        # filter out remaining items locally; by `query`, `offset` and `limit`
        if query is not None:
            wrapped_entries = [
                wrapped_entry for wrapped_entry in wrapped_entries if query in wrapped_entry.entry.get("name", "")
            ]
        if offset is not None:
            wrapped_entries = wrapped_entries[offset - (retrieve_entities_server_side_offset or 0) :]
        if limit is not None:
            wrapped_entries = wrapped_entries[:limit]

        return (entries := [wrapped_entry.entry for wrapped_entry in wrapped_entries]), len(entries)

    @staticmethod
    async def _yield_entity_types(
        endpoint: ParseResult, session: aiohttp.ClientSession
    ) -> AsyncIterator[eLabFTWRemoteEntryWrapper[RemoteDirectory]]:
        """
        List the root directory, i.e. "/".
        """
        # actually, the server does not need to be contacted to list entity types, but it makes sense to check
        # that it is alive and an actual eLabFTW instance is running to avoid giving the false impression that
        # things are working smoothly
        url = f"{endpoint.scheme}://{endpoint.netloc}/api/v2/info"
        async with session.get(
            url,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(sock_connect=CONNECT_TIMEOUT, sock_read=READ_TIMEOUT),
        ) as response:
            try:
                is_valid = all(
                    (
                        response.status == 200,
                        content := await response.json(),
                        content.get("elabftw_version"),
                    )
                )
            except aiohttp.ContentTypeError:
                is_valid = False
            if not is_valid:
                raise ValidationError(err_msg="Invalid response from eLabFTW")

        experiments = eLabFTWRemoteEntryWrapper(
            RemoteDirectory(
                **{
                    "name": "Experiments",
                    "uri": f"elabftw://{endpoint.netloc}/experiments",
                    "path": "/experiments",
                    "class": "Directory",
                }
            )
        )
        resources = eLabFTWRemoteEntryWrapper(
            RemoteDirectory(
                **{
                    "name": "Resources",
                    "uri": f"elabftw://{endpoint.netloc}/resources",
                    "path": "/resources",
                    "class": "Directory",
                }
            )
        )

        yield experiments
        yield resources

    @staticmethod
    async def _yield_entities(
        entity_type: str,
        endpoint: ParseResult,
        session: aiohttp.ClientSession,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        order: Optional[str] = None,
        writable: bool = False,
    ) -> AsyncIterator[eLabFTWRemoteEntryWrapper[RemoteDirectory]]:
        """List an entity type, i.e. either "/experiments" or "/resources"."""
        url = urljoin(
            f"{endpoint.scheme}://{endpoint.netloc}/",
            f"/api/v2/{entity_type.replace('resources', 'items')}",
        )

        class Params(TypedDict):
            order: str
            sort: str
            limit: int
            offset: int
            extended: NotRequired[str]
            q: NotRequired[str]

        params: Params = {
            "order": order or "id",
            "sort": "asc",
            "limit": min(MAX_ITEMS_PER_PAGE, limit) if limit is not None else MAX_ITEMS_PER_PAGE,
            "offset": offset or 0,
        }
        if writable:
            params.update({"extended": "locked:0"})
            # improvement: is there is a way to request only entities the user has permission to write to?
        if query:
            params.update({"q": query})

        content: List[dict] = [{}] * params["limit"]  # stores JSON responses (entities) from the server
        start, timeout = time(), False
        while len(content) >= params["limit"] and not (timeout := ((time() - start) >= PAGINATION_TIMEOUT)):
            entities: Dict[int, dict] = {}

            async with session.get(
                url,
                params={key: str(value) for key, value in params.items()},
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(sock_connect=CONNECT_TIMEOUT, sock_read=READ_TIMEOUT),
            ) as response:
                try:
                    status: int = response.status
                    content = await response.json()

                    def validate_and_register_entity(item, mapping: Dict[int, dict]) -> Literal[True]:
                        valid = isinstance(item, dict) and isinstance(item.get("id"), int)
                        if not valid:
                            raise ValidationError(err_msg="Invalid response from eLabFTW")
                        mapping[item["id"]] = item
                        return True

                    is_valid = all(
                        (
                            status == 200,
                            isinstance(content, list),
                            all(validate_and_register_entity(item, entities) for item in content),
                        )
                    )
                except aiohttp.ContentTypeError:
                    is_valid = False
                if not is_valid:
                    raise ValidationError(err_msg="Invalid response from eLabFTW")

            for entity in entities.values():
                yield eLabFTWRemoteEntryWrapper(
                    RemoteDirectory(
                        **{
                            "name": entity["title"],
                            "uri": f"elabftw://{endpoint.netloc}/{entity_type}/{entity['id']}",
                            "path": f"/{entity_type}/{entity['id']}",
                            "class": "Directory",
                        }
                    ),
                    entity,
                )

            params["offset"] += params["limit"]

        if timeout:
            raise aiohttp.ServerTimeoutError

    @staticmethod
    async def _yield_attachments(
        entity_type: str,
        entity_id: str,
        endpoint: ParseResult,
        session: aiohttp.ClientSession,
    ) -> AsyncIterator[eLabFTWRemoteEntryWrapper[RemoteFile]]:
        """List attachments of a specific entity, e.g. "/resources/48"."""
        url = urljoin(
            f"{endpoint.scheme}://{endpoint.netloc}/",
            f"/api/v2/{entity_type.replace('resources', 'items')}/{entity_id}",
        )
        try:
            async with session.get(
                url,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(sock_connect=CONNECT_TIMEOUT, sock_read=READ_TIMEOUT),
            ) as response:
                try:
                    response_json = await response.json()
                    is_valid = True
                except aiohttp.ContentTypeError:
                    is_valid = False
                if not is_valid:
                    raise ValidationError(err_msg="Invalid response from eLabFTW")

            uploads = {upload["id"]: upload for upload in response_json.get("uploads", [])}
        except aiohttp.ClientResponseError as exception:
            if exception.status == 403:
                # cannot fetch items owned by someone else from the API but can do it from the browser, why?
                logging.exception(exception)
                uploads = {}
            else:
                raise exception

        for upload in uploads.values():
            yield eLabFTWRemoteEntryWrapper(
                RemoteFile(
                    **{
                        "name": upload["real_name"],
                        "uri": f"elabftw://{endpoint.netloc}/{entity_type}/{entity_id}/{upload['id']}",
                        "path": f"/{entity_type}/{entity_id}/{upload['id']}",
                        "class": "File",
                        "size": upload["filesize"],
                        "ctime": datetime.fromisoformat(upload["created_at"]).astimezone(timezone.utc).isoformat(),
                    }
                ),
                upload,
            )

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> str:
        """
        Attach the file located at ``native_path`` on the filesystem to an eLabFTW resource or experiment with URI
        ``target_path``.

        :param target_path: URI of the experiment or resource that the file will be attached to, followed by the name it
            will be assigned; e.g.``elabftw://demo.elabftw.net/experiments/269/name``
        :type target_path: str
        :param native_path: The local file to upload, e.g. ``/tmp/myfile.txt``
        :type native_path: str
        :param user_context: A user context, defaults to ``None``
        :type user_context: OptionalUserContext
        :param opts: A set of options to exercise additional control over this method. Defaults to ``None``
        :type opts: Optional[FilesSourceOptions], optional
        :return: URI *assigned by eLabFTW* to the uploaded file.
        :rtype: str

        :raises requests.RequestException: When there is a connection error.
        :raises ValidationError: If the HTTP response from the eLabFTW server is invalid.
        :raises InvalidPath: After splitting `target_path` into the URI of the experiment or resource that the file will
                             be attached to and the name it will be assigned, the former is validated normally, and thus
                             this exception will be raised if the path constraints described in the docstring of
                             :class:`InvalidPath` are not satisfied. In addition, it will also be raised if the latter
                             is not a name but rather a relative path, meaning that `target_path` consists of more than
                             three components.
        :raises EntityExpected: When attempting to attach the file to the root "/" or an entity type.
        """
        session = self._create_session(options=opts, user_context=user_context)
        endpoint = self._get_endpoint(options=opts, user_context=user_context)

        target_path_obj = Path(target_path)
        attachment_name = target_path_obj.name
        try:
            entity_type, entity_id, attachment_id = split_path(str(target_path_obj.parent))
        finally:
            if len(target_path_obj.parts[1:]) > 3:
                raise InvalidPath(err_msg=InvalidPath.message_path_form % target_path_obj)
        if not all((entity_type, entity_id)):
            raise EntityExpected(err_msg="Expected an entity (an experiment or resource)")
        entity_type, entity_id = cast(str, entity_type), cast(str, entity_id)

        url = urljoin(
            f"{endpoint.scheme}://{endpoint.netloc}/",
            f"/api/v2/{entity_type.replace('resources', 'items')}/{entity_id}/uploads",
        )
        # cannot overwrite attachments by design, hence disabled
        # if attachment_id:
        #     url += f"/{attachment_id}"

        with open(native_path, "rb") as file:
            response = session.post(
                url,
                files={"file": (attachment_name, file)},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            response.raise_for_status()

            try:
                location = urlparse(response.headers["location"])
                is_valid = all(
                    (
                        response.status_code == 201,
                        location.netloc == endpoint.netloc,
                        (match := (re.match(r"^/api/v2/(experiments|items)/([0-9]+)/uploads/([0-9]+)$", location.path)))
                        is not None,
                    )
                )
            except KeyError:
                is_valid = False
            if not is_valid:
                raise ValidationError(err_msg="Invalid response from eLabFTW")
            match = cast(re.Match, match)

        entity_type, entity_id, attachment_id = match.groups()
        entity_type = entity_type.replace("items", "resources")

        return f"elabftw://{location.netloc}/{entity_type}/{entity_id}/{attachment_id}"

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """
        Save the file attachment from an eLabFTW resource or experiment located at ``source_path`` to ``native_path``.

        :param source_path: URI of the file ``elabftw://demo.elabftw.net/experiments/269/69`` to download from eLabFTW
        :type source_path: str
        :param native_path: The path on the filesystem to save the file to, e.g. ``/tmp/myfile.txt``
        :type native_path: str
        :param user_context: A user context, defaults to ``None``
        :type user_context: OptionalUserContext
        :param opts: A set of options to exercise additional control over this method. Defaults to ``None``

        :raises requests.RequestException: When there is a connection error.
        :raises ValidationError: If the HTTP response from the eLabFTW server is invalid.
        :raises AttachmentExpected: When referencing an entity type, an entity or the root rather than an attachment.
        """
        session = self._create_session(options=opts, user_context=user_context)
        endpoint = self._get_endpoint(options=opts, user_context=user_context)

        entity_type, entity_id, attachment_id = split_path(source_path)
        if not all((entity_type, entity_id, attachment_id)):
            raise AttachmentExpected(err_msg="Expected a file attached to an experiment or resource")
        entity_type, entity_id, attachment_id = cast(str, entity_type), cast(str, entity_id), cast(str, attachment_id)

        url = urljoin(
            f"{endpoint.scheme}://{endpoint.netloc}/",
            f"/api/v2/{entity_type.replace('resources', 'items')}/{entity_id}/uploads/{attachment_id}"
            f"?format=binary",
        )
        try:
            with session.get(
                url,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                stream=True,
            ) as response, open(native_path, "wb") as file:
                response.raise_for_status()
                for chunk in response.iter_content(512):
                    file.write(chunk)
        except Exception as exception:
            Path(native_path).unlink(missing_ok=True)
            raise exception


def split_path(path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Split and validate an eLabFTW path.

    Split an eLabFTW path into its parts, and ensure that it satisfies the constraints this module imposes on it (see
    docstring of :class:`InvalidPath`).

    :param path: A path representing an entity type, an entity, or a file attachment in eLabFTW.
    :type path: str

    :returns: The path passed as an argument split into three parts: ``entity_type``, ``entity_id``, and
              ``attachment_id``. ``None`` is returned in place of missing parts.
    :rtype: Tuple[Optional[str], Optional[str], Optional[str]]

    :raises InvalidPath: Path constraints described in the docstring of :class:`InvalidPath` are not satisfied.
    """
    path_obj = Path(path)

    if not path_obj.is_absolute():
        raise InvalidPath(err_msg=InvalidPath.message_path_absolute % path_obj)

    parts = path_obj.parts[1:]
    if len(parts) > 3:
        raise InvalidPath(err_msg=InvalidPath.message_path_form % path_obj)
    entity_type, entity_id, attachment_id = (
        # right pad `parts` with three `None`s
        tuple(parts)
        + (None,) * (3 - len(parts))
    )

    if entity_type not in (None, "experiments", "resources"):
        raise InvalidPath(err_msg=InvalidPath.message_path_entity_type % path_obj)

    if entity_id:
        try:
            if not int(entity_id) >= 0:
                raise ValueError
        except ValueError as exception:
            raise InvalidPath(err_msg=InvalidPath.message_path_entity_id % path_obj) from exception

    if attachment_id:
        try:
            if not int(attachment_id) >= 0:
                raise ValueError
        except ValueError as exception:
            raise InvalidPath(err_msg=InvalidPath.message_path_attachment_id % path_obj) from exception

    return entity_type, entity_id, attachment_id


class eLabFTWFilesSourceException(  # noqa
    ABC,
    Exception,
):
    """Base class for exceptions raised when `eLabFTWFilesSource` encounters a problem."""


class InvalidPath(
    galaxy_exceptions.MessageException,
    eLabFTWFilesSourceException,
):
    """
    Raised when an invalid path is provided.

    Valid paths are of the form `/entity_type/entity_id/attachment_id`, where:
    - `entity_type` is either 'experiments' or 'resources'
    - `entity_id` is the id (an integer) of an experiment or resource
    - `attachment_id` is the id (an integer) of an attachment
    """

    message_path_form = (
        # fmt: off
        "path '%' is invalid, paths must be of the form "
        "`/entity_type/entity_id/attachment_id`, where:"
        + dedent("""
            - `entity_type` is either 'experiments' or 'resources'
            - `entity_id` is the id of an experiment or resource
            - `attachment_id` is the id of an attachment
        """[1:])
        # fmt: on
    )
    message_path_absolute = "path '%' is invalid, paths must be absolute"
    message_path_entity_type = "path '%' is invalid, paths must start with /experiments or /resources"
    message_path_entity_id = (
        "path '%' is invalid, the entity id (second part of the path) must be a non-negative integer"
    )
    message_path_attachment_id = (
        "path '%' is invalid, the attachment id (third part of the path) must be a non-negative integer"
    )


class ResourceNotFound(
    galaxy_exceptions.ObjectNotFound,
    eLabFTWFilesSourceException,
):
    """
    Raised when attempting to access a non-existing experiment, resource or attachment.
    """


class DirectoryExpected(
    galaxy_exceptions.MessageException,
    eLabFTWFilesSourceException,
    ValueError,
):
    """
    Raised when referencing a file attachment where a path referencing an entity type, entity or the root is required.

    For example, it would be raised when attempting to list the contents of a file attachment. Only the root, entity
    types and entities themselves have "contents" (entity types, entities and file attachments respectively).
    """


class EntityExpected(DirectoryExpected):
    """
    Raised when referencing the root, an entity type or an attachment where a path referencing an entity is expected.

    For example, attempting to save a file to an entity type using `_write_from()` raises this exception.
    """


class AttachmentExpected(
    galaxy_exceptions.MessageException,
    eLabFTWFilesSourceException,
    ValueError,
):
    """
    Raised when referencing an entity type, an entity or the root where a path referencing an attachment is required.
    """


class ValidationError(
    galaxy_exceptions.MessageException,
    eLabFTWFilesSourceException,
):
    """
    Raised when validation of a response from eLabFTW fails.

    API responses from eLabFTW are considered untrusted and thus validated before the file source makes use of them.
    This exception will be raised when an invalid response is detected.
    """
