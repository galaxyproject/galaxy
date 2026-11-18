"""The RADAR file source against a fake RADAR API that serves a real dataset tar."""

import hashlib
import io
import ipaddress
import json
import re
import tarfile
from urllib.parse import (
    parse_qsl,
    urlsplit,
)

import pytest
import responses

from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources import radar
from ._util import (
    configured_file_sources,
    realize_to_temp_file,
)

BASE = "http://10.1.2.3"
DATASETS = f"{BASE}/radar/api/datasets"
DATASET = "AbCdEfGhIjKlMnOp"
CONTENT = f"{BASE}/radar-backend/archives/{DATASET}/versions/1/content"
READS = b"ACGT\n" * 40000
NOTES = b"notes\n"


def _tar(manifest_md5=None):
    files = {
        "data/readme.txt": b"about\n",
        "data/dataset/reads.fastq": READS,
        "data/dataset/sub/notes.txt": NOTES,
    }
    md5s = {name: hashlib.md5(body).hexdigest() for name, body in files.items()}
    if manifest_md5:
        md5s["data/dataset/reads.fastq"] = manifest_md5
    files["manifest-md5.txt"] = "".join(f"{md5}  {name}\n" for name, md5 in md5s.items()).encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, body in files.items():
            info = tarfile.TarInfo(f"10.1-{DATASET}/{name}")
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


def _fake_radar(tar, ranges="exact", total=1):
    archive = {"size": len(tar), "checksum": hashlib.md5(tar).hexdigest()}
    record = {"id": DATASET, "descriptiveMetadata": {"title": "Run 1"}, "archive": archive}

    def datasets(request):
        query = dict(parse_qsl(urlsplit(request.url).query))["query"]
        found = [record] if f"id:{DATASET} " in query or not query.startswith("id:") else []
        return 200, {}, json.dumps({"data": found, "totalHits": total if found else 0})

    def content(request):
        match = re.fullmatch(r"bytes=(\d+)-(\d+)", request.headers.get("Range", ""))
        if ranges == "ignored" or not match:
            return 200, {}, tar
        start, end = int(match[1]), len(tar) - 1 if ranges == "too long" else int(match[2])
        return 206, {"Content-Range": f"bytes {start}-{end}/{len(tar)}"}, tar[start : end + 1]

    responses.add_callback(responses.GET, DATASETS, callback=datasets)
    responses.get(f"{DATASETS}/{DATASET}/download", status=302, headers={"Location": CONTENT})
    responses.add_callback(responses.GET, CONTENT, callback=content)


@pytest.fixture(autouse=True)
def _empty_index_cache():
    radar._index_cache.clear()


def _source():
    allowlist = [ipaddress.ip_network("10.0.0.0/8")]
    conf = {"type": "radar", "id": "radar", "base_url": BASE}
    file_sources = configured_file_sources([conf], FileSourcePluginsConfig(fetch_url_allowlist=allowlist))
    return file_sources, file_sources.get_file_source_path("gxfiles://radar").file_source


def _queries():
    urls = [urlsplit(str(call.request.url)) for call in responses.calls]
    return [dict(parse_qsl(url.query)) for url in urls if url.query]


@responses.activate
def test_lists_published_datasets_and_keeps_a_search_inside_the_title():
    _fake_radar(_tar(), total=250)
    entries, total = _source()[1].list("/", limit=500, offset=20, query="Larval OR (")
    assert (total, [(entry.name, entry.path) for entry in entries]) == (250, [("Run 1", f"/{DATASET}")])
    assert _queries() == [
        {
            "query": "state:PUBLISHED AND technicalMetadata.archiveCreator:* "
            r"AND descriptiveMetadata.title:(larval* AND or* AND \(*)",
            "offset": "20",
            "rows": "100",
        }
    ]


@responses.activate
def test_lists_a_dataset_from_its_tar_headers_without_reading_the_files():
    tar = _tar()
    _fake_radar(tar)
    file_source = _source()[1]
    entries = file_source.list(f"/{DATASET}")[0]
    assert [(entry.name, entry.path, getattr(entry, "size", None)) for entry in entries] == [
        ("sub", f"/{DATASET}/sub", None),
        ("reads.fastq", f"/{DATASET}/reads.fastq", len(READS)),
    ]
    assert entries[1].hashes[0].hash_value == hashlib.md5(READS).hexdigest()
    ranges = [
        re.findall(r"\d+", call.request.headers["Range"]) for call in responses.calls if call.request.url == CONTENT
    ]
    assert sum(int(end) - int(start) + 1 for start, end in ranges) < len(READS) / 2
    assert "id:AbCdEfGhIjKlMnOp AND state:PUBLISHED" in _queries()[0]["query"]
    assert [entry.name for entry in file_source.list(f"/{DATASET}/sub")[0]] == ["notes.txt"]


@responses.activate
def test_downloads_one_file_with_one_range_request():
    tar = _tar()
    _fake_radar(tar)
    assert realize_to_temp_file(_source()[0], f"gxfiles://radar/{DATASET}/sub/notes.txt") == NOTES.decode()
    start = tar.index(NOTES)
    assert responses.calls[-1].request.headers["Range"] == f"bytes={start}-{start + len(NOTES) - 1}"


@responses.activate
def test_importing_several_files_of_a_dataset_reads_its_file_list_once():
    _fake_radar(_tar())
    file_sources = _source()[0]
    realize_to_temp_file(file_sources, f"gxfiles://radar/{DATASET}/sub/notes.txt")
    reads = len(responses.calls)
    realize_to_temp_file(file_sources, f"gxfiles://radar/{DATASET}/reads.fastq")
    # the dataset lookup, then the download link and the range request it redirects to
    assert len(responses.calls) - reads == 3


@responses.activate
def test_a_download_that_does_not_match_the_manifest_fails():
    _fake_radar(_tar(manifest_md5="0" * 32))
    with pytest.raises(MessageException, match="does not match"):
        realize_to_temp_file(_source()[0], f"gxfiles://radar/{DATASET}/reads.fastq")


@pytest.mark.parametrize("ranges", ["ignored", "too long"])
@responses.activate
def test_a_server_that_does_not_answer_the_exact_range_is_not_read(ranges):
    _fake_radar(_tar(), ranges=ranges)
    with pytest.raises(MessageException, match="did not answer a partial download"):
        _source()[1].list(f"/{DATASET}")


@pytest.mark.parametrize("limit, value", [("MAX_MEMBERS", 2), ("MAX_INDEX_BYTES", 1024)])
@responses.activate
def test_a_tar_too_large_to_list_is_refused(monkeypatch, limit, value):
    monkeypatch.setattr(radar, limit, value)
    _fake_radar(_tar())
    with pytest.raises(MessageException, match="more than 2 files|too many files"):
        _source()[1].list(f"/{DATASET}")


@pytest.mark.parametrize("path", ["/../etc", "/a b", "/Ab-Cd"])
@responses.activate
def test_an_invalid_id_is_not_found_without_asking_radar(path):
    with pytest.raises(ObjectNotFound):
        _source()[1].list(path)
    assert not responses.calls


@responses.activate
def test_only_published_datasets_and_their_data_files_are_found():
    _fake_radar(_tar())
    file_sources, file_source = _source()
    with pytest.raises(ObjectNotFound, match="no published RADAR dataset"):
        file_source.list("/OtherDataset0000")
    # names are matched exactly against the files below data/dataset, so .. cannot reach data/readme.txt
    with pytest.raises(ObjectNotFound, match="not a file"):
        realize_to_temp_file(file_sources, f"gxfiles://radar/{DATASET}/../readme.txt")


def test_recursive_listing_is_invalid():
    with pytest.raises(RequestParameterInvalidException, match="Recursive listing"):
        _source()[1].list("/", recursive=True)


@responses.activate
def test_a_redirect_to_a_private_address_is_refused_before_it_is_requested():
    responses.get(DATASETS, json={"data": [{"id": DATASET, "archive": {"size": 1024}}], "totalHits": 1})
    responses.get(f"{DATASETS}/{DATASET}/download", status=302, headers={"Location": "http://169.254.169.254/x"})
    responses.get("http://169.254.169.254/x", body=b"secret")
    with pytest.raises(ConfigDoesNotAllowException):
        _source()[1].list(f"/{DATASET}")
    assert not any("169.254" in str(call.request.url) for call in responses.calls)


@responses.activate
def test_a_search_radar_cannot_parse_is_an_invalid_request():
    responses.get(DATASETS, status=400, json={"exception": "Cannot parse"})
    with pytest.raises(RequestParameterInvalidException, match="could not search for x"):
        _source()[1].list("/", limit=10, offset=0, query="x")
