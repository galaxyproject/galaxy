import asyncio
import logging
from typing import (
    Any,
    Dict,
    Optional,
)

import aiohttp
from typing_extensions import Literal

log = logging.getLogger()

REQUEST_METHOD = Literal["GET", "POST", "HEAD"]


async def fetch_url(
    session: aiohttp.ClientSession,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    method: REQUEST_METHOD = "GET",
):
    async with session.request(method=method, url=url, params=params, data=data, headers=headers) as response:
        return await response.json(content_type=None)


async def async_request_with_timeout(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    method: REQUEST_METHOD = "GET",
    timeout: float = 1.0,
):
    async with aiohttp.ClientSession() as session:
        try:
            # Wait for the async request, with a user-defined timeout
            result = await asyncio.wait_for(
                fetch_url(session=session, url=url, params=params, data=data, headers=headers, method=method),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            log.debug("Request timed out after %s second", timeout)
            return None


def request(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    method: REQUEST_METHOD = "GET",
    timeout: float = 1.0,
):
    loop = asyncio.new_event_loop()

    # Run the event loop until the future is done or cancelled
    try:
        result = loop.run_until_complete(
            async_request_with_timeout(
                url=url, params=params, data=data, headers=headers, method=method, timeout=timeout
            )
        )
    except asyncio.CancelledError:
        log.debug("Request cancelled")
        result = None

    loop.close()

    return result
