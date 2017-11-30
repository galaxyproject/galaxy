import time

from base.api_asserts import assert_status_code_is
from base.populators import flakey

from .framework import (
    selenium_test,
    SeleniumTestCase
)


class HistoryPanelCollectionsTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_mapping_collection_states_terminal(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json()
        input_hid = input_collection["hid"]

        failed_response = self.dataset_populator.run_exit_code_from_file(history_id, input_collection["id"])
        failed_hid = failed_response["implicit_collections"][0]["hid"]

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

            self.history_panel_wait_for_hid_state(running_hid, "running")
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
