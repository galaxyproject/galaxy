from galaxy.tool_util.verify import verify


def test_writes_output_to_target_directory(tmp_path):
    item_label = "my test case"
    output_content = b"expected"
    filename = "my_output.txt"

    def get_filecontent(fname) -> bytes:
        return output_content

    assert not (tmp_path / filename).exists()
    verify(
        item_label,
        output_content,
        attributes={},
        filename=filename,
        keep_outputs_dir=str(tmp_path),
        get_filecontent=get_filecontent,
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

    def get_filecontent(fname) -> bytes:
        return b"xpecte"

    assert not (tmp_path / filename).exists()
    verify(
        item_label,
        output_content,
        attributes=attributes,
        filename=filename,
        keep_outputs_dir=str(tmp_path),
        get_filecontent=get_filecontent,
    )
    assert not (tmp_path / filename).exists()


def test_sim_size(tmp_path):
    item_label = "my test case"
    output_content = b"expected"
    attributes = {
        "compare": "sim_size",
        "delta": 2,
    }
    filename = "my_output.txt"

    def get_filecontent(fname) -> bytes:
        return b"xpected"

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

    def get_filecontent(fname) -> bytes:
        return b"ected"

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
