from galaxy_test.driver import integration_util


class TestContainerResolutionApi(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    def test_index(self):
        response = self._get("container_resolvers", admin=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_show(self):
        response = self._get("container_resolvers/0", admin=True)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_resolve(self):
        tool_id = "cat1"

        # no index
        response = self._get(f"container_resolvers/resolve?tool_id={tool_id}", admin=True)
        assert response.status_code == 200

        # with index
        response = self._get(f"container_resolvers/0/resolve?tool_id={tool_id}", admin=True)
        assert response.status_code == 200
