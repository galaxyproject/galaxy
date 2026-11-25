import asyncio
import os
import stat
import threading
import uuid
from collections.abc import Mapping
from logging import getLogger
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
    Union,
)
from weakref import WeakKeyDictionary

import anyio
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.pool import QueuePool
from starlette.requests import ClientDisconnect
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
from galaxy.web.framework.base import (
    parse_byte_range,
    RangeNotSatisfiable,
    walk_controller_modules,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import Pool
    from starlette.background import BackgroundTask
    from starlette.routing import BaseRoute
    from starlette.types import (
        Receive,
        Scope,
        Send,
    )

from galaxy.schema.schema import MessageExceptionModel

log = getLogger(__name__)


def _get_range_header(range_header: str, file_size: int) -> Optional[tuple[int, int]]:
    try:
        return parse_byte_range(range_header, file_size)
    except RangeNotSatisfiable:
        raise HTTPException(
            status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail=f"Invalid request range (Range:{range_header!r})",
            headers={"content-range": f"bytes */{file_size}"},
        )


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


def _release_request_sessions(sessions: list, slot: Optional["RequestSessionSlot"] = None) -> None:
    """Close the captured request-scoped sessions, returning their pooled connections.

    Also gives up the request's session slot, so that a long-lived stream does
    not count against :class:`RequestSessionLimiter` either.

    ``Session.close()`` and ``RequestSessionSlot.release()`` are idempotent, so
    the later guarded close in ``get_app_with_request_session``'s teardown is harmless.
    """
    for session in sessions:
        try:
            session.close()
        except Exception:
            log.warning("Failed to release request-scoped DB session before streaming", exc_info=True)
    if slot is not None:
        slot.release()


def release_request_sessions() -> None:
    """Return this request's pooled DB connection(s) before long non-DB work, e.g. reading a large request body."""
    _release_request_sessions(_live_request_sessions(), _request_session_slot())


#: Share of the connection pool that request-scoped API sessions leave to the
#: other users of the pool in a web process: legacy WSGI controllers, the
#: database heartbeat, control tasks and other background threads.
RESERVED_POOL_FRACTION = 0.2
MIN_RESERVED_POOL_CONNECTIONS = 2
#: A request that waits this many seconds for a session slot is logged.
SLOW_SLOT_WAIT = 30
#: Status of the response to a request whose client went away while it waited for a slot, nginx's "client closed request".
CLIENT_CLOSED_REQUEST = 499
REQUEST_SESSION_SLOT_KEY = "galaxy_request_session_slot"


def request_session_limit(pool: "Pool", thread_tokens: float) -> int | None:
    """How many requests may hold a request-scoped session at once, ``None`` for no limit.

    Never more than there are threadpool threads, so that every request that
    holds a session can also get a thread to use it, and never more than the
    pool can serve next to its other users.
    """
    if not isinstance(pool, QueuePool):
        return None
    max_overflow = pool._max_overflow
    if pool.size() <= 0 or max_overflow < 0:
        # No upper bound on the number of connections.
        return None
    capacity = pool.size() + max_overflow
    reserved = max(MIN_RESERVED_POOL_CONNECTIONS, int(capacity * RESERVED_POOL_FRACTION))
    return max(1, int(min(thread_tokens, capacity - reserved)))


def _has_body(request: Request) -> bool:
    headers = request.headers
    return "transfer-encoding" in headers or headers.get("content-length", "0") != "0"


async def _client_disconnect(request: Request) -> None:
    """Return once the client of ``request``, whose body has been read, goes away."""
    try:
        while (await request.receive())["type"] != "http.disconnect":
            pass
    except Exception:
        # Nothing can be received from the client any more.
        pass


class RequestSessionSlot:
    """One request's permission to hold a request-scoped database session."""

    def __init__(self, limiter: "RequestSessionLimiter") -> None:
        self._limiter = limiter
        self._lock = threading.Lock()
        self._held = True

    def release(self) -> None:
        """Give the slot to the next waiting request. Idempotent, and safe to call from a worker thread."""
        with self._lock:
            if not self._held:
                return
            self._held = False
        self._limiter._release()


class RequestSessionLimiter:
    """Bounds how many requests of a web process hold a request-scoped database session.

    WHY: a request checks a pooled connection out in its first dependency that
    touches the database and keeps it until its teardown, but only borrows a
    threadpool thread for one dependency or the endpoint body at a time. With
    more requests in flight than the pool has connections, every connection
    ends up held by a request that is queued for a thread, while the threads
    are blocked in requests that wait for a connection. Nothing moves until the
    pool timeout fires, the requests it fails are retried, and the process
    stays in that state. Everything else that uses the pool times out with it,
    e.g. the database heartbeat.

    A request therefore waits here, on the event loop and holding neither a
    thread nor a connection, until it may open a session.
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._loop = asyncio.get_running_loop()
        self._semaphore = asyncio.Semaphore(limit)

    async def acquire(self, request: Optional[Request] = None) -> RequestSessionSlot:
        """Wait for a slot.

        A ``request`` without a body is dropped with :data:`CLIENT_CLOSED_REQUEST`
        when its client goes away while it waits, so that the slot it would get
        later serves a client that is still there. Watching a request with a body
        would read the whole body into memory before its endpoint can stream it.
        """
        if not self._semaphore.locked():
            await self._semaphore.acquire()
            return RequestSessionSlot(self)
        # Waiting has no timeout, so this is what shows that the requests holding the slots are stuck.
        slow = self._loop.call_later(
            SLOW_SLOT_WAIT,
            log.warning,
            "A request has waited %d seconds for a database session slot, all %d are held",
            SLOW_SLOT_WAIT,
            self.limit,
        )
        try:
            if request is None or _has_body(request):
                await self._semaphore.acquire()
            elif not await self._acquire_unless_disconnected(request):
                raise HTTPException(
                    CLIENT_CLOSED_REQUEST, "The client closed the request while it waited for a database session slot."
                )
        finally:
            slow.cancel()
        return RequestSessionSlot(self)

    async def _acquire_unless_disconnected(self, request: Request) -> bool:
        """Acquire the semaphore, or return ``False`` when the client goes away first."""
        try:
            # Caches the empty body, so that the endpoint can still read it and only a disconnect is left to receive.
            await request.body()
        except ClientDisconnect:
            return False
        acquired = asyncio.ensure_future(self._semaphore.acquire())
        disconnected = asyncio.ensure_future(_client_disconnect(request))
        try:
            await asyncio.wait((acquired, disconnected), return_when=asyncio.FIRST_COMPLETED)
        except BaseException:
            acquired.cancel()
            if acquired.done() and not acquired.cancelled():
                self._semaphore.release()
            raise
        finally:
            disconnected.cancel()
        if acquired.done():
            return True
        # A waiter that is cancelled after it was woken up hands the semaphore on.
        acquired.cancel()
        return False

    def _release(self) -> None:
        try:
            on_loop = asyncio.get_running_loop() is self._loop
        except RuntimeError:
            on_loop = False
        if on_loop:
            self._semaphore.release()
        elif not self._loop.is_closed():
            # asyncio primitives are not thread-safe; hand the release to the loop.
            self._loop.call_soon_threadsafe(self._semaphore.release)


_request_session_limiters: "WeakKeyDictionary[Engine, RequestSessionLimiter | None]" = WeakKeyDictionary()


def _request_session_limiter(engine: "Engine") -> RequestSessionLimiter | None:
    """The limiter for the requests that the running event loop serves from ``engine``."""
    try:
        limiter = _request_session_limiters[engine]
    except KeyError:
        pass
    else:
        if limiter is None or limiter._loop is asyncio.get_running_loop():
            return limiter
    limit = request_session_limit(engine.pool, anyio.to_thread.current_default_thread_limiter().total_tokens)
    limiter = _request_session_limiters[engine] = RequestSessionLimiter(limit) if limit is not None else None
    if limiter is not None:
        log.info("At most %d requests at a time hold a database session (%s)", limit, engine.pool.status())
    return limiter


def _request_session_slot() -> RequestSessionSlot | None:
    """The session slot this request holds, if any."""
    if not context.exists():
        return None
    return context.data.get(REQUEST_SESSION_SLOT_KEY)


async def acquire_request_session_slot(
    engine: "Engine", request: Optional[Request] = None
) -> RequestSessionSlot | None:
    """Wait until this request may hold a request-scoped session on ``engine``.

    A request takes one slot however many of its dependencies ask for one.
    Returns ``None`` when the engine's pool is unbounded.
    """
    slot = _request_session_slot()
    if slot is None:
        limiter = _request_session_limiter(engine)
        if limiter is not None:
            slot = context.data[REQUEST_SESSION_SLOT_KEY] = await limiter.acquire(request)
    return slot


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
        self._session_slot = _request_session_slot()

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
        byte_range = None
        if not send_header_only:
            for key, value in scope["headers"]:
                if key == b"range":
                    byte_range = _get_range_header(value.decode("latin-1"), stat_result.st_size)
                    if byte_range is not None:
                        start, end = byte_range
                        self.headers["content-length"] = str(end - start + 1)
                        self.headers["content-range"] = f"bytes {start}-{end}/{stat_result.st_size}"
                        self.status_code = status.HTTP_206_PARTIAL_CONTENT
                    break

        # All DB work for this request is done; the body below is pure file I/O
        # (or a header-only x-accel/x-sendfile/HEAD response). Release the pooled
        # connection(s) before we start sending so a slow/large download doesn't
        # pin them for the whole transfer.
        _release_request_sessions(self._sessions_to_release, self._session_slot)
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
                    if byte_range is not None:
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
        self._session_slot = _request_session_slot()

    async def stream_response(self, send: "Send") -> None:
        _release_request_sessions(self._sessions_to_release, self._session_slot)
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
