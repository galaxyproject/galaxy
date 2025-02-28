"""
API Controller to handle remote zip operations.
"""

import logging

import httpx
from fastapi import (
    Query,
    Request,
)
from starlette.responses import (
    Response,
    StreamingResponse,
)

from galaxy.exceptions import RequestParameterMissingException
from . import Router

log = logging.getLogger(__name__)

router = Router(tags=["remote zip handling"])

URLQueryParam: str = Query(
    title="URL",
    description="The URL of the remote zip file",
)


@router.cbv
class FastAPIRemoteZip:

    @router.api_route("/api/proxy", methods=["GET", "HEAD"])
    async def proxy(self, request: Request, url: str = URLQueryParam):
        """
        Proxy a remote file to the client to avoid CORS issues.
        """
        if not url:
            raise RequestParameterMissingException("The 'url' parameter is required")

        headers = {}
        if "range" in request.headers:
            headers["Range"] = request.headers["range"]  # Forward Range requests

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method=request.method, url=url, headers=headers, follow_redirects=True)

                # Return a streaming response for GET requests
                if request.method == "GET":
                    return StreamingResponse(
                        response.aiter_bytes(),
                        status_code=response.status_code,
                        headers={
                            key: value
                            for key, value in response.headers.items()
                            if key.lower() in ["content-length", "content-range", "accept-ranges"]
                        },
                    )
                else:
                    return Response(
                        status_code=response.status_code,
                        headers=response.headers,
                    )

            except httpx.RequestError as e:
                raise Exception(f"Request error: {e}")
