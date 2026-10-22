"""The DSpace file source against a fake DSpace REST API."""

import ipaddress
from urllib.parse import (
    parse_qsl,
    urlsplit,
)

import pytest
import responses

from galaxy.exceptions import (
    AuthenticationRequired,
    ConfigDoesNotAllowException,
    ObjectNotFound,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from ._util import (
    configured_file_sources,
    realize_to_temp_file,
)

API = "http://10.1.2.3/server/api"
CDN = "http://10.9.9.9/assetstore/abc"
COMMUNITY = "1b0a6f3e-3c7e-4a43-9a3e-6f1f5b0c0c01"
COLLECTION = "2c1b7a4f-4d8f-4b54-8b4f-7a2a6c1d1d02"
ITEM = "3d2c8b5a-5e9a-4c65-9c5a-8b3b7d2e2e03"
FASTQ = "4e3d9c6b-6fab-4d76-8d6b-9c4c8e3f3f04"
PDF = "5f4eadc7-7abc-4e87-9e7c-ad5d9f4a4a05"


def _source(**kwd):
    allowlist = [ipaddress.ip_network("10.0.0.0/8")]
    conf = {"type": "dspace", "id": "dspace", "api_url": API, **kwd}
    return configured_file_sources([conf], FileSourcePluginsConfig(fetch_url_allowlist=allowlist))


def _page(key, objects):
    return {"_embedded": {key: objects}, "page": {"totalElements": len(objects)}}


def _fake_repository():
    responses.get(f"{API}/core/communities/search/top", json=_page("communities", [{"uuid": COMMUNITY, "name": "Lab"}]))
    responses.get(f"{API}/core/communities/{COMMUNITY}/subcommunities", json=_page("subcommunities", []))
    responses.get(
        f"{API}/core/communities/{COMMUNITY}/collections",
        json=_page("collections", [{"uuid": COLLECTION, "name": "Data"}]),
    )
    item = {"_embedded": {"indexableObject": {"uuid": ITEM, "name": "Run 1"}}}
    responses.get(
        f"{API}/discover/search/objects",
        json={"_embedded": {"searchResult": {**_page("objects", [item])}}},
    )
    bundles = [{"uuid": "b1", "name": "ORIGINAL"}, {"uuid": "b2", "name": "THUMBNAIL"}]
    responses.get(f"{API}/core/items/{ITEM}/bundles", json=_page("bundles", bundles))
    bitstream = {
        "uuid": FASTQ,
        "name": "reads.fastq",
        "sizeBytes": 3,
        "checkSum": {"checkSumAlgorithm": "MD5", "value": "900150983cd24fb0d6963f7d28e17f72"},
    }
    pdf = {**bitstream, "uuid": PDF, "name": "paper.pdf", "_embedded": {"format": {"mimetype": "application/pdf"}}}
    responses.get(f"{API}/core/bundles/b1/bitstreams", json=_page("bitstreams", [bitstream, pdf]))
    responses.get(f"{API}/core/bundles/b2/bitstreams", json=_page("bitstreams", [{"uuid": "t1", "name": "reads.jpg"}]))


@responses.activate
def test_browse_down_to_the_original_files():
    _fake_repository()
    file_source = _source().get_file_source_path("gxfiles://dspace").file_source

    def names(path, **kwd):
        return [(entry.name, entry.path) for entry in file_source.list(path, **kwd)[0]]

    assert names("/", limit=10, offset=0) == [("Lab", f"/communities/{COMMUNITY}")]
    assert names(f"/communities/{COMMUNITY}") == [("Data", f"/collections/{COLLECTION}")]
    assert names(f"/collections/{COLLECTION}", limit=10, offset=10, query="run a-b") == [("Run 1", f"/items/{ITEM}")]
    assert dict(parse_qsl(urlsplit(str(responses.calls[-1].request.url)).query)) == {
        "dsoType": "ITEM",
        "scope": COLLECTION,
        "sort": "dc.title,ASC",
        "query": "run* a-b",
        "size": "10",
        "page": "1",
    }
    files = file_source.list(f"/items/{ITEM}")[0]
    assert [(entry.name, entry.uri) for entry in files] == [
        ("reads.fastq", f"gxfiles://dspace/bitstreams/{FASTQ}/reads.fastq"),
        ("paper.pdf", f"gxfiles://dspace/bitstreams/{PDF}/paper.pdf"),
    ]
    assert files[0].hashes[0].hash_value == "900150983cd24fb0d6963f7d28e17f72"
    # a citation cover page can change a PDF, so its MD5 is not passed on
    assert files[1].hashes is None


@responses.activate
def test_download_checks_every_redirect_and_keeps_the_token_on_dspace():
    _fake_repository()
    responses.get(f"{API}/core/bitstreams/{FASTQ}/content", status=302, headers={"Location": CDN})
    responses.get(CDN, body=b"abc")
    file_sources = _source(token="secret")
    assert realize_to_temp_file(file_sources, f"gxfiles://dspace/bitstreams/{FASTQ}/reads.fastq") == "abc"
    auth = {str(call.request.url).split("?")[0]: call.request.headers.get("Authorization") for call in responses.calls}
    assert auth[f"{API}/core/bitstreams/{FASTQ}/content"] == "Bearer secret"
    assert auth[CDN] is None

    responses.replace(responses.GET, f"{API}/core/bitstreams/{FASTQ}/content", status=400)
    with pytest.raises(AuthenticationRequired):
        realize_to_temp_file(file_sources, f"gxfiles://dspace/bitstreams/{FASTQ}/reads.fastq")
    responses.replace(responses.GET, f"{API}/core/bitstreams/{FASTQ}/content", status=302, headers={"Location": CDN})
    # an expired token still lists, but only what is public
    responses.get(f"{API}/authn/status", json={"authenticated": False})
    with pytest.raises(AuthenticationRequired):
        file_sources.get_file_source_path("gxfiles://dspace").file_source.list("/")

    responses.replace(responses.GET, CDN, status=302, headers={"Location": "http://169.254.169.254/latest"})
    responses.get("http://169.254.169.254/latest", body=b"secret")
    with pytest.raises(ConfigDoesNotAllowException):
        realize_to_temp_file(file_sources, f"gxfiles://dspace/bitstreams/{FASTQ}/reads.fastq")
    assert not any("169.254" in str(call.request.url) for call in responses.calls)


@responses.activate
def test_an_id_that_is_not_a_uuid_is_not_found_without_asking_dspace():
    file_sources = _source(token="secret")
    with pytest.raises(ObjectNotFound):
        realize_to_temp_file(file_sources, "gxfiles://dspace/bitstreams/not-a-uuid/reads.fastq")
    for path in ("/communities/not-a-uuid", "/collections/c1", "/items/{ITEM}?x"):
        with pytest.raises(ObjectNotFound):
            file_sources.get_file_source_path("gxfiles://dspace").file_source.list(path.format(ITEM=ITEM))
    assert not responses.calls
