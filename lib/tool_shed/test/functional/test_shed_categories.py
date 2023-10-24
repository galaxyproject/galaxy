from typing import Dict

from galaxy_test.base.api_util import random_name
from ..base.api import ShedApiTestCase


class TestShedCategoriesApi(ShedApiTestCase):
    def test_create_requires_name(self):
        body: Dict = {}
        response = self.admin_api_interactor.post("categories", json=body)
        assert response.status_code == 400

    def test_create_okay(self):
        name = random_name(prefix="createokay")
        description = "testcreateokaydescript"
        body = {"name": name, "description": description}
        response = self.admin_api_interactor.post("categories", json=body)
        assert response.status_code == 200
        assert response.json()["name"] == name

        category = self.populator.get_category_with_name(name)
        assert category.name == name
        assert category.description == description

        category_id = category.id
        category = self.populator.get_category_with_id(category_id)
        assert category.name == name
        assert category.description == description
