"""The HAL file source against canned HAL search and file responses, so CI does not need HAL."""

import socket
from datetime import (
    datetime,
    timezone,
)

import pytest
import responses

from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    MessageException,
    ObjectNotFound,
)
from galaxy.files.models import RemoteFile
from ._util import configured_file_sources

API_URL = "https://api.hal.science/search/"
RECORD = {
    "halId_s": "hal-01479142",
    "version_i": 2,
    "title_s": ["Bovine structural variants"],
    "files_s": ["https://hal.science/hal-01479142/file/article.pdf"],
    "fileAnnexes_s": [
        "https://hal.univ-lorraine.fr/hal-01479142/file/variants%20table.xlsx",
        "https://hal.science/hal-01479142/file/report.html",
        "https://zenodo.org/records/1/files/data.csv",
        "https://hal.science/hal-01479142/file/..",
    ],
}
ARTICLE_URL = "https://hal.science/hal-01479142v2/file/article.pdf"
TABLE_URL = "https://hal.science/hal-01479142v2/file/variants%20table.xlsx"
REPORT_URL = "https://hal.science/hal-01479142v2/file/report.html"


@pytest.fixture(autouse=True)
def hal_hosts_resolve_publicly(monkeypatch):
    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        if host.endswith(("hal.science", ".fr")):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        return real_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


@pytest.fixture
def hal():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


def _source():
    file_sources = configured_file_sources([{"type": "hal", "id": "hal", "api_url": API_URL}])
    return file_sources.get_file_source_path("gxfiles://hal").file_source


def _add_search(hal, docs, num_found=None):
    num_found = len(docs) if num_found is None else num_found
    hal.add(responses.GET, API_URL, json={"response": {"docs": docs, "numFound": num_found}})


def _realize(path, tmp_path):
    target = tmp_path / "out"
    _source().realize_to(path, str(target))
    return target.read_bytes()


def test_search_lists_deposits_with_total_matches(hal):
    _add_search(hal, [RECORD], num_found=42)

    entries, total = _source().list("/", limit=2, offset=4, query="title_t:RNA")

    assert total == 42
    assert [(entry.name, entry.uri) for entry in entries] == [
        ("Bovine structural variants (hal-01479142v2)", "gxfiles://hal/hal-01479142v2")
    ]
    params = hal.calls[0].request.params
    assert (params["q"], params["rows"], params["start"]) == ("title_t:RNA", "2", "4")
    assert params["fq"] == "fileType_s:(file OR annex)"


def test_deposit_lists_files_from_hal_portals_with_size_and_time(hal):
    _add_search(hal, [RECORD])
    last_modified = "Thu, 22 Oct 2020 12:20:16 GMT"
    hal.add(responses.HEAD, ARTICLE_URL, headers={"Content-Length": "123", "Last-Modified": last_modified})
    hal.add(responses.HEAD, TABLE_URL, headers={"Content-Length": "456"})
    hal.add(responses.HEAD, REPORT_URL, headers={"Content-Length": "789", "Content-Encoding": "gzip"})

    entries, total = _source().list("/hal-01479142v2/", limit=25)
    files = [entry for entry in entries if isinstance(entry, RemoteFile)]

    assert total == 3
    assert [(file.name, file.uri) for file in files] == [
        ("article.pdf", "gxfiles://hal/hal-01479142v2/article.pdf"),
        ("report.html", "gxfiles://hal/hal-01479142v2/report.html"),
        ("variants table.xlsx", "gxfiles://hal/hal-01479142v2/variants%20table.xlsx"),
    ]
    assert [file.size for file in files] == [123, 0, 456]
    assert files[0].ctime == datetime(2020, 10, 22, 12, 20, 16, tzinfo=timezone.utc)
    assert files[2].ctime is None


def test_deposit_listing_filters_and_pages_file_names(hal):
    _add_search(hal, [RECORD])
    hal.add(responses.HEAD, TABLE_URL, headers={"Content-Length": "456"})

    entries, total = _source().list("/hal-01479142v2", limit=1, offset=1, query="A")

    assert total == 2
    assert [entry.name for entry in entries] == ["variants table.xlsx"]


def test_deposit_listing_without_limit_does_not_probe_files(hal):
    _add_search(hal, [RECORD])

    entries, total = _source().list("/hal-01479142v2")

    assert total == 3
    assert len(hal.calls) == 1


def test_listing_an_older_version_names_the_current_one(hal):
    _add_search(hal, [RECORD])

    with pytest.raises(MessageException, match="browse hal-01479142v2"):
        _source().list("/hal-01479142v1")


def test_invalid_paths_are_not_found(hal):
    for path in ("/not-a-record", "/hal-01479142v0", "/hal-01479142v2/a/b"):
        with pytest.raises(ObjectNotFound):
            _source().list(path)
    assert not hal.calls


def test_imports_current_version_from_the_canonical_endpoint(hal, tmp_path):
    _add_search(hal, [RECORD])
    hal.add(responses.GET, TABLE_URL, body=b"table")

    assert _realize("/hal-01479142v2/variants%20table.xlsx", tmp_path) == b"table"


def test_imports_older_version_from_its_versioned_url(hal, tmp_path):
    _add_search(hal, [RECORD])
    old_url = "https://hal.univ-lorraine.fr/hal-01479142v1/file/old%20table.xlsx"
    hal.add(
        responses.GET,
        "https://hal.science/hal-01479142v1/file/old%20table.xlsx",
        status=301,
        headers={"Location": old_url},
    )
    hal.add(responses.GET, old_url, body=b"old table")

    assert _realize("/hal-01479142v1/old%20table.xlsx", tmp_path) == b"old table"


def test_unknown_version_is_not_found(hal, tmp_path):
    _add_search(hal, [RECORD])
    hal.add(responses.GET, "https://hal.science/hal-01479142v3/file/article.pdf", status=404, content_type="text/html")

    with pytest.raises(ObjectNotFound):
        _realize("/hal-01479142v3/article.pdf", tmp_path)


def test_html_attachment_imports_but_an_html_page_for_other_files_is_refused(hal, tmp_path):
    _add_search(hal, [RECORD])
    hal.add(responses.GET, REPORT_URL, body=b"<html></html>", content_type="text/html")
    hal.add(responses.GET, ARTICLE_URL, body=b"<html>login</html>", content_type="text/html")

    assert _realize("/hal-01479142v2/report.html", tmp_path) == b"<html></html>"
    with pytest.raises(MessageException, match="HTML page"):
        _realize("/hal-01479142v2/article.pdf", tmp_path)


def test_embargoed_file_is_refused(hal, tmp_path):
    _add_search(hal, [RECORD])
    hal.add(responses.GET, ARTICLE_URL, status=403)

    with pytest.raises(MessageException, match="embargo"):
        _realize("/hal-01479142v2/article.pdf", tmp_path)


def test_redirect_to_a_local_address_is_refused(hal, tmp_path):
    _add_search(hal, [RECORD])
    hal.add(responses.GET, ARTICLE_URL, status=302, headers={"Location": "http://127.0.0.1/secret"})

    with pytest.raises(ConfigDoesNotAllowException):
        _realize("/hal-01479142v2/article.pdf", tmp_path)
    assert [call.request.url for call in hal.calls][-1] == ARTICLE_URL


@pytest.mark.parametrize("path", ["/hal-01479142v2", "/hal-01479142v2/"])
@pytest.mark.parametrize("options", [{}, {"limit": 1, "offset": 1, "query": "article"}])
def test_recursive_deposit_listing_returns_all_files_without_probing(hal, path, options):
    _add_search(hal, [RECORD])
    source = _source()

    assert source.supports_recursive
    entries, total = source.list(path, recursive=True, **options)

    assert total == 3
    assert [entry.name for entry in entries] == ["article.pdf", "report.html", "variants table.xlsx"]
    assert all(isinstance(entry, RemoteFile) for entry in entries)
    assert [(call.request.method, call.request.url.split("?")[0]) for call in hal.calls] == [("GET", API_URL)]


@pytest.mark.parametrize("path", ["", "/"])
def test_recursive_root_listing_is_refused_without_requests(hal, path):
    with pytest.raises(MessageException, match="HAL root"):
        _source().list(path, recursive=True)
    assert not hal.calls


def test_recursive_listing_of_an_older_version_is_refused(hal):
    _add_search(hal, [RECORD])
    with pytest.raises(MessageException, match="browse hal-01479142v2"):
        _source().list("/hal-01479142v1", recursive=True)


@pytest.mark.parametrize("method", [responses.GET, responses.HEAD])
def test_canonical_endpoint_can_redirect_to_a_portal(hal, tmp_path, method):
    _add_search(hal, [RECORD])
    portal_url = "https://hal.univ-lorraine.fr/hal-01479142v2/file/variants%20table.xlsx"
    hal.add(method, TABLE_URL, status=302, headers={"Location": portal_url})
    hal.add(method, portal_url, body=b"table", headers={"Content-Length": "5"})

    if method == responses.GET:
        assert _realize("/hal-01479142v2/variants%20table.xlsx", tmp_path) == b"table"
    else:
        entries, total = _source().list("/hal-01479142v2", limit=1, query="variants")
        assert total == 1
        assert entries[0].size == 5
    assert [call.request.url for call in hal.calls][-2:] == [TABLE_URL, portal_url]


def test_indexed_host_is_not_contacted_and_duplicate_attachments_are_collapsed(hal, tmp_path):
    record = {
        **RECORD,
        "files_s": [
            "https://unrelated.example/hal-01479142/file/article.pdf",
            "https://hal.science/hal-01479142v2/file/article.pdf",
        ],
        "fileAnnexes_s": [],
    }
    _add_search(hal, [record])
    hal.add(responses.HEAD, ARTICLE_URL, headers={"Content-Length": "7"})
    hal.add(responses.GET, ARTICLE_URL, body=b"article")

    entries, total = _source().list("/hal-01479142v2", limit=25)
    assert total == 1
    assert entries[0].name == "article.pdf"
    assert entries[0].size == 7
    assert _realize("/hal-01479142v2/article.pdf", tmp_path) == b"article"
    assert all(call.request.url.split("?")[0] in (API_URL, ARTICLE_URL) for call in hal.calls)


def test_search_page_includes_legacy_underscore_identifiers(hal):
    legacy = {**RECORD, "halId_s": "sic_01002025", "version_i": 1}
    _add_search(hal, [RECORD, legacy], num_found=225)

    entries, total = _source().list("/", limit=25, offset=200)

    assert total == 225
    assert [entry.uri for entry in entries] == [
        "gxfiles://hal/hal-01479142v2",
        "gxfiles://hal/sic_01002025v1",
    ]


def test_legacy_underscore_deposit_can_be_listed_and_imported(hal, tmp_path):
    record = {
        "halId_s": "sic_01002025",
        "version_i": 1,
        "files_s": ["https://archivesic.ccsd.cnrs.fr/sic_01002025/file/article.pdf"],
    }
    _add_search(hal, [record])
    url = "https://hal.science/sic_01002025v1/file/article.pdf"
    hal.add(responses.GET, url, body=b"article")

    entries, total = _source().list("/sic_01002025v1", recursive=True)

    assert total == 1
    assert entries[0].uri == "gxfiles://hal/sic_01002025v1/article.pdf"
    assert _realize("/sic_01002025v1/article.pdf", tmp_path) == b"article"
    assert hal.calls[0].request.params["q"] == 'halId_s:"sic_01002025"'


def test_search_api_error_is_reported_as_a_search_failure(hal):
    hal.add(responses.GET, API_URL, json={"error": {"msg": "cURL error (28): Timeout was reached"}})

    with pytest.raises(MessageException, match="narrow your search"):
        _source().list("/", limit=25, offset=1850625)


@pytest.mark.parametrize("payload", [{}, {"response": {"docs": [], "numFound": "invalid"}}])
def test_malformed_search_response_is_reported(hal, payload):
    hal.add(responses.GET, API_URL, json=payload)

    with pytest.raises(MessageException, match="Invalid response"):
        _source().list("/")
