from .framework import (
    SeleniumTestCase,
    selenium_test,
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

        inttest_div_element = self.tool_parameter_div("inttest")
        inttest_input_element = inttest_div_element.find_element_by_css_selector("input")
        recorded_val = inttest_input_element.get_attribute("value")
        # Assert form re-rendered with correct value in textbox.
        assert recorded_val == "42", recorded_val
        self.tool_execute()

        self.history_panel_wait_for_hid_ok(2)
        self._check_dataset_details_for_inttest_value(2)

    @selenium_test
    def test_run_data(self):
        test_path = self.get_filename("1.fasta")
        test_path_decoy = self.get_filename("1.txt")
        self.perform_upload(test_path)
        self.perform_upload(test_path_decoy)
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_wait_for_hid_ok(2)

        self.home()
        self.tool_open("head")
        self.tool_set_value("input", "1.fasta", expected_type="data")
        self.tool_execute()
        self.history_panel_wait_for_hid_ok(3)

        latest_hda = self.latest_history_item()
        assert latest_hda["hid"] == 3
        assert latest_hda["name"] == "Select first on data 1"

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
        self.tool_execute()
