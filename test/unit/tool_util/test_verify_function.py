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


CSV_CONTENT = b"col1,col2,col3\n"
TABULAR_CONTENT = b"col1\tcol2\tcol3\n"


def _has_n_columns(n, **attributes):
    return [{"tag": "has_n_columns", "attributes": {"n": str(n), **attributes}, "children": []}]


def _verify_columns(content, assert_list, profile=None, delimiter=None, fetches=None):
    def get_delimiter():
        if fetches is not None:
            fetches.append(True)
        return delimiter

    verify(
        "column assertion",
        content,
        attributes={"assert_list": assert_list},
        filename=None,
        get_filecontent=t_data_downloader_for(content),
        profile=profile,
        get_delimiter=get_delimiter,
    )


def test_delimiter_metadata_sets_sep():
    """profile >= 26.2 splits on the delimiter the datatype recorded for the dataset"""
    _verify_columns(CSV_CONTENT, _has_n_columns(3), profile="26.2", delimiter=",")


def test_delimiter_metadata_ignored_for_older_profile():
    """older profiles keep the historical tab default, so csv reads as one column"""
    with pytest.raises(AssertionError):
        _verify_columns(CSV_CONTENT, _has_n_columns(3), profile="26.1", delimiter=",")

    _verify_columns(CSV_CONTENT, _has_n_columns(1), profile="26.1", delimiter=",")


def test_delimiter_not_fetched_for_older_profile():
    """the delimiter lookup costs an API call, so it must not happen behind the gate"""
    fetches: list = []
    _verify_columns(TABULAR_CONTENT, _has_n_columns(3), profile="26.1", delimiter=",", fetches=fetches)
    assert not fetches


def test_tab_delimiter_metadata():
    _verify_columns(TABULAR_CONTENT, _has_n_columns(3), profile="26.2", delimiter="\t")


def test_unset_delimiter_metadata_falls_back_to_tab():
    """delimiter is declared optional with no_value=[], so an unset element is not a string"""
    _verify_columns(TABULAR_CONTENT, _has_n_columns(3), profile="26.2", delimiter=[])
    _verify_columns(TABULAR_CONTENT, _has_n_columns(3), profile="26.2", delimiter=None)


def test_explicit_sep_overrides_delimiter_metadata():
    """an explicit sep in the assertion wins over the dataset delimiter"""
    _verify_columns(TABULAR_CONTENT, _has_n_columns(3, sep="\t"), profile="26.2", delimiter=",")


def test_no_delimiter_source_keeps_tab_default():
    """callers without dataset metadata (workflow and selenium tests) keep the tab default"""
    verify(
        "column assertion",
        TABULAR_CONTENT,
        attributes={"assert_list": _has_n_columns(3)},
        filename=None,
        get_filecontent=t_data_downloader_for(TABULAR_CONTENT),
        profile="26.2",
    )
