from galaxy_test.base.api_asserts import assert_status_code_is_ok
from ..base.api import (
    ShedApiTestCase,
    skip_if_api_v1,
)


class TestShedGraphqlApi(ShedApiTestCase):
    @skip_if_api_v1
    def test_graphql_query(self):
        populator = self.populator
        category = populator.new_category(prefix="testcreate")
        json = {"query": r"query { categories { name } }"}
        response = self.api_interactor.post("graphql/", json=json)
        assert_status_code_is_ok(response)
        result = response.json()
        assert "data" in result
        data = result["data"]
        assert "categories" in data
        categories = data["categories"]
        assert category.name in [c["name"] for c in categories]
