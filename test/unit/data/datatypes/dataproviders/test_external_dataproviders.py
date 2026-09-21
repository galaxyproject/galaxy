import io
from unittest import mock

from galaxy.datatypes.dataproviders import external
from galaxy.util import DEFAULT_SOCKET_TIMEOUT


class DecodableBytesIO(io.BytesIO):
    decode_content = False


def test_url_data_provider_get_sends_query_and_closes_response():
    url = "https://example.com/data"
    raw = DecodableBytesIO(b"result")
    response = mock.Mock(raw=raw)
    session = mock.Mock()
    session.get.return_value = response

    with mock.patch("galaxy.datatypes.dataproviders.external.requests.Session", return_value=session):
        provider = external.URLDataProvider(url, data={"gene": "BRCA1"})
    assert provider.read() == b"result"
    assert provider.url == f"{url}?gene=BRCA1"
    provider.__exit__()

    session.get.assert_called_once_with(
        f"{url}?gene=BRCA1",
        stream=True,
        timeout=DEFAULT_SOCKET_TIMEOUT,
    )
    response.raise_for_status.assert_called_once_with()
    assert raw.decode_content is True
    response.close.assert_called_once_with()
    session.close.assert_called_once_with()


def test_url_data_provider_post_sends_form_and_closes_response():
    url = "https://example.com/data"
    raw = DecodableBytesIO(b"result")
    response = mock.Mock(raw=raw)
    session = mock.Mock()
    session.post.return_value = response

    with mock.patch("galaxy.datatypes.dataproviders.external.requests.Session", return_value=session):
        provider = external.URLDataProvider(url, method="POST", data={"gene": "BRCA1"})
    assert provider.read() == b"result"
    provider.__exit__()

    session.post.assert_called_once_with(
        url,
        data={"gene": "BRCA1"},
        stream=True,
        timeout=DEFAULT_SOCKET_TIMEOUT,
    )
    response.raise_for_status.assert_called_once_with()
    assert raw.decode_content is True
    response.close.assert_called_once_with()
    session.close.assert_called_once_with()


def test_url_data_provider_keeps_ftp_fallback():
    opened = io.BytesIO(b"ftp result")
    with mock.patch.object(external, "urlopen", return_value=opened) as urlopen:
        provider = external.URLDataProvider("ftp://example.com/data", data={"gene": "BRCA1"})
        assert provider.read() == b"ftp result"
        provider.__exit__()

    urlopen.assert_called_once_with(
        "ftp://example.com/data?gene=BRCA1",
        None,
        timeout=DEFAULT_SOCKET_TIMEOUT,
    )
    assert opened.closed
