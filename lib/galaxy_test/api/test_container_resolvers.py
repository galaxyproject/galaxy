from ._framework import ApiTestCase


class ContainerResolversApiTestCase(ApiTestCase):

    def test_index(self):
        response = self._get("container_resolvers", admin=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_show(self):
        response = self._get("container_resolvers/0", admin=True)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
