import time

from base.api_asserts import assert_status_code_is
from base.populators import flakey

from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase
)


class HistoryPanelCollectionsTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_mapping_collection_states_terminal(self):
        history_id = self.current_history_id()
        input_collection, failed_collection = self._generate_partially_failed_collection_with_input()
        input_hid = input_collection["hid"]
        failed_hid = failed_collection["hid"]
        ok_inputs = {
            "input1": {'batch': True, 'values': [{"src": "hdca", "id": input_collection["id"]}]},
            "sleep_time": 0,
        }
        ok_response = self.dataset_populator.run_tool(
            "cat_data_and_sleep",
            ok_inputs,
            history_id,
            assert_ok=True,
        )
        ok_hid = ok_response["implicit_collections"][0]["hid"]
        # sleep really shouldn't be needed :(
        time.sleep(1)

        self.home()

        self.history_panel_wait_for_hid_state(input_hid, "ok")
        self.history_panel_wait_for_hid_state(failed_hid, "error")
        self.history_panel_wait_for_hid_state(ok_hid, "ok")
        self.screenshot("history_panel_collections_state_mapping_terminal")

    @selenium_test
    @flakey  # Some times a Paste web thread will stall when jobs are running.
    def test_mapping_collection_states_running(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1"]).json()
        running_inputs = {
            "input1": {'batch': True, 'values': [{"src": "hdca", "id": input_collection["id"]}]},
            "sleep_time": 60,
        }
        running_response = self.dataset_populator.run_tool(
            "cat_data_and_sleep",
            running_inputs,
            history_id,
            assert_ok=False,
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
        input_collection = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json()

        ok_inputs = {
            "input1": {"src": "hdca", "id": input_collection["id"]}
        }
        ok_response = self.dataset_populator.run_tool(
            "collection_creates_list",
            ok_inputs,
            history_id
        )
        ok_hid = ok_response["output_collections"][0]["hid"]

        failed_response = self.dataset_populator.run_tool(
            "collection_creates_dynamic_nested_fail",
            {},
            history_id,
        )
        failed_hid = failed_response["output_collections"][0]["hid"]

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
        running_response = self.dataset_populator.run_tool(
            "collection_creates_dynamic_nested",
            running_inputs,
            history_id,
            assert_ok=False,
        )
        try:
            assert_status_code_is(running_response, 200)
            running_hid = running_response.json()["output_collections"][0]["hid"]

            # sleep really shouldn't be needed :(
            time.sleep(1)

            self.home()
            self.history_panel_wait_for_hid_state(running_hid, "running")
            self.screenshot("history_panel_collections_state_running")
        finally:
            for job in running_response.json()["jobs"]:
                self.dataset_populator.cancel_job(job["id"])

    @selenium_test
    def test_collection_operations(self):
        # Test back and rename.
        input_collection = self._populated_paired_and_wait_for_it()
        collection_hid = input_collection["hid"]
        collection_view = self._click_and_wait_for_collection_view(collection_hid)

        collection_view.back.wait_for_and_click()
        self.history_panel_wait_for_hid_state(collection_hid, "ok")

        self._click_and_wait_for_collection_view(collection_hid)

        title_element = collection_view.title.wait_for_visible()
        assert title_element.text == input_collection["name"]
        title_element.click()
        title_rename_element = collection_view.title_input.wait_for_visible()
        self.screenshot("history_panel_collection_view_rename")
        title_rename_element.send_keys("My New Name")
        self.send_enter(title_rename_element)
        title_element = collection_view.title.wait_for_visible()
        assert title_element.text == "My New Name"

    @selenium_test
    def test_name_tags_display(self):
        # Test setting a name tag and viewing it from the outer history panel.
        input_collection = self._populated_paired_and_wait_for_it()
        collection_hid = input_collection["hid"]
        collection_view = self._click_and_wait_for_collection_view(collection_hid)

        self.tagging_add(["#moo"])

        self.screenshot("history_panel_collection_view_add_nametag")
        collection_view.back.wait_for_and_click()

        self.history_panel_wait_for_hid_state(collection_hid, "ok")
        nametags = self.history_panel_item_get_nametags(collection_hid)

        assert nametags == ["moo"]
        self.screenshot("history_panel_collection_with_nametag")

    @selenium_test
    def test_paired_display(self):
        input_collection = self._populated_paired_and_wait_for_it()
        collection_hid = input_collection["hid"]
        collection_view = self._click_and_wait_for_collection_view(collection_hid)

        dataset_elements = collection_view.list_items.all()
        assert len(dataset_elements) == 2, dataset_elements
        title_elements = [de.find_element_by_css_selector(".title .name").text for de in dataset_elements]
        assert title_elements == ["forward", "reverse"]
        self.screenshot("history_panel_collection_view_paired")

    @selenium_test
    @flakey  # Fails only in Jenkins full suite - possibly due to #3782.
    def test_list_display(self):
        _, failed_collection = self._generate_partially_failed_collection_with_input()
        failed_hid = failed_collection["hid"]
        self.home()
        self.history_panel_wait_for_hid_state(failed_hid, "error")
        collection_view = self._click_and_wait_for_collection_view(failed_hid)

        @retry_assertion_during_transitions
        def check_four_datasets_shown():
            dataset_elements = collection_view.list_items.all()
            assert len(dataset_elements) == 4, dataset_elements
            title_elements = [de.find_element_by_css_selector(".title .name").text for de in dataset_elements]
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
        self._click_and_wait_for_collection_view(collection_hid)
        self.screenshot("history_panel_collection_view_list_paired")

    @selenium_test
    def test_list_list_display(self):
        history_id = self.current_history_id()
        collection = self.dataset_collection_populator.create_list_of_list_in_history(history_id).json()
        collection_hid = collection["hid"]
        self.home()
        self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self._click_and_wait_for_collection_view(collection_hid)
        self.screenshot("history_panel_collection_view_list_list")

    @selenium_test
    def test_limiting_collection_rendering(self):
        history_id = self.current_history_id()
        collection = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json()
        collection_hid = collection["hid"]

        with self.local_storage("collectionFuzzyCountDefault", 2):
            self.home()

            self.history_panel_wait_for_hid_state(collection_hid, "ok")
            self._click_and_wait_for_collection_view(collection_hid)
            self.screenshot("history_panel_collection_view_limiting")
            warning_text = self.components.history_panel.collection_view.elements_warning.wait_for_text()
            assert "only 2 of 4 items" in warning_text, warning_text

    def _generate_partially_failed_collection_with_input(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json()
        failed_response = self.dataset_populator.run_exit_code_from_file(history_id, input_collection["id"])
        failed_collection = failed_response["implicit_collections"][0]
        return input_collection, failed_collection

    def _click_and_wait_for_collection_view(self, collection_hid):
        self.history_panel_click_item_title(collection_hid)

        collection_view = self.components.history_panel.collection_view
        collection_view._.wait_for_visible()
        return collection_view

    def _populated_paired_and_wait_for_it(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_pair_in_history(history_id).json()
        collection_hid = input_collection["hid"]
        self.home()
        self.history_panel_wait_for_hid_state(collection_hid, "ok")

        return input_collection
