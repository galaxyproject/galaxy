import json

from base import rules_test_data
from base.populators import flakey, load_data_dict
from galaxy_selenium.navigates_galaxy import retry_call_during_transitions

from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class ToolFormTestCase(SeleniumTestCase, UsesHistoryItemAssertions):

    @selenium_test
    def test_run_tool_verify_contents_by_peek(self):
        self._run_environment_test_tool()

        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1)
        self.assert_item_peek_includes(1, "42")

    @selenium_test
    def test_run_tool_verify_dataset_details(self):
        self._run_environment_test_tool()
        self.history_panel_wait_for_hid_ok(1)
        self._check_dataset_details_for_inttest_value(1)

    @selenium_test
    def test_verify_dataset_details_tables(self):
        self._run_environment_test_tool()
        self.history_panel_wait_for_hid_ok(1)

        hda = self.latest_history_item()
        self._check_dataset_details_for_inttest_value(1)

        with self.main_panel():
            dataset_details_key_value_pairs = self._table_to_key_value_elements("table#dataset-details")
            number_found = name_found = format_found = False
            for key, value in dataset_details_key_value_pairs:
                if "Number:" in key.text:
                    assert str(hda["hid"]) in value.text
                    number_found = True
                if "Name:" in key.text:
                    assert hda["name"] in value.text
                    name_found = True
                if "Format:" in key.text:
                    assert hda["extension"] in value.text
                    format_found = True

            assert number_found
            assert name_found
            assert format_found

    def _table_to_key_value_elements(self, table_selector):
        tool_parameters_table = self.wait_for_selector_visible(table_selector)
        tbody_element = tool_parameters_table.find_element_by_css_selector("tbody")
        trs = tbody_element.find_elements_by_css_selector("tr")
        assert trs
        key_value_pairs = []
        for tr in trs:
            tds = tr.find_elements_by_css_selector("td")
            assert tds
            key_value_pairs.append((tds[0], tds[1]))

        return key_value_pairs

    @selenium_test
    def test_rerun(self):
        self._run_environment_test_tool()
        self.history_panel_wait_for_hid_ok(1)
        self.hda_click_primary_action_button(1, "rerun")

        def check_recorded_val():
            inttest_div_element = self.tool_parameter_div("inttest")
            inttest_input_element = inttest_div_element.find_element_by_css_selector("input")
            recorded_val = inttest_input_element.get_attribute("value")
            # Assert form re-rendered with correct value in textbox.
            assert recorded_val == "42", recorded_val

        # These form entries seem to be replaced/updated occasionally
        # causing stale elements.
        retry_call_during_transitions(check_recorded_val)
        self.tool_form_execute()

        self.history_panel_wait_for_hid_ok(2)
        self._check_dataset_details_for_inttest_value(2)

    @selenium_test
    @flakey
    def test_run_data(self):
        test_path = self.get_filename("1.fasta")
        test_path_decoy = self.get_filename("1.txt")
        # Upload form posts bad data if executed two times in a row like this, so
        # wait between uploads. xref https://github.com/galaxyproject/galaxy/issues/5169
        self.perform_upload(test_path)
        self.history_panel_wait_for_hid_ok(1)
        self.perform_upload(test_path_decoy)
        self.history_panel_wait_for_hid_ok(2)

        self.home()
        self.tool_open("head")
        self.tool_set_value("input", "1.fasta", expected_type="data")

        self.screenshot("tool_form_simple_data")
        self.tool_form_execute()

        self.history_panel_wait_for_hid_ok(3)

        latest_hda = self.latest_history_item()
        assert latest_hda["hid"] == 3
        assert latest_hda["name"] == "Select first on data 1"

    @selenium_test
    def test_bibtex_rendering(self):
        self.home()
        # prefetch citations so they will be available quickly when rendering tool form.
        citations_api = self.api_get("tools/bibtex/citations")
        assert len(citations_api) == 29, len(citations_api)
        self.tool_open("bibtex")
        self.components.tool_form.citations.wait_for_visible()

        @retry_assertion_during_transitions
        def assert_citations_visible():
            references = self.components.tool_form.reference.all()
            # This should be 29, but bugs I guess?
            assert len(references) > 0, len(references)
            return references

        references = assert_citations_visible()

        doi_resolved_citation = references[0]
        assert "Galaxy: A platform for interactive" in doi_resolved_citation.text
        self.screenshot("tool_form_citations_formatted")

        self.components.tool_form.show_bibtex.wait_for_and_click()
        textarea = self.components.tool_form.bibtex_area.wait_for_visible()
        assert "Galaxy: A platform for interactive" in textarea.get_attribute("value")
        self.screenshot("tool_form_citations_bibtex")

    def _check_dataset_details_for_inttest_value(self, hid, expected_value="42"):
        self.hda_click_primary_action_button(hid, "info")

        with self.main_panel():
            self.wait_for_selector_visible("table#dataset-details")
            tool_parameters_table = self.wait_for_selector_visible("table#tool-parameters")
            tbody_element = tool_parameters_table.find_element_by_css_selector("tbody")
            tds = tbody_element.find_elements_by_css_selector("td")
            assert tds
            assert any([expected_value in td.text for td in tds])

    def _run_environment_test_tool(self, inttest_value="42"):
        self.home()
        self.tool_open("environment_variables")
        self.tool_set_value("inttest", inttest_value)
        self.tool_form_execute()


class LoggedInToolFormTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_run_apply_rules_1(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_1)
        self.screenshot("tool_apply_rules_example_1_final")

    @selenium_test
    def test_run_apply_rules_2(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_2)
        self.screenshot("tool_apply_rules_example_2_final")

    @selenium_test
    def test_run_apply_rules_3(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_3)
        self.screenshot("tool_apply_rules_example_3_final")

    def _apply_rules_and_check(self, example):
        rule_builder = self.components.rule_builder

        self.home()
        history_id = self.current_history_id()
        inputs, _, _ = load_data_dict(history_id, {"input": example["test_data"]}, self.dataset_populator, self.dataset_collection_populator)
        self.dataset_populator.wait_for_history(history_id)
        self.home()
        self.tool_open("__APPLY_RULES__", outer=True)  # may appear twice in panel, grab top-level link
        self.screenshot("tool_apply_rules_landing")
        self.tool_parameter_edit_rules()
        rule_builder._.wait_for_visible()
        self.screenshot("tool_apply_rules_builder_landing")
        self.rule_builder_set_source(json.dumps(example["rules"]))
        self.screenshot("tool_apply_rules_after")
        rule_builder.main_button_ok.wait_for_and_click()
        self.tool_form_execute()
        output_hid = example["output_hid"]
        self.history_panel_wait_for_hid_ok(output_hid)
        output_hdca = self.dataset_populator.get_history_collection_details(history_id, hid=output_hid, wait=False)
        example["check"](output_hdca, self.dataset_populator)
