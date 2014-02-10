# Test tools API.
from itertools import chain

from base import api
from operator import itemgetter
from .helpers import TestsDatasets


class ToolsTestCase( api.ApiTestCase, TestsDatasets ):

    def test_index( self ):
        index = self._get( "tools" )
        tools_index = index.json()
        # In panels by default, so flatten out sections...
        tools = list( chain( *map( itemgetter( "elems" ), tools_index ) ) )
        tool_ids = map( itemgetter( "id" ), tools )
        assert "upload1" in tool_ids
        assert "cat1" in tool_ids

    def test_no_panel_index( self ):
        index = self._get( "tools", data=dict(in_panel="false") )
        tools_index = index.json()
        # No need to flatten out sections, with in_panel=False, only tools are
        # returned.
        tool_ids = map( itemgetter( "id" ), tools_index )
        assert "upload1" in tool_ids
        assert "cat1" in tool_ids

    def test_upload1_paste( self ):
        history_id = self._new_history()
        payload = self._upload_payload( history_id, 'Hello World' )
        create_response = self._post( "tools", data=payload )
        self._assert_has_keys( create_response.json(), 'outputs' )

    def test_upload_posix_newline_fixes( self ):
        windows_content = "1\t2\t3\r4\t5\t6\r"
        posix_content = windows_content.replace("\r", "\n")
        result_content = self._upload_and_get_content( windows_content )
        self.assertEquals( result_content, posix_content )

    def test_upload_disable_posix_fix( self ):
        windows_content = "1\t2\t3\r4\t5\t6\r"
        result_content = self._upload_and_get_content( windows_content, to_posix_lines=None )
        self.assertEquals( result_content, windows_content )

    def test_upload_tab_to_space( self ):
        table = "1 2 3\n4 5 6\n"
        result_content = self._upload_and_get_content( table, space_to_tab="Yes" )
        self.assertEquals( result_content, "1\t2\t3\n4\t5\t6\n" )

    def test_upload_tab_to_space_off_by_default( self ):
        table = "1 2 3\n4 5 6\n"
        result_content = self._upload_and_get_content( table )
        self.assertEquals( result_content, table )

    def test_run_cat1( self ):
        history_id = self._new_history()
        new_dataset = self._new_dataset( history_id )
        dataset_id = new_dataset[ 'id' ]
        payload = self._run_tool_payload(
            tool_id='cat1',
            inputs=dict(
                input1=dict(
                    src='hda',
                    id=dataset_id
                ),
            ),
            history_id=history_id,
        )
        create_response = self._post( "tools", data=payload )
        self._assert_status_code_is( create_response, 200 )
        self._assert_has_keys( create_response.json(), 'outputs' )
        self._wait_for_history( history_id, assert_ok=True )

    def _upload_and_get_content( self, content, **upload_kwds ):
        history_id = self._new_history()
        new_dataset = self._new_dataset( history_id, content=content, **upload_kwds )
        self._wait_for_history( history_id, assert_ok=True )
        display_response = self._get( "histories/%s/contents/%s/display" % ( history_id, new_dataset[ "id" ] ) )
        self._assert_status_code_is( display_response, 200 )
        return display_response.content
