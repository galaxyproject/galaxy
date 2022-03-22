"""Tests for the tool data API.

The tests for the DELETE endpoint can be found in the
integration tests directory (tests/integration/test_tool_data_delete.py)
since these tests can mutate the server config state.
"""

import operator

from ._framework import ApiTestCase


class ToolDataApiTestCase(ApiTestCase):
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
        assert len(files) == 2, f"Length of files [{files}] was not 2."

    def test_download_field_file(self):
        show_field_response = self._get("tool_data/testalpha/fields/data1/files/entry.txt", admin=True)
        self._assert_status_code_is(show_field_response, 200)
        content = show_field_response.text
        assert content == "This is data 1.", content

    def test_reload(self):
        show_response = self._get("tool_data/test_fasta_indexes/reload", admin=True)
        self._assert_status_code_is(show_response, 200)
        print(show_response.content)
        data_table = show_response.json()
        assert data_table["columns"] == ["value", "dbkey", "name", "path"]

    def test_show_unknown_raises_404(self):
        show_response = self._get("tool_data/unknown", admin=True)
        self._assert_status_code_is(show_response, 404)

    def test_show_unknown_field_raises_404(self):
        show_response = self._get("tool_data/testalpha/fields/unknown", admin=True)
        self._assert_status_code_is(show_response, 404)

    def test_reload_unknown_raises_404(self):
        show_response = self._get("tool_data/unknown/reload", admin=True)
        self._assert_status_code_is(show_response, 404)

    def test_download_field_unknown_file_raises_404(self):
        show_field_response = self._get("tool_data/testalpha/fields/data1/files/unknown.txt", admin=True)
        self._assert_status_code_is(show_field_response, 404)

    def test_delete_without_payload_raises_400(self):
        delete_response = self._delete("tool_data/testbeta", admin=True)
        self._assert_status_code_is(delete_response, 400)

    def test_delete_without_values_raises_400(self):
        payload = {"unknown": "test"}
        delete_response = self._delete("tool_data/testbeta", data=payload, admin=True)
        self._assert_status_code_is(delete_response, 400)

    def test_delete_with_wrong_values_raises_400(self):
        payload = {"values": "wrong"}
        delete_response = self._delete("tool_data/testbeta", data=payload, admin=True)
        self._assert_status_code_is(delete_response, 400)
