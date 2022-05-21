from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class HistoryStructureTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    @managed_history
    def test_history_structure(self):
        def assert_details(expected_to_be_visible):

            error_message = "details are visible!"
            if expected_to_be_visible:
                error_message = "details are not visible!"

            assert expected_to_be_visible == self.components.history_structure.details.is_displayed, error_message

        self.perform_upload(self.get_filename("1.fasta"))
        self.wait_for_history()
        self.components.history_structure.header.assert_absent_or_hidden()
        self.components.history_structure.dataset.assert_absent_or_hidden()

        self.history_panel_show_structure()

        # assert details are not visible before expand
        self.components.history_structure.details.assert_absent_or_hidden()

        self.components.history_structure.dataset.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        assert_details(True)
        self.components.history_structure.header.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        assert_details(False)
        self.components.history_structure.dataset.assert_absent_or_hidden()
