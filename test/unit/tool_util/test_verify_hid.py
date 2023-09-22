from typing import (
    Callable,
    Dict,
    Optional,
)

from galaxy.tool_util.unittest_utils import t_data_downloader_for
from galaxy.tool_util.verify.interactor import verify_hid


def dataset_fetcher_for(
    expected_hda_id: str, content: Dict[Optional[str], bytes]
) -> Callable[[str, Optional[str]], bytes]:
    def get_content(hda_id, filename: Optional[str] = None) -> bytes:
        assert expected_hda_id == hda_id
        return content[filename]

    return get_content


TEST_ID = "mydatasetid"


def test_verify_hid_simple_pass():
    test_data_downloader = t_data_downloader_for(b"expected")
    dataset_fetcher = dataset_fetcher_for(TEST_ID, {None: b"expected"})
    verify_hid(
        "",
        TEST_ID,
        {},
        dataset_fetcher=dataset_fetcher,
        test_data_downloader=test_data_downloader,
    )


def test_verify_hid_simple_fail():
    test_data_downloader = t_data_downloader_for(b"expected")
    dataset_fetcher = dataset_fetcher_for(TEST_ID, {None: b"unexpected"})
    assertion_error = None
    try:
        verify_hid(
            "",
            TEST_ID,
            {},
            dataset_fetcher=dataset_fetcher,
            test_data_downloader=test_data_downloader,
        )
    except AssertionError as ae:
        assertion_error = ae
    assert assertion_error


def test_verify_extra_files_success(tmp_path):
    test_data_downloader = t_data_downloader_for(
        {
            "": b"expected",
            "test_extras/expected.txt": b"extra_expected",
        }
    )
    found_data = {
        None: b"expected",
        "extra_1": b"extra_expected",
    }
    extra_files = [{"type": "file", "name": "extra_1", "attributes": {}, "value": "test_extras/expected.txt"}]
    dataset_fetcher = dataset_fetcher_for(TEST_ID, found_data)
    assert not (tmp_path / "expected.txt").exists()
    verify_hid(
        "",
        TEST_ID,
        {"extra_files": extra_files},
        dataset_fetcher=dataset_fetcher,
        test_data_downloader=test_data_downloader,
        keep_outputs_dir=tmp_path,
    )
    extra_path = tmp_path / "test_extras" / "expected.txt"
    assert extra_path.exists()
    assert extra_path.open("rb").read() == b"extra_expected"


def test_verify_extra_files_failed(tmp_path):
    test_data_downloader = t_data_downloader_for(
        {
            "": b"expected",
            "test_extras/expected.txt": b"extra_expected",
        }
    )
    found_data = {
        None: b"expected",
        "extra_1": b"extra_unexpected",
    }
    extra_files = [{"type": "file", "name": "extra_1", "attributes": {}, "value": "test_extras/expected.txt"}]
    dataset_fetcher = dataset_fetcher_for(TEST_ID, found_data)
    assert not (tmp_path / "expected.txt").exists()
    assert_error = None
    try:
        verify_hid(
            "",
            TEST_ID,
            {"extra_files": extra_files},
            dataset_fetcher=dataset_fetcher,
            test_data_downloader=test_data_downloader,
            keep_outputs_dir=tmp_path,
        )
    except AssertionError as ae:
        assert_error = ae
    assert assert_error
    assert "Composite file (extra_1) of History item mydatasetid different than expected" in str(assert_error)
    extra_path = tmp_path / "test_extras" / "expected.txt"
    assert extra_path.exists()
    assert extra_path.open("rb").read() == b"extra_unexpected"
