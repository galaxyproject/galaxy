import os
from StringIO import StringIO
from galaxy.tools.parameters import grouping
from galaxy.util import listify
from galaxy.util.odict import odict
import galaxy.model
from galaxy.model.orm import and_, desc
from functional import database_contexts
from json import dumps, loads

from logging import getLogger
log = getLogger( __name__ )

VERBOSE_ERRORS = False
ERROR_MESSAGE_DATASET_SEP = "--------------------------------------"


def build_interactor( test_case, type="api" ):
    interactor_class = GALAXY_INTERACTORS[ type ]
    return interactor_class( test_case )


def stage_data_in_history( galaxy_interactor, all_test_data, history, shed_tool_id=None ):
    # Upload any needed files
    upload_waits = []

    for test_data in all_test_data:
        upload_waits.append( galaxy_interactor.stage_data_async( test_data, history, shed_tool_id ) )
    for upload_wait in upload_waits:
        upload_wait()


class GalaxyInteractorApi( object ):

    def __init__( self, twill_test_case, test_user=None ):
        self.twill_test_case = twill_test_case
        self.api_url = "%s/api" % twill_test_case.url.rstrip("/")
        self.master_api_key = twill_test_case.master_api_key
        self.api_key = self.__get_user_key( twill_test_case.user_api_key, twill_test_case.master_api_key, test_user=test_user )
        self.uploads = {}

    def verify_output( self, history_id, output_data, outfile, attributes, shed_tool_id, maxseconds ):
        self.wait_for_history( history_id, maxseconds )
        hid = self.__output_id( output_data )
        fetcher = self.__dataset_fetcher( history_id )
        ## TODO: Twill version verifys dataset is 'ok' in here.
        self.twill_test_case.verify_hid( outfile, hda_id=hid, attributes=attributes, dataset_fetcher=fetcher, shed_tool_id=shed_tool_id )
        metadata = attributes.get( 'metadata', {} )
        if metadata:
            dataset = self._get( "histories/%s/contents/%s" % ( history_id, hid ) ).json()
            for key, value in metadata.iteritems():
                dataset_key = "metadata_%s" % key
                try:
                    dataset_value = dataset.get( dataset_key, None )
                    if dataset_value != value:
                        msg = "Dataset metadata verification for [%s] failed, expected [%s] but found [%s]."
                        msg_params = ( key, value, dataset_value )
                        msg = msg % msg_params
                        raise Exception( msg )
                except KeyError:
                    msg = "Failed to verify dataset metadata, metadata key [%s] was not found." % key
                    raise Exception( msg )

    def wait_for_history( self, history_id, maxseconds ):
        self.twill_test_case.wait_for( lambda: not self.__history_ready( history_id ), maxseconds=maxseconds)

    def get_job_stream( self, history_id, output_data, stream ):
        hid = self.__output_id( output_data )
        data = self._dataset_provenance( history_id, hid )
        return data.get( stream, '' )

    def new_history( self ):
        history_json = self._post( "histories", {"name": "test_history"} ).json()
        return history_json[ 'id' ]

    def __output_id( self, output_data ):
        # Allow data structure coming out of tools API - {id: <id>, output_name: <name>, etc...}
        # or simple id as comes out of workflow API.
        try:
            output_id = output_data.get( 'id' )
        except AttributeError:
            output_id = output_data
        return output_id

    def stage_data_async( self, test_data, history_id, shed_tool_id, async=True ):
        fname = test_data[ 'fname' ]
        tool_input = {
            "file_type": test_data[ 'ftype' ],
            "dbkey": test_data[ 'dbkey' ],
        }
        for elem in test_data.get('metadata', []):
            tool_input["files_metadata|%s" % elem.get( 'name' )] = elem.get( 'value' )

        composite_data = test_data[ 'composite_data' ]
        if composite_data:
            files = {}
            for i, composite_file in enumerate( composite_data ):
                file_name = self.twill_test_case.get_filename( composite_file.get( 'value' ), shed_tool_id=shed_tool_id )
                files["files_%s|file_data" % i] = open( file_name, 'rb' )
                tool_input.update({
                    #"files_%d|NAME" % i: name,
                    "files_%d|type" % i: "upload_dataset",
                    ## TODO:
                    #"files_%d|space_to_tab" % i: composite_file.get( 'space_to_tab', False )
                })
            name = test_data[ 'name' ]
        else:
            file_name = self.twill_test_case.get_filename( fname, shed_tool_id=shed_tool_id )
            name = test_data.get( 'name', None )
            if not name:
                name = os.path.basename( file_name )

            tool_input.update({
                "files_0|NAME": name,
                "files_0|type": "upload_dataset",
            })
            files = {
                "files_0|file_data": open( file_name, 'rb')
            }
        submit_response_object = self.__submit_tool( history_id, "upload1", tool_input, extra_data={"type": "upload_dataset"}, files=files )
        submit_response = submit_response_object.json()
        try:
            dataset = submit_response["outputs"][0]
        except KeyError:
            raise Exception(submit_response)
        #raise Exception(str(dataset))
        hid = dataset['id']
        self.uploads[ os.path.basename(fname) ] = self.uploads[ fname ] = self.uploads[ name ] = {"src": "hda", "id": hid}
        return self.__wait_for_history( history_id )

    def run_tool( self, testdef, history_id ):
        # We need to handle the case where we've uploaded a valid compressed file since the upload
        # tool will have uncompressed it on the fly.

        inputs_tree = testdef.inputs.copy()
        for key, value in inputs_tree.iteritems():
            values = [value] if not isinstance(value, list) else value
            new_values = []
            for value in values:
                if value in self.uploads:
                    new_values.append( self.uploads[ value ] )
                else:
                    new_values.append( value )
            inputs_tree[ key ] = new_values

        # # HACK: Flatten single-value lists. Required when using expand_grouping
        for key, value in inputs_tree.iteritems():
            if isinstance(value, list) and len(value) == 1:
                inputs_tree[key] = value[0]

        datasets = self.__submit_tool( history_id, tool_id=testdef.tool.id, tool_input=inputs_tree )
        datasets_object = datasets.json()
        try:
            return self.__dictify_outputs( datasets_object )
        except KeyError:
            raise Exception( datasets_object[ 'message' ] )

    def __dictify_outputs( self, datasets_object ):
        ## Convert outputs list to a dictionary that can be accessed by
        ## output_name so can be more flexiable about ordering of outputs
        ## but also allows fallback to legacy access as list mode.
        outputs_dict = odict()
        index = 0
        for output in datasets_object[ 'outputs' ]:
            outputs_dict[ index ] = outputs_dict[ output.get("output_name") ] = output
            index += 1
        return outputs_dict

    def output_hid( self, output_data ):
        return output_data[ 'id' ]

    def delete_history( self, history ):
        return None

    def __wait_for_history( self, history_id ):
        def wait():
            while not self.__history_ready( history_id ):
                pass
        return wait

    def __history_ready( self, history_id ):
        history_json = self._get( "histories/%s" % history_id ).json()
        state = history_json[ 'state' ]
        try:
            return self._state_ready( state, error_msg="History in error state." )
        except Exception:
            if VERBOSE_ERRORS:
                self._summarize_history_errors( history_id )
            raise

    def _summarize_history_errors( self, history_id ):
        print "History with id %s in error - summary of datasets in error below." % history_id
        try:
            history_contents = self.__contents( history_id )
        except Exception:
            print "*TEST FRAMEWORK FAILED TO FETCH HISTORY DETAILS*"

        for dataset in history_contents:
            if dataset[ 'state' ] != 'error':
                continue

            print ERROR_MESSAGE_DATASET_SEP
            dataset_id = dataset.get( 'id', None )
            print "| %d - %s (HID - NAME) " % ( int( dataset['hid'] ), dataset['name'] )
            try:
                dataset_info = self._dataset_info( history_id, dataset_id )
                print "| Dataset Blurb:"
                print self.format_for_error( dataset_info.get( "misc_blurb", "" ), "Dataset blurb was empty." )
                print "| Dataset Info:"
                print self.format_for_error( dataset_info.get( "misc_info", "" ), "Dataset info is empty." )
            except Exception:
                print "| *TEST FRAMEWORK ERROR FETCHING DATASET DETAILS*"
            try:
                provenance_info = self._dataset_provenance( history_id, dataset_id )
                print "| Dataset Job Standard Output:"
                print self.format_for_error( provenance_info.get( "stdout", "" ), "Standard output was empty." )
                print "| Dataset Job Standard Error:"
                print self.format_for_error( provenance_info.get( "stderr", "" ), "Standard error was empty." )
            except Exception:
                print "| *TEST FRAMEWORK ERROR FETCHING JOB DETAILS*"
            print "|"
        print ERROR_MESSAGE_DATASET_SEP

    def format_for_error( self, blob, empty_message, prefix="|  " ):
        contents = "\n".join([ "%s%s" % (prefix, line.strip()) for line in StringIO(blob).readlines() if line.rstrip("\n\r") ] )
        return contents or "%s*%s*" % ( prefix, empty_message )

    def _dataset_provenance( self, history_id, id ):
        provenance = self._get( "histories/%s/contents/%s/provenance" % ( history_id, id ) ).json()
        return provenance

    def _dataset_info( self, history_id, id ):
        dataset_json = self._get( "histories/%s/contents/%s" % ( history_id, id ) ).json()
        return dataset_json

    def __contents( self, history_id ):
        history_contents_json = self._get( "histories/%s/contents" % history_id ).json()
        return history_contents_json

    def _state_ready( self, state_str, error_msg ):
        if state_str == 'ok':
            return True
        elif state_str == 'error':
            raise Exception( error_msg )
        return False

    def __submit_tool( self, history_id, tool_id, tool_input, extra_data={}, files=None ):
        data = dict(
            history_id=history_id,
            tool_id=tool_id,
            inputs=dumps( tool_input ),
            **extra_data
        )
        return self._post( "tools", files=files, data=data )

    def ensure_user_with_email( self, email ):
        admin_key = self.master_api_key
        all_users = self._get( 'users', key=admin_key ).json()
        try:
            test_user = [ user for user in all_users if user["email"] == email ][0]
        except IndexError:
            data = dict(
                email=email,
                password='testuser',
                username='admin-user',
            )
            test_user = self._post( 'users', data, key=admin_key ).json()
        return test_user

    def __get_user_key( self, user_key, admin_key, test_user=None ):
        if not test_user:
            test_user = "test@bx.psu.edu"
        if user_key:
            return user_key
        test_user = self.ensure_user_with_email(test_user)
        return self._post( "users/%s/api_key" % test_user['id'], key=admin_key ).json()

    def __dataset_fetcher( self, history_id ):
        def fetcher( hda_id, base_name=None ):
            url = "histories/%s/contents/%s/display?raw=true" % (history_id, hda_id)
            if base_name:
                url += "&filename=%s" % base_name
            return self._get( url ).content

        return fetcher

    def _post( self, path, data={}, files=None, key=None, admin=False):
        if not key:
            key = self.api_key if not admin else self.master_api_key
        data = data.copy()
        data['key'] = key
        return post_request( "%s/%s" % (self.api_url, path), data=data, files=files )

    def _get( self, path, data={}, key=None, admin=False ):
        if not key:
            key = self.api_key if not admin else self.master_api_key
        data = data.copy()
        data['key'] = key
        if path.startswith("/api"):
            path = path[ len("/api"): ]
        url = "%s/%s" % (self.api_url, path)
        return get_request( url, params=data )


class GalaxyInteractorTwill( object ):

    def __init__( self, twill_test_case ):
        self.twill_test_case = twill_test_case

    def verify_output( self, history, output_data, outfile, attributes, shed_tool_id, maxseconds ):
        hid = output_data.get( 'hid' )
        self.twill_test_case.verify_dataset_correctness( outfile, hid=hid, attributes=attributes, shed_tool_id=shed_tool_id, maxseconds=maxseconds )

    def get_job_stream( self, history_id, output_data, stream ):
        return self.twill_test_case._get_job_stream_output( output_data.get( 'id' ), stream=stream, format=False )

    def stage_data_async( self, test_data, history, shed_tool_id, async=True ):
            name = test_data.get( 'name', None )
            if name:
                async = False
            self.twill_test_case.upload_file( test_data['fname'],
                                              ftype=test_data['ftype'],
                                              dbkey=test_data['dbkey'],
                                              metadata=test_data['metadata'],
                                              composite_data=test_data['composite_data'],
                                              shed_tool_id=shed_tool_id,
                                              wait=(not async) )
            if name:
                hda_id = self.twill_test_case.get_history_as_data_list()[-1].get( 'id' )
                try:
                    self.twill_test_case.edit_hda_attribute_info( hda_id=str(hda_id), new_name=name )
                except:
                    print "### call to edit_hda failed for hda_id %s, new_name=%s" % (hda_id, name)
            return lambda: self.twill_test_case.wait()

    def run_tool( self, testdef, test_history ):
        # We need to handle the case where we've uploaded a valid compressed file since the upload
        # tool will have uncompressed it on the fly.

        # Lose tons of information to accomodate legacy repeat handling.
        all_inputs = {}
        for key, value in testdef.inputs.iteritems():
            all_inputs[ key.split("|")[-1] ] = value

        # See if we have a grouping.Repeat element
        repeat_name = None
        for input_name, input_value in testdef.tool.inputs_by_page[0].items():
            if isinstance( input_value, grouping.Repeat ) and all_inputs.get( input_name, 1 ) not in [ 0, "0" ]:  # default behavior is to test 1 repeat, for backwards compatibility
                if not input_value.min:  # If input_value.min == 1, the element is already on the page don't add new element.
                    repeat_name = input_name
                break

        #check if we need to verify number of outputs created dynamically by tool
        if testdef.tool.force_history_refresh:
            job_finish_by_output_count = len( self.twill_test_case.get_history_as_data_list() )
        else:
            job_finish_by_output_count = False

        inputs_tree = testdef.inputs
        # # # HACK: Flatten single-value lists. Required when using expand_grouping
        # #for key, value in inputs_tree.iteritems():
        #    if isinstance(value, list) and len(value) == 1:
        #        inputs_tree[key] = value[0]

        # Strip out just a given page of inputs from inputs "tree".
        def filter_page_inputs( n ):
            page_input_keys = testdef.tool.inputs_by_page[ n ].keys()
            return dict( [ (k, v) for k, v in inputs_tree.iteritems() if k.split("|")[0] or k.split("|")[0].resplit("_", 1)[0] in page_input_keys ] )

        # Do the first page
        page_inputs = filter_page_inputs( 0 )

        # Run the tool
        self.twill_test_case.run_tool( testdef.tool.id, repeat_name=repeat_name, **page_inputs )
        print "page_inputs (0)", page_inputs
        # Do other pages if they exist
        for i in range( 1, testdef.tool.npages ):
            page_inputs = filter_page_inputs( i )
            self.twill_test_case.submit_form( **page_inputs )
            print "page_inputs (%i)" % i, page_inputs

        # Check the results ( handles single or multiple tool outputs ).  Make sure to pass the correct hid.
        # The output datasets from the tool should be in the same order as the testdef.outputs.
        data_list = None
        while data_list is None:
            data_list = self.twill_test_case.get_history_as_data_list()
            if job_finish_by_output_count and len( testdef.outputs ) > ( len( data_list ) - job_finish_by_output_count ):
                data_list = None
        return data_list

    def new_history( self ):
        # Start with a new history
        self.twill_test_case.logout()
        self.twill_test_case.login( email='test@bx.psu.edu' )
        admin_user = database_contexts.galaxy_context.query( galaxy.model.User ).filter( galaxy.model.User.table.c.email == 'test@bx.psu.edu' ).one()
        self.twill_test_case.new_history()
        latest_history = database_contexts.galaxy_context.query( galaxy.model.History ) \
                                   .filter( and_( galaxy.model.History.table.c.deleted == False,
                                                  galaxy.model.History.table.c.user_id == admin_user.id ) ) \
                                   .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                   .first()
        assert latest_history is not None, "Problem retrieving latest_history from database"
        if len( self.twill_test_case.get_history_as_data_list() ) > 0:
            raise AssertionError("ToolTestCase.do_it failed")
        return latest_history

    def delete_history( self, latest_history ):
        self.twill_test_case.delete_history( id=self.twill_test_case.security.encode_id( latest_history.id ) )

    def output_hid( self, output_data ):
        return output_data.get( 'hid' )


GALAXY_INTERACTORS = {
    'api': GalaxyInteractorApi,
    'twill': GalaxyInteractorTwill,
}


# Lets just try to use requests if it is available, but if not provide fallback
# on custom implementations of limited requests get, put, etc... functionality.
try:
    from requests import get as get_request
    from requests import post as post_request
    from requests import put as put_request
    from requests import delete as delete_request
except ImportError:
    import urllib2
    import httplib

    class RequestsLikeResponse( object ):

        def __init__( self, content, status_code ):
            self.content = content
            self.status_code = status_code

        def json( self ):
            return loads( self.content )

    def get_request( url, params={} ):
        argsep = '&'
        if '?' not in url:
            argsep = '?'
        param_pairs = []
        for key, value in params.iteritems():
            # Handle single parameters or lists and tuples of them.
            if isinstance( value, tuple ):
                value = list( value )
            elif not isinstance( value, list ):
                value = [ value ]
            for val in value:
                param_pairs.append( "%s=%s" % ( key, val ) )
        url = url + argsep + '&'.join( param_pairs )
        #req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' } )
        try:
            response = urllib2.urlopen( url )
            return RequestsLikeResponse( response.read(), status_code=response.getcode() )
        except urllib2.HTTPError as e:
            return RequestsLikeResponse( e.read(), status_code=e.code )

    def post_request( url, data, files={} ):
        return __multipart_request( url, data, files, verb="POST" )

    def put_request( url, data, files={} ):
        return __multipart_request( url, data, files, verb="PUT" )

    def delete_request( url ):
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(url)
        request.get_method = lambda: 'DELETE'
        try:
            response = opener.open(request)
            return RequestsLikeResponse( response.read(), status_code=response.getcode() )
        except urllib2.HTTPError as e:
            return RequestsLikeResponse( e.read(), status_code=e.code )

    def __multipart_request( url, data, files={}, verb="POST" ):
        parsed_url = urllib2.urlparse.urlparse( url )
        return __multipart( host=parsed_url.netloc, selector=parsed_url.path, fields=data.iteritems(), files=(files or {}).iteritems(), verb=verb )

    # http://stackoverflow.com/a/681182
    def __multipart(host, selector, fields, files, verb="POST"):
        h = httplib.HTTP(host)
        h.putrequest(verb, selector)
        content_type, body = __encode_multipart_formdata(fields, files)
        h.putheader('content-type', content_type)
        h.putheader('content-length', str(len(body)))
        h.endheaders()
        h.send(body)
        errcode, errmsg, headers = h.getreply()
        return RequestsLikeResponse(h.file.read(), status_code=errcode)

    def __encode_multipart_formdata(fields, files):
        LIMIT = '----------lImIt_of_THE_fIle_eW_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + LIMIT)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, value) in files:
            L.append('--' + LIMIT)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s";' % (key, key))
            L.append('Content-Type: application/octet-stream')
            L.append('')
            L.append(value.read())
        L.append('--' + LIMIT + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % LIMIT
        return content_type, body
