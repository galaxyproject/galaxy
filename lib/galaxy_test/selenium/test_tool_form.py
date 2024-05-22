import json
from typing import (
    Any,
    Dict,
    List,
)

import pytest
from selenium.webdriver.common.by import By

from galaxy.model.unittest_utils.store_fixtures import one_hda_model_store_dict
from galaxy.selenium.navigates_galaxy import retry_call_during_transitions
from galaxy.util.unittest_utils import skip_if_github_down
from galaxy_test.base import rules_test_data
from galaxy_test.base.populators import (
    flakey,
    stage_rules_example,
)
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestToolForm(SeleniumTestCase, UsesHistoryItemAssertions):
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
            if "Number" in key.text:
                assert str(hda["hid"]) in value.text
                number_found = True
            if "Name" in key.text:
                assert hda["name"] in value.text
                name_found = True
            if "Format" in key.text:
                assert hda["extension"] in value.text
                format_found = True

        assert number_found
        assert name_found
        assert format_found

        job_outputs = self._table_to_key_value_elements("table#job-outputs")
        assert job_outputs[0][0].text == "environment_variables"
        generic_item = job_outputs[0][1]
        assert "1: environment_variables" in generic_item.text
        generic_item.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        assert generic_item.find_element(By.CSS_SELECTOR, "pre").text == "42\nmoo\nNOTTHREE"
        generic_item.find_element(By.CSS_SELECTOR, "[title='Run Job Again']").click()
        self.components.tool_form.execute.wait_for_visible()

    @selenium_test
    def test_drilldown_tool(self):
        self._open_drilldown_test_tool()
        # click first option in first drilldown component
        self.wait_for_and_click(self.components.tool_form.drilldown_expand)
        self.wait_for_and_click(self.components.tool_form.drilldown_option)
        # click select all in second drilldown component
        self.wait_for_and_click(self.components.tool_form.drilldown_select_all(parameter="dd_recurse"))
        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(1)
        # click hid 1 in history panel
        self.history_panel_click_item_title(hid=1)
        # assert that the dataset peek is d = a dd_recurse = a,b,c
        self.assert_item_peek_includes(1, "dd a")
        self.assert_item_peek_includes(1, "dd_recurse aa,aba,abb,ba,bba,bbb")

    def _open_drilldown_test_tool(self):
        self.home()
        self.tool_open("drill_down")

    @staticmethod
    def click_menu_item(menu, text):
        for element in menu.find_elements(By.CSS_SELECTOR, "a"):
            if element.text == text:
                return element.click()

    def _table_to_key_value_elements(self, table_selector):
        tool_parameters_table = self.wait_for_selector_visible(table_selector)
        tbody_element = tool_parameters_table.find_element(By.CSS_SELECTOR, "tbody")
        trs = tbody_element.find_elements(By.CSS_SELECTOR, "tr")
        assert trs
        key_value_pairs = []
        for tr in trs:
            tds = tr.find_elements(By.CSS_SELECTOR, "td")
            assert tds
            key_value_pairs.append((tds[0], tds[1]))

        return key_value_pairs

    @selenium_test
    def test_repeat_reordering(self):
        self.home()
        self.tool_open("text_repeat")

        def assert_input_order(inputs: List[str]):
            for index, input in enumerate(inputs):
                parameter_input = self.components.tool_form.parameter_input(parameter=f"the_repeat_{index}|texttest")
                parameter_value = parameter_input.wait_for_value()
                assert parameter_value == input

        self.components.tool_form.repeat_insert.wait_for_and_click()
        self.tool_set_value("the_repeat_0|texttest", "Text A")
        self.components.tool_form.repeat_insert.wait_for_and_click()
        self.tool_set_value("the_repeat_1|texttest", "Text B")
        self.components.tool_form.repeat_insert.wait_for_and_click()
        self.tool_set_value("the_repeat_2|texttest", "Text C")

        assert_input_order(["Text A", "Text B", "Text C"])
        self.components.tool_form.repeat_move_up(parameter="the_repeat_1").wait_for_and_click()
        assert_input_order(["Text B", "Text A", "Text C"])
        self.components.tool_form.repeat_move_up(parameter="the_repeat_2").wait_for_and_click()
        assert_input_order(["Text B", "Text C", "Text A"])
        self.components.tool_form.repeat_move_up(parameter="the_repeat_1").wait_for_and_click()
        assert_input_order(["Text C", "Text B", "Text A"])
        self.components.tool_form.repeat_move_up(parameter="the_repeat_0").wait_for_and_click()
        assert_input_order(["Text C", "Text B", "Text A"])

        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(1)

        details = [d.text for d in self._get_dataset_tool_parameters(1)]

        assert details == ["texttest", "Text C", "texttest", "Text B", "texttest", "Text A"]

    @selenium_test
    def test_rerun(self):
        self._run_environment_test_tool()
        self.history_panel_wait_for_hid_ok(1)
        self.hda_click_primary_action_button(1, "rerun")

        def check_recorded_val():
            inttest_div_element = self.tool_parameter_div("inttest")
            inttest_input_element = inttest_div_element.find_element(By.CSS_SELECTOR, "input")
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
    def test_rerun_deleted_dataset(self):
        # upload a first dataset that should not become selected on re-run
        test_path = self.get_filename("1.tabular")
        self.perform_upload(test_path)
        self.history_panel_wait_for_hid_ok(1)
        self.tool_open("column_param")
        self.select_set_value("#col", "3")
        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(2)
        # delete source dataset and click re-run on resulting dataset
        item = self.history_panel_item_component(hid=1)
        item.delete_button.wait_for_and_click()
        item = self.history_panel_item_component(hid=2)
        item.title.wait_for_and_click()
        item.rerun_button.wait_for_and_click()
        # validate initial warnings
        error_input1 = self.components.tool_form.parameter_error(parameter="input1").wait_for_visible()
        error_col = self.components.tool_form.parameter_error(parameter="col").wait_for_visible()
        assert (
            error_input1.text
            == "parameter 'input1': the previously selected dataset has been deleted. Using default: ''."
        )
        assert error_col.text == "parameter 'col': an invalid option ('3') was selected (valid options: 1)"
        # validate errors when inputs are missing
        self.components.tool_form.parameter_data_input_collection(parameter="input1").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        error_input1 = self.components.tool_form.parameter_error(parameter="input1").wait_for_visible()
        error_col = self.components.tool_form.parameter_error(parameter="col").wait_for_visible()
        error_col_names = self.components.tool_form.parameter_error(parameter="col_names").wait_for_visible()
        assert error_input1.text == "Please provide a value for this option."
        assert error_col.text == "parameter 'col': requires a value, but no legal values defined"
        assert error_col_names.text == "parameter 'col_names': requires a value, but no legal values defined"
        # validate warnings when inputs are restored
        self.components.tool_form.parameter_data_input_single(parameter="input1").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        error_input1 = self.components.tool_form.parameter_error(parameter="input1").wait_for_visible()
        error_col = self.components.tool_form.parameter_error(parameter="col").wait_for_visible()
        assert (
            error_input1.text
            == "parameter 'input1': the previously selected dataset has been deleted. Using default: ''."
        )
        assert error_col.text == "parameter 'col': an invalid option ('3') was selected (valid options: 1)"

    @selenium_test
    def test_rerun_dataset_collection_element(self):
        # upload a first dataset that should not become selected on re-run
        test_path = self.get_filename("1.fasta")
        self.perform_upload(test_path)
        self.history_panel_wait_for_hid_ok(1)

        history_id = self.current_history_id()
        # upload a nested collection
        self.dataset_collection_populator.create_list_of_list_in_history(
            history_id,
            collection_type="list:list",
            wait=True,
        ).json()["id"]
        self.tool_open("identifier_multiple")
        self.components.tool_form.parameter_data_input_collection(parameter="input1").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        select_field = self.components.tool_form.parameter_data_select(parameter="input1")
        self.select_set_value(select_field, "list:list")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(7)
        self.history_panel_expand_collection(7)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.history_panel_click_item_title(1)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.hda_click_primary_action_button(1, "rerun")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.tool_form_execute()
        self.components.history_panel.collection_view.back_to_history.wait_for_and_click()
        self.history_panel_wait_for_hid_ok(9)

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
        citation_count = len(citations_api)
        self.tool_open("bibtex")
        self.components.tool_form.about.wait_for_and_click()

        @retry_assertion_during_transitions
        def assert_citations_visible():
            references = self.components.tool_form.reference.all()
            if (references_rendered := len(references)) != citation_count:
                citations_api = self.api_get("tools/bibtex/citations")
                current_citation_count = len(citations_api)
                message = f"Expected {citation_count} references to be rendered, {references_rendered} actually rendered. Currently the API yields {current_citation_count} references"
                raise AssertionError(message)
            return references

        references = assert_citations_visible()
        doi_resolved_citation = references[0]
        assert "platform for interactive" in doi_resolved_citation.text
        self.screenshot("tool_form_citations_formatted")

    def _check_dataset_details_for_inttest_value(self, hid, expected_value="42"):
        tds = self._get_dataset_tool_parameters(hid)
        assert tds
        assert any(expected_value in td.text for td in tds)

    def _get_dataset_tool_parameters(self, hid):
        self.hda_click_details(hid)
        self.components.dataset_details._.wait_for_visible()
        tool_parameters_table = self.components.dataset_details.tool_parameters.wait_for_visible()
        tbody_element = tool_parameters_table.find_element(By.CSS_SELECTOR, "tbody")
        tds = tbody_element.find_elements(By.CSS_SELECTOR, "td")
        return tds

    def _run_environment_test_tool(self, inttest_value="42"):
        self.home()
        self.tool_open("environment_variables")
        self.tool_set_value("inttest", inttest_value)
        self.tool_form_execute()


class TestLoggedInToolForm(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_dataset_state_filtering(self):
        # upload an ok (HID 1) and a discarded (HID 2) dataset and run a tool
        # normally HID 2 would be selected but since it is discarded - it won't
        # be an option so verify the result was run with HID 1.
        test_path = self.get_filename("1.fasta")
        self.perform_upload(test_path)
        self.history_panel_wait_for_hid_ok(1)

        history_id = self.current_history_id()
        self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=one_hda_model_store_dict(include_source=False),
        )

        self.home()
        self.tool_open("head")
        self.components.tool_form.execute.wait_for_visible()
        self.screenshot("tool_form_with_filtered_discarded_input")
        self.tool_form_execute()

        self.history_panel_wait_for_hid_ok(3)

        latest_hda = self.latest_history_item()
        assert latest_hda["hid"] == 3
        assert latest_hda["name"] == "Select first on data 1"

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

    @selenium_test
    def test_run_apply_rules_4(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_4)
        self.screenshot("tool_apply_rules_example_4_final")

    @selenium_test
    @managed_history
    @skip_if_github_down
    @pytest.mark.gtn_screenshot
    @pytest.mark.local
    def test_run_apply_rules_tutorial(self):
        self.home()
        self.upload_rule_start()
        self.upload_rule_set_data_type("Collections")
        self.components.upload.rule_source_content.wait_for_and_send_keys(
            """https://raw.githubusercontent.com/jmchilton/galaxy/apply_rules_tutorials/test-data/rules/treated1fb.txt treated_single_1
https://raw.githubusercontent.com/jmchilton/galaxy/apply_rules_tutorials/test-data/rules/treated2fb.txt treated_paired_2
https://raw.githubusercontent.com/jmchilton/galaxy/apply_rules_tutorials/test-data/rules/treated3fb.txt treated_paired_3
https://raw.githubusercontent.com/jmchilton/galaxy/apply_rules_tutorials/test-data/rules/untreated1fb.txt untreated_single_4
https://raw.githubusercontent.com/jmchilton/galaxy/apply_rules_tutorials/test-data/rules/untreated2fb.txt untreated_single_5
https://raw.githubusercontent.com/jmchilton/galaxy/apply_rules_tutorials/test-data/rules/untreated3fb.txt untreated_paired_6
https://raw.githubusercontent.com/jmchilton/galaxy/apply_rules_tutorials/test-data/rules/untreated4fb.txt untreated_paired_7
"""
        )
        self.screenshot("rules_apply_rules_example_4_1_input_paste")
        self.upload_rule_build()
        rule_builder = self.components.rule_builder
        rule_builder._.wait_for_and_click()
        self.rule_builder_set_mapping("url", "A")
        self.rule_builder_set_mapping("list-identifiers", ["B"])
        self.rule_builder_set_collection_name("flat_count_list")
        self.rule_builder_set_extension("txt")

        self.screenshot("rules_apply_rules_example_4_2_input_rules")
        rule_builder.main_button_ok.wait_for_and_click()
        self.history_panel_wait_for_hid_ok(1)
        self.screenshot("rules_apply_rules_example_4_3_input_ready")
        self.history_multi_view_display_collection_contents(1, "list")
        self.screenshot("rules_apply_rules_example_4_4_input_list")
        self.home()
        add_depth_rules = {
            "rules": [
                {
                    "type": "add_column_metadata",
                    "value": "identifier0",
                },
                {"type": "add_column_regex", "target_column": 0, "expression": "(.*)_(.*)_.*", "group_count": 2},
            ],
            "mapping": [
                {
                    "type": "list_identifiers",
                    "columns": [1, 2, 0],
                }
            ],
        }
        self._tool_apply_with_source(
            add_depth_rules,
            hid=1,
            landing_screenshot="rules_apply_rules_example_4_5_apply_rules_landing",
            rule_init_screenshot="rules_apply_rules_example_4_6_apply_rules_init_flat",
            rule_complete_screenshot="rules_apply_rules_example_4_7_apply_rules_add_depth",
        )
        self.history_panel_wait_for_hid_ok(16)
        self.history_multi_view_display_collection_contents(16, "list:list:list")
        self.screenshot("rules_apply_rules_example_4_8_nested")
        self.home()
        invert_rules = {
            "rules": [
                {
                    "type": "add_column_metadata",
                    "value": "identifier0",
                },
                {
                    "type": "add_column_metadata",
                    "value": "identifier1",
                },
                {
                    "type": "add_column_metadata",
                    "value": "identifier2",
                },
            ],
            "mapping": [
                {
                    "type": "list_identifiers",
                    "columns": [1, 0, 2],
                }
            ],
        }
        self._tool_apply_with_source(
            invert_rules,
            rule_init_screenshot="rules_apply_rules_example_4_9_apply_rules_init_nested",
            rule_complete_screenshot="rules_apply_rules_example_4_10_apply_rules_inverted",
        )
        self.history_panel_wait_for_hid_ok(24)
        self.history_multi_view_display_collection_contents(24, "list:list:list")
        self.screenshot("rules_apply_rules_example_4_11_inverted")
        self.home()
        filter_rules = {
            "rules": [
                {
                    "type": "add_column_metadata",
                    "value": "identifier0",
                },
                {
                    "type": "add_filter_regex",
                    "target_column": 0,
                    "expression": ".*_single_.*",
                    "invert": False,
                },
            ],
            "mapping": [
                {
                    "type": "list_identifiers",
                    "columns": [0],
                }
            ],
        }
        self._tool_apply_with_source(
            filter_rules, hid=1, rule_complete_screenshot="rules_apply_rules_example_4_12_apply_rules_filter"
        )
        self.history_panel_wait_for_hid_ok(28)
        self.history_multi_view_display_collection_contents(28, "list")
        self.screenshot("rules_apply_rules_example_4_13_filtered")
        self.home()
        filter_and_nest_rules = {
            "rules": [
                {
                    "type": "add_column_metadata",
                    "value": "identifier0",
                },
                {
                    "type": "add_filter_regex",
                    "target_column": 0,
                    "expression": ".*_single_.*",
                    "invert": False,
                },
                {"type": "add_column_regex", "target_column": 0, "expression": "(.*)_single_.*", "group_count": 1},
            ],
            "mapping": [
                {
                    "type": "list_identifiers",
                    "columns": [1, 0],
                }
            ],
        }
        self._tool_apply_with_source(
            filter_and_nest_rules,
            hid=1,
            rule_complete_screenshot="rules_apply_rules_example_4_14_apply_rules_filtered_and_nested",
        )
        self.history_panel_wait_for_hid_ok(32)
        self.history_multi_view_display_collection_contents(32, "list:list")
        self.screenshot("rules_apply_rules_example_4_15_filtered_and_nested")

    def _apply_rules_and_check(self, example: Dict[str, Any]) -> None:
        rule_builder = self.components.rule_builder

        self.home()
        history_id = self.current_history_id()
        stage_rules_example(self.api_interactor_for_logged_in_user(), history_id, example)
        self.dataset_populator.wait_for_history(history_id)
        self.home()
        self._tool_open_apply_rules()
        self.screenshot("tool_apply_rules_landing")
        self.tool_parameter_edit_rules()
        rule_builder._.wait_for_visible()
        self.screenshot("tool_apply_rules_builder_landing")
        self.rule_builder_set_source(json.dumps(example["rules"]))
        self.screenshot("tool_apply_rules_after")
        rule_builder.main_button_ok.wait_for_and_click()
        self.tool_form_execute()
        output_hid = example["output_hid"]
        self.home()
        self.history_panel_wait_for_hid_ok(output_hid)
        output_hdca = self.dataset_populator.get_history_collection_details(history_id, hid=output_hid, wait=False)
        example["check"](output_hdca, self.dataset_populator)

    def _tool_apply_with_source(
        self, rules_json, hid=None, landing_screenshot=None, rule_init_screenshot=None, rule_complete_screenshot=None
    ):
        self._tool_open_apply_rules()
        if hid:
            self.tool_set_value("input", f"{hid}:", expected_type="data_collection")
        if landing_screenshot:
            self.screenshot(landing_screenshot)
        rule_builder = self.components.rule_builder
        self.tool_parameter_edit_rules()
        rule_builder._.wait_for_visible()
        if rule_init_screenshot:
            self.screenshot(rule_init_screenshot)
        self.rule_builder_set_source(json.dumps(rules_json))
        if rule_complete_screenshot:
            self.screenshot(rule_complete_screenshot)
        rule_builder.main_button_ok.wait_for_and_click()
        self.tool_form_execute()

    def _tool_open_apply_rules(self):
        self.tool_open("__APPLY_RULES__", outer=True)  # may appear twice in panel, grab top-level link
