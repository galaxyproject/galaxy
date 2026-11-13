import gzip
import hashlib

import pytest

from galaxy.tool_util.unittest_utils import t_data_downloader_for
from galaxy.tool_util.verify import verify


def test_writes_output_to_target_directory(tmp_path):
    item_label = "my test case"
    output_content = b"expected"
    filename = "my_output.txt"

    assert not (tmp_path / filename).exists()
    verify(
        item_label,
        output_content,
        attributes={},
        filename=filename,
        keep_outputs_dir=str(tmp_path),
        get_filecontent=t_data_downloader_for(output_content),
    )
    assert (tmp_path / filename).exists()
    assert (tmp_path / filename).open("rb").read() == output_content


def test_no_writes_output_to_target_directory_on_contains(tmp_path):
    item_label = "my test case"
    output_content = b"expected"
    attributes = {
        "compare": "contains",
    }
    filename = "my_output.txt"

    get_filecontent = t_data_downloader_for(b"xpecte")
    assert not (tmp_path / filename).exists()
    verify(
        item_label,
        output_content,
        attributes=attributes,
        filename=filename,
        keep_outputs_dir=str(tmp_path),
        get_filecontent=get_filecontent,
    )
    # Consider switching this to not update - see discussion on
    # https://github.com/galaxyproject/galaxy/pull/14661
    assert (tmp_path / filename).exists()


def test_sim_size(tmp_path):
    item_label = "my test case"
    output_content = b"expected"
    attributes = {
        "compare": "sim_size",
        "delta": 2,
    }
    filename = "my_output.txt"

    get_filecontent = t_data_downloader_for(b"xpected")
    assert not (tmp_path / filename).exists()
    verify(
        item_label,
        output_content,
        attributes=attributes,
        filename=filename,
        keep_outputs_dir=str(tmp_path),
        get_filecontent=get_filecontent,
    )
    assert (tmp_path / filename).exists()
    assert (tmp_path / filename).open("rb").read() == b"expected"


def test_sim_size_failure_still_updates(tmp_path):
    item_label = "my test case"
    output_content = b"expected"
    attributes = {
        "compare": "sim_size",
        "delta": 2,
    }
    filename = "my_output.txt"

    get_filecontent = t_data_downloader_for(b"ected")
    assert not (tmp_path / filename).exists()
    assertion_error = None
    try:
        verify(
            item_label,
            output_content,
            attributes=attributes,
            filename=filename,
            keep_outputs_dir=str(tmp_path),
            get_filecontent=get_filecontent,
        )
    except AssertionError as ae:
        assertion_error = ae

    assert assertion_error
    assert (tmp_path / filename).exists()
    assert (tmp_path / filename).open("rb").read() == b"expected"


GZ_CONTENT = b"@read1\nACGT\n+\nIIII\n"


@pytest.mark.parametrize(
    "checksum_of, decompress, error_match",
    [
        ("decompressed", True, None),
        ("compressed", True, "checksum of the decompressed content"),
        ("compressed", False, None),
        ("decompressed", False, "checksum"),
    ],
)
def test_checksum_honors_decompress(checksum_of, decompress, error_match):
    compressed = gzip.compress(GZ_CONTENT)
    hashed = GZ_CONTENT if checksum_of == "decompressed" else compressed
    attributes = {"checksum": f"md5${hashlib.md5(hashed).hexdigest()}", "decompress": decompress}
    if error_match is None:
        verify("out", compressed, attributes=attributes)
    else:
        with pytest.raises(AssertionError, match=error_match):
            verify("out", compressed, attributes=attributes)


def test_checksum_with_decompress_on_uncompressed_output():
    attributes = {"checksum": f"md5${hashlib.md5(GZ_CONTENT).hexdigest()}", "decompress": True}
    verify("out", GZ_CONTENT, attributes=attributes)


def test_md5_honors_decompress():
    compressed = gzip.compress(GZ_CONTENT)
    verify("out", compressed, attributes={"md5": hashlib.md5(GZ_CONTENT).hexdigest(), "decompress": True})


def test_corrupt_compressed_output_is_an_assertion_error():
    truncated = gzip.compress(GZ_CONTENT)[:-8]
    with pytest.raises(AssertionError, match="could not be decompressed"):
        verify("out", truncated, attributes={"checksum": "md5$" + "0" * 32, "decompress": True})


def test_corrupt_compressed_output_with_assertions_is_an_assertion_error():
    truncated = gzip.compress(GZ_CONTENT)[:-8]
    assert_list = [{"tag": "has_text", "attributes": {"text": "ACGT"}, "children": []}]
    with pytest.raises(AssertionError, match="out could not be decompressed"):
        verify("out", truncated, attributes={"assert_list": assert_list, "decompress": True})
