import tempfile

from galaxy.tool_util.cwl.util import output_properties


def test_output_properties_in_memory():
    props = output_properties(content=b"hello world", basename="hello.txt")
    assert props["basename"] == "hello.txt"
    assert props["nameroot"] == "hello"
    assert props["nameext"] == ".txt"
    assert props["size"] == 11
    assert props["checksum"] == "sha1$2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"


def test_output_properties_path():
    f = tempfile.NamedTemporaryFile(mode="w")
    f.write("hello world")
    f.flush()

    props = output_properties(path=f.name, basename="hello.txt")
    assert props["basename"] == "hello.txt"
    assert props["nameroot"] == "hello"
    assert props["nameext"] == ".txt"
    assert props["size"] == 11
    assert props["checksum"] == "sha1$2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"
