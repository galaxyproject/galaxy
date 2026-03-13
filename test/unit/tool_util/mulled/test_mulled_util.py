import pytest
import requests
import responses

from galaxy.tool_util.deps.mulled.util import (
    quay_repository,
    quay_tag_exists,
    QuayApiException,
    version_sorted,
)

MANIFEST_URL = "https://quay.io/v2/biocontainers/samtools/manifests/1.17--0"
REPOSITORY_URL = "https://quay.io/api/v1/repository/biocontainers/samtools"


@pytest.mark.parametrize(
    "tags,tag",
    [
        (["2.22--he941832_1", "2.22--he860b03_2", "2.22--hdbcaa40_3"], "2.22--hdbcaa40_3"),
        (["1.1.2--py27_0", "1.1.2--py36_0", "1.1.2--py35_0"], "1.1.2--py36_0"),
        (
            ["6725cda82000b8e514baddcbf8c2dce054e3f797-1", "6725cda82000b8e514baddcbf8c2dce054e3f797-0"],
            "6725cda82000b8e514baddcbf8c2dce054e3f797-1",
        ),
        (["python:3.5", "python:3.7", "python:3.7--2"], "python:3.7--2"),
    ],
)
def test_version_sorted(tags, tag):
    assert version_sorted(tags)[0] == tag


@responses.activate
def test_quay_tag_exists_uses_registry_head():
    session = requests.Session()
    responses.add(responses.HEAD, MANIFEST_URL, status=200)

    assert quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session) is True
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == MANIFEST_URL
    assert responses.calls[0].request.method == "HEAD"


@responses.activate
def test_quay_tag_exists_returns_false_for_missing_tag():
    session = requests.Session()
    responses.add(responses.HEAD, MANIFEST_URL, status=404)

    assert quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session) is False


@responses.activate
def test_quay_tag_exists_falls_back_to_repository_metadata():
    session = requests.Session()
    responses.add(responses.HEAD, MANIFEST_URL, status=502)
    responses.add(responses.GET, REPOSITORY_URL, json={"tags": {"1.17--0": {}}}, status=200)

    assert quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session) is True
    assert [call.request.method for call in responses.calls] == ["HEAD", "GET"]


@responses.activate
def test_quay_tag_exists_does_not_fall_back_for_non_transient_errors():
    session = requests.Session()
    responses.add(responses.HEAD, MANIFEST_URL, status=403)

    with pytest.raises(QuayApiException):
        quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session)
    assert len(responses.calls) == 1


@responses.activate
def test_quay_repository_returns_invalid_token_response_for_401():
    session = requests.Session()
    responses.add(responses.GET, REPOSITORY_URL, json={"error_type": "invalid_token"}, status=401)

    assert quay_repository("biocontainers", "samtools", session=session) == {"error_type": "invalid_token"}
