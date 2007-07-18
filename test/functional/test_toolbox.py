import sys
import new
from base.twilltestcase import TwillTestCase

toolbox = None

class ToolTestCase( TwillTestCase ):
    """
    Abstract test case that runs tests based on a `galaxy.tools.test.ToolTest`
    """
    def do_it( self ):
        # If the test generation had an error, raise
        if self.testdef.error:
            if self.testdef.exception:
                raise self.testdef.exception
            else:
                raise Exception( "Test parse failure" )
        # Start with an empty history
        self.clear_history()
        # Upload any needed files
        for fname, extra in self.testdef.required_files:
            self.upload_file( fname, ftype=extra.get( 'ftype', 'auto' ), dbkey=extra.get( 'dbkey', 'hg17' ) )
        # Run the tool
        all_inputs = dict( ( name, value ) for ( name, value, _ ) in self.testdef.inputs )
        # Do the first page
        page_inputs = dict( ( key, all_inputs[key] )
                            for key in self.testdef.tool.inputs_by_page[0].keys() )   
             
        self.run_tool( self.testdef.tool.id, **page_inputs )
        # Do other pages if they exist
        for i in range( 1, self.testdef.tool.npages ):
            
            page_inputs = dict()
            
            for key in self.testdef.tool.inputs_by_page[i].keys():
                try:
                    a_test_list = all_inputs[key].split(',')
                    if len(a_test_list) > 1:
                        page_inputs[key] = a_test_list
                    else:
                        page_inputs[key] = all_inputs[key]
                except:
                    page_inputs[key] = all_inputs[key]
            self.submit_form( **page_inputs )
        # Check the result
        assert len( self.testdef.outputs ) == 1, "ToolTestCase does not deal with multiple outputs properly yet."
        for name, file in self.testdef.outputs:
            self.check_data( file )
    def shortDescription( self ):
        return self.name

def get_testcase( testdef, name ):
    """
    Dynamically generate a `ToolTestCase` for `testdef`
    """
    n = "GeneratedToolTestCase_" + testdef.tool.id.replace( ' ', '_' )
    s = ( ToolTestCase, )
    def test_tool( self ):
        self.do_it()
    d = dict( testdef=testdef, test_tool=test_tool, name=name )
    return new.classobj( n, s, d )

def setup():
    """
    If the module level variable `toolbox` is set, generate `ToolTestCase`
    classes for all of its tests and put them into this modules globals() so
    they can be discovered by nose.
    """
    if toolbox is None:
        return
    # Push all the toolbox tests to module level
    G = globals()
    for i, section in enumerate( toolbox.sections ):
        for j, tool in enumerate( section.tools ):
            if tool.tests:
                for k, testdef in enumerate( tool.tests ):
                    name = "%s > %s > %s" % ( section.name, tool.name, testdef.name )
                    testcase = get_testcase( testdef, name )
                    G[ 'testcase_%d_%d_%d' % ( i, j, k ) ] = testcase
