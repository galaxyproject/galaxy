""" Tests for the tool data API.
"""
from base import api

import operator


class ToolDataApiTestCase( api.ApiTestCase ):

    def test_admin_only( self ):
        index_response = self._get( "tool_data", admin=False )
        self._assert_status_code_is( index_response, 403 )

    def test_list(self):
        index_response = self._get( "tool_data", admin=True )
        self._assert_status_code_is( index_response, 200 )
        print index_response.content
        index = index_response.json()
        assert "testalpha" in map(operator.itemgetter("name"), index)

    def test_show(self):
        show_response = self._get( "tool_data/testalpha", admin=True )
        self._assert_status_code_is( show_response, 200 )
        print show_response.content
        data_table = show_response.json()
        assert data_table["columns"] == ["value", "name", "path"]
        first_entry = data_table["fields"][0]
        assert first_entry[0] == "data1"
        assert first_entry[1] == "data1name"
        assert first_entry[2].endswith("test/functional/tool-data/data1/entry.txt")
