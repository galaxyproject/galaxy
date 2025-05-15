"""Unit test logic related to finding externally referenced files in tool
descriptions.
"""

import os
import shutil
import tempfile

from galaxy.tools import Tool


def test_finds_external_code_file():
    assert __external_files("""<tool><code file="foo.py" /></tool>""") == ["foo.py"]


def test_finds_skips_empty_code_file_attribute():
    assert __external_files("""<tool><code /></tool>""") == []


def test_finds_external_macro_file():
    assert __external_files("""<tool><macros><import>cool_macros.xml</import></macros></tool>""") == ["cool_macros.xml"]


def __external_files(contents):
    base_path = tempfile.mkdtemp()
    try:
        tool_path = os.path.join(base_path, "tool.xml")
        with open(tool_path, "w") as f:
            f.write(contents)
        return Tool.get_externally_referenced_paths(tool_path)
    finally:
        shutil.rmtree(base_path)
