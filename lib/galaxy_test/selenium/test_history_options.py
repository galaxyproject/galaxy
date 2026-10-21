from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity


class TestHistoryOptions(SeleniumTestCase, UsesUploadActivity):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_options(self):
        self.upload_context("paste-content").stage_paste_content("text content").start()
        menu_selector = self.navigation.history_panel.selectors.options_menu
        self.wait_for_absent_or_hidden(menu_selector)
        self.click_history_options()
        component = self.wait_for_visible(menu_selector)
        self.screenshot("history_options")
        self.send_escape(component)
        self.wait_for_absent_or_hidden(menu_selector)
        hid = 1
        self.history_panel_wait_for_hid_state(hid, "ok")
        self.history_panel_click_item_title(hid=hid, wait=True)
        item_component = self.history_panel_item_body_component(hid=hid)
        item_component.wait_for_visible()
        # Wait for metadata to replace the loading placeholder before testing collapse.
        self.history_panel_item_component(hid=hid).summary.wait_for_visible()
        self.history_panel_click_item_title(hid=hid, wait=True)
        item_component.assert_absent_or_hidden_after_transitions()

    @selenium_test
    @managed_history
    def test_export_tool_references(self):
        history_id = self.current_history_id()
        self.dataset_populator.run_tool("bibtex", {}, history_id)
        self.dataset_populator.wait_for_history(history_id)
        tool_citation_count = len(self.api_get(f"histories/{history_id}/citations"))
        # Galaxy's own citation is listed ahead of the tools'.
        galaxy_citation_key = self.dataset_populator.get_configuration()["citation_bibtex"].split(",")[0]
        self.home()
        self.click_history_option_tool_references()
        citations = self.components.citations

        @retry_assertion_during_transitions
        def assert_references(galaxy_fragment, tool_fragment):
            references = [reference.text for reference in citations._.reference.all()]
            assert len(references) == tool_citation_count + 1, references
            assert galaxy_fragment in references[0], references
            assert any(tool_fragment in reference for reference in references[1:]), references

        assert_references("Galaxy", "Garrison")
        self.screenshot("history_tool_references_apa")
        citations.bibtex_tab.wait_for_and_click()
        assert_references(galaxy_citation_key, "@misc{Garrison2015")
        self.screenshot("history_tool_references_bibtex")
        citations.apa_tab.wait_for_and_click()
        assert_references("Galaxy", "Garrison")
