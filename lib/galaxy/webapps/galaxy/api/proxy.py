"""
API Controller to proxy remote files.
"""

import logging
import time
from functools import partial
from urllib.parse import (
    urljoin,
    urlparse,
)

import anyio
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
    GatewayTimeoutException,
    RequestParameterInvalidException,
    UpstreamProxyError,
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
MAX_STREAM_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_STREAM_SECONDS = 10


def is_valid_url(url: str) -> bool:
    if url.count("://") != 1:
        return False  # Ensure there is exactly one scheme
    try:
        parsed = urlparse(url)

        # Check if urlparse had to strip/modify any characters
        # If the reconstructed URL differs from the original, the URL contained
        # invalid characters (like tabs, newlines) that were silently removed
        if parsed.geturl() != url:
            return False

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

        await anyio.to_thread.run_sync(partial(self._validate_url_and_access, url, trans))

        headers: dict[str, str] = {}
        if "range" in request.headers:
            headers["Range"] = self._validate_range_header(request.headers["range"])

        # Set the timeout for the request to 10 seconds and connection timeout to 60 seconds
        # This is to prevent the server from hanging indefinitely
        timeout = httpx.Timeout(10.0, connect=60.0)

        client = await anyio.to_thread.run_sync(partial(httpx.AsyncClient, timeout=timeout))
        response = None
        streaming = False
        try:
            response = await self._handle_redirects_validation(request, url, trans, headers, client)

            if request.method == "GET":
                # Return a streaming response for GET requests
                filtered_headers = self._filter_response_headers(response.headers)

                async def stream_with_cleanup():
                    """Stream response chunks and ensure cleanup on completion or error."""
                    total_bytes = 0
                    start_time = time.monotonic()
                    try:
                        async for chunk in response.aiter_bytes():
                            total_bytes += len(chunk)
                            if total_bytes > MAX_STREAM_BYTES:
                                log.warning(
                                    "Proxy stream to %s exceeded max size of %d bytes",
                                    url,
                                    MAX_STREAM_BYTES,
                                )
                                break
                            elapsed = time.monotonic() - start_time
                            if elapsed > MAX_STREAM_SECONDS:
                                log.warning(
                                    "Proxy stream to %s exceeded max time of %d seconds",
                                    url,
                                    MAX_STREAM_SECONDS,
                                )
                                break
                            yield chunk
                    finally:
                        await response.aclose()
                        await client.aclose()

                streaming = True
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

        except httpx.InvalidURL as e:
            # Catch any URL validation errors that slip through our pre-validation
            raise RequestParameterInvalidException(f"Invalid URL format: {e}")
        except httpx.TimeoutException as e:
            raise GatewayTimeoutException(f"Timeout proxying request to {url}: {type(e).__name__}")
        except httpx.RequestError as e:
            raise UpstreamProxyError(f"Error proxying request to {url}: {type(e).__name__}: {e}")
        finally:
            # Only cleanup if we're NOT handing off to the stream generator
            if not streaming:
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
            req = client.build_request(
                method=request.method,
                url=current_url,
                headers=headers,
            )
            response = await client.send(req, follow_redirects=False, stream=True)

            if self._is_redirect_response(response):
                redirect_count += 1
                if redirect_count > MAX_REDIRECTS:
                    raise RequestParameterInvalidException("Too many redirects")

                redirect_location = response.headers["location"]

                # Handle relative URLs by resolving them against the current URL
                redirect_url = urljoin(current_url, redirect_location)

                await anyio.to_thread.run_sync(partial(self._validate_url_and_access, redirect_url, trans))

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
        - content-length: always removed because the actual streamed bytes may differ
          from the upstream value (auto-decompression, stream size/time limits)

        Args:
            headers: The response headers from the upstream server

        Returns:
            Filtered dictionary of headers safe to forward to the client
        """
        # Always exclude these hop-by-hop and encoding headers.
        # content-length is always excluded because:
        # 1. httpx auto-decompresses, so compressed content-length is wrong after decompression
        # 2. The stream may be truncated by MAX_STREAM_BYTES or MAX_STREAM_SECONDS limits
        # StreamingResponse will use chunked transfer encoding instead.
        # accept-ranges is excluded because range requests are not meaningful without content-length.
        excluded_headers = [
            "transfer-encoding",
            "connection",
            "keep-alive",
            "content-encoding",
            "content-length",
            "accept-ranges",
        ]

        return {key: value for key, value in headers.items() if key.lower() not in excluded_headers}
