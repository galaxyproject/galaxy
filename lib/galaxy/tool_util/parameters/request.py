"""Helpers for reading references from persisted tool request payloads."""

from typing import (
    Any,
    Literal,
    NamedTuple,
)

from boltons.iterutils import remap

RequestInputContentType = Literal["dataset", "collection", "dataset_collection_element"]


class RequestInputRef(NamedTuple):
    content_type: RequestInputContentType
    id: int
    input_name: str
    src: str


class RequestUrlInputRef(NamedTuple):
    input_name: str
    url: str
    request: dict[str, Any]


_SRC_TO_CONTENT_TYPE: dict[str, RequestInputContentType] = {
    "hda": "dataset",
    "hdca": "collection",
    "dce": "dataset_collection_element",
}


def request_internal_input_refs(
    payload: dict,
    allowed_srcs: set[str] | None = None,
) -> list[RequestInputRef]:
    """Walk a request_internal payload and return declared data refs.

    The walk intentionally follows the same ``remap`` idiom used by job
    request handling: when visiting an ``id`` leaf, inspect the sibling ``src``
    value on the parent container to decide whether the value is a data ref.
    """
    refs: list[RequestInputRef] = []

    def visit(path, key, value):
        if key == "id" and isinstance(value, int) and not isinstance(value, bool):
            parent = payload
            for step in path:
                parent = parent[step]
            if isinstance(parent, dict):
                src = parent.get("src")
                if isinstance(src, str) and (allowed_srcs is None or src in allowed_srcs):
                    content_type = _SRC_TO_CONTENT_TYPE.get(src)
                    if content_type is not None:
                        refs.append(RequestInputRef(content_type, value, _input_name_from_request_path(path), src))
        return key, value

    remap(payload, visit=visit)
    return refs


def request_internal_url_inputs(payload: dict) -> list[RequestUrlInputRef]:
    """Walk a request_internal payload and return declared URL inputs."""
    refs: list[RequestUrlInputRef] = []

    def visit(path, key, value):
        if key == "url" and isinstance(value, str):
            parent = payload
            for step in path:
                parent = parent[step]
            if isinstance(parent, dict) and parent.get("src") == "url":
                refs.append(RequestUrlInputRef(_input_name_from_request_path(path), value, dict(parent)))
        return key, value

    remap(payload, visit=visit)
    return refs


def _input_name_from_request_path(path) -> str:
    """Convert a request payload path to a workflow input connection name."""
    parts: list[str] = []
    i = 0
    while i < len(path):
        segment = path[i]
        if segment == "values" and i + 1 < len(path) and isinstance(path[i + 1], int):
            i += 2
            continue
        if isinstance(segment, int):
            if parts and i + 1 < len(path) and isinstance(path[i + 1], str):
                parts[-1] = f"{parts[-1]}_{segment}"
        else:
            parts.append(str(segment))
        i += 1
    return "|".join(parts)
