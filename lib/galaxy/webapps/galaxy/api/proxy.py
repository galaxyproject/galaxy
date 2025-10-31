"""
API Controller to handle remote zip operations.
"""

import logging
from urllib.parse import (
    urljoin,
    urlparse,
)

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

ALLOWED_SCHEMES = ("https", "http")
MAX_REDIRECTS = 5


def is_valid_url(url: str) -> bool:
    if url.count("://") != 1:
        return False  # Ensure there is exactly one scheme
    try:
        parsed = urlparse(url)
        return all([parsed.scheme in ALLOWED_SCHEMES, parsed.netloc])
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

        self._validate_url_and_access(url, trans)

        headers: dict[str, str] = {}
        if "range" in request.headers:
            headers["Range"] = self._validate_range_header(request.headers["range"])

        # Set the timeout for the request to 10 seconds and connection timeout to 60 seconds
        # This is to prevent the server from hanging indefinitely
        timeout = httpx.Timeout(10.0, connect=60.0)

        client = httpx.AsyncClient(timeout=timeout)
        try:
            response = await self._handle_redirects_validation(request, url, trans, headers, client)

            if request.method == "GET":
                # Return a streaming response for GET requests
                filtered_headers = self._filter_response_headers(response.headers)

                async def stream_with_cleanup():
                    """Stream response chunks and ensure cleanup on completion or error."""
                    try:
                        async for chunk in response.aiter_bytes():
                            yield chunk
                    finally:
                        await response.aclose()
                        await client.aclose()

                # StreamingResponse will handle chunked transfer encoding automatically
                return StreamingResponse(
                    stream_with_cleanup(),
                    status_code=response.status_code,
                    headers=filtered_headers,
                )
            else:
                # For HEAD requests, return immediately and cleanup in finally block
                return Response(
                    status_code=response.status_code,
                    headers=response.headers,
                )

        except httpx.RequestError as e:
            raise Exception(f"Request error: {e}")
        finally:
            # Only cleanup for non-GET requests (GET cleanup happens in the stream generator)
            if request.method != "GET":
                if response is not None:
                    await response.aclose()
                await client.aclose()

    async def _handle_redirects_validation(
        self,
        request: Request,
        url: str,
        trans: ProvidesUserContext,
        headers: dict[str, str],
        client: httpx.AsyncClient,
    ) -> httpx.Response:
        """Handle redirects manually to validate each redirect URL."""
        response = None
        current_url = url
        redirect_count = 0

        while redirect_count <= MAX_REDIRECTS:
            response = await client.request(
                method=request.method, url=current_url, headers=headers, follow_redirects=False
            )

            if self._is_redirect_response(response):
                redirect_count += 1
                if redirect_count > MAX_REDIRECTS:
                    raise RequestParameterInvalidException("Too many redirects")

                redirect_location = response.headers["location"]

                # Handle relative URLs by resolving them against the current URL
                redirect_url = urljoin(current_url, redirect_location)

                self._validate_url_and_access(redirect_url, trans)

                # Close current response and follow the validated redirect
                await response.aclose()
                current_url = redirect_url
            else:
                # Not a redirect, we have our final response
                break

        assert response is not None, "Response should not be None after redirect loop"
        return response

    def _validate_url_and_access(self, url: str, trans: ProvidesUserContext):
        if not is_valid_url(url):
            raise RequestParameterInvalidException("Invalid URL format.")

        validate_uri_access(url, trans.user_is_admin, trans.app.config.fetch_url_allowlist_ips)

    def _is_redirect_response(self, response: httpx.Response) -> bool:
        return response.status_code in (301, 302, 303, 307, 308) and "location" in response.headers

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

    def _filter_response_headers(self, headers: httpx.Headers) -> dict[str, str]:
        """
        Filter out headers that shouldn't be forwarded when proxying responses.

        Removes:
        - Hop-by-hop headers (transfer-encoding, connection, keep-alive)
        - content-encoding: httpx auto-decompresses, so content is no longer encoded
        - content-length: only if response was compressed (size changes after decompression)

        Args:
            headers: The response headers from the upstream server

        Returns:
            Filtered dictionary of headers safe to forward to the client
        """
        had_content_encoding = "content-encoding" in headers

        # Always exclude these hop-by-hop and encoding headers
        excluded_headers = ["transfer-encoding", "connection", "keep-alive", "content-encoding"]

        if had_content_encoding:
            # If content was compressed, the content-length is now incorrect after decompression
            excluded_headers.append("content-length")

        return {key: value for key, value in headers.items() if key.lower() not in excluded_headers}
