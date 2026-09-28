from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from ._framework import ApiTestCase


class TestUnprivilegedToolsApiSurface(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_public_dynamic_tools_index_excludes_private_udt(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        response = self._get("dynamic_tools", anon=True)
        assert response.status_code == 200, response.text
        listed_uuids = {t["uuid"] for t in response.json()}
        assert dynamic_tool["uuid"] not in listed_uuids, response.text
