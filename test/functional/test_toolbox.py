import sys
import new
import os
from galaxy.tools.parameters import grouping
from galaxy.util import string_as_bool
from base.twilltestcase import TwillTestCase
import galaxy.model
from galaxy.model.orm import and_, desc
from galaxy.model.mapping import context as sa_session
from simplejson import dumps, loads

import logging
log = logging.getLogger( __name__ )

toolbox = None


class ToolTestCase( TwillTestCase ):
    """Abstract test case that runs tests based on a `galaxy.tools.test.ToolTest`"""

    def do_it( self, testdef ):
        """
        Run through a tool test case.
        """
        shed_tool_id = self.shed_tool_id

        self.__handle_test_def_errors( testdef )

        galaxy_interactor = self.__galaxy_interactor( testdef )

        test_history = galaxy_interactor.new_history()

        # Upload any needed files
        upload_waits = []
        for test_data in testdef.test_data():
            upload_waits.append( galaxy_interactor.stage_data_async( test_data, test_history, shed_tool_id ) )
        for upload_wait in upload_waits:
            upload_wait()

        data_list = galaxy_interactor.run_tool( testdef, test_history )
        self.assertTrue( data_list )

        self.__verify_outputs( testdef, test_history, shed_tool_id, data_list, galaxy_interactor )

        galaxy_interactor.delete_history( test_history )

    def __galaxy_interactor( self, testdef ):
        interactor_key = testdef.interactor
        interactor_class = GALAXY_INTERACTORS[ interactor_key ]
        return interactor_class( self )

    def __handle_test_def_errors(self, testdef):
        # If the test generation had an error, raise
        if testdef.error:
            if testdef.exception:
                raise testdef.exception
            else:
                raise Exception( "Test parse failure" )

    def __verify_outputs( self, testdef, history, shed_tool_id, data_list, galaxy_interactor ):
        maxseconds = testdef.maxseconds

        for output_index, output_tuple in enumerate(testdef.outputs):
            # Get the correct hid
            name, outfile, attributes = output_tuple
            try:
                output_data = data_list[ name ]
            except (TypeError, KeyError):
                # Legacy - fall back on ordered data list access if data_list is
                # just a list (case with twill variant)
                output_data = data_list[ len(data_list) - len(testdef.outputs) + output_index ]
            self.assertTrue( output_data is not None )
            try:
                galaxy_interactor.verify_output( history, output_data, outfile, attributes=attributes, shed_tool_id=shed_tool_id, maxseconds=maxseconds )
            except Exception:
                for stream in ['stdout', 'stderr']:
                    stream_output = galaxy_interactor.get_job_stream( history, output_data, stream=stream )
                    print >>sys.stderr, self._format_stream( stream_output, stream=stream, format=True )
                raise


class GalaxyInteractorApi( object ):

    def __init__( self, twill_test_case ):
        self.twill_test_case = twill_test_case
        self.api_url = "%s/api" % twill_test_case.url.rstrip("/")
        self.api_key = self.__get_user_key( twill_test_case.user_api_key, twill_test_case.master_api_key )
        self.uploads = {}

    def verify_output( self, history_id, output_data, outfile, attributes, shed_tool_id, maxseconds ):
        self.twill_test_case.wait_for( lambda: not self.__history_ready( history_id ), maxseconds=maxseconds)
        hid = output_data.get( 'id' )
        fetcher = self.__dataset_fetcher( history_id )
        ## TODO: Twill version verifys dataset is 'ok' in here.
        self.twill_test_case.verify_hid( outfile, hda_id=hid, attributes=attributes, dataset_fetcher=fetcher, shed_tool_id=shed_tool_id )
        metadata = attributes.get( 'metadata', {} )
        if metadata:
            dataset = self.__get( "histories/%s/contents/%s" % ( history_id, hid ) ).json()
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

    def get_job_stream( self, history_id, output_data, stream ):
        hid = output_data.get( 'id' )
        data = self.__get( "histories/%s/contents/%s/provenance" % (history_id, hid) ).json()
        return data.get( stream, '' )

    def new_history( self ):
        history_json = self.__post( "histories", {"name": "test_history"} ).json()
        return history_json[ 'id' ]

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
            for value in values:
                if value in self.uploads:
                    inputs_tree[ key ] = self.uploads[ value ]

        # # HACK: Flatten single-value lists. Required when using expand_grouping
        for key, value in inputs_tree.iteritems():
            if isinstance(value, list) and len(value) == 1:
                inputs_tree[key] = value[0]

        log.info( "Submiting tool with params %s" % inputs_tree )
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
        outputs_dict = {}
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
        history_json = self.__get( "histories/%s" % history_id ).json()
        state = history_json[ 'state' ]
        if state == 'ok':
            return True
        elif state == 'error':
            raise Exception("History in error state.")
        return False

    def __submit_tool( self, history_id, tool_id, tool_input, extra_data={}, files=None ):
        data = dict(
            history_id=history_id,
            tool_id=tool_id,
            inputs=dumps( tool_input ),
            **extra_data
        )
        return self.__post( "tools", files=files, data=data )

    def __get_user_key( self, user_key, admin_key ):
        if user_key:
            return user_key
        all_users = self.__get( 'users', key=admin_key ).json()
        try:
            test_user = [ user for user in all_users if user["email"] == 'test@bx.psu.edu' ][0]
        except IndexError:
            data = dict(
                email='test@bx.psu.edu',
                password='testuser',
                username='admin-user',
            )
            test_user = self.__post( 'users', data, key=admin_key ).json()
        return self.__post( "users/%s/api_key" % test_user['id'], key=admin_key ).json()

    def __dataset_fetcher( self, history_id ):
        def fetcher( hda_id, base_name=None ):
            url = "histories/%s/contents/%s/display?raw=true" % (history_id, hda_id)
            if base_name:
                url += "&filename=%s" % base_name
            return self.__get( url ).content

        return fetcher

    def __post( self, path, data={}, files=None, key=None):
        if not key:
            key = self.api_key
        data = data.copy()
        data['key'] = key
        return post_request( "%s/%s" % (self.api_url, path), data=data, files=files )

    def __get( self, path, data={}, key=None ):
        if not key:
            key = self.api_key
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
        admin_user = sa_session.query( galaxy.model.User ).filter( galaxy.model.User.table.c.email == 'test@bx.psu.edu' ).one()
        self.twill_test_case.new_history()
        latest_history = sa_session.query( galaxy.model.History ) \
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


def build_tests( testing_shed_tools=False, master_api_key=None, user_api_key=None ):
    """
    If the module level variable `toolbox` is set, generate `ToolTestCase`
    classes for all of its tests and put them into this modules globals() so
    they can be discovered by nose.
    """
    if toolbox is None:
        return

    # Push all the toolbox tests to module level
    G = globals()

    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith( 'TestForTool_' ):
            del G[ key ]

    for i, tool_id in enumerate( toolbox.tools_by_id ):
        tool = toolbox.get_tool( tool_id )
        if tool.tests:
            shed_tool_id = None if not testing_shed_tools else tool.id
            # Create a new subclass of ToolTestCase, dynamically adding methods
            # named test_tool_XXX that run each test defined in the tool config.
            name = "TestForTool_" + tool.id.replace( ' ', '_' )
            baseclasses = ( ToolTestCase, )
            namespace = dict()
            for j, testdef in enumerate( tool.tests ):
                def make_test_method( td ):
                    def test_tool( self ):
                        self.do_it( td )
                    return test_tool
                test_method = make_test_method( testdef )
                test_method.__doc__ = "%s ( %s ) > %s" % ( tool.name, tool.id, testdef.name )
                namespace[ 'test_tool_%06d' % j ] = test_method
                namespace[ 'shed_tool_id' ] = shed_tool_id
                namespace[ 'master_api_key' ] = master_api_key
                namespace[ 'user_api_key' ] = user_api_key
            # The new.classobj function returns a new class object, with name name, derived
            # from baseclasses (which should be a tuple of classes) and with namespace dict.
            new_class_obj = new.classobj( name, baseclasses, namespace )
            G[ name ] = new_class_obj


GALAXY_INTERACTORS = {
    'api': GalaxyInteractorApi,
    'twill': GalaxyInteractorTwill,
}


# Lets just try to use requests if it is available, but if not provide fallback
# on custom implementations of limited requests get/post functionality.
try:
    from requests import get as get_request
    from requests import post as post_request
except ImportError:
    import urllib2
    import httplib

    class RequestsLikeResponse( object ):

        def __init__( self, content ):
            self.content = content

        def json( self ):
            return loads( self.content )

    def get_request( url, params={} ):
        argsep = '&'
        if '?' not in url:
            argsep = '?'
        url = url + argsep + '&'.join( [ '%s=%s' % (k, v) for k, v in params.iteritems() ] )
        #req = urllib2.Request( url, headers = { 'Content-Type': 'application/json' } )
        return RequestsLikeResponse(urllib2.urlopen( url ).read() )

    def post_request( url, data, files ):
        parsed_url = urllib2.urlparse.urlparse( url )
        return __post_multipart( host=parsed_url.netloc, selector=parsed_url.path, fields=data.iteritems(), files=(files or {}).iteritems() )

    # http://stackoverflow.com/a/681182
    def __post_multipart(host, selector, fields, files):
        content_type, body = __encode_multipart_formdata(fields, files)
        h = httplib.HTTP(host)
        h.putrequest('POST', selector)
        h.putheader('content-type', content_type)
        h.putheader('content-length', str(len(body)))
        h.endheaders()
        h.send(body)
        errcode, errmsg, headers = h.getreply()
        return RequestsLikeResponse(h.file.read())

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
