import sys, new
from galaxy.tools.parameters import grouping
from galaxy.tools.parameters import basic
from base.twilltestcase import TwillTestCase
import galaxy.model
from galaxy.model.orm import *
from galaxy.model.mapping import context as sa_session

toolbox = None

class ToolTestCase( TwillTestCase ):
    """Abstract test case that runs tests based on a `galaxy.tools.test.ToolTest`"""
    def do_it( self, testdef, shed_tool_id=None ):
        # If the test generation had an error, raise
        if testdef.error:
            if testdef.exception:
                raise testdef.exception
            else:
                raise Exception( "Test parse failure" )
        # Start with a new history
        self.logout()
        self.login( email='test@bx.psu.edu' )
        admin_user = sa_session.query( galaxy.model.User ).filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).one()
        self.new_history()
        latest_history = sa_session.query( galaxy.model.History ) \
                                   .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                  galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                                   .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                   .first()
        assert latest_history is not None, "Problem retrieving latest_history from database"
        if len( self.get_history_as_data_list() ) > 0:
            raise AssertionError("ToolTestCase.do_it failed")
        # Upload any needed files
        for fname, extra in testdef.required_files:
            children = extra.get( 'children', [] )
            metadata = extra.get( 'metadata', [] )
            composite_data = extra.get( 'composite_data', [] )
            self.upload_file( fname,
                              ftype=extra.get( 'ftype', 'auto' ),
                              dbkey=extra.get( 'dbkey', 'hg17' ),
                              metadata=metadata,
                              composite_data=composite_data,
                              shed_tool_id=shed_tool_id )
            print "Uploaded file: ", fname, ", ftype: ", extra.get( 'ftype', 'auto' ), ", extra: ", extra
            #Post upload attribute editing
            edit_attributes = extra.get( 'edit_attributes', [] )
            #currently only renaming is supported
            for edit_att in edit_attributes:
                if edit_att.get( 'type', None ) == 'name':
                    new_name = edit_att.get( 'value', None )
                    assert new_name, 'You must supply the new dataset name as the value tag of the edit_attributes tag'
                    hda_id = self.get_history_as_data_list()[-1].get( 'id' )
                    try:
                        self.edit_hda_attribute_info( hda_id = str(hda_id), new_name = new_name )
                    except:
                        print "### call to edit_hda failed for hda_id %s, new_name=%s" % (hda_id,new_name)
                else:
                    raise Exception( 'edit_attributes type (%s) is unimplemented' % edit_att.get( 'type', None ) )
        # We need to handle the case where we've uploaded a valid compressed file since the upload
        # tool will have uncompressed it on the fly.
        all_inputs = {}
        for name, value, _ in testdef.inputs:
            all_inputs[ name ] = value
        # See if we have a grouping.Repeat element
        repeat_name = None
        for input_name, input_value in testdef.tool.inputs_by_page[0].items():
            if isinstance( input_value, grouping.Repeat ) and all_inputs.get( input_name, 1 ) not in [ 0, "0" ]: #default behavior is to test 1 repeat, for backwards compatibility
                repeat_name = input_name
                break
        #check if we need to verify number of outputs created dynamically by tool
        if testdef.tool.force_history_refresh:
            job_finish_by_output_count = len( self.get_history_as_data_list() )
        else:
            job_finish_by_output_count = False
        # Do the first page
        page_inputs =  self.__expand_grouping(testdef.tool.inputs_by_page[0], all_inputs)
        # Run the tool
        self.run_tool( testdef.tool.id, repeat_name=repeat_name, **page_inputs )
        print "page_inputs (0)", page_inputs
        # Do other pages if they exist
        for i in range( 1, testdef.tool.npages ):
            page_inputs = self.__expand_grouping(testdef.tool.inputs_by_page[i], all_inputs)
            self.submit_form( **page_inputs )
            print "page_inputs (%i)" % i, page_inputs
        # Check the results ( handles single or multiple tool outputs ).  Make sure to pass the correct hid.
        # The output datasets from the tool should be in the same order as the testdef.outputs.
        data_list = None
        while data_list is None:
            data_list = self.get_history_as_data_list()
            if job_finish_by_output_count and len( testdef.outputs ) > ( len( data_list ) - job_finish_by_output_count ):
                data_list = None
        self.assertTrue( data_list )
        elem_index = 0 - len( testdef.outputs )
        for output_tuple in testdef.outputs:
            name, outfile, attributes = output_tuple
            # Get the correct hid
            elem = data_list[ elem_index ]
            self.assertTrue( elem is not None )
            elem_hid = elem.get( 'hid' )
            elem_index += 1
            try:
                self.verify_dataset_correctness( outfile, hid=elem_hid, maxseconds=testdef.maxseconds, attributes=attributes, shed_tool_id=shed_tool_id )
            except Exception, e:
                print >>sys.stderr, self.get_job_stdout( elem.get( 'id' ), format=True )
                print >>sys.stderr, self.get_job_stderr( elem.get( 'id' ), format=True )
                raise
        self.delete_history( id=self.security.encode_id( latest_history.id ) )

    def __expand_grouping( self, tool_inputs, declared_inputs, prefix='' ):
        expanded_inputs = {}
        for key, value in tool_inputs.items():
            if isinstance( value, grouping.Conditional ):
                if prefix:
                    new_prefix = "%s|%s" % ( prefix, value.name )
                else:
                    new_prefix = value.name
                for i, case in enumerate( value.cases ):
                    if declared_inputs[ value.test_param.name ] == case.value:
                        if isinstance(case.value, str):
                            expanded_inputs[ "%s|%s" % ( new_prefix, value.test_param.name ) ] = case.value.split( "," )
                        else:
                            expanded_inputs[ "%s|%s" % ( new_prefix, value.test_param.name ) ] = case.value
                        for input_name, input_value in case.inputs.items():
                            expanded_inputs.update( self.__expand_grouping( { input_name:input_value }, declared_inputs, prefix = new_prefix ) )
            elif isinstance( value, grouping.Repeat ):
                for repeat_index in xrange( 0, 1 ): #need to allow for and figure out how many repeats we have
                    for r_name, r_value in value.inputs.iteritems():
	                    new_prefix = "%s_%d" % ( value.name, repeat_index )
	                    if prefix:
	                        new_prefix = "%s|%s" % ( prefix, new_prefix )
	                    expanded_inputs.update( self.__expand_grouping( { new_prefix : r_value }, declared_inputs, prefix = new_prefix ) )
            elif value.name not in declared_inputs:
                print "%s not declared in tool test, will not change default value." % value.name
            elif isinstance(declared_inputs[value.name], str):
                if prefix:
                    expanded_inputs["%s|%s" % ( prefix, value.name ) ] = declared_inputs[value.name].split(",")
                else:
                    expanded_inputs[value.name] = declared_inputs[value.name].split(",")
            else:
                if prefix:
                    expanded_inputs["%s|%s" % ( prefix, value.name ) ] = declared_inputs[value.name]
                else:
                    expanded_inputs[value.name] = declared_inputs[value.name]
        return expanded_inputs

def build_tests( testing_shed_tools=False ):
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
            # Create a new subclass of ToolTestCase, dynamically adding methods
            # named test_tool_XXX that run each test defined in the tool config.
            name = "TestForTool_" + tool.id.replace( ' ', '_' )
            baseclasses = ( ToolTestCase, )
            namespace = dict()
            for j, testdef in enumerate( tool.tests ):
                def make_test_method( td, shed_tool_id=None ):
                    def test_tool( self ):
                        self.do_it( td, shed_tool_id=shed_tool_id )
                    return test_tool
                if testing_shed_tools:
                    test_method = make_test_method( testdef, shed_tool_id=tool.id )
                else:
                    test_method = make_test_method( testdef )
                test_method.__doc__ = "%s ( %s ) > %s" % ( tool.name, tool.id, testdef.name )
                namespace[ 'test_tool_%06d' % j ] = test_method
            # The new.classobj function returns a new class object, with name name, derived
            # from baseclasses (which should be a tuple of classes) and with namespace dict.
            new_class_obj = new.classobj( name, baseclasses, namespace )
            G[ name ] = new_class_obj
