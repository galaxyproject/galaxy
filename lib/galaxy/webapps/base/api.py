import os
import stat
import uuid
from collections.abc import Mapping
from logging import getLogger
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
    Union,
)

import anyio
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import (
    FileResponse,
    Response,
    StreamingResponse,
)
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware
from starlette_context.plugins import (
    Plugin,
    RequestIdPlugin,
)

from galaxy.exceptions import MessageException
from galaxy.exceptions.utils import (
    api_error_to_dict,
    validation_error_to_message_exception,
)
from galaxy.util.path import StrPath
from galaxy.web.framework.base import walk_controller_modules

if TYPE_CHECKING:
    from starlette.background import BackgroundTask
    from starlette.routing import BaseRoute
    from starlette.types import (
        Receive,
        Scope,
        Send,
    )

from galaxy.schema.schema import MessageExceptionModel

log = getLogger(__name__)


# Copied from https://github.com/tiangolo/fastapi/issues/1240#issuecomment-1055396884
def _get_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    def _invalid_range():
        return HTTPException(
            status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail=f"Invalid request range (Range:{range_header!r})",
        )

    try:
        h = range_header.replace("bytes=", "").rsplit("-", 1)
        start = int(h[0]) if h[0] != "" else 0
        end = int(h[1]) if h[1] != "" else file_size - 1
    except ValueError:
        raise _invalid_range()

    if start > end or start < 0 or end > file_size - 1:
        raise _invalid_range()
    return start, end


def _live_request_sessions() -> list:
    """Concrete request-scoped SQLAlchemy Sessions that already exist for this request.

    Reads ``galaxy.app.app``'s ``model`` + ``install_model`` scoped registries
    directly, keyed by the current request-id (``request_scopefunc``). It never
    calls the ``scoped_session`` proxy, which would lazily *create* a session.
    Returns ``[]`` when no Galaxy app is bound (the tool shed / reports webapps
    reuse this module) or when no session was opened during the request.
    """
    try:
        from galaxy import app as galaxy_app  # lazy: keep base/api.py importable by non-Galaxy webapps
    except Exception:
        return []
    app = getattr(galaxy_app, "app", None)
    if app is None:
        return []
    sessions = []
    for mapping in (getattr(app, "model", None), getattr(app, "install_model", None)):
        if mapping is None:
            continue
        existing = mapping.scoped_registry.registry.get(mapping.request_scopefunc())
        if existing is not None:
            sessions.append(existing)
    return sessions


def _release_request_sessions(sessions: list) -> None:
    """Close the captured request-scoped sessions, returning their pooled connections.

    ``Session.close()`` is idempotent, so the later guarded close in
    ``get_app_with_request_session``'s teardown is harmless.
    """
    for session in sessions:
        try:
            session.close()
        except Exception:
            log.warning("Failed to release request-scoped DB session before streaming", exc_info=True)


class GalaxyFileResponse(FileResponse):
    """
    Augments starlette FileResponse with x-accel-redirect/x-sendfile and byte-range handling.

    Like :class:`GalaxyStreamingResponse`, it releases the request-scoped DB
    connection(s) before sending the file body — see that class's docstring for
    the rationale and the contract/footgun. File downloads never touch the
    database after the response is constructed.
    """

    nginx_x_accel_redirect_base: Optional[str] = None
    apache_xsendfile: Optional[bool] = None

    def __init__(
        self,
        path: StrPath,
        status_code: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional["BackgroundTask"] = None,
        filename: Optional[str] = None,
        stat_result: Optional[os.stat_result] = None,
        content_disposition_type: str = "attachment",
    ) -> None:
        super().__init__(
            path=path,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
            filename=filename,
            stat_result=stat_result,
            content_disposition_type=content_disposition_type,
        )
        self.headers["accept-ranges"] = "bytes"
        self.xsendfile = self.nginx_x_accel_redirect_base or self.apache_xsendfile
        if self.nginx_x_accel_redirect_base:
            self.headers["x-accel-redirect"] = self.nginx_x_accel_redirect_base + os.path.abspath(path)
        elif self.apache_xsendfile:
            self.headers["x-sendfile"] = os.path.abspath(path)
        # Capture the live request-scoped session(s) now, while we are in the
        # request's asyncio task (so the request-id ContextVar resolves), to
        # release before streaming the body. See GalaxyStreamingResponse.
        self._sessions_to_release = _live_request_sessions()

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if self.stat_result is None:
            try:
                stat_result = await anyio.to_thread.run_sync(os.stat, self.path)
                self.set_stat_headers(stat_result)
            except FileNotFoundError:
                raise RuntimeError(f"File at path {self.path} does not exist.")
            else:
                mode = stat_result.st_mode
                if not stat.S_ISREG(mode):
                    raise RuntimeError(f"File at path {self.path} is not a file.")

        # This is where we diverge from the superclass, this adds support for byte range requests
        is_head_request = scope["method"].upper() == "HEAD"
        if not is_head_request and self.xsendfile:
            # Not a head request, but nginx_x_accel_redirect_base / send_header_only, we don't send a body
            self.headers["content-length"] = "0"
        send_header_only = self.xsendfile or is_head_request

        start = 0
        end = stat_result.st_size - 1
        if not send_header_only:
            http_range = ""
            for key, value in scope["headers"]:
                if key == b"range":
                    http_range = value.decode("latin-1")
                    start, end = _get_range_header(http_range, stat_result.st_size)
                    self.headers["content-length"] = str(end - start + 1)
                    self.headers["content-range"] = f"bytes {start}-{end}/{stat_result.st_size}"
                    self.status_code = status.HTTP_206_PARTIAL_CONTENT
                    break

        # All DB work for this request is done; the body below is pure file I/O
        # (or a header-only x-accel/x-sendfile/HEAD response). Release the pooled
        # connection(s) before we start sending so a slow/large download doesn't
        # pin them for the whole transfer.
        _release_request_sessions(self._sessions_to_release)
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        if send_header_only:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        else:
            # This also diverges from the superclass by seeking to start and limiting to end if handling byte range requests
            async with await anyio.open_file(self.path, mode="rb") as file:
                more_body = True
                if start:
                    await file.seek(start)
                while more_body:
                    if http_range:
                        pos = await file.tell()
                        read_size = min(self.chunk_size, end + 1 - pos)
                        if pos + read_size == end + 1:
                            more_body = False
                    else:
                        read_size = self.chunk_size
                    chunk = await file.read(read_size)
                    if more_body:
                        more_body = len(chunk) == self.chunk_size
                    await send(
                        {
                            "type": "http.response.body",
                            "body": chunk,
                            "more_body": more_body,
                        }
                    )
        if self.background is not None:
            await self.background()


class GalaxyStreamingResponse(StreamingResponse):
    """A ``StreamingResponse`` that releases the request-scoped DB connection(s)
    before the body starts streaming.

    WHY: FastAPI's request-scoped SQLAlchemy session (and its pooled DB
    connection) is held checked-out by the ``get_app_with_request_session``
    yield-dependency until the *entire* response body has been sent. For a
    long-lived stream (SSE, a large file/archive download, an upstream proxy)
    that can be minutes to hours, pinning one pooled connection per in-flight
    stream and exhausting the pool / server connection slots. This class closes
    the session(s) the moment streaming begins, returning the connection to the
    pool while bytes are still flowing.

    CONTRACT — read before using this class:
      This is ONLY safe when the response body performs NO database access after
      the response object is constructed. Every byte the body yields must come
      from data already materialized (a zipstream over files on disk, a
      ``BytesIO``, an upstream HTTP proxy, the SSE in-memory queue). If the body
      lazily loads an ORM relationship, issues a query, or commits, it trips the
      FOOTGUN below.

    FOOTGUN: the request-id ``ContextVar`` that keys the ``scoped_session`` is
      still set while the body streams (same asyncio task). If body code touches
      ``app.model.session`` after we close it, ``scoped_session`` will SILENTLY
      create a brand-new session under the same request-id — re-pinning a
      connection for the rest of the stream, and any writes on it are a latent
      correctness bug. Do not stream DB-backed lazy data through this class.

    Idempotency: ``Session.close()`` is a no-op on an already-closed session, and
    the dependency teardown's ``unset_request_id`` is guarded, so the
    double-close at request end is harmless. This class never deletes the
    registry entry — the teardown owns that.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Capture concrete, already-open request-scoped sessions NOW, while we
        # are guaranteed to be in the request's asyncio task (so the request-id
        # ContextVar resolves). We never call the scoped proxy, which would
        # lazily create a session if none exists.
        self._sessions_to_release = _live_request_sessions()

    async def stream_response(self, send: "Send") -> None:
        _release_request_sessions(self._sessions_to_release)
        await super().stream_response(send)


def add_sentry_middleware(app: FastAPI) -> None:
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    app.add_middleware(SentryAsgiMiddleware)


def get_error_response_for_request(request: Request, exc: MessageException) -> JSONResponse:
    error_dict = api_error_to_dict(exception=exc)
    status_code = exc.status_code
    if "ga4gh" in (path := request.url.path):
        # When serving GA4GH APIs use limited exceptions to conform their expected
        # error schema. Tailored to DRS currently.
        message = error_dict["err_msg"]
        if "drs" in path:
            content = {"status_code": status_code, "msg": message}
        elif "trs" in path:
            content = {"code": status_code, "message": message}
        else:
            # unknown schema - just yield the most useful error message
            content = error_dict
    else:
        content = error_dict

    retry_after: Optional[int] = getattr(exc, "retry_after", None)
    headers: dict[str, str] = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(status_code=status_code, content=content, headers=headers)


def add_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validate_exception_middleware(request: Request, exc: RequestValidationError) -> Response:
        message_exception = validation_error_to_message_exception(exc)
        return get_error_response_for_request(request, message_exception)

    @app.exception_handler(MessageException)
    async def message_exception_middleware(request: Request, exc: MessageException) -> Response:
        # Intentionally not logging traceback here as the full context will be
        # dispatched to Sentry if configured.  This just makes logs less opaque
        # when one sees a 500.
        if exc.status_code >= 500:
            log.info(f"MessageException: {exc}")
        return get_error_response_for_request(request, exc)


class AccessLoggingMiddleware(Plugin):

    key = "access_line"

    async def process_request(self, request):
        scope = request.scope
        path = scope["root_path"] + scope["path"]
        if scope["query_string"]:
            path = f"{path}?{scope['query_string'].decode('ascii')}"
        access_line = f"{scope['method']} {path} {uuid.uuid4()}"
        log.debug(access_line)
        return access_line

    async def enrich_response(self, response) -> None:
        access_line = context.get("access_line")
        if status := response.get("status"):
            log.debug(f"{access_line} {status}")


def add_raw_context_middlewares(app: FastAPI):
    getLogger("uvicorn.access").handlers = []
    plugins = (RequestIdPlugin(force_new_uuid=True), AccessLoggingMiddleware())
    app.add_middleware(RawContextMiddleware, plugins=plugins)


def add_request_id_middleware(app: FastAPI):
    app.add_middleware(RawContextMiddleware, plugins=(RequestIdPlugin(force_new_uuid=True),))


def build_route_name_index(app: FastAPI) -> dict[str, list["BaseRoute"]]:
    """Build a name -> [route] index for O(1) route lookup.

    Routes are immutable after app startup, so this index is built once
    and reused for all subsequent requests. For most route names there
    is exactly one candidate, making lookups O(1) instead of O(n).
    """
    index: dict[str, list[BaseRoute]] = {}
    for route in app.routes:
        name = getattr(route, "name", None)
        if name:
            index.setdefault(name, []).append(route)
    return index


def include_all_package_routers(app: FastAPI, package_name: str):
    responses: dict[Union[int, str], dict[str, Any]] = {
        "4XX": {
            "description": "Request Error",
            "model": MessageExceptionModel,
        },
        "5XX": {
            "description": "Server Error",
            "model": MessageExceptionModel,
        },
    }
    for _, module in walk_controller_modules(package_name):
        router = getattr(module, "router", None)
        if router:
            app.include_router(router, responses=responses)

    # handle CORS preflight requests - synchronize with wsgi behavior.
    # this needs to happen last so it doesn't clobber routes with explicit cors handling
    # it doesn't affect the CORS middleware since the middleware terminates the request handling before routing
    @app.options("/api/{rest_of_path:path}", include_in_schema=False)
    async def preflight_handler(request: Request, rest_of_path: str) -> Response:
        response = Response()
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "600"
        return response
