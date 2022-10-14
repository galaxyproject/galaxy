from galaxy_test.base.api_util import random_name
from ..base.api import ShedApiTestCase


class TestShedCategoriesApi(ShedApiTestCase):
    def test_create_requires_name(self):
        body = {}
        response = self.admin_api_interactor.post("categories", json=body)
        assert response.status_code == 400

    def test_create_okay(self):
        name = random_name(prefix="createokay")
        body = {"name": name, "description": "testcreateokaydescript"}
        response = self.admin_api_interactor.post("categories", json=body)
        assert response.status_code == 200
        assert response.json()["name"] == name
