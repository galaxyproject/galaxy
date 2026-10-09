import asyncio
from unittest import mock

from galaxy.tools.parameters import cancelable_request


class AsyncSessionContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


def test_async_request_uses_certifi_ssl_context():
    ssl_context = mock.Mock()
    connector = mock.Mock()
    session = AsyncSessionContext()

    with (
        mock.patch.object(cancelable_request, "create_ssl_context", return_value=ssl_context),
        mock.patch(
            "galaxy.tools.parameters.cancelable_request.aiohttp.TCPConnector", return_value=connector
        ) as tcp_connector,
        mock.patch(
            "galaxy.tools.parameters.cancelable_request.aiohttp.ClientSession", return_value=session
        ) as client_session,
        mock.patch.object(cancelable_request, "fetch_url", new=mock.AsyncMock(return_value={"ok": True})),
    ):
        result = asyncio.run(cancelable_request.async_request_with_timeout("https://example.com"))

    assert result == {"ok": True}
    tcp_connector.assert_called_once_with(ssl=ssl_context)
    client_session.assert_called_once_with(connector=connector)
