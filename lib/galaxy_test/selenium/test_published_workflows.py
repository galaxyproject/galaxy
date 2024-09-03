from typing import (
    Any,
    Dict,
)

from .framework import (
    selenium_test,
    SharedStateSeleniumTestCase,
)


class TestPublishedWorkflowsGrid(SharedStateSeleniumTestCase):
    @selenium_test
    def test_index(self):
        self.navigate_to_published_workflows()
        self.components.workflows.dropdown(id=self.id_1).wait_for_visible()

    def setup_shared_state(self):
        self.user1_email = self._get_random_email("test1")
        self.user2_email = self._get_random_email("test2")
        self.register(self.user1_email)
        workflow_1 = self._new_public_workflow()
        self.name_1 = workflow_1["name"]
        self.id_1 = workflow_1["id"]
        self.logout_if_needed()

        self.register(self.user2_email)
        workflow_2 = self._new_public_workflow()
        self.name_2 = workflow_2["name"]
        self.id_2 = workflow_2["id"]
        self.logout_if_needed()

    def _new_public_workflow(self) -> Dict[str, Any]:
        name = self._get_random_name()
        contents = self.workflow_populator.load_workflow(name)
        workflow_response = self.workflow_populator.create_workflow_response(contents, publish=True)
        workflow_response.raise_for_status()
        workflow = workflow_response.json()
        return workflow
