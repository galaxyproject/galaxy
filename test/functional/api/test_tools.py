# Test tools API.
from itertools import chain
from json import dumps
import time

from base import api
from operator import itemgetter


class ToolsTestCase( api.ApiTestCase ):

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

    def _new_dataset( self, history_id, content='TestData123', **kwds ):
        payload = self._upload_payload( history_id, content, **kwds )
        run_response = self._post( "tools", data=payload )
        self._assert_status_code_is( run_response, 200 )
        return run_response.json()["outputs"][0]

    def _wait_for_history( self, history_id, assert_ok=False ):
        while True:
            history_details_response = self._get( "histories/%s" % history_id )
            self._assert_status_code_is( history_details_response, 200 )
            history_state = history_details_response.json()[ "state" ]
            if history_state not in [ "running", "queued" ]:
                break
            time.sleep( .1 )
        if assert_ok:
            self.assertEquals( history_state, 'ok' )

    def _new_history( self, **kwds ):
        name = kwds.get( "name", "API Test History" )
        create_history_response = self._post( "histories", data=dict( name=name ) )
        self._assert_status_code_is( create_history_response, 200 )
        history_id = create_history_response.json()[ "id" ]
        return history_id

    def _upload_payload( self, history_id, content, **kwds ):
        name = kwds.get( "name", "Test Dataset" )
        dbkey = kwds.get( "dbkey", "?" )
        file_type = kwds.get( "file_type", 'txt' )
        upload_params = {
            'files_0|NAME': name,
            'files_0|url_paste': content,
            'dbkey': dbkey,
            'file_type': file_type,
        }
        return self._run_tool_payload(
            tool_id='upload1',
            inputs=upload_params,
            history_id=history_id,
            upload_type='upload_dataset'
        )

    def _run_tool_payload( self, tool_id, inputs, history_id, **kwds ):
        return dict(
            tool_id=tool_id,
            inputs=dumps(inputs),
            history_id=history_id,
            **kwds
        )
