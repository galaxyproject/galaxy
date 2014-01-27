import time
from json import dumps


class TestsDatasets:

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
        if "to_posix_lines" in kwds:
            upload_params[ "files_0|to_posix_lines"] = kwds[ "to_posix_lines" ]
        if "space_to_tab" in kwds:
            upload_params[ "files_0|space_to_tab" ] = kwds[ "space_to_tab" ]
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
