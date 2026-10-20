from typing import cast

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers import repositories as repositories_manager
from tool_shed.managers.repositories import (
    guid_to_repository,
    repository_categories,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import Repository
from tool_shed_client.schema import CategorySummary
from ._util import (
    attach_category,
    create_category,
    random_name,
)


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


def test_repository_categories_leave_out_deleted_categories(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    # No API deletes a category, so this can't be set up through the API tests
    live = create_category(provides_repositories, {"name": random_name()})
    deleted = create_category(provides_repositories, {"name": random_name()})
    attach_category(provides_repositories, new_repository, live)
    attach_category(provides_repositories, new_repository, deleted)
    deleted.deleted = True
    provides_repositories.sa_session.flush()

    app = provides_repositories.app
    categories = repository_categories(app, new_repository)

    assert categories == [CategorySummary(id=app.security.encode_id(live.id), name=live.name)]
