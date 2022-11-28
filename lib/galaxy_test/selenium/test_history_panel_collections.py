import time

import pytest

from galaxy.selenium.navigates_galaxy import WAIT_TYPES
from galaxy_test.base.api_asserts import assert_status_code_is
from galaxy_test.base.populators import flakey
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class HistoryPanelCollectionsTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_mapping_collection_states_terminal(self):
        history_id = self.current_history_id()
        input_collection, failed_collection = self._generate_partially_failed_collection_with_input()
        input_hid = input_collection["hid"]
        failed_hid = failed_collection["hid"]
        self.home()

        ok_inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": input_collection["id"]}]},
            "sleep_time": 0,
        }
        ok_response = self.dataset_populator.run_tool(
            "cat_data_and_sleep",
            ok_inputs,
            history_id,
        )
        ok_hid = ok_response["implicit_collections"][0]["hid"]

        self.history_panel_wait_for_hid_state(input_hid, "ok")
        self.history_panel_wait_for_hid_state(failed_hid, "error")
        self.history_panel_wait_for_hid_state(ok_hid, "ok")
        self.screenshot("history_panel_collections_state_mapping_terminal")

    @selenium_test
    @flakey  # Some times a Paste web thread will stall when jobs are running.
    def test_mapping_collection_states_running(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1"]
        ).json()
        running_inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": input_collection["id"]}]},
            "sleep_time": 60,
        }
        running_response = self.dataset_populator.run_tool_raw(
            "cat_data_and_sleep",
            running_inputs,
            history_id,
        )
        try:
            assert_status_code_is(running_response, 200)
            running_hid = running_response.json()["implicit_collections"][0]["hid"]

            # sleep really shouldn't be needed :(
            time.sleep(1)

            self.home()

            self.history_panel_wait_for_hid_state(running_hid, "running", 1)
            self.screenshot("history_panel_collections_state_mapping_running")
        finally:
            for job in running_response.json()["jobs"]:
                self.dataset_populator.cancel_job(job["id"])

    @selenium_test
    def test_output_collection_states_terminal(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"]
        ).json()["outputs"][0]

        ok_inputs = {"input1": {"src": "hdca", "id": input_collection["id"]}}
        ok_response = self.dataset_populator.run_tool("collection_creates_list", ok_inputs, history_id)
        ok_hid = ok_response["output_collections"][0]["hid"]
        assert ok_hid > 0

        failed_response = self.dataset_populator.run_tool(
            "collection_creates_dynamic_nested_fail",
            {},
            history_id,
        )
        failed_hid = failed_response["output_collections"][0]["hid"]
        assert failed_hid > 0

        # sleep really shouldn't be needed :(
        time.sleep(1)

        self.home()

        self.history_panel_wait_for_hid_state(ok_hid, "ok")
        self.history_panel_wait_for_hid_state(failed_hid, "error")

        self.screenshot("history_panel_collections_state_terminal")

    @selenium_test
    @flakey  # Some times a Paste web thread will stall when jobs are running.
    def test_output_collection_states_running(self):
        history_id = self.current_history_id()
        running_inputs = {
            "sleep_time": 180,
        }
        payload = self.dataset_populator.run_tool(
            "collection_creates_dynamic_nested",
            running_inputs,
            history_id,
        )
        assert payload["output_collections"]
        assert payload["jobs"]
        assert len(payload["jobs"]) > 0
        assert len(["output_collections"]) > 0

        running_hid = payload["output_collections"][0]["hid"]
        assert running_hid

        try:
            if not self.is_beta_history():
                # sleep really shouldn't be needed :(
                time.sleep(1)
                self.home()
            self.history_panel_wait_for_hid_state(running_hid, "running")
            self.screenshot("history_panel_collections_state_running")
        finally:
            for job in payload["jobs"]:
                self.dataset_populator.cancel_job(job["id"])

    @selenium_test
    def test_collection_job_details(self):
        ok_collection_hid, failed_collection_hid = self._generate_ok_and_failed_collections()
        ok_collection_element = self.history_panel_wait_for_hid_state(ok_collection_hid, "ok")
        failed_collection_element = self.history_panel_wait_for_hid_state(failed_collection_hid, "error")

        ok_collection_element.collection_job_details_button.wait_for_and_click()
        self.components.job_details.galaxy_tool_with_id(tool_id="collection_creates_list").wait_for_visible()
        tool_exit_code_component = self.components.job_details.tool_exit_code.wait_for_visible()
        self.screenshot("history_panel_collections_job_details_ok")
        assert int(tool_exit_code_component.text) == 0

        failed_collection_element.collection_job_details_button.wait_for_and_click()
        self.components.job_details.galaxy_tool_with_id(tool_id="collection_creates_list_fail").wait_for_visible()
        tool_exit_code_component = self.components.job_details.tool_exit_code.wait_for_visible()
        self.screenshot("history_panel_collections_job_details_failed")
        assert int(tool_exit_code_component.text) > 0

    @selenium_test
    def test_back_to_history_button(self):
        input_collection = self._populated_paired_and_wait_for_it()
        collection_hid = input_collection["hid"]
        self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self.history_panel_expand_collection(collection_hid)
        self._back_to_history()
        self.history_panel_wait_for_hid_state(collection_hid, "ok")

    def _back_to_history(self):
        if self.is_beta_history():
            # it's either a single back button or a dropdown with an option depending
            # on how deeply nested the collection is
            menu = self.beta_history_element("collection breadcrumbs menu")
            if not menu.is_absent:
                # menu.is_displayed results in an error but I don't understand why
                menu.wait_for_and_click()
            back = self.beta_history_element("back to history")
        else:
            back = self.components.history_panel.collection_view.back
        back.wait_for_and_click()
        self.sleep_for(WAIT_TYPES.UX_RENDER)

    @selenium_test
    def test_rename_collection(self):
        input_collection = self._populated_paired_and_wait_for_it()
        collection_hid = input_collection["hid"]
        self.history_panel_wait_for_hid_state(collection_hid, "ok")

        new_name = "My New Name"
        self.history_panel_collection_rename(collection_hid, new_name, assert_old_name=input_collection["name"])
        if self.is_beta_history():
            self.screenshot("history_panel_collection_view_rename_beta")
        else:
            self.screenshot("history_panel_collection_view_rename")

        @retry_assertion_during_transitions
        def assert_name_changed():
            title_element = self.history_panel_collection_name_element()
            assert title_element.text == new_name

        assert_name_changed()

    @selenium_test
    def test_name_tags_display(self):
        # Test setting a name tag and viewing it from the outer history panel.
        input_collection = self._populated_paired_and_wait_for_it()
        collection_hid = input_collection["hid"]
        self.history_panel_expand_collection(collection_hid)
        self.sleep_for(self.wait_types.UX_RENDER)

        if self.is_beta_history():
            self.history_panel_add_tags(["#moo"])
        else:
            # the space on the end of the parent_selector is important
            self.tagging_add(["#moo"], parent_selector=".dataset-collection-panel .controls ")

        self.sleep_for(self.wait_types.HISTORY_POLL)
        self.screenshot("history_panel_collection_view_add_nametag")
        self._back_to_history()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.history_panel_wait_for_hid_state(collection_hid, "ok")
        nametags = self.history_panel_item_get_tags(collection_hid)
        assert nametags == ["#moo"]
        self.screenshot("history_panel_collection_with_nametag")

    @selenium_test
    def test_paired_display(self):
        input_collection = self._populated_paired_and_wait_for_it()
        collection_hid = input_collection["hid"]
        collection_view = self.history_panel_expand_collection(collection_hid)
        self.sleep_for(WAIT_TYPES.UX_TRANSITION)
        if self.is_beta_history():
            dataset_elements = collection_view.list_items_beta.all()
        else:
            dataset_elements = collection_view.list_items.all()
        assert len(dataset_elements) == 2, dataset_elements
        selector = ".title .name"
        if self.is_beta_history():
            selector = ".content-title"
        titles = [de.find_element_by_css_selector(selector).text for de in dataset_elements]
        assert titles == ["forward", "reverse"]
        self.screenshot("history_panel_collection_view_paired")

    @selenium_test
    @flakey  # Fails only in Jenkins full suite - possibly due to #3782
    def test_list_display(self):
        input_collection, failed_collection = self._generate_partially_failed_collection_with_input()
        failed_hid = failed_collection["hid"]

        self.home()
        self.history_panel_wait_for_hid_state(failed_hid, "error")
        collection_view = self.history_panel_expand_collection(failed_hid)

        @retry_assertion_during_transitions
        def check_four_datasets_shown():
            if self.is_beta_history():
                self.sleep_for(WAIT_TYPES.HISTORY_POLL)
                dataset_elements = collection_view.list_items_beta.all()
            else:
                dataset_elements = collection_view.list_items.all()
            assert len(dataset_elements) == 4, dataset_elements
            selector = ".title .name"
            if self.is_beta_history():
                selector = ".content-title"
            title_elements = [de.find_element_by_css_selector(selector).text for de in dataset_elements]
            assert title_elements == ["data1", "data2", "data3", "data4"]

        check_four_datasets_shown()
        self.screenshot("history_panel_collection_view_list")

    @selenium_test
    def test_list_paired_display(self):
        history_id = self.current_history_id()
        collection = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id).json()["outputs"][0]
        collection_hid = collection["hid"]
        self.home()
        self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self.history_panel_expand_collection(collection_hid)
        self.screenshot("history_panel_collection_view_list_paired")

    @selenium_test
    def test_list_list_display(self):
        history_id = self.current_history_id()
        collection = self.dataset_collection_populator.create_list_of_list_in_history(history_id).json()
        collection_hid = collection["hid"]
        self.home()
        self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self.history_panel_expand_collection(collection_hid)
        self.screenshot("history_panel_collection_view_list_list")

    @selenium_test
    def test_limiting_collection_rendering(self):
        if self.is_beta_history():
            raise pytest.skip("Beta history can scroll through collections of any length")
        history_id = self.current_history_id()
        collection = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"]
        ).json()
        collection_hid = collection["hid"]

        with self.local_storage("collectionFuzzyCountDefault", 2):
            self.home()

            self.history_panel_wait_for_hid_state(collection_hid, "ok")
            self.history_panel_expand_collection(collection_hid)
            self.screenshot("history_panel_collection_view_limiting")
            warning_text = self.components.history_panel.collection_view.elements_warning.wait_for_text()
            assert "only 2 of 4 items" in warning_text, warning_text

    def _generate_partially_failed_collection_with_input(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"], wait=True
        ).json()["outputs"][0]
        failed_response = self.dataset_populator.run_exit_code_from_file(history_id, input_collection["id"])
        failed_collection = failed_response["implicit_collections"][0]
        return input_collection, failed_collection

    def _populated_paired_and_wait_for_it(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_pair_in_history(history_id, wait=True).json()[
            "outputs"
        ][0]
        collection_hid = input_collection["hid"]
        if not self.is_beta_history():
            self.home()
        self.history_panel_wait_for_hid_state(collection_hid, "ok")

        return input_collection

    def _generate_ok_and_failed_collections(self):
        history_id = self.current_history_id()
        fetch_response = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"]
        ).json()
        hdca_id = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)["id"]
        collection_input = {"input1": {"src": "hdca", "id": hdca_id}}
        ok_response = self.dataset_populator.run_tool("collection_creates_list", collection_input, history_id)
        failed_response = self.dataset_populator.run_tool("collection_creates_list_fail", collection_input, history_id)
        ok_collection_hid = ok_response["output_collections"][0]["hid"]
        failed_collection_hid = failed_response["output_collections"][0]["hid"]
        return ok_collection_hid, failed_collection_hid
