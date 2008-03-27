import sys
import new
from base.twilltestcase import TwillTestCase

toolbox = None

class ToolTestCase( TwillTestCase ):
    """Abstract test case that runs tests based on a `galaxy.tools.test.ToolTest`"""
    def do_it( self ):
        # If the test generation had an error, raise
        if self.testdef.error:
            if self.testdef.exception:
                raise self.testdef.exception
            else:
                raise Exception( "Test parse failure" )
        # Start with a new history
        self.login()
        if len(self.get_history()) > 0:
            raise AssertionError("ToolTestCase.do_it failed")
        # Upload any needed files
        for fname, extra in self.testdef.required_files:
            self.upload_file( fname, ftype=extra.get( 'ftype', 'auto' ), dbkey=extra.get( 'dbkey', 'hg17' ) )
            print "Uploaded file: ", fname, ", ftype: ", extra.get( 'ftype', 'auto' ), ", extra: ", extra
        # We need to handle the case where we've uploaded a valid compressed file since the upload
        # tool will have decompressed it on the fly.
        all_inputs = {}
        for name, value, _ in self.testdef.inputs:
            if value:
                for end in [ '.zip', '.gz' ]:
                    if value.endswith( end ):
                        value = value.rstrip( end )
                        break
            all_inputs[ name ] = value

        # Do the first page
        page_inputs =  self.__expand_grouping(self.testdef.tool.inputs_by_page[0], all_inputs)
        # Run the tool
        self.run_tool( self.testdef.tool.id, **page_inputs )
        print "page_inputs (0)", page_inputs
        # Do other pages if they exist
        for i in range( 1, self.testdef.tool.npages ):
            page_inputs = self.__expand_grouping(self.testdef.tool.inputs_by_page[i], all_inputs)
            self.submit_form( **page_inputs )
            print "page_inputs (%i)" % i, page_inputs
        # Check the result
        assert len( self.testdef.outputs ) == 1, "ToolTestCase does not deal with multiple outputs properly yet."
        for name, file in self.testdef.outputs:
            self.verify_dataset_correctness( file )
        #Clean up
        self.delete_history()
        self.logout()
    def shortDescription( self ):
        return self.name

    def __expand_grouping(self, tool_inputs, declared_inputs ):
        from galaxy.tools.parameters import grouping
        expanded_inputs = {}
        for key, value in tool_inputs.items():
            if isinstance(value, grouping.Conditional):
                for i, case in enumerate(value.cases):
                    if declared_inputs[value.test_param.name] == case.value:
                        if isinstance(case.value, str):
                            expanded_inputs["%s|%s" % (value.name, value.test_param.name)] = case.value.split(",")
                        else:
                            expanded_inputs["%s|%s" % (value.name, value.test_param.name)] = case.value
                        for input_name, input_value in case.inputs.items():
                            if isinstance(input_value, grouping.Conditional):
                                expanded_inputs.update(self.__expand_grouping({input_name:input_value}), declared_inputs)
                            elif isinstance(declared_inputs[input_name], str):
                                expanded_inputs.update({"%s|%s" % (value.name, input_name):declared_inputs[input_name].split(",")})
                            else:
                                expanded_inputs.update({"%s|%s" % (value.name, input_name):declared_inputs[input_name]})
            elif isinstance(declared_inputs[value.name], str):
                expanded_inputs[value.name] = declared_inputs[value.name].split(",")
            else:
                expanded_inputs[value.name] = declared_inputs[value.name]
        return expanded_inputs

def get_testcase( testdef, name ):
    """Dynamically generate a `ToolTestCase` for `testdef`"""
    n = "TestForTool_" + testdef.tool.id.replace( ' ', '_' )
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
