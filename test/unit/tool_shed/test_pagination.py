from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers.repositories import (
    index_repositories,
    index_repositories_paginated,
    IndexRequest,
    PaginatedIndexRequest,
)
from tool_shed.webapp.model import User
from ._util import (
    create_category,
    repository_fixture,
    user_fixture,
)


def test_index_repositories(provides_repositories: ProvidesRepositoriesContext, new_user: User):
    category = create_category(provides_repositories, {"name": "test_pagination_1"})
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
    paginated_results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert len(paginated_results.hits) == 2
    assert paginated_results.page == 1
    assert paginated_results.page_size == 2
    assert paginated_results.total_results == 3

    paginated_request.owner = new_user.username
    paginated_results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert len(paginated_results.hits) == 2
    assert paginated_results.page == 1
    assert paginated_results.page_size == 2
    assert paginated_results.total_results == 3

    paginated_request.owner = other_user.username
    paginated_results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert len(paginated_results.hits) == 0
    assert paginated_results.total_results == 0


def test_index_repositories_with_category_name(provides_repositories: ProvidesRepositoriesContext, new_user: User):
    category1 = create_category(provides_repositories, {"name": "test_category_pagination_1"})
    category2 = create_category(provides_repositories, {"name": "test_category_pagination_2"})
    repository_fixture(provides_repositories.app, new_user, "paginate-test-with-category-1", category1)
    repository_fixture(provides_repositories.app, new_user, "paginate-test-with-category-2", category1)
    repository_fixture(provides_repositories.app, new_user, "paginate-test-with-category-3", category2)
    unpaginated_request = IndexRequest(
        category_id=None,
    )
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 3

    unpaginated_request = IndexRequest(
        category_id=provides_repositories.app.security.encode_id(category1.id),
    )
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 2

    unpaginated_request = IndexRequest(
        category_id=provides_repositories.app.security.encode_id(category2.id),
    )
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 1

    paginated_request = PaginatedIndexRequest(
        page=1,
        page_size=2,
    )
    paginated_request.category_id = provides_repositories.app.security.encode_id(category1.id)
    paginated_results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert paginated_results.total_results == 2
    assert paginated_results.page == 1

    paginated_request.category_id = provides_repositories.app.security.encode_id(category2.id)
    paginated_results = index_repositories_paginated(provides_repositories.app, paginated_request)
    assert paginated_results.total_results == 1
    assert paginated_results.page == 1


def test_index_repositories_with_filter_text(provides_repositories: ProvidesRepositoriesContext, new_user: User):
    category1 = create_category(provides_repositories, {"name": "test_category_pagination_1"})
    repository_fixture(provides_repositories.app, new_user, "paginate-test-with-filter-text-1-foo123", category1)
    repository_fixture(provides_repositories.app, new_user, "paginate-test-with-filter-text-2-bar123", category1)

    results = index_repositories(provides_repositories.app, IndexRequest())
    assert len(results) == 2

    unpaginated_request = IndexRequest(filter="foo123")
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 1
    assert results[0].name and results[0].name.endswith("foo123")

    unpaginated_request = IndexRequest(filter="nomatch")
    results = index_repositories(provides_repositories.app, unpaginated_request)
    assert len(results) == 0


def test_index_repositories_sorting(provides_repositories: ProvidesRepositoriesContext, new_user: User):
    category1 = create_category(provides_repositories, {"name": "test_category_pagination_1"})
    repository_fixture(provides_repositories.app, new_user, "paginate-test-sorting-z1", category1)
    repository_fixture(provides_repositories.app, new_user, "paginate-test-sorting-x1", category1)
    repository_fixture(provides_repositories.app, new_user, "paginate-test-sorting-y1", category1)

    results = index_repositories(provides_repositories.app, IndexRequest())
    assert len(results) == 3
    # default sorting is name asc... so x1, y1, z1 should be right.
    assert results[0].name and "x1" in results[0].name
    assert results[1].name and "y1" in results[1].name
    assert results[2].name and "z1" in results[2].name

    # now lets invert the default
    results = index_repositories(provides_repositories.app, IndexRequest(sort_desc=True))
    assert len(results) == 3
    # default sorting is name asc... so x1, y1, z1 should be right.
    assert results[0].name and "z1" in results[0].name
    assert results[1].name and "y1" in results[1].name
    assert results[2].name and "x1" in results[2].name

    # now lets sort on create_time
    results = index_repositories(provides_repositories.app, IndexRequest(sort_by="create_time"))
    assert len(results) == 3
    assert results[0].name and "z1" in results[0].name
    assert results[1].name and "x1" in results[1].name
    assert results[2].name and "y1" in results[2].name

    # test combining sort_by and sort_desc
    results = index_repositories(provides_repositories.app, IndexRequest(sort_by="create_time", sort_desc=True))
    assert len(results) == 3
    assert results[0].name and "y1" in results[0].name
    assert results[1].name and "x1" in results[1].name
    assert results[2].name and "z1" in results[2].name
