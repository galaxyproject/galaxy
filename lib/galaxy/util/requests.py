from typing import (
    Callable,
    Union,
)

import requests
from requests import (  # noqa: F401
    codes as codes,
    exceptions as exceptions,
    Response as Response,
)
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from typing_extensions import ParamSpec

from .user_agent import get_default_headers

DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.1


class Session(requests.Session):
    def __init__(self) -> None:
        super().__init__()
        self.headers.update(get_default_headers())


class RetrySession(Session):
    def __init__(
        self, total: Union[bool, int, None] = DEFAULT_RETRIES, backoff_factor: float = DEFAULT_BACKOFF_FACTOR, **kwargs
    ) -> None:
        super().__init__()
        retry = Retry(total=total, backoff_factor=backoff_factor, **kwargs)
        adapter = HTTPAdapter(max_retries=retry)
        self.mount("https://", adapter)
        self.mount("http://", adapter)


Param = ParamSpec("Param")


def _request_decorator(f: Callable[Param, Response]) -> Callable[Param, Response]:
    def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> Response:
        with Session() as s:
            return getattr(s, f.__name__)(*args, **kwargs)

    return wrapper


delete = _request_decorator(requests.delete)
get = _request_decorator(requests.get)
head = _request_decorator(requests.head)
patch = _request_decorator(requests.patch)
post = _request_decorator(requests.post)
options = _request_decorator(requests.options)
put = _request_decorator(requests.put)
session = Session
