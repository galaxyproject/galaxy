from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers.repositories import (
    IndexRequest,
    index_repositories,
    index_repositories_paginated,
    PaginatedIndexRequest,
)
from tool_shed.webapp.model import User

from ._util import (
    create_category,
    repository_fixture,
    user_fixture,
)


def test_index_repositories(provides_repositories: ProvidesRepositoriesContext, new_user: User):
    category = create_category(provides_repositories, {"name": "test_category_pagination_1"})
    repository_fixture(provides_repositories.app, new_user, "paginate-test-1", category)
    repository_fixture(provides_repositories.app, new_user, "paginate-test-2", category)
    repository_fixture(provides_repositories.app, new_user, "paginate-test-3", category)
    unpaginated_request = IndexRequest(
        owner=None,
        name=None,
        deleted=False,
    )
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 3

    unpaginated_request.owner = new_user.username
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 3

    other_user = user_fixture(provides_repositories.app, "otheruseforpaginate")
    unpaginated_request.owner = other_user.username
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 0

    paginated_request = PaginatedIndexRequest(
        owner=None,
        name=None,
        deleted=False,
        page=1,
        page_size=2,
    )
    results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert len(results.hits) == 2
    assert results.page == 1
    assert results.page_size == 2
    assert results.total_results == 3

    paginated_request.owner = new_user.username
    results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert len(results.hits) == 2
    assert results.page == 1
    assert results.page_size == 2
    assert results.total_results == 3

    paginated_request.owner = other_user.username
    results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert len(results.hits) == 0
    assert results.total_results == 0
