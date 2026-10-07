import gzip
from types import SimpleNamespace
from typing import cast

import pytest
import responses
from requests import Response

from galaxy.exceptions import (
    AuthenticationRequired,
    ObjectNotFound,
)
from galaxy.files.sources.dataverse import (
    DataverseRDMFilesSource,
    DataverseRepositoryInteractor,
)


def _source():
    return DataverseRepositoryInteractor("https://example.com", object.__new__(DataverseRDMFilesSource))


@responses.activate
def test_dataverse_streams_download_and_closes_response(tmp_path):
    url = "https://example.com/download/1"
    responses.add(
        responses.GET,
        url,
        body=gzip.compress(b"dataset contents", mtime=0),
        headers={"Content-Encoding": "gzip"},
    )
    target = tmp_path / "dataset.txt"

    _source()._download_file(str(target), url, SimpleNamespace())

    assert target.read_bytes() == b"dataset contents"
    response = cast(Response, responses.calls[0].response)
    assert response.raw.closed


@pytest.mark.parametrize(
    ("status", "exception", "message"),
    (
        (401, AuthenticationRequired, "Authentication required"),
        (403, ObjectNotFound, "Access forbidden"),
        (404, ObjectNotFound, "File not found"),
    ),
)
@responses.activate
def test_dataverse_maps_download_errors(tmp_path, status, exception, message):
    url = "https://example.com/download/1"
    responses.add(responses.GET, url, status=status)

    with pytest.raises(exception, match=message):
        _source()._download_file(str(tmp_path / "dataset.txt"), url, SimpleNamespace())
