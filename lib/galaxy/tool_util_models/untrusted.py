"""Track whether the tools being parsed or loaded come from an untrusted source."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_loading_untrusted_tools: ContextVar[bool] = ContextVar("loading_untrusted_tools", default=False)


@contextmanager
def loading_untrusted_tools() -> Iterator[None]:
    """Tools parsed or loaded in this context come from untrusted sources, like Tool Shed uploads.

    These must not evaluate Python they contain or read files they name outside of ``tool_data_path``.
    """
    token = _loading_untrusted_tools.set(True)
    try:
        yield
    finally:
        _loading_untrusted_tools.reset(token)


def is_loading_untrusted_tools() -> bool:
    return _loading_untrusted_tools.get()
