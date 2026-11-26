from unittest import mock

import pytest
import responses

from galaxy.files.sources.bioairepo import BioAIRepoFilesSource
from ._util import configured_file_sources

API_URL = "https://example.org/api/v1"
FILES_URL = "https://example.org/files"
SEARCH_URL = f"{API_URL}/BioAIRepo/search"
STUDY_URL = f"{API_URL}/studies/S-BAIR2"

STUDY = {
    "accno": "S-BAIR2",
    "section": {
        "type": "Study",
        "files": [
            [
                {"path": "model.yaml", "size": 1472, "type": "file"},
                {"path": "models/weights.h5", "size": 787632, "type": "file"},
                {"path": "models/nested/config.json", "size": 42, "type": "file"},
                {"path": "../unsafe.txt", "size": 1, "type": "file"},
            ]
        ],
        "subsections": [
            {"type": "Results", "files": {"path": "predictions.h5", "size": 354135, "type": "file"}}
        ],
    },
}


def source_config():
    return {
        "type": "bioairepo",
        "id": "bioairepo",
        "api_url": API_URL,
        "files_url": FILES_URL,
        "collection": "BioAIRepo",
    }


def get_source():
    sources = configured_file_sources([source_config()])
    return sources.get_file_source_path("bioairepo://bioairepo").file_source


def entry_names(entries):
    return [(entry.class_, entry.name) for entry in entries]


def test_plugin_is_discovered_and_read_only():
    source = get_source()
    assert isinstance(source, BioAIRepoFilesSource)
    assert source.get_browsable()
    assert not source.get_writable()
    assert source.get_uri_root() == "bioairepo://bioairepo"


def test_writable_configuration_is_rejected():
    config = source_config()
    config["writable"] = True
    with pytest.raises(ValueError, match="read-only"):
        configured_file_sources([config])


@responses.activate
def test_lists_collection_studies_with_server_side_search_and_pagination():
    responses.add(
        responses.GET,
        SEARCH_URL,
        json={
            "page": 2,
            "pageSize": 2,
            "totalHits": 4,
            "hits": [
                {"accession": "S-BAIR2", "title": "SiSp"},
                {"accession": "S-BAIR3", "title": "decoupler"},
            ],
        },
    )
    source = get_source()
    with mock.patch("galaxy.files.sources.bioairepo.validate_non_local", side_effect=lambda url, allowlist: url):
        entries, total = source.list("/", limit=2, offset=2, query="splicing")

    assert entry_names(entries) == [("Directory", "S-BAIR2"), ("Directory", "S-BAIR3")]
    assert total == 4
    request_url = responses.calls[0].request.url
    assert "page=2" in request_url
    assert "pageSize=2" in request_url
    assert "query=splicing" in request_url


@responses.activate
def test_lists_nested_study_files_and_ignores_unsafe_paths():
    responses.add(responses.GET, STUDY_URL, json=STUDY)
    responses.add(responses.GET, STUDY_URL, json=STUDY)
    source = get_source()
    with mock.patch("galaxy.files.sources.bioairepo.validate_non_local", side_effect=lambda url, allowlist: url):
        root_entries, root_total = source.list("/S-BAIR2")
        nested_entries, nested_total = source.list("/S-BAIR2/models")

    assert entry_names(root_entries) == [
        ("Directory", "models"),
        ("File", "model.yaml"),
        ("File", "predictions.h5"),
    ]
    assert root_total == 3
    assert entry_names(nested_entries) == [("Directory", "nested"), ("File", "weights.h5")]
    assert nested_total == 2
    weights = nested_entries[1]
    assert weights.size == 787632
    assert weights.uri == "bioairepo://bioairepo/S-BAIR2/models/weights.h5"


@responses.activate
def test_realizes_file_for_galaxy_upload(tmp_path):
    responses.add(responses.GET, STUDY_URL, json=STUDY)
    responses.add(responses.GET, f"{FILES_URL}/S-BAIR2/models/weights.h5", body=b"model weights")
    source = get_source()
    target = tmp_path / "weights.h5"
    with mock.patch("galaxy.files.sources.bioairepo.validate_non_local", side_effect=lambda url, allowlist: url):
        source.realize_to("/S-BAIR2/models/weights.h5", str(target))

    assert target.read_bytes() == b"model weights"


def test_write_is_rejected(tmp_path):
    source = get_source()
    with pytest.raises(Exception, match="non-writable"):
        source.write_from("/S-BAIR2/file.txt", str(tmp_path / "file.txt"))


@pytest.mark.parametrize(
    "folder, expected",
    [
        ("/S-BAIR2", {"model.yaml", "predictions.h5", "models/weights.h5", "models/nested/config.json"}),
        ("/S-BAIR2/models", {"models/weights.h5", "models/nested/config.json"}),
        ("/S-BAIR2/models/nested", {"models/nested/config.json"}),
    ],
)
@responses.activate
def test_import_files_from_each_folder(folder, expected, tmp_path):
    responses.add(responses.GET, STUDY_URL, json=STUDY)
    source = get_source()
    assert source.supports_recursive
    with mock.patch("galaxy.files.sources.bioairepo.validate_non_local", side_effect=lambda url, allowlist: url):
        entries, total = source.list(folder, recursive=True)
        files = [entry for entry in entries if entry.class_ == "File"]
        assert {entry.path.removeprefix("/S-BAIR2/") for entry in files} == expected
        assert total == len(entries)
        for index, entry in enumerate(files):
            relative_path = entry.path.removeprefix("/S-BAIR2/")
            content = relative_path.encode()
            responses.add(responses.GET, f"{FILES_URL}/S-BAIR2/{relative_path}", body=content)
            target = tmp_path / str(index)
            source.realize_to(entry.path, str(target))
            assert target.read_bytes() == content


def test_recursive_collection_import_requires_a_study_folder():
    with pytest.raises(Exception, match="Select a BioAIRepo study folder"):
        get_source().list("/", recursive=True)
