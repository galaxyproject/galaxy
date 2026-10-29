from galaxy.datatypes.genetics import RexpBase


def test_get_file_peek(tmp_path):
    p = tmp_path / "my.file"
    p.write_text("a\nb\nc\nd\ne\nf\n")  # content > 5 lines
    assert RexpBase().get_file_peek(p) == "a\nb\nc\nd\ne\n"

    p.write_text("a\n")  # content < 5 lines
    assert RexpBase().get_file_peek(p) == "a\n"
