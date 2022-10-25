from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Union,
)
from unittest import SkipTest
from unittest.mock import Mock

import requests


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


def is_site_up(url: str) -> bool:
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def skip_if_site_down(url: str) -> Callable:
    def method_wrapper(method: Callable):
        @wraps(method)
        def wrapped_method(*args, **kwargs) -> Any:
            if not is_site_up(url):
                raise SkipTest(f"Test depends on [{url}] being up and it appears to be down.")
            return method(*args, **kwargs)

        return wrapped_method

    return method_wrapper
