from functools import wraps
from typing import (
    Any,
    Callable,
)
from unittest import SkipTest

import requests


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


skip_if_github_down = skip_if_site_down("https://github.com/")
