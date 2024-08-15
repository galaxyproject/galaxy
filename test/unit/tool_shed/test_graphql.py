from typing import (
    Callable,
    List,
    Optional,
    Tuple,
)

from graphql.execution import ExecutionResult

from tool_shed.context import (
    ProvidesRepositoriesContext,
    ProvidesUserContext,
)
from tool_shed.webapp.graphql.schema import schema
from tool_shed.webapp.model import Repository
from ._util import (
    attach_category,
    create_category,
    repository_fixture,
    upload_directories_to_repository,
    user_fixture,
)


def relay_query(query_name: str, params: Optional[str], node_def: str) -> str:
    params_call = f"({params})" if params else ""
    return f"""
query {{
    {query_name}{params_call} {{
        edges {{
            cursor
            node {{
                {node_def}
            }}
        }}
        pageInfo {{
            endCursor
            hasNextPage
        }}
    }}
}}
"""


class PageInfo:
    def __init__(self, result: dict):
        assert "pageInfo" in result
        self.info = result["pageInfo"]

    @property
    def end_cursor(self) -> str:
        return self.info["endCursor"]

    @property
    def has_next_page(self) -> bool:
        return self.info["hasNextPage"]


def relay_result(result: ExecutionResult) -> Tuple[list, PageInfo]:
    data = result.data
    assert data
    data_values = data.values()
    query_result = list(data_values)[0]
    return query_result["edges"], PageInfo(query_result)


QueryExecutor = Callable[[str], ExecutionResult]


def query_execution_builder_for_trans(trans: ProvidesRepositoriesContext) -> QueryExecutor:
    cv = context_value(trans)

    def e(query: str) -> ExecutionResult:
        return schema.execute(query, context_value=cv, root_value=cv)

    return e


def context_value(trans: ProvidesUserContext):
    return {
        "session": trans.app.model.context,
        "security": trans.security,
    }


def test_simple_repositories(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    e = query_execution_builder_for_trans(provides_repositories)
    repositories_query = """
        query {
            repositories {
                id
                encodedId
                name
                categories {
                    name
                }
                user {
                    username
                }
            }
        }
    """
    result = e(repositories_query)
    _assert_no_errors(result)
    repos = _assert_result_data_has_key(result, "repositories")
    repository_names = [r["name"] for r in repos]
    assert new_repository.name in repository_names


def test_relay_repos_by_category(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    name = new_repository.name
    category = create_category(provides_repositories, {"name": "test_graphql_relay_categories_1"})
    user = provides_repositories.user
    assert user
    uc1 = repository_fixture(provides_repositories.app, user, "uc1")
    uc2 = repository_fixture(provides_repositories.app, user, "uc2")

    other_user = user_fixture(provides_repositories.app, "otherusernamec")
    ouc1 = repository_fixture(provides_repositories.app, other_user, "ouc1")
    ouc2 = repository_fixture(provides_repositories.app, other_user, "ouc2")

    category_id = category.id
    e = query_execution_builder_for_trans(provides_repositories)

    names = repository_names(e, "relayRepositoriesForCategory", f"id: {category_id}")
    assert len(names) == 0

    encoded_id = provides_repositories.security.encode_id(category_id)
    names = repository_names(e, "relayRepositoriesForCategory", f'encodedId: "{encoded_id}"')
    assert len(names) == 0
    attach_category(provides_repositories, new_repository, category)

    names = repository_names(e, "relayRepositoriesForCategory", f'encodedId: "{encoded_id}"')
    assert len(names) == 1
    assert name in names

    names = repository_names(e, "relayRepositoriesForCategory", f"id: {category_id}")
    assert len(names) == 1
    assert name in names

    attach_category(provides_repositories, uc1, category)
    attach_category(provides_repositories, ouc1, category)
    names = repository_names(e, "relayRepositoriesForCategory", f'encodedId: "{encoded_id}"')
    assert len(names) == 3, names
    assert "uc1" in names, names
    assert "ouc1" in names, names

    category2 = create_category(provides_repositories, {"name": "test_graphql_relay_categories_2"})
    attach_category(provides_repositories, uc2, category2)
    attach_category(provides_repositories, ouc2, category2)

    names = repository_names(e, "relayRepositoriesForCategory", f'encodedId: "{encoded_id}"')
    assert len(names) == 3, names
    assert "uc1" in names, names
    assert "ouc1" in names, names

    encoded_id_2 = provides_repositories.security.encode_id(category2.id)
    names = repository_names(e, "relayRepositoriesForCategory", f'encodedId: "{encoded_id_2}"')
    assert len(names) == 2, names
    assert "uc2" in names, names
    assert "ouc2" in names, names


def test_simple_categories(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    assert provides_repositories.user

    category = create_category(provides_repositories, {"name": "test_graphql"})
    e = query_execution_builder_for_trans(provides_repositories)
    result = e(
        """
    query {
        categories {
            name
            encodedId
        }
    }
"""
    )
    _assert_no_errors(result)
    categories = _assert_result_data_has_key(result, "categories")
    category_names = [c["name"] for c in categories]
    assert "test_graphql" in category_names
    encoded_id = [c["encodedId"] for c in categories if c["name"] == "test_graphql"][0]
    assert encoded_id == provides_repositories.security.encode_id(category.id)

    repository_fixture(provides_repositories.app, provides_repositories.user, "foo1", category=category)
    result = e(
        """
    query {
        categories {
            name
            repositories {
                name
            }
        }
    }
"""
    )
    _assert_no_errors(result)
    categories = _assert_result_data_has_key(result, "categories")
    repositories = [c["repositories"] for c in categories if c["name"] == "test_graphql"][0]
    assert repositories
    repository_names = [r["name"] for r in repositories]
    assert "foo1" in repository_names


def test_simple_revisions(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker_with_download_gaps")
    e = query_execution_builder_for_trans(provides_repositories)
    # (id: "1")
    query = """
    query {
        revisions {
            id
            encodedId
            createTime
            repository {
                name
            }
            changesetRevision
            numericRevision
            downloadable
        }
    }
"""

    result = e(query)
    _assert_no_errors(result)


def test_relay(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    assert provides_repositories.user
    repository_fixture(provides_repositories.app, provides_repositories.user, "foo1")
    repository_fixture(provides_repositories.app, provides_repositories.user, "f002")
    repository_fixture(provides_repositories.app, provides_repositories.user, "cow")
    repository_fixture(provides_repositories.app, provides_repositories.user, "u3")

    e = query_execution_builder_for_trans(provides_repositories)
    q1 = relay_query("relayRepositories", "sort: NAME_ASC first: 2", "encodedId, name, type, createTime")
    result = e(q1)
    _assert_no_errors(result)
    edges, page_info = relay_result(result)
    has_next_page = page_info.has_next_page
    assert has_next_page

    last_cursor = edges[-1]["cursor"]
    q2 = relay_query("relayRepositories", f'sort: NAME_ASC first: 2 after: "{last_cursor}"', "name, type, createTime")
    result = e(q2)
    _assert_no_errors(result)
    edges, page_info = relay_result(result)
    has_next_page = page_info.has_next_page


def test_relay_by_owner(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    user = provides_repositories.user
    assert user
    repository_fixture(provides_repositories.app, user, "u1")
    repository_fixture(provides_repositories.app, user, "u2")
    repository_fixture(provides_repositories.app, user, "u3")
    repository_fixture(provides_repositories.app, user, "u4")
    other_user = user_fixture(provides_repositories.app, "otherusername")
    repository_fixture(provides_repositories.app, other_user, "ou1")
    repository_fixture(provides_repositories.app, other_user, "ou2")
    repository_fixture(provides_repositories.app, other_user, "ou3")
    repository_fixture(provides_repositories.app, other_user, "ou4")

    e = query_execution_builder_for_trans(provides_repositories)
    names = repository_names(e, "relayRepositoriesForOwner", f'username: "{user.username}"')
    assert "u1" in names
    assert "ou1" not in names

    names = repository_names(e, "relayRepositoriesForOwner", 'username: "otherusername"')
    assert "ou4" in names
    assert "u4" not in names


def repository_names(e: QueryExecutor, field: str, base_variables: str) -> List[str]:
    edges = walk_relay(e, field, base_variables, "name")
    return [e["node"]["name"] for e in edges]


def walk_relay(e: QueryExecutor, field: str, base_variables: str, fragment: str):
    variables = f"{base_variables} first: 2"
    query = relay_query(field, variables, fragment)
    result: ExecutionResult = e(query)
    _assert_no_errors(result, query)
    all_edges, page_info = relay_result(result)
    has_next_page = page_info.has_next_page
    while has_next_page:
        variables = f'{base_variables} first: 2 after: "${page_info.end_cursor}"'
        query = relay_query(field, variables, fragment)
        result = e(query)
        _assert_no_errors(result, query)
        these_edges, page_info = relay_result(result)
        if len(these_edges) == 0:
            # I was using .options instead of .join and such with the queries
            # and this would break. The queries are better now anyway, but
            # be careful with new queries - there seem to be bugs around this
            # potentially
            assert not page_info.has_next_page
            break
        all_edges.extend(these_edges)
        has_next_page = page_info.has_next_page
    return all_edges


def _assert_result_data_has_key(result: ExecutionResult, key: str):
    data = result.data
    assert data
    assert key in data
    return data[key]


def _assert_no_errors(result: ExecutionResult, query=None):
    if result.errors is not None:
        message = f"Found unexpected GraphQL errors {str(result.errors)}"
        if query is not None:
            message = f"{message} in query {query}"
        raise AssertionError(message)
