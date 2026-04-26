from typing import Callable

import requests
from requests import (  # noqa: F401
    codes as codes,
    exceptions as exceptions,
    Response as Response,
)
from typing_extensions import ParamSpec

from .user_agent import get_default_headers


class Session(requests.Session):
    def __init__(self) -> None:
        super().__init__()
        self.headers.update(get_default_headers())


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
