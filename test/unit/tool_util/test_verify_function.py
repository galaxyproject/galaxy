from galaxy.tool_util.verify import verify


def test_writes_output_to_target_directory(tmp_path):
    item_label = "my test case"
    output_content = b"expected"
    filename = "my_output.txt"

    def get_filecontent(str) -> bytes:
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

