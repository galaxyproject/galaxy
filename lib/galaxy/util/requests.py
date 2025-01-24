from typing import (
    Callable,
    cast,
    TypeVar,
)

import requests
from requests import (  # noqa: F401
    codes as codes,
    exceptions as exceptions,
    Response as Response,
)
from typing_extensions import ParamSpec

from .user_agent import get_default_headers

Param = ParamSpec("Param")
RetType = TypeVar("RetType")


def default_user_agent_decorator(f: Callable[Param, RetType]) -> Callable[Param, RetType]:

    def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RetType:
        headers = cast(dict, kwargs.pop("headers", None) or {})
        headers.update(get_default_headers())
        is_session = f in (requests.session, requests.Session)
        if not is_session:
            kwargs["headers"] = headers
        rval = f(*args, **kwargs)
        if is_session:
            rval.headers = headers  # type: ignore[attr-defined]
        return rval

    return wrapper


delete = default_user_agent_decorator(requests.delete)
get = default_user_agent_decorator(requests.get)
head = default_user_agent_decorator(requests.head)
patch = default_user_agent_decorator(requests.patch)
post = default_user_agent_decorator(requests.post)
put = default_user_agent_decorator(requests.put)
session = default_user_agent_decorator(requests.session)
Session = default_user_agent_decorator(requests.Session)
