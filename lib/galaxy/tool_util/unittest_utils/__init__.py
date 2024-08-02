import os
from typing import (
    Callable,
    Dict,
    Optional,
    Union,
)
from unittest.mock import Mock

from galaxy.util import galaxy_directory


def mock_trans(has_user=True, is_admin=False):
    """A mock ``trans`` object for exposing user info to toolbox filter unit tests."""
    trans = Mock(user_is_admin=is_admin)
    if has_user:
        trans.user = Mock(preferences={})
    else:
        trans.user = None
    return trans


def t_data_downloader_for(content: Union[Dict[Optional[str], bytes], bytes]) -> Callable[[str], bytes]:
    def get_content(filename: Optional[str]) -> bytes:
        if isinstance(content, dict):
            assert filename in content, f"failed to find {filename} in {content}"
            return content[filename]
        else:
            return content

    return get_content


def functional_test_tool_directory() -> str:
    return os.path.join(galaxy_directory(), "test/functional/tools")


def functional_test_tool_path(test_path: str) -> str:
    return os.path.join(functional_test_tool_directory(), test_path)
