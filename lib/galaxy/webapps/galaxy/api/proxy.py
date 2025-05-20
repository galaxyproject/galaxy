"""
API Controller to handle remote zip operations.
"""

import logging
from urllib.parse import urlparse

import httpx
from fastapi import (
    Query,
    Request,
)
from starlette.responses import (
    Response,
    StreamingResponse,
)

from galaxy.exceptions import (
    RequestParameterInvalidException,
    UserRequiredException,
)
from galaxy.files.uris import validate_uri_access
from galaxy.managers.context import ProvidesUserContext
from . import (
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["utilities"])

URLQueryParam: str = Query(
    title="URL",
    description="The URL of the remote file",
)


def is_valid_url(url: str) -> bool:
    if url.count("://") != 1:
        return False  # Ensure there is exactly one scheme
    try:
        parsed = urlparse(url)
        return all([parsed.scheme in ("http", "https"), parsed.netloc])
    except ValueError:
        return False


@router.cbv
class FastAPIProxy:

    @router.get("/api/proxy")
    @router.head("/api/proxy")
    async def proxy(self, request: Request, url: str = URLQueryParam, trans: ProvidesUserContext = DependsOnTrans):
        """
        Proxy a remote file to the client to avoid CORS issues.
        """
        if trans.anonymous:
            raise UserRequiredException("Anonymous users are not allowed to access this endpoint")

        if not is_valid_url(url):
            raise RequestParameterInvalidException("Invalid URL format.")

        validate_uri_access(url, trans.user_is_admin, trans.app.config.fetch_url_allowlist_ips)

        headers = {}
        if "range" in request.headers:
            headers["Range"] = self._validate_range_header(request.headers["range"])

        # Set the timeout for the request to 10 seconds and connection timeout to 60 seconds
        # This is to prevent the server from hanging indefinitely
        timeout = httpx.Timeout(10.0, connect=60.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(method=request.method, url=url, headers=headers, follow_redirects=True)

                # Return a streaming response for GET requests
                if request.method == "GET":
                    return StreamingResponse(
                        response.aiter_bytes(),
                        status_code=response.status_code,
                        headers=response.headers,
                    )
                else:
                    return Response(
                        status_code=response.status_code,
                        headers=response.headers,
                    )

            except httpx.RequestError as e:
                raise Exception(f"Request error: {e}")

    def _validate_range_header(self, range_header: str) -> str:
        """
        Validate the Range header format and values.
        """
        if not range_header.startswith("bytes="):
            raise RequestParameterInvalidException("Invalid Range header format")
        try:
            start, end = range_header[6:].split("-")
            if not start.isdigit() or (end and not end.isdigit()):
                raise RequestParameterInvalidException("Invalid Range header values")
        except ValueError:
            raise RequestParameterInvalidException("Invalid Range header format")
        return f"bytes={start}-{end}" if end else f"bytes={start}-"
