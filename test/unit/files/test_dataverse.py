from ._util import configured_file_sources

MD5 = {"checksum": {"type": "MD5", "value": "887d4b7467d3c40c8b6176c57d568eac"}}


def test_converted_tabular_files_have_no_hash():
    file_sources = configured_file_sources([{"type": "dataverse", "id": "dv", "url": "https://dataverse.example.org"}])
    repository = file_sources.get_file_source_path("gxfiles://dv").file_source.repository
    files = repository._get_files_from_response(
        "doi:10.7910/DVN/25551",
        [
            {"dataFile": {"id": 1, "filename": "notes.pdf", "filesize": 3, **MD5}},
            {
                "dataFile": {
                    "id": 2,
                    "filename": "rev_lit.tab",
                    "filesize": 3,
                    "originalFileFormat": "application/x-spss-sav",
                    **MD5,
                }
            },
        ],
    )
    assert files[0].hashes[0].hash_value == MD5["checksum"]["value"]
    assert files[1].hashes is None
