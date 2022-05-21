import pytest

from galaxy_test.base.populators import flakey
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class HistoryPanelPaginationTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    @flakey  # The next button doesn't always work - maybe a delay in JS callback registering for that.
    def test_pagination(self):
        if self.is_beta_history():
            raise pytest.skip("There is no pagination on the beta history panel")

        history_id = self.current_history_id()

        self.dataset_populator.new_dataset(history_id, content="1\t2\t3", name="data1")
        self.dataset_populator.new_dataset(history_id, content="2\t3\t4", name="data2")
        self.dataset_populator.new_dataset(history_id, content="3\t4\t5", name="data3")
        self.dataset_populator.new_dataset(history_id, content="4\t5\t6", name="data4")
        self.dataset_populator.new_dataset(history_id, content="5\t6\t7", name="data5")

        self.home()
        for hid in [1, 2, 3, 4, 5]:
            self.history_panel_wait_for_hid_state(hid, "ok")

        with self.local_storage("historyContentsLimitPerPageDefault", 3):
            self.home()
            self.history_panel_wait_for_hid_state(5, "ok")
            self.screenshot("history_panel_pagination_initial")
            pagination_option_text = self.components.history_panel.pagination_pages_selected_option.wait_for_text()
            assert "1st of 2 pages" in pagination_option_text
            self.components.history_panel.pagination_pages.wait_for_and_click()
            self.screenshot("history_panel_pagination_pages_drop_down")
            self.components.history_panel.pagination_next.wait_for_and_click()
            self.sleep_for(self.wait_types.UX_TRANSITION)
            self.screenshot("history_panel_pagination_second")
            pagination_option_text = self.components.history_panel.pagination_pages_selected_option.wait_for_text()
            assert "2nd of 2 pages" in pagination_option_text
            self.components.history_panel.pagination_previous.wait_for_and_click()

            self.sleep_for(self.wait_types.UX_TRANSITION)
            pagination_option_text = self.components.history_panel.pagination_pages_selected_option.wait_for_text()
            assert "1st of 2 pages" in pagination_option_text
