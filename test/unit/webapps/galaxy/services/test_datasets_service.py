import pytest

from galaxy.webapps.galaxy.services.datasets import is_direct_download_candidate


@pytest.mark.parametrize(
    ("filename", "to_ext", "raw", "offset", "ck_size", "is_archive", "expected"),
    [
        # plain download (floppy disk / bioblend) -> candidate
        (None, "data", False, None, None, False, True),
        # raw byte access of the main file -> candidate
        (None, None, True, None, None, False, True),
        # preview / display (no to_ext, not raw) -> not a candidate
        (None, None, False, None, None, False, False),
        # extra-files access -> not a candidate
        ("index.html", None, True, None, None, False, False),
        ("subfile", "data", False, None, None, False, False),
        # chunked display -> not a candidate
        (None, "data", False, 0, None, False, False),
        (None, "data", False, None, 1024, False, False),
        # composite/archived datatypes are zipped through Galaxy -> not a candidate
        (None, "data", False, None, None, True, False),
        (None, None, True, None, None, True, False),
    ],
)
def test_is_direct_download_candidate(filename, to_ext, raw, offset, ck_size, is_archive, expected):
    assert is_direct_download_candidate(filename, to_ext, raw, offset, ck_size, is_archive) is expected
