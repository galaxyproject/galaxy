import os
import stat
import uuid
from logging import getLogger
from typing import (
    Any,
    Dict,
    Mapping,
    Optional,
    Tuple,
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
)
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware
from starlette_context.plugins import (
    Plugin,
    RequestIdPlugin,
)

from galaxy.exceptions import MessageException
from galaxy.exceptions.utils import api_error_to_dict
from galaxy.util.path import StrPath
from galaxy.web.framework.base import walk_controller_modules
from galaxy.web.framework.decorators import validation_error_to_message_exception

if TYPE_CHECKING:
    from starlette.background import BackgroundTask
    from starlette.types import (
        Receive,
        Scope,
        Send,
    )

from galaxy.schema.schema import MessageExceptionModel

log = getLogger(__name__)


# Copied from https://github.com/tiangolo/fastapi/issues/1240#issuecomment-1055396884
def _get_range_header(range_header: str, file_size: int) -> Tuple[int, int]:
    def _invalid_range():
        return HTTPException(
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
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


class GalaxyFileResponse(FileResponse):
    """
    Augments starlette FileResponse with x-accel-redirect/x-sendfile and byte-range handling.
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
        method: Optional[str] = None,
        content_disposition_type: str = "attachment",
    ) -> None:
        super().__init__(
            path, status_code, headers, media_type, background, filename, stat_result, method, content_disposition_type
        )
        self.headers["accept-ranges"] = "bytes"
        self.xsendfile = self.nginx_x_accel_redirect_base or self.apache_xsendfile
        if self.nginx_x_accel_redirect_base:
            self.headers["x-accel-redirect"] = self.nginx_x_accel_redirect_base + os.path.abspath(path)
        elif self.apache_xsendfile:
            self.headers["x-sendfile"] = os.path.abspath(path)

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
    headers: Dict[str, str] = {}
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


def include_all_package_routers(app: FastAPI, package_name: str):
    responses: Dict[Union[int, str], Dict[str, Any]] = {
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
