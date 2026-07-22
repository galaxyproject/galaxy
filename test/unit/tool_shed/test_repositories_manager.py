from typing import cast

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from tool_shed.managers import repositories as repositories_manager
from tool_shed.managers.repositories import guid_to_repository
from tool_shed.structured_app import ToolShedApp


def test_guid_to_repository_rejects_malformed_guid():
    # A guid without enough slashes used to raise a bare ValueError from the
    # tuple unpacking, surfacing as a 500 in the TRS API (see issue #23139).
    # The malformed-id check runs before app is dereferenced, so a cast None
    # is enough to exercise this path.
    app = cast(ToolShedApp, None)
    with pytest.raises(RequestParameterInvalidException):
        guid_to_repository(app, "localhost/repos/owner")


def test_guid_to_repository_parses_owner_and_name(monkeypatch):
    # A well-formed guid is "shed/repos/owner/name/rest...". The manager should
    # extract owner and name and look the repository up by name and owner,
    # ignoring the shed host and everything after the name.
    captured = {}
    sentinel_repository = object()
    sentinel_context = object()

    def fake_lookup(context, name, owner):
        captured["context"] = context
        captured["name"] = name
        captured["owner"] = owner
        return sentinel_repository

    monkeypatch.setattr(repositories_manager, "_get_repository_by_name_and_owner", fake_lookup)

    class _Model:
        context = sentinel_context

    class _App:
        model = _Model()

    app = cast(ToolShedApp, _App())
    result = guid_to_repository(app, "localhost:9009/repos/owner/name/1234abcd/tool_id")

    assert result is sentinel_repository
    assert captured["owner"] == "owner"
    assert captured["name"] == "name"
    assert captured["context"] is sentinel_context
