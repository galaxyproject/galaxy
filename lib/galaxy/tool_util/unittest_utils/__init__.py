import os
from collections.abc import Callable
from unittest.mock import Mock

from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.interface import ToolSource


def mock_trans(has_user=True, is_admin=False):
    """A mock ``trans`` object for exposing user info to toolbox filter unit tests."""
    trans = Mock(user_is_admin=is_admin)
    if has_user:
        trans.user = Mock(preferences={})
    else:
        trans.user = None
    return trans


def t_data_downloader_for(content: dict[str | None, bytes] | bytes) -> Callable[[str], bytes]:
    def get_content(filename: str | None) -> bytes:
        if isinstance(content, dict):
            assert filename in content, f"failed to find {filename} in {content}"
            return content[filename]
        else:
            return content

    return get_content


def functional_test_tool_directory() -> str:
    """Galaxy's sample tools, shipped with this package so the tests that parse them run anywhere."""
    return os.path.join(os.path.dirname(__file__), "functional_tools")


def functional_test_tool_path(test_path: str) -> str:
    return os.path.join(functional_test_tool_directory(), test_path)


def functional_test_tool_source(tool_name: str) -> ToolSource:
    test_tool_directory = functional_test_tool_directory()
    if tool_name.endswith("_y"):
        yaml_name = tool_name[:-2]
        tool_path = os.path.join(test_tool_directory, f"{yaml_name}.yml")
    else:
        tool_path = os.path.join(test_tool_directory, f"{tool_name}.xml")
    tool_source = get_tool_source(tool_path)
    return tool_source
