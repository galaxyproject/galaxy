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


def test_csv_ftype_auto_sep():
    """test that ftype='csv' automatically sets separator for has_n_columns assertion"""
    item_label = "csv test"
    output_content = b"col1,col2,col3\n"
    attributes = {
        "ftype": "csv",
        "assert_list": [
            {
                "tag": "has_n_columns",
                "attributes": {"n": "3"},
                "children": [],
            }
        ],
    }

    # This should pass because ftype="csv" triggers sep="," auto-detection
    verify(
        item_label,
        output_content,
        attributes=attributes,
        filename=None,
        get_filecontent=t_data_downloader_for(output_content),
    )


def test_tabular_ftype_auto_sep():
    """test that ftype='tabular' uses tab separator for has_n_columns assertion"""
    item_label = "tabular test"
    output_content = b"col1\tcol2\tcol3\n"
    attributes = {
        "ftype": "tabular",
        "assert_list": [
            {
                "tag": "has_n_columns",
                "attributes": {"n": "3"},
                "children": [],
            }
        ],
    }

    # This should pass because ftype="tabular" triggers sep="\t" (default)
    verify(
        item_label,
        output_content,
        attributes=attributes,
        filename=None,
        get_filecontent=t_data_downloader_for(output_content),
    )


def test_csv_ftype_explicit_sep_override():
    """test that explicit sep in assertion overrides ftype='csv' auto-detection"""
    item_label = "csv with explicit sep test"
    # Tab-separated data (not comma-separated!)
    output_content = b"col1\tcol2\tcol3\n"
    attributes = {
        "ftype": "csv",  # ftype is csv but data is actually tab-separated
        "assert_list": [
            {
                "tag": "has_n_columns",
                "attributes": {"n": "3", "sep": "\t"},  # Explicit sep overrides
                "children": [],
            }
        ],
    }

    # This should pass because explicit sep="\t" overrides the ftype="csv" auto-detection
    verify(
        item_label,
        output_content,
        attributes=attributes,
        filename=None,
        get_filecontent=t_data_downloader_for(output_content),
    )
