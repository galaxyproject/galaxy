from types import SimpleNamespace
from typing import cast
from unittest import mock

from galaxy.files.sources import elabftw


def test_async_session_uses_certifi_ssl_context():
    ssl_context = mock.Mock()
    connector = mock.Mock()
    session = mock.Mock()
    source = object.__new__(elabftw.eLabFTWFilesSource)
    config = cast(elabftw.eLabFTWFileSourceConfiguration, SimpleNamespace(api_key="secret"))

    with (
        mock.patch("galaxy.files.sources.elabftw.requests.create_ssl_context", return_value=ssl_context),
        mock.patch("galaxy.files.sources.elabftw.aiohttp.TCPConnector", return_value=connector) as tcp_connector,
        mock.patch("galaxy.files.sources.elabftw.aiohttp.ClientSession", return_value=session) as client_session,
    ):
        assert source._create_session_async(config) is session

    tcp_connector.assert_called_once_with(limit=elabftw.MAX_CONCURRENT_REQUESTS, ssl=ssl_context)
    client_session.assert_called_once_with(
        connector=connector,
        raise_for_status=True,
        headers={"Authorization": "secret", "Accept": "application/json"},
    )
