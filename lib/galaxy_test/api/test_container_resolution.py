from galaxy_test.base.decorators import requires_admin
from galaxy_test.base.populators import skip_without_tool
from ._framework import ApiTestCase


class TestContainerResolutionApi(ApiTestCase):
    @requires_admin
    def test_index(self):
        response = self._get("container_resolvers", admin=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @requires_admin
    def test_show(self):
        response = self._get("container_resolvers/0", admin=True)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    @skip_without_tool("cat1")
    @requires_admin
    def test_resolve(self):
        tool_id = "cat1"

        # no index
        response = self._get(f"container_resolvers/resolve?tool_id={tool_id}", admin=True)
        assert response.status_code == 200

        # with index
        response = self._get(f"container_resolvers/0/resolve?tool_id={tool_id}", admin=True)
        assert response.status_code == 200
