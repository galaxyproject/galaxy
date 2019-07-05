""" Tests for the tool data API.
"""
from __future__ import print_function

import operator

from base import api


class ToolDataApiTestCase(api.ApiTestCase):

    def test_admin_only(self):
        index_response = self._get("tool_data", admin=False)
        self._assert_status_code_is(index_response, 403)

    def test_list(self):
        index_response = self._get("tool_data", admin=True)
        self._assert_status_code_is(index_response, 200)
        print(index_response.content)
        index = index_response.json()
        assert "testalpha" in [operator.itemgetter("name")(_) for _ in index]

    def test_show(self):
        show_response = self._get("tool_data/testalpha", admin=True)
        self._assert_status_code_is(show_response, 200)
        print(show_response.content)
        data_table = show_response.json()
        assert data_table["columns"] == ["value", "name", "path"]
        first_entry = data_table["fields"][0]
        assert first_entry[0] == "data1"
        assert first_entry[1] == "data1name"
        assert first_entry[2].endswith("test/functional/tool-data/data1/entry.txt")

    def test_show_field(self):
        show_field_response = self._get("tool_data/testalpha/fields/data1", admin=True)
        self._assert_status_code_is(show_field_response, 200)
        field = show_field_response.json()
        self._assert_has_keys(field, "files", "name", "fields", "fingerprint", "base_dir")
        files = field["files"]
        assert len(files) == 2, "Length of files [%s] was not 2." % files

    def test_download_field_file(self):
        show_field_response = self._get("tool_data/testalpha/fields/data1/files/entry.txt", admin=True)
        self._assert_status_code_is(show_field_response, 200)
        content = show_field_response.text
        assert content == "This is data 1.", content

    # Following test case rendered invalid by the fix in
    # https://github.com/galaxyproject/galaxy/commit/48f77dc742acf01ddbafafcc4634e69378f1f020#diff-bfb557a99c1f7d646d4968d8d680b885R154.
    # TODO: Restore the test case when test framework allows actions from
    # admin users.

    # def test_delete_entry(self):
    #     show_response = self._get( "tool_data/testbeta", admin=True )
    #     original_count = len(show_response.json()["fields"])

    #     dataset_populator = DatasetPopulator( self.galaxy_interactor )
    #     history_id = dataset_populator.new_history()
    #     payload = dataset_populator.run_tool_payload(
    #         tool_id="data_manager",
    #         inputs={"ignored_value": "moo"},
    #         history_id=history_id,
    #     )
    #     create_response = self._post( "tools", data=payload )
    #     self._assert_status_code_is( create_response, 200 )
    #     dataset_populator.wait_for_history( history_id, assert_ok=True )
    #     show_response = self._get( "tool_data/testbeta", admin=True )
    #     updated_fields = show_response.json()["fields"]
    #     assert len(updated_fields) == original_count + 1
    #     field0 = updated_fields[0]
    #     url = self._api_url( "tool_data/testbeta?key=%s" % self.galaxy_interactor.master_api_key )
    #     delete( url, data=json.dumps({"values": "\t".join(field0)}) )

    #     show_response = self._get( "tool_data/testbeta", admin=True )
    #     updated_fields = show_response.json()["fields"]
    #     assert len(updated_fields) == original_count
