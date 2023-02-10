import os
import stat
import typing

import anyio
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import (
    FileResponse,
    Response,
)
from starlette_context.middleware import RawContextMiddleware
from starlette_context.plugins import RequestIdPlugin

from galaxy.exceptions import MessageException
from galaxy.web.framework.base import walk_controller_modules
from galaxy.web.framework.decorators import (
    api_error_message,
    validation_error_to_message_exception,
)

if typing.TYPE_CHECKING:
    from starlette.background import BackgroundTask
    from starlette.types import (
        Receive,
        Scope,
        Send,
    )


# Copied from https://github.com/tiangolo/fastapi/issues/1240#issuecomment-1055396884
def _get_range_header(range_header: str, file_size: int) -> typing.Tuple[int, int]:
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

    nginx_x_accel_redirect_base: typing.Optional[str] = None
    apache_xsendfile: typing.Optional[bool] = None
    send_header_only: bool

    def __init__(
        self,
        path: typing.Union[str, "os.PathLike[str]"],
        status_code: int = 200,
        headers: typing.Optional[typing.Mapping[str, str]] = None,
        media_type: typing.Optional[str] = None,
        background: typing.Optional["BackgroundTask"] = None,
        filename: typing.Optional[str] = None,
        stat_result: typing.Optional[os.stat_result] = None,
        method: typing.Optional[str] = None,
        content_disposition_type: str = "attachment",
    ) -> None:
        super().__init__(
            path, status_code, headers, media_type, background, filename, stat_result, method, content_disposition_type
        )
        self.headers["accept-ranges"] = "bytes"
        send_header_only = self.nginx_x_accel_redirect_base or self.apache_xsendfile
        if self.nginx_x_accel_redirect_base:
            self.headers["x-accel-redirect"] = self.nginx_x_accel_redirect_base + os.path.abspath(path)
        elif self.apache_xsendfile:
            self.headers["x-sendfile"] = os.path.abspath(path)
        if not self.send_header_only and send_header_only:
            # Not a head request, but nginx_x_accel_redirect_base / send_header_only, we don't send a body
            self.send_header_only = True
            self.headers["content-length"] = "0"

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
        start = 0
        end = stat_result.st_size - 1
        if not self.send_header_only:
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
        if self.send_header_only:
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


# Copied from https://stackoverflow.com/questions/71222144/runtimeerror-no-response-returned-in-fastapi-when-refresh-request/72677699#72677699
class SuppressNoResponseReturnedMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except RuntimeError as exc:
            if str(exc) == "No response returned." and await request.is_disconnected():
                return Response(status_code=status.HTTP_204_NO_CONTENT)
            raise


def add_empty_response_middleware(app: FastAPI) -> None:
    app.add_middleware(SuppressNoResponseReturnedMiddleware)


def add_sentry_middleware(app: FastAPI) -> None:
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
    app.add_middleware(SentryAsgiMiddleware)


def add_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validate_exception_middleware(request: Request, exc: RequestValidationError) -> Response:
        exc = validation_error_to_message_exception(exc)
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(status_code=400, content=error_dict)

    @app.exception_handler(MessageException)
    async def message_exception_middleware(request: Request, exc: MessageException) -> Response:
        error_dict = api_error_message(None, exception=exc)
        return JSONResponse(status_code=exc.status_code, content=error_dict)


def add_request_id_middleware(app: FastAPI):
    app.add_middleware(RawContextMiddleware, plugins=(RequestIdPlugin(force_new_uuid=True),))


def include_all_package_routers(app: FastAPI, package_name: str):
    for _, module in walk_controller_modules(package_name):
        router = getattr(module, "router", None)
        if router:
            app.include_router(router)
