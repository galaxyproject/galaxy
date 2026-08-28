import gzip
from typing import cast
from unittest import mock

import responses
from requests import Response

from galaxy.files.sources.cbioportal import CBioPortalFilesSource


@responses.activate
def test_cbioportal_streams_download_and_closes_response(tmp_path):
    url = "https://example.com/study.tar.gz"
    responses.add(
        responses.GET,
        url,
        body=gzip.compress(b"archive contents", mtime=0),
        headers={"Content-Encoding": "gzip"},
    )
    source = object.__new__(CBioPortalFilesSource)
    target = tmp_path / "study.tar.gz"

    with (
        mock.patch.object(CBioPortalFilesSource, "_allowlist", new_callable=mock.PropertyMock, return_value=[]),
        mock.patch("galaxy.files.sources.cbioportal.validate_non_local", side_effect=lambda value, allowlist: value),
    ):
        source._stream_url_to_file(url, str(target))

    assert target.read_bytes() == b"archive contents"
    response = cast(Response, responses.calls[0].response)
    assert response.raw.closed
