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
    def do_it( self, testdef ):
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
            self.upload_file( fname, ftype=extra.get( 'ftype', 'auto' ), dbkey=extra.get( 'dbkey', 'hg17' ) )
            print "Uploaded file: ", fname, ", ftype: ", extra.get( 'ftype', 'auto' ), ", extra: ", extra
        # We need to handle the case where we've uploaded a valid compressed file since the upload
        # tool will have uncompressed it on the fly.
        all_inputs = {}
        for name, value, _ in testdef.inputs:
            if value:
                for end in [ '.zip', '.gz' ]:
                    if value.endswith( end ):
                        value = value.rstrip( end )
                        break
            all_inputs[ name ] = value
        # See if we have a grouping.Repeat element
        repeat_name = None
        for input_name, input_value in testdef.tool.inputs_by_page[0].items():
            if isinstance( input_value, grouping.Repeat ):
                repeat_name = input_name
                break
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
        # Check the result
        assert len( testdef.outputs ) == 1, "ToolTestCase does not deal with multiple outputs properly yet."
        for name, file in testdef.outputs:
            self.verify_dataset_correctness( file, maxseconds=testdef.maxseconds )
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

def build_tests():
    """
    If the module level variable `toolbox` is set, generate `ToolTestCase`
    classes for all of its tests and put them into this modules globals() so
    they can be discovered by nose.
    """
    if toolbox is None:
        return
    # Push all the toolbox tests to module level
    G = globals()
    for i, tool_id in enumerate( toolbox.tools_by_id ):
        tool = toolbox.tools_by_id[ tool_id ]
        if tool.tests:
            # Create a new subclass of ToolTestCase dynamically adding methods
            # names test_tool_XXX that run each test defined in the tool.
            n = "TestForTool_" + tool.id.replace( ' ', '_' )
            s = ( ToolTestCase, )
            d = dict()
            for j, testdef in enumerate( tool.tests ):
                def make_test_method( td ):
                    def test_tool( self ):
                        self.do_it( td )
                    return test_tool
                m = make_test_method( testdef )
                m.__doc__ = "%s ( %s ) > %s" % ( tool.name, tool.id, testdef.name )
                d['test_tool_%06d' % j] = m
            G[ n ] = new.classobj( n, s, d )
