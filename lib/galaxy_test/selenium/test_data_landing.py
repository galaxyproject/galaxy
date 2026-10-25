import base64

from galaxy.schema.fetch_data import (
    CreateDataLandingPayload,
    DataLandingRequestState,
)
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


def _base64_url(content: str) -> str:
    return f"base64://{base64.b64encode(content.encode()).decode()}"


class TestDataLanding(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_edited_fetch_grid_cells_reach_request(self):
        request_state = DataLandingRequestState(
            targets=[
                {
                    "destination": {"type": "hdas"},
                    "items": [
                        {
                            "src": "url",
                            "url": _base64_url("original content\n"),
                            "name": "original.txt",
                            "ext": "txt",
                            "deferred": False,
                        }
                    ],
                }
            ],
        )
        landing = self.dataset_populator.create_data_landing(
            CreateDataLandingPayload(request_state=request_state, public=True)
        )
        self.go_to_tool_landing(str(landing.uuid))
        data_landing = self.components.data_landing
        for column, text in [("name", "edited.txt"), ("url", _base64_url("edited content\n"))]:
            self.ag_grid_edit_cell(data_landing, column, 2, text, clear=True)
        self.screenshot("data_landing_fetch_grid_edited")
        data_landing.execute.wait_for_and_click()
        data_landing.success.wait_for_visible(wait_type=self.wait_types.JOB_COMPLETION)
        self.history_panel_wait_for_hid_ok(1)
        history_id = self.current_history_id()
        details = self.dataset_populator.get_history_dataset_details(history_id, hid=1)
        assert details["name"] == "edited.txt", details["name"]
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=1)
        assert content == "edited content\n", content
