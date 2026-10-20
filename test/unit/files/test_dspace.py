"""The DSpace file source against a fake DSpace REST API."""

import ipaddress
from urllib.parse import (
    parse_qsl,
    urlsplit,
)

import pytest
import responses

from galaxy.exceptions import ConfigDoesNotAllowException
from galaxy.files.plugins import FileSourcePluginsConfig
from ._util import (
    configured_file_sources,
    realize_to_temp_file,
)

API = "http://10.1.2.3/server/api"
CDN = "http://10.9.9.9/assetstore/abc"


def _source(**kwd):
    allowlist = [ipaddress.ip_network("10.0.0.0/8")]
    conf = {"type": "dspace", "id": "dspace", "api_url": API, **kwd}
    return configured_file_sources([conf], FileSourcePluginsConfig(fetch_url_allowlist=allowlist))


def _page(key, objects):
    return {"_embedded": {key: objects}, "page": {"totalElements": len(objects)}}


def _fake_repository():
    responses.get(f"{API}/core/communities/search/top", json=_page("communities", [{"uuid": "c1", "name": "Lab"}]))
    responses.get(f"{API}/core/communities/c1/subcommunities", json=_page("subcommunities", []))
    responses.get(
        f"{API}/core/communities/c1/collections", json=_page("collections", [{"uuid": "col1", "name": "Data"}])
    )
    item = {"_embedded": {"indexableObject": {"uuid": "i1", "name": "Run 1"}}}
    responses.get(
        f"{API}/discover/search/objects",
        json={"_embedded": {"searchResult": {**_page("objects", [item])}}},
    )
    bundles = [{"uuid": "b1", "name": "ORIGINAL"}, {"uuid": "b2", "name": "THUMBNAIL"}]
    responses.get(f"{API}/core/items/i1/bundles", json=_page("bundles", bundles))
    bitstream = {
        "uuid": "f1",
        "name": "reads.fastq",
        "sizeBytes": 3,
        "checkSum": {"checkSumAlgorithm": "MD5", "value": "900150983cd24fb0d6963f7d28e17f72"},
    }
    pdf = {**bitstream, "uuid": "f2", "name": "paper.pdf", "_embedded": {"format": {"mimetype": "application/pdf"}}}
    responses.get(f"{API}/core/bundles/b1/bitstreams", json=_page("bitstreams", [bitstream, pdf]))
    responses.get(f"{API}/core/bundles/b2/bitstreams", json=_page("bitstreams", [{"uuid": "t1", "name": "reads.jpg"}]))


@responses.activate
def test_browse_down_to_the_original_files():
    _fake_repository()
    file_source = _source().get_file_source_path("gxfiles://dspace").file_source

    def names(path, **kwd):
        return [(entry.name, entry.path) for entry in file_source.list(path, **kwd)[0]]

    assert names("/", limit=10, offset=0) == [("Lab", "/communities/c1")]
    assert names("/communities/c1") == [("Data", "/collections/col1")]
    assert names("/collections/col1", limit=10, offset=10, query="run a-b") == [("Run 1", "/items/i1")]
    assert dict(parse_qsl(urlsplit(str(responses.calls[-1].request.url)).query)) == {
        "dsoType": "ITEM",
        "scope": "col1",
        "sort": "dc.title,ASC",
        "query": "run* a-b",
        "size": "10",
        "page": "1",
    }
    files = file_source.list("/items/i1")[0]
    assert [(entry.name, entry.uri) for entry in files] == [
        ("reads.fastq", "gxfiles://dspace/bitstreams/f1/reads.fastq"),
        ("paper.pdf", "gxfiles://dspace/bitstreams/f2/paper.pdf"),
    ]
    assert files[0].hashes[0].hash_value == "900150983cd24fb0d6963f7d28e17f72"
    # a citation cover page can change a PDF, so its MD5 is not passed on
    assert files[1].hashes is None


@responses.activate
def test_download_checks_every_redirect_and_keeps_the_token_on_dspace():
    _fake_repository()
    responses.get(f"{API}/core/bitstreams/f1/content", status=302, headers={"Location": CDN})
    responses.get(CDN, body=b"abc")
    file_sources = _source(token="secret")
    assert realize_to_temp_file(file_sources, "gxfiles://dspace/bitstreams/f1/reads.fastq") == "abc"
    auth = {str(call.request.url).split("?")[0]: call.request.headers.get("Authorization") for call in responses.calls}
    assert auth[f"{API}/core/bitstreams/f1/content"] == "Bearer secret"
    assert auth[CDN] is None

    responses.replace(responses.GET, CDN, status=302, headers={"Location": "http://169.254.169.254/latest"})
    responses.get("http://169.254.169.254/latest", body=b"secret")
    with pytest.raises(ConfigDoesNotAllowException):
        realize_to_temp_file(file_sources, "gxfiles://dspace/bitstreams/f1/reads.fastq")
    assert not any("169.254" in str(call.request.url) for call in responses.calls)
